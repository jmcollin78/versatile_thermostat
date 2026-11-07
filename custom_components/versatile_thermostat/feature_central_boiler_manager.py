"""This module manages the central boiler feature of the Versatile Thermostat integration."""

from datetime import timedelta
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import (
    HassJob,
    HomeAssistant,
    HomeAssistantError,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.template import Template

from .base_manager import BaseFeatureManager
from .commons import check_and_extract_service_configuration, write_event_log
from .const import *  # pylint: disable=wildcard-import, unused-wildcard-import
from vtherm_api.log_collector import get_vtherm_logger


_LOGGER = get_vtherm_logger(__name__)

# How long a VTherm which is not ready can hold back the boiler decision. A VTherm is not ready until
# its underlyings are available, and an underlying may be broken: this must not block the boiler forever.
DEMAND_MAX_WAIT_SEC = 300


class FeatureCentralBoilerManager(BaseFeatureManager):
    """The implementation of the Central Boiler Feature Manager for Versatile Thermostat"""

    def __init__(self, hass: HomeAssistant, vtherm_api: Any):
        """Initialize the FeatureCentralBoilerManager."""
        super().__init__(vtherm_api, hass)
        self._vtherm_api = vtherm_api
        self._is_configured: bool = False
        self._is_ready: bool = False
        self._is_on: bool | None = None
        self._service_activate: dict | None = None
        self._service_deactivate: dict | None = None

        self._central_boiler_entity = None
        self._nb_active_device_threshold_number_entity = None
        self._total_power_active_threshold_number_entity = None
        self._nb_active_device_number_entity = None
        self._total_power_active_entity = None
        self._all_boiler_entities: list[Entity] = []

        self._activation_delay_sec: int = 0
        self._call_later_handle = None

        # Keep-alive tracking
        self._keep_alive_boiler_state_enabled: bool = False
        self._keep_alive_boiler_delay_sec: int = 0
        self._time_interval_listener_cancel = None
        self._last_activated_service: dict | None = None

        # A command waiting for its target entity to be available
        self._cancel_service_target_listener = None
        self._service_target_entity_id: str | None = None
        # The activation delay is over but the activation could not be sent
        self._activation_delay_elapsed: bool = False

        # Demand knowledge
        self._evaluation_suspended: bool = False
        self._cancel_demand_wait = None
        self._demand_wait_expired: bool = False

    @overrides
    def post_init(self, entry_infos: dict):
        """Reinit of the manager. Called at each reload: _is_on survives it, as the boiler device did not change"""
        old_services = (self._service_activate, self._service_deactivate)
        self._service_activate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_ACTIVATION_SRV)
        )
        self._service_deactivate = check_and_extract_service_configuration(
            entry_infos.get(CONF_CENTRAL_BOILER_DEACTIVATION_SRV)
        )
        if old_services != (self._service_activate, self._service_deactivate):
            # The configured commands have changed: what is known about the device is not valid anymore
            self._is_on = None
        self._stop_waiting_service_target()
        self._activation_delay_elapsed = False
        self._activation_delay_sec = entry_infos.get(CONF_CENTRAL_BOILER_ACTIVATION_DELAY_SEC, 0)
        self._keep_alive_boiler_delay_sec = entry_infos.get(CONF_KEEP_ALIVE_BOILER_DELAY_SEC, DEFAULT_KEEP_ALIVE_BOILER_DELAY_SEC)
        self._is_configured = bool(self._service_activate or self._service_deactivate)
        self._keep_alive_boiler_state_enabled = self._keep_alive_boiler_delay_sec > 0 and self._is_configured
        # No command is sent by a reload which does not change the boiler state: keep-alive must go on with the state in place
        self._last_activated_service = None
        if self._keep_alive_boiler_state_enabled and self._is_on is not None:
            self._last_activated_service = self._service_activate if self._is_on else self._service_deactivate

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

            # Add periodic keep-alive if delay is configured
            if self._keep_alive_boiler_state_enabled:
                interval_listener_cancel = async_track_time_interval(
                    self._hass,
                    self._keep_alive_boiler,
                    timedelta(seconds=self._keep_alive_boiler_delay_sec),
                )
                self._time_interval_listener_cancel = interval_listener_cancel
                self.add_listener(interval_listener_cancel)
                _LOGGER.debug(
                    "%s - Keep-alive boiler enabled (every %d seconds)",
                    self,
                    self._keep_alive_boiler_delay_sec,
                )

            await self.calculate_central_boiler_state(None)
        else:
            _LOGGER.debug("%s - no VTherm could controls the central boiler", self)

    @overrides
    def stop_listening(self) -> bool:
        """Stop all listeners, including the ones which are waiting for the demand or the service target"""
        self._stop_waiting_service_target()
        self._stop_waiting_demand()
        return super().stop_listening()

    def suspend_evaluation(self) -> None:
        """Stop deciding the boiler state while VTherms are being reloaded: the sensors only see a part of them"""
        self._evaluation_suspended = True

    async def resume_evaluation(self) -> None:
        """All VTherms have been reloaded: decide the boiler state"""
        self._evaluation_suspended = False
        if self.is_ready:
            await self.calculate_central_boiler_state(None)

    @property
    def is_configured(self) -> bool:
        """True if the FeatureManager is fully configured"""
        return self._is_configured

    @property
    def is_ready(self) -> bool:
        """True if the FeatureManager is fully configured and has all registered entities"""
        return self._is_ready

    @property
    def is_on(self) -> bool | None:
        """Return True if the central boiler is on. Return None if the state is unknown (at startup for example)"""
        return self._is_on

    @property
    def is_detected(self) -> bool:
        """Return True if the central boiler is detected"""
        return self._is_on if self._is_on is not None else False

    async def calculate_central_boiler_state(self, _):
        """Calculate the central boiler state depending on all VTherm that
        controls this central boiler"""

        _LOGGER.debug("%s - calculating the new central boiler state", self)

        def _send_vtherm_event(data: dict):
            send_vtherm_event(
                hass=self._hass,
                event_type=EventType.CENTRAL_BOILER_EVENT,
                entity=self.central_boiler_entity,
                data=data,
            )

        async def _activate_later(_):
            """Activate the central boiler after a delay"""
            if self._call_later_handle:
                self._call_later_handle()
                self._call_later_handle = None

            # the condition may have changed during the delay, so we check it again before activating the boiler
            active = self.is_nb_active_active_for_boiler_exceeded or self.is_total_power_active_for_boiler_exceeded
            if not active:
                _LOGGER.info("%s - central boiler delayed activation cancelled because condition is not valid anymore", self)
                return

            if not self._is_service_target_available(self._service_activate):
                # The delay is over: the activation will be sent as soon as the target is back
                self._activation_delay_elapsed = True
                self._wait_for_service_target(self._service_activate)
                return

            _LOGGER.info("%s - central boiler will be turned on", self)
            try:
                await self.call_service(self._service_activate)
                _LOGGER.info("%s - central boiler have been turned on after delay", self)
                self._is_on = True
                self._activation_delay_elapsed = False
                self._stop_waiting_service_target()
                if self._keep_alive_boiler_state_enabled:
                    self._last_activated_service = self._service_activate
                _send_vtherm_event(
                    data={"central_boiler": True},
                )
            except HomeAssistantError as err:
                _LOGGER.error(
                    "%s - Impossible to activate boiler due to error %s. "
                    "Central boiler will not being controlled by VTherm. "
                    "Please check your service configuration. Cf. README.",
                    self,
                    err,
                )
                return

        if not self.is_ready:
            _LOGGER.warning(
                "%s - the central boiler manager is not ready. Central boiler state cannot be calculated",
                self,
            )
            return False

        if self._evaluation_suspended or not self._check_demand_known():
            _LOGGER.debug("%s - the demand is not known yet. Central boiler state is not calculated", self)
            return

        active = self.is_nb_active_active_for_boiler_exceeded or self.is_total_power_active_for_boiler_exceeded

        if not active:
            self._activation_delay_elapsed = False

        if self._is_on == active:
            # Nothing to send anymore, even if a command was waiting for its target
            self._stop_waiting_service_target()
        else:
            try:
                if active:
                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned on (nb_active= {self.nb_active_device_for_boiler}/{self.nb_active_device_for_boiler_threshold},"
                        f"total_power= {self.total_power_active_for_boiler}/{self.total_power_active_for_boiler_threshold})",
                    )
                    if self._call_later_handle:
                        _LOGGER.debug("%s - central boiler activation is already scheduled", self)
                        return

                    if self._activation_delay_sec > 0 and not self._activation_delay_elapsed:
                        self._call_later_handle = async_call_later(self._hass, timedelta(seconds=self._activation_delay_sec), _activate_later)
                        _send_vtherm_event(
                            data={"delayed_activation_sec": self._activation_delay_sec},
                        )
                    else:
                        await _activate_later(None)
                else:
                    # Cancel any pending activation
                    if self._call_later_handle:
                        self._call_later_handle()
                        self._call_later_handle = None

                    if not self._is_service_target_available(self._service_deactivate):
                        self._wait_for_service_target(self._service_deactivate)
                        return

                    write_event_log(
                        _LOGGER,
                        self,
                        f"Central boiler is being turned off (nb_active= {self.nb_active_device_for_boiler}/{self.nb_active_device_for_boiler_threshold},"
                        f"total_power= {self.total_power_active_for_boiler}/{self.total_power_active_for_boiler_threshold})",
                    )

                    # call deactivation service
                    await self.call_service(self._service_deactivate)
                    _LOGGER.info("%s - central boiler have been turned off", self)
                    self._is_on = active
                    self._stop_waiting_service_target()
                    if self._keep_alive_boiler_state_enabled:
                        self._last_activated_service = self._service_deactivate
                    _send_vtherm_event(
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

    def _check_demand_known(self) -> bool:
        """True if the demand can be trusted. The sensors must have been calculated, and calculated
        from VTherms which are all ready: before this, a 0 only means that a VTherm has not started."""
        sensors = (self._nb_active_device_number_entity, self._total_power_active_entity)
        if any(sensor is None or sensor.native_value is None for sensor in sensors):
            return False

        if all(sensor.all_vtherms_ready for sensor in sensors):
            self._stop_waiting_demand()
            self._demand_wait_expired = False
            return True

        if self._demand_wait_expired:
            return True

        if self._cancel_demand_wait is None:
            self._cancel_demand_wait = async_call_later(
                self._hass,
                timedelta(seconds=DEMAND_MAX_WAIT_SEC),
                HassJob(self._on_demand_wait_expired, cancel_on_shutdown=True),
            )
        return False

    async def _on_demand_wait_expired(self, _) -> None:
        """Some VTherms are still not ready after the maximum wait: decide without them"""
        self._cancel_demand_wait = None
        self._demand_wait_expired = True
        if not (self._nb_active_device_number_entity.all_vtherms_ready and self._total_power_active_entity.all_vtherms_ready):
            _LOGGER.warning(
                "%s - some VTherm used by the central boiler are not ready after %d seconds (check their underlying devices and temperature sensor). "
                "The central boiler state is now calculated without them",
                self,
                DEMAND_MAX_WAIT_SEC,
            )
        await self.calculate_central_boiler_state(None)

    def _stop_waiting_demand(self) -> None:
        """Cancel the maximum wait of the demand"""
        if self._cancel_demand_wait is not None:
            self._cancel_demand_wait()
            self._cancel_demand_wait = None

    def _is_service_target_available(self, service_config: dict | None) -> bool:
        """True if the service can be delivered. A service with no entity target has nothing to wait for.
        STATE_UNKNOWN is available: the entity is loaded, and a scene for example is unknown until its first use."""
        entity_id = service_config.get("entity_id") if service_config else None
        if not entity_id:
            return True
        state = self._hass.states.get(entity_id)
        return state is not None and state.state != STATE_UNAVAILABLE

    def _wait_for_service_target(self, service_config: dict) -> None:
        """Calculate the boiler state again when the target of this service becomes available.
        This is needed because the demand may not change in the meantime."""
        entity_id = service_config["entity_id"]
        if self._service_target_entity_id == entity_id:
            return

        self._stop_waiting_service_target()
        _LOGGER.warning(
            "%s - the target %s of the central boiler command is not available. The command will be sent when it becomes available",
            self,
            entity_id,
        )
        self._service_target_entity_id = entity_id
        self._cancel_service_target_listener = async_track_state_change_event(self._hass, [entity_id], self._on_service_target_changed)

    def _stop_waiting_service_target(self) -> None:
        """Remove the listener of the service target if any"""
        if self._cancel_service_target_listener is not None:
            self._cancel_service_target_listener()
            self._cancel_service_target_listener = None
        self._service_target_entity_id = None

    async def _on_service_target_changed(self, event) -> None:
        """The target of a waiting command has changed"""
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state == STATE_UNAVAILABLE:
            return

        _LOGGER.debug("%s - the central boiler target %s is available", self, new_state.entity_id)
        self._stop_waiting_service_target()
        await self.calculate_central_boiler_state(None)

    async def _keep_alive_boiler(self, _=None):
        """Send keep-alive command to maintain boiler state (called periodically if delay is configured)"""
        if self._keep_alive_boiler_delay_sec <= 0:
            return

        # If we have a pending activation (after delay), don't send keep-alive yet
        if self._call_later_handle is not None:
            return

        # Send keep-alive command for the last activated service
        if self._last_activated_service:
            try:
                await self.call_service(self._last_activated_service)
                entity_id = self._last_activated_service.get("entity_id", "unknown")
                _LOGGER.debug(
                    "%s - Keep-alive boiler command sent (entity %s)",
                    self,
                    entity_id,
                )
            except HomeAssistantError as err:
                _LOGGER.warning(
                    "%s - Failed to send keep-alive command: %s",
                    self,
                    err,
                )

    async def call_service(self, service_config: dict):
        """Make a call to a service if correctly configured.
        Raises HomeAssistantError if the service cannot be called (template rendering included)
        so that the caller does not update the boiler state"""
        if not service_config:
            return

        service_data = service_config["data"]
        if service_config.get("is_template"):
            # The template is rendered each time the command is sent (activation, deactivation and keep-alive)
            try:
                service_data = {service_config["attribute_name"]: Template(service_config["attribute_value"], self._hass).async_render(parse_result=True)}
            except (TemplateError, ValueError, TypeError) as err:
                raise HomeAssistantError(
                    f"cannot render central boiler template {service_config['attribute_value']}: {err}. "
                    f"The service {service_config['service_domain']}.{service_config['service_name']} is not called"
                ) from err

        _LOGGER.debug(
            "%s - Calling central boiler service %s with data %s",
            self,
            f"{service_config['service_domain']}.{service_config['service_name']}",
            service_data,
        )
        entity_id = service_config.get("entity_id")
        await self._hass.services.async_call(
            service_config["service_domain"],
            service_config["service_name"],
            service_data=service_data,
            target={"entity_id": entity_id} if entity_id else None,
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
                        "activation_scheduled": self._call_later_handle is not None,
                        "delayed_activation_sec": self._activation_delay_sec,
                        "nb_active_device_for_boiler": self.nb_active_device_for_boiler,
                        "nb_active_device_for_boiler_threshold": self.nb_active_device_for_boiler_threshold,
                        "total_power_active_for_boiler": self.total_power_active_for_boiler,
                        "total_power_active_for_boiler_threshold": self.total_power_active_for_boiler_threshold,
                        "service_activate": self._service_activate,
                        "service_deactivate": self._service_deactivate,
                        "keep_alive_boiler_delay_sec": self._keep_alive_boiler_delay_sec,
                    }
                }
            )

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
        if self.total_power_active_for_boiler is None or self.total_power_active_for_boiler_threshold is None or self.total_power_active_for_boiler_threshold == 0:
            return False

        total_power = self.total_power_active_for_boiler
        power_threshold = self.total_power_active_for_boiler_threshold

        total_power_watts = power_to_watts(
            total_power,
            self._total_power_active_entity.native_unit_of_measurement,
        )
        power_threshold_watts = power_to_watts(
            power_threshold,
            self._total_power_active_threshold_number_entity.native_unit_of_measurement,
        )

        return total_power_watts >= power_threshold_watts

    def _get_all_boiler_entity_ids(self, force=False) -> list[str]:
        """Returns the list of all VTherm entity ids which have an influence
        on the central boiler"""
        if self._is_configured and not force:
            return self._all_boiler_entities

        required_entities = {
            "number activation threshold": self._nb_active_device_threshold_number_entity,
            "power activation threshold": self._total_power_active_threshold_number_entity,
            "number of active devices": self._nb_active_device_number_entity,
            "total active power": self._total_power_active_entity,
        }
        self._all_boiler_entities = []
        for entity in required_entities.values():
            if entity:
                self._all_boiler_entities.append(entity.entity_id)

        old_ready = self._is_ready
        self._is_ready = self.is_configured and len(self._all_boiler_entities) == 4 and self._central_boiler_entity is not None
        if not self._is_ready and self.is_configured:
            missing_entities = [name for name, entity in required_entities.items() if entity is None]
            _LOGGER.warning(
                "%s - central boiler manager is not fully configured. Found only %d/4 entities and central boiler entity=%s. Missing entities: %s. Central boiler control will not work properly. This could a temporary message at startup.",
                self,
                len(self._all_boiler_entities),
                self._central_boiler_entity,
                ", ".join(missing_entities) or "none",
            )
            return []
        if not self._is_ready and not self.is_configured:
            # Silence warning if the feature is not configured (user doesn't want it)
            _LOGGER.debug(
                "%s - central boiler manager is not configured. Ignoring initialization.",
                self,
            )
            return []
        if self._is_ready != old_ready and self._central_boiler_entity:
            # Notify the central boiler entity that the manager is now ready
            self.hass.create_task(self.refresh_central_boiler_custom_attributes())

        return self._all_boiler_entities

    async def refresh_central_boiler_custom_attributes(self):
        """Refresh the custom attributes of the central boiler entity"""
        if self._central_boiler_entity:
            self._central_boiler_entity.refresh_custom_attributes()

    async def refresh_active_devices(self):
        """Recalculate boiler activity sensors and the resulting boiler state."""
        if self._nb_active_device_number_entity is not None:
            await self._nb_active_device_number_entity.calculate_nb_active_devices(None)
        if self._total_power_active_entity is not None:
            await self._total_power_active_entity.calculate_total_power(None)
        await self.calculate_central_boiler_state(None)

    @property
    def nb_device_active_for_boiler_entity(self):
        """Returns the entity if the sensor which gives the number of active VTherm which have an
        influence on boiler"""
        return self._nb_active_device_number_entity

    # For testing purpose
    def _set_nb_active_device_threshold(self, value: int) -> None:
        """Set the number of active device threshold"""
        if self._nb_active_device_threshold_number_entity:
            self._nb_active_device_threshold_number_entity.set_native_value(value)

    def _set_total_power_active_threshold(self, value: int) -> None:
        """Set the total power of active device threshold"""
        if self._total_power_active_threshold_number_entity:
            self._total_power_active_threshold_number_entity.set_native_value(value)

    def __str__(self):
        return "FeatureCentralBoilerManager"
