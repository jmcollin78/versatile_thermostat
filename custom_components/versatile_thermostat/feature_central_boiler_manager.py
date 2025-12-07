""" This module manages the central boiler feature of the Versatile Thermostat integration. """
import logging
from typing import Any

from homeassistant.core import (
    HomeAssistant,
    HomeAssistantError,
)

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event

from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from .commons import check_and_extract_service_configuration, write_event_log

from .base_manager import BaseFeatureManager


_LOGGER = logging.getLogger(__name__)


class FeatureCentralBoilerManager(BaseFeatureManager):
    """The implementation of the Central Boiler Feature Manager for Versatile Thermostat"""

    def __init__(self, hass: HomeAssistant, vtherm_api: Any):
        """Initialize the FeatureCentralBoilerManager."""
        super().__init__(vtherm_api, hass)
        self._vtherm_api = vtherm_api
        self._is_configured: bool = False
        self._is_ready: bool = False
        self._is_on: bool = False
        self._service_activate: dict | None = None
        self._service_deactivate: dict | None = None

        self._central_boiler_entity = None
        self._nb_active_device_threshold_number_entity = None
        self._total_power_active_threshold_number_entity = None
        self._nb_active_device_number_entity = None
        self._total_power_active_entity = None
        self._all_boiler_entities: list[Entity] = []

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
    async def start_listening(self, force: bool = False):
        """Initialize the listening of state change of VTherms"""

        # Listen to all VTherm state change
        boiler_entity_ids = self._get_all_boiler_entity_ids(force=force)
        if self.is_ready:
            self.stop_listening()
            listener_cancel = async_track_state_change_event(
                self._hass,
                boiler_entity_ids,
                self.calculate_central_boiler_state,
            )
            _LOGGER.debug(
                "%s - entities to get the nb of active VTherm are %s",
                self,
                boiler_entity_ids,
            )
            self.add_listener(listener_cancel)
            await self.calculate_central_boiler_state(None)
        else:
            _LOGGER.debug("%s - no VTherm could controls the central boiler", self)

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        return self._is_configured

    @property
    def is_ready(self) -> bool:
        """True if the FeatureManager is fully configured and has all registered entities"""
        return self._is_ready

    @property
    def is_on(self) -> bool:
        """Return True if the central boiler is on."""
        return self._is_on

    async def calculate_central_boiler_state(self, _):
        """Calculate the central boiler state depending on all VTherm that
        controls this central boiler"""

        _LOGGER.debug("%s - calculating the new central boiler state", self)
        if not self.is_ready:
            _LOGGER.warning(
                "%s - the central boiler manager is not ready. Central boiler state cannot be calculated",
                self,
            )
            return False

        active = self.is_nb_active_active_for_boiler_exceeded or self.is_total_power_active_for_boiler_exceeded

        if self._is_on != active:
            try:
                if active:
                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned on (nb_active= {self.nb_active_device_for_boiler}/{self.nb_active_device_for_boiler_threshold},"
                        "total_power= {self.total_power_active_for_boiler}/{self.total_power_active_for_boiler_threshold})",
                    )
                    await self.call_service(self._service_activate)
                    _LOGGER.info("%s - central boiler have been turned on", self)
                else:
                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned off (nb_active= {self.nb_active_device_for_boiler}/{self.nb_active_device_for_boiler_threshold},"
                        "total_power= {self.total_power_active_for_boiler}/{self.total_power_active_for_boiler_threshold})",
                    )
                    await self.call_service(self._service_deactivate)
                    _LOGGER.info("%s - central boiler have been turned off", self)
                self._is_on = active
                send_vtherm_event(
                    hass=self._hass,
                    event_type=EventType.CENTRAL_BOILER_EVENT,
                    entity=self.central_boiler_entity,
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

    async def reload_central_boiler_binary_listener(self):
        """Reloads the BinarySensor entity which listen to the number of
        active devices and the thresholds entities"""
        if self._nb_active_device_number_entity:
            await self._nb_active_device_number_entity.listen_vtherms_entities()
        if self._total_power_active_entity:
            await self._total_power_active_entity.listen_vtherms_entities()

    async def reload_central_boiler_entities_list(self):
        """Reload the central boiler list of entities if a central boiler is used"""
        if self._nb_active_device_number_entity is not None:
            await self._nb_active_device_number_entity.listen_vtherms_entities()

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]) -> None:
        """Add custom attributes to the attributes dict."""
        extra_state_attributes.update(
            {
                "is_central_boiler_configured": self._is_configured,
                "is_central_boiler_ready": self._is_ready,
            }
        )
        if self._is_ready:
            extra_state_attributes.update(
                {
                    "central_boiler_manager": {
                        "is_on": self._is_on,
                        "service_activate": self._service_activate,
                        "service_deactivate": self._service_deactivate,
                        "nb_active_device_for_boiler": self.nb_active_device_for_boiler,
                        "nb_active_device_for_boiler_threshold": self.nb_active_device_for_boiler_threshold,
                        "total_power_active_for_boiler": self.total_power_active_for_boiler,
                        "total_power_active_for_boiler_threshold": self.total_power_active_for_boiler_threshold,
                    }
                }
            )

    def __str__(self):
        return f"FeatureCentralBoilerManager-{self._name}"

    def register_central_boiler(self, central_boiler_entity):
        """Register the central boiler entity. This is used by the CentralBoilerBinarySensor
        class to register itself at creation"""
        self._central_boiler_entity = central_boiler_entity
        self.hass.create_task(self.start_listening(force=True))

    def register_central_boiler_activation_number_threshold(self, threshold_number_entity):
        """register the number entities needed for boiler activation"""
        self._nb_active_device_threshold_number_entity = threshold_number_entity
        self.hass.create_task(self.start_listening(force=True))

    def register_central_boiler_power_activation_threshold(self, power_threshold_number_entity):
        """register the power entities needed for boiler activation"""
        self._total_power_active_threshold_number_entity = power_threshold_number_entity
        self.hass.create_task(self.start_listening(force=True))

    def register_nb_device_active_boiler(self, nb_active_number_entity):
        """register the two number entities needed for boiler activation"""
        self._nb_active_device_number_entity = nb_active_number_entity
        self.hass.create_task(self.start_listening(force=True))

    def register_total_power_active_boiler(self, total_power_active_entity):
        """register the two number entities needed for boiler activation"""
        self._total_power_active_entity = total_power_active_entity
        self.hass.create_task(self.start_listening(force=True))

    @property
    def central_boiler_entity(self):
        """Get the central boiler binary_sensor entity"""
        return self._central_boiler_entity

    @property
    def nb_active_device_for_boiler(self):
        """Returns the number of active VTherm which have an
        influence on boiler"""
        if self._nb_active_device_number_entity is None:
            return None
        else:
            return self._nb_active_device_number_entity.native_value

    @property
    def nb_active_device_for_boiler_threshold(self):
        """Returns the number of active VTherm entity which have an
        influence on boiler"""
        if self._nb_active_device_threshold_number_entity is None:
            return None
        return int(self._nb_active_device_threshold_number_entity.native_value)

    @property
    def total_power_active_for_boiler(self):
        """Returns the total power of active VTherm which have an
        influence on boiler"""
        if self._total_power_active_entity is None:
            return None
        else:
            return self._total_power_active_entity.native_value

    @property
    def total_power_active_for_boiler_threshold(self):
        """Returns the number of active VTherm entity which have an
        influence on boiler"""
        if self._total_power_active_threshold_number_entity is None:
            return None
        return int(self._total_power_active_threshold_number_entity.native_value)

    @property
    def is_nb_active_active_for_boiler_exceeded(self) -> bool:
        """Returns True if the number of active VTherm for boiler
        have exceeded the threshold"""
        if self.nb_active_device_for_boiler is None or self.nb_active_device_for_boiler_threshold is None or self.nb_active_device_for_boiler_threshold == 0:
            return False

        return self.nb_active_device_for_boiler >= self.nb_active_device_for_boiler_threshold

    @property
    def is_total_power_active_for_boiler_exceeded(self) -> bool:
        """Returns True if the total power of active VTherm for boiler
        have exceeded the threshold"""
        if (
            self._total_power_active_entity is None
            or self._total_power_active_threshold_number_entity is None
            or self._total_power_active_threshold_number_entity.native_value == 0
        ):
            return False

        total_power = self._total_power_active_entity.native_value
        power_threshold = self._total_power_active_threshold_number_entity.native_value

        return total_power >= power_threshold

    def _get_all_boiler_entity_ids(self, force=False) -> list[str]:
        """Returns the list of all VTherm entity ids which have an influence
        on the central boiler"""
        if self._is_configured and not force:
            return self._all_boiler_entities

        self._all_boiler_entities = []
        if self._nb_active_device_threshold_number_entity:
            self._all_boiler_entities.append(self._nb_active_device_threshold_number_entity.entity_id)
        if self._total_power_active_threshold_number_entity:
            self._all_boiler_entities.append(self._total_power_active_threshold_number_entity.entity_id)
        if self._nb_active_device_number_entity:
            self._all_boiler_entities.append(self._nb_active_device_number_entity.entity_id)
        if self._total_power_active_entity:
            self._all_boiler_entities.append(self._total_power_active_entity.entity_id)

        old_ready = self._is_ready
        self._is_ready = self.is_configured and len(self._all_boiler_entities) == 4 and self._central_boiler_entity is not None
        if not self._is_ready:
            _LOGGER.warning(
                "%s - central boiler manager is not fully configured. Found only %d/4 entities and central boiler entity=%s. Central boiler control will not work properly. This could a temporary message at startup.",
                self,
                len(self._all_boiler_entities),
                self._central_boiler_entity,
            )
            return []
        if self._is_ready != old_ready and self._central_boiler_entity:
            # Notify the central boiler entity that the manager is now ready
            self.refresh_central_boiler_custom_attributes()

        return self._all_boiler_entities

    def refresh_central_boiler_custom_attributes(self):
        """Refresh the custom attributes of the central boiler entity"""
        if self._central_boiler_entity:
            self._central_boiler_entity.refresh_custom_attributes()

    # For testing purpose
    def _set_nb_active_device_threshold(self, value: int) -> None:
        """Set the number of active device threshold"""
        if self._nb_active_device_threshold_number_entity:
            self._nb_active_device_threshold_number_entity.set_native_value(value)

    def _set_total_power_active_threshold(self, value: int) -> None:
        """Set the total power of active device threshold"""
        if self._total_power_active_threshold_number_entity:
            self._total_power_active_threshold_number_entity.set_native_value(value)
