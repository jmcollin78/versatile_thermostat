# pylint: disable=line-too-long, abstract-method
"""Base class for proportional thermostats (TPI, SmartPI)."""

import logging
from typing import Generic, Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from .base_thermostat import BaseThermostat, ConfigData
from .underlyings import T
from .vtherm_hvac_mode import VThermHvacMode_OFF
from .const import CONF_PROP_FUNCTION

_LOGGER = logging.getLogger(__name__)


class ThermostatProp(BaseThermostat[T], Generic[T]):
    """Base class for proportional thermostats.

    This class provides the common infrastructure for proportional
    control algorithms (TPI, SmartPI). Algorithm-specific logic is
    delegated to a handler via composition.

    Note: TPI-specific attributes (_tpi_coef_int, _proportional_function, etc.)
    are inherited from BaseThermostat and updated by the handler during init.
    """

    def __init__(self, hass: HomeAssistant, unique_id: str, name: str, entry_infos: ConfigData):
        """Initialize the proportional thermostat."""
        # Handler for algorithm-specific logic (TPI or SmartPI)
        self._algo_handler = None
        self._on_time_sec: float | None = 0
        self._off_time_sec: float | None = 0
        self._safety_state: bool = False
        self._safety_default_on_percent: float = 0.0

        super().__init__(hass, unique_id, name, entry_infos)

    # =========================================================================
    # COMMON PROPERTIES
    # =========================================================================

    @property
    def has_prop(self) -> bool:
        """True if the Thermostat uses a proportional algorithm (TPI, SmartPI)."""
        return True

    @property
    def prop_algorithm(self):
        """Get the proportional algorithm."""
        return self._prop_algorithm

    @prop_algorithm.setter
    def prop_algorithm(self, value):
        """Set the proportional algorithm."""
        self._prop_algorithm = value

    @property
    def proportional_algorithm(self):
        """Get the proportional algorithm (alias)."""
        return self._prop_algorithm

    @property
    def on_percent(self) -> float:
        """Returns the percentage the heater must be ON
        In safety mode this value is overridden with the _default_on_percent
        """
        if self._safety_state:
            val = self._safety_default_on_percent
        elif self._prop_algorithm:
            val = self._prop_algorithm.on_percent
        else:
            val = 0

        # Clamp with max_on_percent
        # issue 538 - clamping with max_on_percent should be done here
        if self._max_on_percent is not None and val > self._max_on_percent:
            val = self._max_on_percent

        # Notify the algorithm of the realized power (if supported)
        # Only if the value has been modified by safety or clamping
        if self._prop_algorithm and hasattr(self._prop_algorithm, "update_realized_power"):
            # Get what the algorithm proposes
            algo_percent = self._prop_algorithm.on_percent if self._prop_algorithm else 0
            if val != algo_percent:
                self._prop_algorithm.update_realized_power(val)

        return val

    @property
    def safe_on_percent(self) -> float:
        """Return the on_percent safe value.
        Deprecated: use on_percent directly as it now handles safety.
        """
        return self.on_percent

    def set_safety(self, default_on_percent: float):
        """Set a default value for on_percent (used for safety mode)"""
        _LOGGER.info("%s - Set safety to ON with default_on_percent=%s", self, default_on_percent)
        self._safety_state = True
        self._safety_default_on_percent = default_on_percent

    def unset_safety(self):
        """Unset the safety mode"""
        _LOGGER.info("%s - Set safety to OFF", self)
        self._safety_state = False

    @property
    def auto_tpi_manager(self):
        """Return the Auto TPI manager from handler."""
        return self._algo_handler.auto_tpi_manager if self._algo_handler else None

    @property
    def on_time_sec(self) -> float | None:
        """Return the on time in seconds"""
        return self._on_time_sec

    @property
    def off_time_sec(self) -> float | None:
        """Return the off time in seconds"""
        return self._off_time_sec

    # =========================================================================
    # LIFECYCLE METHODS - Delegate to handler
    # =========================================================================

    def post_init(self, config_entry: ConfigData):
        """Finish the initialization of the thermostat."""
        super().post_init(config_entry)

        # Initialize the proportional function from config
        # This allows selecting the correct handler (TPI, or other prop algorithms)
        self._proportional_function = self._entry_infos.get(CONF_PROP_FUNCTION)

        self._init_algorithm_handler()

    def _init_algorithm_handler(self):
        """Initialize the algorithm handler based on proportional_function config.

        This method creates the appropriate handler (TPI or other future ones) based on
        the CONF_PROP_FUNCTION setting in the configuration.
        """
        # Import here to avoid circular imports
        from .prop_handler_tpi import TPIHandler  # pylint: disable=import-outside-toplevel
        self._algo_handler = TPIHandler(self)
        self._algo_handler.init_algorithm()

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        if self._algo_handler:
            await self._algo_handler.async_added_to_hass()
        await super().async_added_to_hass()

    async def async_startup(self, central_configuration):
        """Startup the thermostat."""
        await super().async_startup(central_configuration)
        if self._algo_handler:
            await self._algo_handler.async_startup()

    def remove_thermostat(self):
        """Called when the thermostat will be removed."""
        if self._algo_handler:
            self._algo_handler.remove()
        super().remove_thermostat()

    # =========================================================================
    # COMMON METHODS
    # =========================================================================

    def recalculate(self, force=False):
        """Force the calculation of the algo and update attributes."""
        if self._prop_algorithm:
            self._prop_algorithm.calculate(
                self.target_temperature,
                self._cur_temp,
                self._cur_ext_temp,
                self.last_temperature_slope,
                self.vtherm_hvac_mode or VThermHvacMode_OFF,
            )

    async def _control_heating_specific(self, force=False):
        """Control heating using the algorithm handler."""
        if self._algo_handler:
            await self._algo_handler.control_heating(force)

    async def update_states(self, force=False):
        """Update states and delegate to handler."""
        changed = await super().update_states(force)
        if changed and self._algo_handler:
            await self._algo_handler.on_state_changed()
        return changed

    def update_custom_attributes(self):
        """Update custom attributes."""
        super().update_custom_attributes()
        if self._algo_handler:
            self._algo_handler.update_attributes()

    # =========================================================================
    # SERVICE METHODS - Delegate to handler
    # =========================================================================

    async def service_set_tpi_parameters(
        self,
        tpi_coef_int: float | None = None,
        tpi_coef_ext: float | None = None,
        minimal_activation_delay: int | None = None,
        minimal_deactivation_delay: int | None = None,
        tpi_threshold_low: float | None = None,
        tpi_threshold_high: float | None = None,
    ):
        """Service: set TPI parameters."""
        if hasattr(self._algo_handler, 'service_set_tpi_parameters'):
            await self._algo_handler.service_set_tpi_parameters(
                tpi_coef_int=tpi_coef_int,
                tpi_coef_ext=tpi_coef_ext,
                minimal_activation_delay=minimal_activation_delay,
                minimal_deactivation_delay=minimal_deactivation_delay,
                tpi_threshold_low=tpi_threshold_low,
                tpi_threshold_high=tpi_threshold_high,
            )
        else:
            raise ServiceValidationError(f"{self} - This service is only available for TPI algorithm.")

    async def service_set_auto_tpi_mode(
        self,
        auto_tpi_mode: bool,
        reinitialise: bool = True,
        allow_kint_boost_on_stagnation: bool = False,
        allow_kext_compensation_on_overshoot: bool = False,
    ):
        """Service: set Auto TPI mode."""
        if hasattr(self._algo_handler, 'service_set_auto_tpi_mode'):
            await self._algo_handler.service_set_auto_tpi_mode(
                auto_tpi_mode=auto_tpi_mode,
                reinitialise=reinitialise,
                allow_kint_boost_on_stagnation=allow_kint_boost_on_stagnation,
                allow_kext_compensation_on_overshoot=allow_kext_compensation_on_overshoot,
            )
        else:
            raise ServiceValidationError(f"{self} - This service is only available for TPI algorithm.")

    async def service_auto_tpi_calibrate_capacity(
        self,
        save_to_config: bool,
        min_power_threshold: int,
        start_date=None,
        end_date=None,
    ):
        """Service: calibrate Auto TPI capacity."""
        if hasattr(self._algo_handler, 'service_auto_tpi_calibrate_capacity'):
            return await self._algo_handler.service_auto_tpi_calibrate_capacity(
                save_to_config=save_to_config,
                min_power_threshold=min_power_threshold,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            raise ServiceValidationError(f"{self} - This service is only available for TPI algorithm.")

    async def async_set_auto_tpi_mode(
        self,
        auto_tpi_mode: bool,
        reinitialise: bool = True,
        allow_kint_boost: bool = False,
        allow_kext_overshoot: bool = False,
    ):
        """Set the auto TPI mode."""
        if hasattr(self._algo_handler, 'async_set_auto_tpi_mode'):
            await self._algo_handler.async_set_auto_tpi_mode(
                auto_tpi_mode=auto_tpi_mode,
                reinitialise=reinitialise,
                allow_kint_boost=allow_kint_boost,
                allow_kext_overshoot=allow_kext_overshoot,
            )
    async def _on_prop_cycle_start(self, params: dict[str, Any]):
        """Called by Algorithm Handler when a new cycle starts.

        Args:
            params: Dictionary containing cycle parameters (on_time, off_time, etc.)
        """
        await self._fire_cycle_start_callbacks(
            params.get("on_time_sec", 0),
            params.get("off_time_sec", 0),
            params.get("on_percent", 0),
            params.get("hvac_mode", "stop")
        )
