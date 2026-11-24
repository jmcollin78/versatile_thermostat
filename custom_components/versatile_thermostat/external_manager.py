"""Collection and hook facade for feature managers provided by external plugins."""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
from typing import TYPE_CHECKING

from vtherm_api import (
    UNDERLYING_HOOK_TIMEOUT_SEC,
    CalibrationOffsetRequest,
    UnderlyingPowerCommand,
    ValveCommand,
    ValveWriteDecision,
    ValveWriteRequest,
)
from vtherm_api.log_collector import get_vtherm_logger

from .base_manager import BaseFeatureManager
from .commons import is_finite_number, round_to_nearest
from .commons_type import ConfigData
from .vtherm_central_api import VersatileThermostatAPI

if TYPE_CHECKING:
    from .base_thermostat import BaseThermostat
    from .vtherm_hvac_mode import VThermHvacMode

_LOGGER = get_vtherm_logger(__name__)


class ExternalManager:
    """Holds the external feature managers of a thermostat and loads them."""

    def __init__(self, vtherm: "BaseThermostat"):
        self._vtherm = vtherm
        self._managers: list[BaseFeatureManager] = []
        self._manager_names: set[str] = set()

    # --- Collection protocol ---
    def __iter__(self):
        return iter(self._managers)

    def __len__(self) -> int:
        return len(self._managers)

    def __bool__(self) -> bool:
        return bool(self._managers)

    def __eq__(self, other) -> bool:
        if isinstance(other, ExternalManager):
            return self._managers == other._managers
        if isinstance(other, (list, tuple)):
            return self._managers == list(other)
        return NotImplemented

    __hash__ = None  # mutable collection, like list

    def has_manager(self, name: str) -> bool:
        """True if a manager from the factory `name` has been loaded."""
        return name in self._manager_names

    # --- Loading ---
    def load_feature_managers(self, entry_infos: ConfigData) -> list[BaseFeatureManager]:
        """Instantiate feature managers provided by external plugins.

        Returns the newly created (and post_init-ed) managers. The caller is
        responsible for registering them with the thermostat lifecycle.
        """
        new_managers: list[BaseFeatureManager] = []

        api = VersatileThermostatAPI.get_vtherm_api(self._vtherm.hass)
        if api is None or not hasattr(api, "get_feature_manager_factories"):
            _LOGGER.debug(
                "%s - external feature managers not loaded: api=%s, has get_feature_manager_factories=%s",
                self._vtherm,
                api is not None,
                hasattr(api, "get_feature_manager_factories"),
            )
            return new_managers

        for factory in api.get_feature_manager_factories():
            name = factory.name
            if name in self._manager_names:
                _LOGGER.debug("%s - external feature manager '%s' already loaded", self._vtherm, name)
                continue
            try:
                if not factory.supports(self._vtherm):
                    _LOGGER.debug("%s - external feature manager '%s' not created: supports() returned False", self._vtherm, name)
                    continue
                manager = factory.create(self._vtherm)
                manager.post_init(entry_infos)
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error(
                    "%s - Error while creating external feature manager '%s': %s",
                    self._vtherm,
                    name,
                    exc,
                )
                continue

            self._managers.append(manager)
            self._manager_names.add(name)
            new_managers.append(manager)
            _LOGGER.info("%s - Registered external feature manager '%s'", self._vtherm, name)

        return new_managers

    def _is_configured(self, manager) -> bool:
        """Read is_configured of an external manager. A failing manager is considered not configured."""
        try:
            return bool(manager.is_configured)
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error(
                "%s - Error while reading is_configured of external feature manager '%s': %s",
                self._vtherm,
                getattr(manager, "name", None),
                exc,
            )
            return False

    def _configured_managers(self, method_name: str) -> list:
        """The configured external feature managers which implement a method, in the order they were registered"""
        managers = []
        for manager in self._managers:
            if not hasattr(manager, method_name):
                continue
            if self._is_configured(manager):
                managers.append(manager)
        return managers

    async def _call_hook(self, method_name: str, *args) -> None:
        """Call an optional hook on each configured external feature manager.

        A failing or slow plugin is logged and never blocks the core command.
        """
        for manager in self._managers:
            hook = getattr(manager, method_name, None)
            if hook is None:
                _LOGGER.debug("%s - external hook %s skipped for '%s': the manager has no such hook", self._vtherm, method_name, manager.name)
                continue
            if not self._is_configured(manager):
                _LOGGER.debug("%s - external hook %s skipped for '%s': is_configured is False", self._vtherm, method_name, manager.name)
                continue
            _LOGGER.debug("%s - calling external hook %s of '%s'", self._vtherm, method_name, manager.name)
            try:
                async with asyncio.timeout(UNDERLYING_HOOK_TIMEOUT_SEC):
                    await hook(*args)
            except TimeoutError:
                _LOGGER.warning(
                    "%s - External feature manager '%s' timed out in %s",
                    self._vtherm,
                    manager.name,
                    method_name,
                )
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error(
                    "%s - Error in %s of external feature manager '%s': %s",
                    self._vtherm,
                    method_name,
                    manager.name,
                    exc,
                )

    # --- Hooks ---
    async def async_before_underlying_hvac_mode(
        self,
        climate_entity_id: str,
        hvac_mode: "VThermHvacMode | str",
        current_hvac_mode: "VThermHvacMode | str | None",
        command_cause: str | None = None,
    ) -> None:
        """Notify external managers that an underlying climate is about to change its HVAC mode."""
        if not self._managers:
            return
        await self._call_hook(
            "async_before_underlying_hvac_mode",
            climate_entity_id,
            str(hvac_mode),
            None if current_hvac_mode is None else str(current_hvac_mode),
            command_cause,
        )

    async def async_before_valve_write(self, request: ValveWriteRequest) -> tuple[int, bool, float | None]:
        """Let the external feature managers change the opening degree before it is written, or write the valve themselves.

        Returns the final opening degree, True when a plugin writes the valve itself (the core writes nothing) and the time
        the core must wait before repairing the valve (None for the default one). Each manager receives the value left by
        the previous one. A manager which fails, times out or returns an invalid value is logged and ignored.
        """
        opening_degree = request.opening_degree
        if not self._managers:
            return opening_degree, False, None

        vtherm = self._vtherm
        handled = False
        settle_sec: float | None = None
        for manager in self._configured_managers("async_before_valve_write"):
            _LOGGER.debug("%s - calling external hook async_before_valve_write of '%s' with opening_degree=%s", vtherm, manager.name, opening_degree)
            try:
                async with asyncio.timeout(UNDERLYING_HOOK_TIMEOUT_SEC):
                    decision = await manager.async_before_valve_write(dataclasses.replace(request, opening_degree=opening_degree))
            except TimeoutError:
                _LOGGER.warning("%s - External feature manager '%s' timed out in async_before_valve_write", vtherm, manager.name)
                continue
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("%s - Error in async_before_valve_write of external feature manager '%s': %s", vtherm, manager.name, exc)
                continue

            if decision is None:
                continue
            if not isinstance(decision, ValveWriteDecision):
                _LOGGER.warning("%s - External feature manager '%s' returned an invalid valve write decision (%s). It is ignored", vtherm, manager.name, decision)
                continue

            if decision.opening_degree is not None:
                if is_finite_number(decision.opening_degree):
                    opening_degree = int(min(max(round(decision.opening_degree), 0), request.max_opening_degree))
                else:
                    _LOGGER.warning("%s - External feature manager '%s' returned an invalid opening degree (%s). It is ignored", vtherm, manager.name, decision.opening_degree)

            if decision.settle_sec is not None:
                if is_finite_number(decision.settle_sec) and decision.settle_sec >= 0:
                    settle_sec = decision.settle_sec if settle_sec is None else max(settle_sec, decision.settle_sec)
                else:
                    _LOGGER.warning("%s - External feature manager '%s' returned an invalid settle_sec (%s). It is ignored", vtherm, manager.name, decision.settle_sec)

            if decision.handled:
                _LOGGER.debug("%s - external feature manager '%s' writes the valve itself", vtherm, manager.name)
                handled = True
                break

        return opening_degree, handled, settle_sec

    def adjust_calibration_offset(self, request: CalibrationOffsetRequest) -> float:
        """Let the external feature managers adjust the calibration offset. Each one receives the value left by the previous one.
        When a manager changed it, the result is rounded to the step and clamped to min..max. A manager which fails or returns an
        invalid value is logged and ignored."""
        if not self._managers:
            return request.offset

        offset = request.offset
        for manager in self._configured_managers("adjust_calibration_offset"):
            try:
                adjusted = manager.adjust_calibration_offset(dataclasses.replace(request, offset=offset))
            except Exception as exc:  # pylint: disable=broad-except
                _LOGGER.error("%s - Error while adjusting the calibration offset with external feature manager '%s': %s", self._vtherm, manager.name, exc)
                continue
            if adjusted is None:
                continue
            if inspect.iscoroutine(adjusted):
                # The method must not be a coroutine: close it to avoid a "never awaited" warning
                adjusted.close()
            if not is_finite_number(adjusted):
                _LOGGER.warning("%s - External feature manager '%s' returned an invalid calibration offset (%s). It is ignored", self._vtherm, manager.name, adjusted)
                continue
            offset = adjusted

        if offset != request.offset:
            offset = min(request.max_offset, max(request.min_offset, round_to_nearest(offset, request.step)))
        return offset

    async def async_after_valve_command(self, command: ValveCommand) -> None:
        """Notify external managers that a valve command was sent to a valve-regulation underlying."""
        if not self._managers:
            return
        await self._call_hook("async_after_valve_command", command)

    async def async_on_underlying_power(self, command: UnderlyingPowerCommand) -> None:
        """Notify external managers of the power requested from and applied to an underlying."""
        if not self._managers:
            return
        await self._call_hook("async_on_underlying_power", command)
