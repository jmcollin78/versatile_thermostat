"""
Test: auto_start_stop hvac_off_reason is preserved after HA restart.

Add this test to tests/test_auto_start_stop.py (or create a new file
tests/test_auto_start_stop_restore.py).

The test follows the existing patterns in the VTherm test suite:
  - Use @pytest.mark.asyncio
  - Mock a previous State object with the relevant attributes
  - Call get_my_previous_state() (which internally calls restore_state())
  - Assert the VTherm stays off with the correct off-reason
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant.components.climate import HVACMode
from homeassistant.core import State

# Adjust these imports to match the actual module paths in the project
from custom_components.versatile_thermostat.const import (
    HVAC_OFF_REASON_AUTO_START_STOP,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_old_state(hvac_mode="off", hvac_off_reason=None, saved_hvac_mode=None):
    """Build a minimal State object that mimics what HA persists."""
    attributes = {}
    if hvac_off_reason:
        attributes["hvac_off_reason"] = hvac_off_reason
    if saved_hvac_mode:
        attributes["saved_hvac_mode"] = saved_hvac_mode
    # Minimal auto_start_stop_manager dict (mirrors add_custom_attributes output)
    attributes["auto_start_stop_manager"] = {
        "auto_start_stop_enable": True,
        "auto_start_stop_level": "auto_start_stop_medium",
        "is_auto_stop_detected": True,
    }
    return State(
        entity_id="climate.test_vtherm",
        state=hvac_mode,
        attributes=attributes,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAutoStartStopRestoreState:
    """Unit tests for FeatureAutoStartStopManager.restore_state()."""

    def _make_manager(self):
        """Return a FeatureAutoStartStopManager with a mocked VTherm."""
        from custom_components.versatile_thermostat.feature_auto_start_stop_manager import (
            FeatureAutoStartStopManager,
        )

        vtherm = MagicMock()
        vtherm.name = "TestVTherm"
        vtherm.hvac_off_reason = None
        vtherm.saved_hvac_mode = None

        manager = FeatureAutoStartStopManager.__new__(FeatureAutoStartStopManager)
        manager._vtherm = vtherm
        manager._auto_start_stop_enable = True
        manager._is_auto_stop_detected = True
        return manager, vtherm

    # ------------------------------------------------------------------
    # Nominal case: VTherm was stopped by auto_start_stop before restart
    # ------------------------------------------------------------------
    def test_restore_state_auto_stop_restores_off_reason(self):
        """hvac_off_reason must be HVAC_OFF_REASON_AUTO_START_STOP after restore."""
        manager, vtherm = self._make_manager()
        old_state = _make_old_state(
            hvac_mode="off",
            hvac_off_reason=HVAC_OFF_REASON_AUTO_START_STOP,
            saved_hvac_mode="heat",
        )

        manager.restore_state(old_state)

        assert vtherm.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP

    def test_restore_state_auto_stop_restores_saved_hvac_mode(self):
        """saved_hvac_mode must be HVACMode.HEAT after restore."""
        manager, vtherm = self._make_manager()
        old_state = _make_old_state(
            hvac_mode="off",
            hvac_off_reason=HVAC_OFF_REASON_AUTO_START_STOP,
            saved_hvac_mode="heat",
        )

        manager.restore_state(old_state)

        assert vtherm.saved_hvac_mode == HVACMode.HEAT

    # ------------------------------------------------------------------
    # Edge cases: should NOT restore when reason is different
    # ------------------------------------------------------------------
    def test_restore_state_manual_off_does_not_override(self):
        """If VTherm was turned off manually, restore_state must be a no-op."""
        manager, vtherm = self._make_manager()
        old_state = _make_old_state(
            hvac_mode="off",
            hvac_off_reason="manual",
            saved_hvac_mode="heat",
        )

        manager.restore_state(old_state)

        # Nothing should be set by this manager
        assert vtherm.hvac_off_reason is None
        assert vtherm.saved_hvac_mode is None

    def test_restore_state_no_reason_is_noop(self):
        """If hvac_off_reason is absent, restore_state must be a no-op."""
        manager, vtherm = self._make_manager()
        old_state = _make_old_state(hvac_mode="heat")  # normal running state

        manager.restore_state(old_state)

        assert vtherm.hvac_off_reason is None
        assert vtherm.saved_hvac_mode is None

    def test_restore_state_none_old_state_is_noop(self):
        """restore_state(None) must not raise."""
        manager, vtherm = self._make_manager()

        manager.restore_state(None)  # must not raise

        assert vtherm.hvac_off_reason is None

    def test_restore_state_missing_manager_attr_is_noop(self):
        """If the auto_start_stop_manager attribute is absent, skip silently."""
        manager, vtherm = self._make_manager()
        old_state = State(
            entity_id="climate.test_vtherm",
            state="off",
            attributes={"hvac_off_reason": HVAC_OFF_REASON_AUTO_START_STOP},
            # NOTE: no "auto_start_stop_manager" key
        )

        manager.restore_state(old_state)

        assert vtherm.hvac_off_reason is None

    # ------------------------------------------------------------------
    # Integration-style: full get_my_previous_state flow
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_vtherm_stays_off_after_restart(self, hass):
        """
        Integration test: after restoring state from a previous auto-stop,
        the VTherm hvac_mode must remain 'off' and not transition to 'heat'.

        This test requires the standard VTherm test fixtures. Adapt the
        entity creation to match helper functions already used in the suite
        (e.g. create_thermostat() or similar factories).
        """
        # TODO: instantiate a full VTherm using the project's test helpers,
        # inject a previous State with hvac_off_reason=HVAC_OFF_REASON_AUTO_START_STOP,
        # call async_added_to_hass(), and assert hvac_mode == HVACMode.OFF.
        #
        # Example skeleton (adapt to actual test helpers):
        #
        #   entity = await create_over_climate_vtherm(hass, with_auto_start_stop=True)
        #   old_state = _make_old_state(
        #       hvac_mode="off",
        #       hvac_off_reason=HVAC_OFF_REASON_AUTO_START_STOP,
        #       saved_hvac_mode="heat",
        #   )
        #   with patch_object(entity, "async_get_last_state", return_value=old_state):
        #       await entity.async_added_to_hass()
        #   assert entity.hvac_mode == HVACMode.OFF
        #   assert entity.hvac_off_reason == HVAC_OFF_REASON_AUTO_START_STOP
        pytest.skip("Requires full VTherm test fixture – implement with project helpers")
