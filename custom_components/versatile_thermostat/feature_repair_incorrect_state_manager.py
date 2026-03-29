# pylint: disable=line-too-long

"""Implements the Repair Incorrect State feature as a Feature Manager"""

from typing import Any
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant

from .const import (
    CONF_REPAIR_INCORRECT_STATE,
    DEFAULT_REPAIR_INCORRECT_STATE,
    REPAIR_MAX_ATTEMPTS,
    REPAIR_MIN_DELAY_AFTER_INIT_SEC,
    overrides,
)
from .log_collector import get_vtherm_logger
from .commons_type import ConfigData
from .base_manager import BaseFeatureManager

_LOGGER = get_vtherm_logger(__name__)


class FeatureRepairIncorrectStateManager(BaseFeatureManager):
    """Detects and repairs discrepancies between VTherm's desired state
    and the actual state of underlying entities.

    On each control heating cycle, if the feature is enabled, it compares
    the desired state (should_device_be_active) with the actual state
    (is_device_active) for each underlying entity. If they differ, it
    re-emits the desired command. The number of consecutive repairs is
    capped at REPAIR_MAX_ATTEMPTS to prevent infinite loops.

    The feature only activates at least REPAIR_MIN_DELAY_AFTER_INIT_SEC
    seconds after VTherm has become fully operational (is_ready).
    """

    unrecorded_attributes = frozenset(
        {
            "is_repair_incorrect_state_configured",
        }
    )

    def __init__(self, vtherm: Any, hass: HomeAssistant):
        """Init of a FeatureManager"""
        super().__init__(vtherm, hass)

        self._is_configured: bool = False
        self._ready_start_time: datetime | None = None
        self._consecutive_repair_count: int = 0

    @overrides
    def post_init(self, entry_infos: ConfigData):
        """Reinit of the manager"""
        self._is_configured = entry_infos.get(
            CONF_REPAIR_INCORRECT_STATE, DEFAULT_REPAIR_INCORRECT_STATE
        )
        self._ready_start_time = None
        self._consecutive_repair_count = 0

    @overrides
    async def start_listening(self):
        """Start listening - no external entity to monitor for this feature"""

    @overrides
    def stop_listening(self):
        """Stop listening - nothing to clean up for this feature"""

    @property
    @overrides
    def is_configured(self) -> bool:
        """True if the feature is enabled"""
        return self._is_configured

    async def check_and_repair(self) -> bool:
        """Check all underlyings for state discrepancies and repair if needed.

        Called on each control heating cycle.
        Returns True if at least one repair was performed, False otherwise.
        """
        if not self._is_configured:
            return False

        if not self._vtherm.is_ready:
            # Reset so the delay restarts if VTherm loses readiness
            self._ready_start_time = None
            return False

        now = datetime.now(timezone.utc)

        # Record the first time VTherm becomes ready
        if self._ready_start_time is None:
            self._ready_start_time = now
            _LOGGER.debug(
                "%s - RepairIncorrectStateManager: VTherm just became ready, "
                "waiting %ds before activating",
                self._vtherm.name,
                REPAIR_MIN_DELAY_AFTER_INIT_SEC,
            )
            return False

        # Wait for the minimum delay after init
        elapsed = (now - self._ready_start_time).total_seconds()
        if elapsed < REPAIR_MIN_DELAY_AFTER_INIT_SEC:
            return False

        # Stop if the maximum consecutive repair count is reached
        if self._consecutive_repair_count >= REPAIR_MAX_ATTEMPTS:
            _LOGGER.error(
                "%s - RepairIncorrectStateManager: maximum repair attempts (%d) " "reached. Stopped attempting repairs to avoid infinite loop.",
                self._vtherm.name,
                REPAIR_MAX_ATTEMPTS,
            )
            self._consecutive_repair_count += 1
            if self._consecutive_repair_count >= 2 * REPAIR_MAX_ATTEMPTS:
                _LOGGER.info(
                    "%s - RepairIncorrectStateManager: consecutive repair count has doubled the max attempts, resetting the counter to allow new repair attempts.",
                    self._vtherm.name,
                )
                self._consecutive_repair_count = 0
            else:
                return False

        repaired = False
        # build a list of underlying to repair as the vtherm.underlyings concatened to the list of vtherm.underlyings_valve_regulation if it exists
        for underlying in self._vtherm.all_underlying_entities:
            _LOGGER.debug("%s - RepairIncorrectStateManager: checking underlying %s for state discrepancies", self, underlying.entity_id)
            repaired_this = await underlying.check_and_repair()
            if repaired_this:
                _LOGGER.warning(
                    "%s - RepairIncorrectStateManager: underlying %s was repaired. Consecutive repairs so far: %d",
                    self._vtherm.name,
                    underlying.entity_id,
                    self._consecutive_repair_count + 1,
                )
                repaired = True

        if repaired:
            self._consecutive_repair_count += 1
        else:
            self._consecutive_repair_count = 0

        return repaired

    def add_custom_attributes(self, extra_state_attributes: dict[str, Any]):
        """Add custom attributes for diagnostics"""
        extra_state_attributes.update(
            {
                "is_repair_incorrect_state_configured": self._is_configured,
            }
        )

        if self._is_configured:
            extra_state_attributes.update(
                {
                    "repair_incorrect_state_manager": {
                        "consecutive_repair_count": self._consecutive_repair_count,
                        "max_attempts": REPAIR_MAX_ATTEMPTS,
                        "min_delay_after_init_sec": REPAIR_MIN_DELAY_AFTER_INIT_SEC,
                    }
                }
            )

    @property
    def is_detected(self) -> bool:
        """Return the overall state of the feature manager based on repair attempts"""
        return self._consecutive_repair_count > 0

    def __str__(self):
        return f"RepairIncorrectStateManager-{self.name}"
