import pytest
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN, HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_ON,
    SERVICE_TURN_OFF,
)
from homeassistant.core import Context
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.versatile_thermostat.const import DOMAIN
from .commons import (
    FULL_SWITCH_CONFIG,
    create_thermostat,
)

THERM_ENTITY_ID = "climate.mock_title"


@pytest.fixture
async def vtherm_locked(hass):
    """Create a VTherm entity and lock it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="mock_title",
        unique_id="mock_title",
        data=FULL_SWITCH_CONFIG,
    )
    vtherm = await create_thermostat(hass, entry, THERM_ENTITY_ID)
    assert vtherm is not None

    # Ensure a known initial state
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == HVACMode.HEAT

    # Lock via entity API (same behavior as service_lock)
    await vtherm.async_set_lock(True)
    await hass.async_block_till_done()
    assert vtherm.is_locked() is True

    return vtherm


@pytest.fixture
async def vtherm_unlocked(hass):
    """Create an unlocked VTherm entity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="mock_title",
        unique_id="mock_title",
        data=FULL_SWITCH_CONFIG,
    )
    vtherm = await create_thermostat(hass, entry, THERM_ENTITY_ID)
    assert vtherm is not None

    # Ensure unlocked and with initial mode
    await vtherm.async_set_lock(False)
    await vtherm.async_set_hvac_mode(HVACMode.HEAT)
    await hass.async_block_till_done()
    assert vtherm.is_locked() is False
    assert vtherm.hvac_mode == HVACMode.HEAT

    return vtherm


@pytest.mark.asyncio
async def test_lock_blocks_external_temperature_change(hass, vtherm_locked):
    """When locked, external async_set_temperature must be blocked for protected ops."""
    vtherm = vtherm_locked
    initial_temp = vtherm.target_temperature or 19.0

    # External / unknown context: call without internal markers
    await vtherm.async_set_temperature(**{ATTR_TEMPERATURE: initial_temp + 5})
    await hass.async_block_till_done()

    # Target temperature must not change (lock_policy denies protected operation)
    assert vtherm.target_temperature in (initial_temp, None)


@pytest.mark.asyncio
async def test_lock_blocks_external_hvac_mode_change(hass, vtherm_locked):
    """When locked, external async_set_hvac_mode must be blocked."""
    vtherm = vtherm_locked
    initial_mode = vtherm.hvac_mode or HVACMode.HEAT

    await vtherm.async_set_hvac_mode(HVACMode.OFF)
    await hass.async_block_till_done()

    # Mode unchanged, as lock_policy denies protected operation from external context
    assert vtherm.hvac_mode == initial_mode


@pytest.mark.asyncio
async def test_unlocked_allows_external_changes(hass, vtherm_unlocked):
    """When unlocked, standard behavior: external changes are allowed."""
    vtherm = vtherm_unlocked

    # Change temperature
    await vtherm.async_set_temperature(**{ATTR_TEMPERATURE: 21.0})
    await hass.async_block_till_done()
    assert vtherm.target_temperature == 21.0

    # Change hvac_mode
    await vtherm.async_set_hvac_mode(HVACMode.OFF)
    await hass.async_block_till_done()
    assert vtherm.hvac_mode == HVACMode.OFF


@pytest.mark.asyncio
async def test_lock_does_not_break_entity_and_services(hass, vtherm_locked):
    """
    Minimal sanity check: climate domain services remain callable while locked.

    We do not assert exact mode after service calls here, just that:
    - The entity is still present.
    - The lock flag remains True.
    This avoids coupling to HA's generic climate service wiring while
    still probing that lock behavior does not corrupt the entity.
    """
    vtherm = vtherm_locked
    initial_mode = vtherm.hvac_mode

    # Call generic climate.turn_off with an external context
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: vtherm.entity_id},
        blocking=True,
        context=Context(),  # external context
    )

    await hass.async_block_till_done()

    # Entity must still be locked; mode can be OFF or unchanged depending on HA wiring
    assert vtherm.is_locked() is True
    assert vtherm.hvac_mode in (initial_mode, HVACMode.OFF)

    # Call generic climate.turn_on as well; same minimal assertion strategy
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: vtherm.entity_id},
        blocking=True,
        context=Context(),
    )
    await hass.async_block_till_done()

    assert vtherm.is_locked() is True