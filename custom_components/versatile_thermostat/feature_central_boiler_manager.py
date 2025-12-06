""" This module manages the central boiler feature of the Versatile Thermostat integration. """
import logging
from typing import Any

from homeassistant.core import (
    HomeAssistant,
    HomeAssistantError,
)

from homeassistant.helpers.event import async_track_state_change_event

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import check_and_extract_service_configuration, write_event_log

from .base_manager import BaseFeatureManager
from .vtherm_api import VersatileThermostatAPI


_LOGGER = logging.getLogger(__name__)


class FeatureCentralBoilerManager(BaseFeatureManager):
    """The implementation of the Central Boiler Feature Manager for Versatile Thermostat"""

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Initialize the FeatureCentralBoilerManager."""
        super().__init__(vtherm, hass)
        self._is_configured: bool = False
        self._is_on: bool = False
        self._service_activate: dict | None = None
        self._service_deactivate: dict | None = None

    @overrides
    def post_init(self, entry_infos: dict):
        """Reinit of the manager"""
        self._service_activate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV)
        )
        self._service_deactivate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV)
        )
        self._is_configured = bool(self._service_activate or self._service_deactivate)

    @overrides
    async def start_listening(self):
        """Start listening to the nb_active_device_for_boiler entity changes"""
        await self.start_listening_active_vtherm_entity()

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        return self._is_configured

    @property
    def is_on(self) -> bool:
        """Return True if the central boiler is on."""
        return self._is_on

    async def start_listening_active_vtherm_entity(self):
        """Initialize the listening of state change of VTherms"""

        # Listen to all VTherm state change
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)

        if (
            api.nb_active_device_for_boiler_entity
            and api.nb_active_device_for_boiler_threshold_entity
        ):
            listener_cancel = async_track_state_change_event(
                self._hass,
                [
                    api.nb_active_device_for_boiler_entity.entity_id,
                    api.nb_active_device_for_boiler_threshold_entity.entity_id,
                ],
                self.calculate_central_boiler_state,
            )
            _LOGGER.debug(
                "%s - entity to get the nb of active VTherm is %s",
                self,
                api.nb_active_device_for_boiler_entity.entity_id,
            )
            self.add_listener(listener_cancel)
        else:
            _LOGGER.debug("%s - no VTherm could controls the central boiler", self)

        await self.calculate_central_boiler_state(None)

    async def calculate_central_boiler_state(self, _):
        """Calculate the central boiler state depending on all VTherm that
        controls this central boiler"""

        _LOGGER.debug("%s - calculating the new central boiler state", self)
        api: VersatileThermostatAPI = VersatileThermostatAPI.get_vtherm_api(self._hass)
        if (
            api.nb_active_device_for_boiler is None
            or api.nb_active_device_for_boiler_threshold is None
        ):
            _LOGGER.warning(
                "%s - the entities to calculate the boiler state are not initialized. Boiler state cannot be calculated",
                self,
            )
            return False

        active = (
            api.nb_active_device_for_boiler >= api.nb_active_device_for_boiler_threshold
        )

        if self._is_on != active:
            try:
                if active:
                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned on ({api.nb_active_device_for_boiler}/{api.nb_active_device_for_boiler_threshold})",
                    )
                    await self.call_service(self._service_activate)
                    _LOGGER.info("%s - central boiler have been turned on", self)
                else:
                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned off ({api.nb_active_device_for_boiler}/{api.nb_active_device_for_boiler_threshold})",
                    )
                    await self.call_service(self._service_deactivate)
                    _LOGGER.info("%s - central boiler have been turned off", self)
                self._is_on = active
                send_vtherm_event(
                    hass=self._hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=api.central_boiler_entity,
                    data={"central_boiler": active},
                )
            except HomeAssistantError as err:
                _LOGGER.error(
                    "%s - Impossible to activate/deactivate boiler due to error %s. "
                    "Central boiler will not being controlled by VTherm. "
                    "Please check your service configuration. Cf. README.",
                    self,
                    err,
                )

        return self._is_on

    async def call_service(self, service_config: dict):
        """Make a call to a service if correctly configured"""
        if not service_config:
            return

        await self._hass.services.async_call(
            service_config["service_domain"],
            service_config["service_name"],
            service_data=service_config["data"],
            target={
                "entity_id": service_config["entity_id"],
            },
        )

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]) -> None:
        """Add custom attributes to the attributes dict."""
        extra_state_attributes.update(
            {
                "is_central_boiler_configured": self._is_configured,
            }
        )
        if self._is_configured:
            extra_state_attributes.update(
                {
                    "central_boiler_manager": {
                        "is_on": self._is_on,
                    }
                }
            )

    def __str__(self):
        return f"FeatureCentralBoilerManager-{self._name}"
