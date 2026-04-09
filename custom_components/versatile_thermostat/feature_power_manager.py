""" Implements the Power Feature Manager """

# pylint: disable=line-too-long

from typing import Any

from homeassistant.const import (
    STATE_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from homeassistant.core import (
    HomeAssistant,
)

from .log_collector import get_vtherm_logger
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import write_event_log, round_to_nearest
from .commons_type import ConfigData

from .base_manager import BaseFeatureManager
from .vtherm_api import VersatileThermostatAPI

_LOGGER = get_vtherm_logger(__name__)


class FeaturePowerManager(BaseFeatureManager):
    """The implementation of the Power feature"""

    unrecorded_attributes = frozenset(
        {
            "power_sensor_entity_id",
            "max_power_sensor_entity_id",
            "is_power_configured",
            "device_power",
            "power_temp",
            "current_power",
            "current_max_power",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a featureManager"""
        super().__init__(vtherm, hass)
        self._power_temp: float | None = None
        self._overpowering_state: str | None = None
        self._is_configured: bool = False
        self._device_power: float = 0
        self._use_power_feature: bool = False

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""

        # Power management
        self._power_temp = entry_infos.get(CONF_PRESET_POWER)

        self._device_power = entry_infos.get(CONF_DEVICE_POWER) or 0
        self._use_power_feature = entry_infos.get(CONF_USE_POWER_FEATURE, False)
        self._is_configured = False

    @overrides
    async def start_listening(self):
        """Start listening the underlying entity. There is nothing to listen"""
        central_power_configuration = (
            VersatileThermostatAPI.get_vtherm_api().central_power_manager.is_configured
        )

        if self._use_power_feature and self._device_power and central_power_configuration:
            self._is_configured = True
            # Try to restore _overpowering_state from previous state
            old_state = await self._vtherm.async_get_last_state()
            self._overpowering_state = (
                STATE_ON if old_state is not None and hasattr(old_state, "attributes") and old_state.attributes.get("overpowering_state") == STATE_ON else STATE_UNKNOWN
            )
        else:
            if self._use_power_feature:
                if not central_power_configuration:
                    _LOGGER.warning(
                        "%s - Power management is not fully configured. You have to configure the central configuration power",
                        self,
                    )
                else:
                    _LOGGER.warning(
                        "%s - Power management is not fully configured. You have to configure the power feature of the VTherm",
                        self,
                    )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add some custom attributes"""
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        extra_state_attributes.update(
            {
                "is_power_configured": self.is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "power_manager": {
                        "power_sensor_entity_id": vtherm_api.central_power_manager.power_sensor_entity_id,
                        "max_power_sensor_entity_id": vtherm_api.central_power_manager.max_power_sensor_entity_id,
                        "overpowering_state": self.overpowering_state,
                        "device_power": self._device_power,
                        "power_temp": self._power_temp,
                        "current_power": vtherm_api.central_power_manager.current_power,
                        "current_max_power": vtherm_api.central_power_manager.current_max_power,
                        "mean_cycle_power": self.mean_cycle_power,
                    }
                }
            )
        else:
            extra_state_attributes.update(
                {
                    "power_manager": {
                        "device_power": self._device_power,
                        "mean_cycle_power": self.mean_cycle_power,
                    }
                }
            )

    async def check_power_available(
        self, reservation_key: str | None = None
    ) -> tuple[bool, float]:
        """Check if the Vtherm can be started considering overpowering.
        Returns True if no overpowering conditions are found.
        If True the vtherm power is written into the temporay vtherm started
        """

        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if (
            not self._is_configured
            or not vtherm_api.central_power_manager.is_configured
        ):
            return True, 0

        effective_reservation_key = reservation_key or self._default_power_reservation_key
        current_power = vtherm_api.central_power_manager.current_power
        current_max_power = vtherm_api.central_power_manager.current_max_power
        started_vtherm_total_power = vtherm_api.central_power_manager.started_vtherm_total_power
        current_started_power = vtherm_api.central_power_manager.get_started_vtherm_power(
            effective_reservation_key
        )
        if (
            current_power is None
            or current_max_power is None
            or self._device_power is None
        ):
            _LOGGER.warning(
                "%s - power not valued. check_power_available not available", self
            )
            return True, 0

        _LOGGER.debug(
            "%s - overpowering check: power=%.3f, max_power=%.3f heater power=%.3f",
            self,
            current_power,
            current_max_power,
            self._device_power,
        )

        startup_power = self.calculate_underlying_startup_power()

        ret = (
            current_power
            + started_vtherm_total_power
            - current_started_power
            + startup_power
        ) < current_max_power
        if not ret:
            _LOGGER.info(
                "%s - there is not enough power available power=%.3f, max_power=%.3f started_power=%.3f current_started_power=%.3f startup_power=%.3f heater power=%.3f reservation_key=%s",
                self,
                current_power,
                current_max_power,
                started_vtherm_total_power,
                current_started_power,
                startup_power,
                self._device_power,
                effective_reservation_key,
            )

        return ret, startup_power

    def calculate_underlying_startup_power(self) -> float:
        """Calculate the incremental startup power for a single underlying.

        This is the power to *reserve* between two power sensor measurements
        when a new underlying is about to be turned on. It is deliberately
        distinct from ``calculate_power_consumption_max()`` (used for global
        shedding decisions) and intentionally ignores ``on_percent``: startup
        is an instantaneous decision, not a cycle-average one.
        """
        if not self._device_power:
            return 0

        # over_climate and mono-underlying over_switch: if the device is
        # already active, its load is already reflected in current_power, so
        # no additional reservation is needed (returning device_power here
        # would double-count the load between two sensor refreshes).
        if self._vtherm.is_over_climate:
            return 0 if self._vtherm.is_device_active else self._device_power

        if self._vtherm.nb_underlying_entities <= 1:
            return 0 if self._vtherm.is_device_active else self._device_power

        # Multi-underlying over_switch: each underlying contributes an
        # independent incremental slice, regardless of whether the VTherm is
        # globally "active". Starting a 2nd underlying while the 1st is on
        # must still reserve its own device_power/n slice.
        return self._device_power / self._vtherm.nb_underlying_entities

    def calculate_power_consumption_max(self) -> float:
        """Calculate the maximum power consumption"""
        power_consumption_max = 0
        if not self._vtherm.is_device_active:
            if self._vtherm.is_over_climate:
                power_consumption_max = self._device_power
            else:
                # if on_percent is not defined, we consider that the device can consume all its power in the worst case
                on_percent = self._vtherm.safe_on_percent if self._vtherm.safe_on_percent is not None else 1

                power_consumption_max = max(
                    self._device_power / self._vtherm.nb_underlying_entities,
                    self._device_power * on_percent,
                )
        return power_consumption_max

    def add_power_consumption_to_central_power_manager(
        self,
        reservation_key: str | None = None,
    ):
        """
        Add the current power consumption to the central power manager.
        """
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if not self._is_configured or not vtherm_api.central_power_manager.is_configured:
            return

        startup_power = self.calculate_underlying_startup_power()

        vtherm_api.central_power_manager.set_started_vtherm_power(
            reservation_key or self._default_power_reservation_key,
            startup_power,
        )

    def sub_power_consumption_to_central_power_manager(
        self,
        reservation_key: str | None = None,
    ):
        """
        Substract the current power consumption to the central power manager.
        """
        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        if not self._is_configured or not vtherm_api.central_power_manager.is_configured:
            return

        vtherm_api.central_power_manager.set_started_vtherm_power(
            reservation_key or self._default_power_reservation_key,
            0,
        )

    async def set_overpowering(self, overpowering: bool, power_consumption_max: float = 0):
        """Force the overpowering state for the VTherm"""

        vtherm_api = VersatileThermostatAPI.get_vtherm_api()
        current_power = vtherm_api.central_power_manager.current_power
        current_max_power = vtherm_api.central_power_manager.current_max_power

        if overpowering and not self.is_overpowering_detected:
            write_event_log(_LOGGER, self._vtherm, "Overpowering is detected")
            _LOGGER.warning("%s - overpowering is detected.", self)

            self._overpowering_state = STATE_ON

            await self._vtherm.async_underlying_entity_turn_off()
            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "start",
                    "current_power": current_power,
                    "device_power": self._device_power,
                    "current_max_power": current_max_power,
                    "current_power_consumption": power_consumption_max,
                },
            )
        elif not overpowering and self.is_overpowering_detected:
            write_event_log(_LOGGER, self._vtherm, "End of overpowering is detected")
            _LOGGER.warning("%s - end of overpowering is detected.", self)
            self._overpowering_state = STATE_OFF

            self._vtherm.send_event(
                EventType.POWER_EVENT,
                {
                    "type": "end",
                    "current_power": current_power,
                    "device_power": self._device_power,
                    "current_max_power": current_max_power,
                },
            )
        elif not overpowering and self._overpowering_state != STATE_OFF:
            # just set to not overpowering the state which was not set
            self._overpowering_state = STATE_OFF
        else:
            # Nothing to do (already in the right state)
            return
        # self._vtherm.update_custom_attributes()

    @overrides
    @property
    def is_configured(self) -> bool:
        """Return True of the presence is configured"""
        return self._is_configured

    @property
    def overpowering_state(self) -> str | None:
        """Return the current overpowering state STATE_ON or STATE_OFF
        or STATE_UNAVAILABLE if not configured"""
        if not self._is_configured:
            return STATE_UNAVAILABLE
        return self._overpowering_state

    @property
    def is_overpowering_detected(self) -> bool:
        """Return True if the Vtherm is in overpowering state"""
        return self._overpowering_state == STATE_ON

    @property
    def is_detected(self) -> bool:
        """Return the overall state of the feature manager based on detection states"""
        return self.is_overpowering_detected

    @property
    def power_temperature(self) -> float | None:
        """Return the power temperature"""
        return self._power_temp

    @property
    def device_power(self) -> float:
        """Return the device power"""
        return self._device_power

    @property
    def mean_cycle_power(self) -> float | None:
        """Returns the mean power consumption during the cycle"""
        if not self._device_power:
            return None

        if self._vtherm.proportional_algorithm:
            algo_on_percent = self._vtherm.proportional_algorithm.on_percent
            if algo_on_percent is None:
                return None
            return float(round_to_nearest(self._device_power * algo_on_percent, 0.01))

        if self._vtherm.is_over_climate:
            return self._device_power if self._vtherm.is_device_active else 0.0

        return None

    @property
    def _default_power_reservation_key(self) -> str:
        """Return a stable fallback key for temporary power reservations."""
        return getattr(self._vtherm, "entity_id", None) or self._vtherm.name

    def __str__(self):
        return f"PowerManager-{self.name}"
