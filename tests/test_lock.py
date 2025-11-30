# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument

""" Test the Lock feature """
from unittest.mock import patch, call
from datetime import timedelta, datetime
import logging

from homeassistant.core import HomeAssistant, ServiceCall, Context
from homeassistant.exceptions import HomeAssistantError
from homeassistant.components.climate.const import PRESET_BOOST, HVACMode
from homeassistant.const import ATTR_ENTITY_ID

from custom_components.versatile_thermostat.const import (
    CONF_LOCK_USERS,
    CONF_LOCK_AUTOMATIONS,
    CONF_LOCK_CODE,
    SERVICE_LOCK,
    SERVICE_UNLOCK,
)

from .commons import *  # pylint: disable=wildcard-import, unused-wild-import

logging.getLogger().setLevel(logging.DEBUG)


async def setup_thermostat(
    hass: HomeAssistant,
    lock_users: bool,
    lock_automations: bool,
    lock_code: str | None = None,
):
    """Setup the thermostat with the given lock configuration"""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="TheOverSwitchMockName",
        unique_id="uniqueId",
        data={
            "name": "TheOverSwitchMockName",
            "thermostat_type": "thermostat_over_switch",
            "temperature_sensor_entity_id": "sensor.mock_temp_sensor",
            "external_temperature_sensor_entity_id": "sensor.mock_ext_temp_sensor",
            "cycle_min": 5,
            "temp_min": 15,
            "temp_max": 30,
            "use_window_feature": False,
            "use_motion_feature": False,
            "use_power_feature": False,
            "use_presence_feature": False,
            CONF_UNDERLYING_LIST: ["switch.mock_switch"],
            "proportional_function": "tpi",
            "tpi_coef_int": 0.3,
            "tpi_coef_ext": 0.01,
            "minimal_activation_delay": 30,
            "minimal_deactivation_delay": 0,
            "security_delay_min": 5,  # 5 minutes
            "security_min_on_percent": 0.2,
            "security_default_on_percent": 0.1,
            CONF_LOCK_USERS: lock_users,
            CONF_LOCK_AUTOMATIONS: lock_automations,
            CONF_LOCK_CODE: lock_code,
        },
    )

    entity: BaseThermostat = await create_thermostat(
        hass, entry, "climate.theoverswitchmockname"
    )
    return entity


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lock_feature_services(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the lock feature and services (legacy, no code)"""
    entity = await setup_thermostat(hass, True, True, None)
    assert entity

    # 1. Test that lock is off by default
    assert entity.lock_manager.is_locked is False

    # 2. Test the lock service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: "climate.theoverswitchmockname"},
        blocking=True,
    )
    assert entity.lock_manager.is_locked is True

    # 3. Test the unlock service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: "climate.theoverswitchmockname"},
        blocking=True,
    )
    assert entity.lock_manager.is_locked is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lock_code_feature_services_with_code(hass: HomeAssistant, skip_hass_states_is_state):
    """Test the lock feature services with a lock code"""
    LOCK_CODE = "1234"
    entity = await setup_thermostat(hass, True, True, LOCK_CODE)
    assert entity
    entity_id = "climate.theoverswitchmockname"

    # 1. Test that lock is off by default
    assert entity.lock_manager.is_locked is False

    # 2. Test lock service: correct code
    await hass.services.async_call(
        DOMAIN,
        SERVICE_LOCK,
        {ATTR_ENTITY_ID: entity_id, "code": LOCK_CODE},
        blocking=True,
    )
    assert entity.lock_manager.is_locked is True

    # 3. Test unlock service: incorrect code -> should fail/remain locked
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: entity_id, "code": "9999"},
            blocking=True,
        )
    assert entity.lock_manager.is_locked is True  # Should remain locked

    # 4. Test unlock service: missing code -> should fail/remain locked
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_UNLOCK,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
    assert entity.lock_manager.is_locked is True  # Should remain locked

    # 5. Test unlock service: correct code -> should unlock
    await hass.services.async_call(
        DOMAIN,
        SERVICE_UNLOCK,
        {ATTR_ENTITY_ID: entity_id, "code": LOCK_CODE},
        blocking=True,
    )
    assert entity.lock_manager.is_locked is False


@pytest.mark.parametrize("expected_lingering_tasks", [True])
@pytest.mark.parametrize("expected_lingering_timers", [True])
@pytest.mark.parametrize(
    "lock_users, lock_automations, is_user_context, is_automation_context, should_be_locked",
    [
        (True, True, True, False, True),
        (True, True, False, True, True),
        (True, False, True, False, True),
        (True, False, False, True, False),
        (False, True, True, False, False),
        (False, True, False, True, True),
    ],
)
async def test_lock_feature_behavior(
    hass: HomeAssistant,
    skip_hass_states_is_state,
    lock_users,
    lock_automations,
    is_user_context,
    is_automation_context,
    should_be_locked,
):
    """Test the lock feature behavior for users and automations (legacy, no code)"""
    entity = await setup_thermostat(hass, lock_users, lock_automations, None)
    assert entity

    # Lock the thermostat
    entity.lock_manager.change_lock_state(True)
    assert entity.lock_manager.is_locked is True

    # Create a context
    context = Context()
    if is_user_context:
        context.user_id = "a_user_id"
    if is_automation_context:
        context.parent_id = "a_parent_id"

    # Initial state
    initial_preset = entity.preset_mode
    initial_hvac_mode = entity.hvac_mode
    initial_temperature = entity.target_temperature

    # Try to change preset
    with patch.object(entity, "_context", context):
        await entity.async_set_preset_mode(PRESET_BOOST)
    if should_be_locked:
        assert entity.preset_mode == initial_preset
    else:
        assert entity.preset_mode == PRESET_BOOST

    # Try to change HVAC mode
    with patch.object(entity, "_context", context):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
    if should_be_locked:
        assert entity.hvac_mode == initial_hvac_mode
    else:
        assert entity.hvac_mode == HVACMode.HEAT

    # Try to change temperature
    new_temp = 25
    with patch.object(entity, "_context", context):
        await entity.async_set_temperature(temperature=new_temp)
    if should_be_locked:
        assert entity.target_temperature == initial_temperature
    else:
        assert entity.target_temperature == new_temp

    # Test unlock allows changes
    entity.lock_manager.change_lock_state(False)
    assert entity.lock_manager.is_locked is False

    with patch.object(entity, "_context", context):
        await entity.async_set_preset_mode(PRESET_BOOST)
    assert entity.preset_mode == PRESET_BOOST

    with patch.object(entity, "_context", context):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
    assert entity.hvac_mode == HVACMode.HEAT

    with patch.object(entity, "_context", context):
        await entity.async_set_temperature(temperature=new_temp)
    assert entity.target_temperature == new_temp
