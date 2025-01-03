# pylint: disable=protected-access, unused-argument, line-too-long
""" Test the Central Power management """
from unittest.mock import patch, call, AsyncMock, MagicMock, PropertyMock
from datetime import datetime, timedelta
import logging

from custom_components.versatile_thermostat.thermostat_switch import (
    ThermostatOverSwitch,
)
from custom_components.versatile_thermostat.feature_power_manager import (
    FeaturePowerManager,
)
from custom_components.versatile_thermostat.central_feature_power_manager import (
    CentralFeaturePowerManager,
)
from custom_components.versatile_thermostat.prop_algorithm import PropAlgorithm
from .commons import *  # pylint: disable=wildcard-import, unused-wildcard-import

logging.getLogger().setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "use_power_feature, power_entity_id, max_power_entity_id, power_temp, is_configured",
    [
        (True, "sensor.power_id", "sensor.max_power_id", 13, True),
        (True, None, "sensor.max_power_id", 13, False),
        (True, "sensor.power_id", None, 13, False),
        (True, "sensor.power_id", "sensor.max_power_id", None, False),
        (False, "sensor.power_id", "sensor.max_power_id", 13, False),
    ],
)
async def test_central_power_manager_init(
    hass: HomeAssistant,
    use_power_feature,
    power_entity_id,
    max_power_entity_id,
    power_temp,
    is_configured,
):
    """Test creation and post_init of the Central Power Manager"""
    vtherm_api: VersatileThermostatAPI = MagicMock(spec=VersatileThermostatAPI)
    central_power_manager = CentralFeaturePowerManager(hass, vtherm_api)

    assert central_power_manager.is_configured is False
    assert central_power_manager.current_max_power is None
    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature is None
    assert central_power_manager.name == "centralPowerManager"

    # 2. post_init
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: power_entity_id,
            CONF_MAX_POWER_SENSOR: max_power_entity_id,
            CONF_USE_POWER_FEATURE: use_power_feature,
            CONF_PRESET_POWER: power_temp,
        }
    )

    assert central_power_manager.is_configured == is_configured
    assert central_power_manager.current_max_power is None
    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature == power_temp

    # 3. start listening
    central_power_manager.start_listening()
    assert len(central_power_manager._active_listener) == (2 if is_configured else 0)

    # 4. stop listening
    central_power_manager.stop_listening()
    assert len(central_power_manager._active_listener) == 0


@pytest.mark.parametrize(
    "vtherm_configs, results",
    [
        # simple sort
        (
            [
                {
                    "name": "vtherm1",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 13,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm2",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 18,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm3",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 12,
                    "target_temperature": 18,
                },
            ],
            ["vtherm2", "vtherm1", "vtherm3"],
        ),
        # Ignore power not configured and not on
        (
            [
                {
                    "name": "vtherm1",
                    "is_configured": False,
                    "is_on": True,
                    "current_temperature": 13,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm2",
                    "is_configured": True,
                    "is_on": False,
                    "current_temperature": 18,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm3",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 12,
                    "target_temperature": 18,
                },
            ],
            ["vtherm3"],
        ),
        # None current_temperature are in last
        (
            [
                {
                    "name": "vtherm1",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 13,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm2",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": None,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm3",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 12,
                    "target_temperature": 18,
                },
            ],
            ["vtherm1", "vtherm3", "vtherm2"],
        ),
        # None target_temperature are in last
        (
            [
                {
                    "name": "vtherm1",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 13,
                    "target_temperature": 12,
                },
                {
                    "name": "vtherm2",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 18,
                    "target_temperature": None,
                },
                {
                    "name": "vtherm3",
                    "is_configured": True,
                    "is_on": True,
                    "current_temperature": 12,
                    "target_temperature": 18,
                },
            ],
            ["vtherm1", "vtherm3", "vtherm2"],
        ),
    ],
)
async def test_central_power_manageer_find_vtherms(
    hass: HomeAssistant, vtherm_configs, results
):
    """Test the find_all_vtherm_with_power_management_sorted_by_dtemp"""
    vtherm_api: VersatileThermostatAPI = MagicMock(spec=VersatileThermostatAPI)
    central_power_manager = CentralFeaturePowerManager(hass, vtherm_api)

    vtherms = []
    for vtherm_config in vtherm_configs:
        vtherm = MagicMock(spec=BaseThermostat)
        type(vtherm).name = PropertyMock(return_value=vtherm_config.get("name"))
        type(vtherm).is_on = PropertyMock(return_value=vtherm_config.get("is_on"))
        type(vtherm).current_temperature = PropertyMock(
            return_value=vtherm_config.get("current_temperature")
        )
        type(vtherm).target_temperature = PropertyMock(
            return_value=vtherm_config.get("target_temperature")
        )
        type(vtherm.power_manager).is_configured = PropertyMock(
            return_value=vtherm_config.get("is_configured")
        )
        vtherms.append(vtherm)

    with patch(
        "custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.get_climate_components_entities",
        return_value=vtherms,
    ):
        vtherm_sorted = (
            central_power_manager.find_all_vtherm_with_power_management_sorted_by_dtemp()
        )

        # extract results
        vtherm_results = [vtherm.name for vtherm in vtherm_sorted]

        assert vtherm_results == results


@pytest.mark.parametrize(
    "current_power, current_max_power, vtherm_configs, expected_results",
    [
        # simple nominal test (no shedding)
        (
            1000,
            5000,
            [
                {
                    "name": "vtherm1",
                    "device_power": 100,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 0,
                    "is_overpowering_detected": False,
                },
            ],
            {},
        ),
        # Simple trivial shedding
        (
            1000,
            2000,
            [
                # should be overpowering
                {
                    "name": "vtherm1",
                    "device_power": 1100,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": False,
                },
                # should be overpowering with many underlmying entities
                {
                    "name": "vtherm2",
                    "device_power": 4000,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 4,
                    "on_percent": 0.1,
                    "is_overpowering_detected": False,
                },
                # over_climate should be overpowering
                {
                    "name": "vtherm3",
                    "device_power": 1000,
                    "is_device_active": False,
                    "is_over_climate": True,
                    "is_overpowering_detected": False,
                },
                # should pass but because will be also overpowering because previous was overpowering
                {
                    "name": "vtherm4",
                    "device_power": 800,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": False,
                },
            ],
            {"vtherm1": True, "vtherm2": True, "vtherm3": True, "vtherm4": True},
        ),
        # More complex shedding
        (
            1000,
            2000,
            [
                # already overpowering (non change)
                {
                    "name": "vtherm1",
                    "device_power": 1100,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": True,
                },
                # already overpowering and already active (can be un overpowered)
                {
                    "name": "vtherm2",
                    "device_power": 1100,
                    "is_device_active": True,
                    "is_over_climate": True,
                    "is_overpowering_detected": True,
                },
                # should terminate the overpowering
                {
                    "name": "vtherm3",
                    "device_power": 800,
                    "is_device_active": False,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": True,
                },
                # should terminate the overpowering and active
                {
                    "name": "vtherm4",
                    "device_power": 3800,
                    "is_device_active": True,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": True,
                },
            ],
            {"vtherm2": False, "vtherm3": False, "vtherm4": False},
        ),
        # More complex shedding
        (
            1000,
            2000,
            [
                # already overpowering (non change)
                {
                    "name": "vtherm1",
                    "device_power": 1100,
                    "is_device_active": True,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": True,
                },
                # should be overpowering
                {
                    "name": "vtherm2",
                    "device_power": 1800,
                    "is_device_active": False,
                    "is_over_climate": True,
                    "is_overpowering_detected": False,
                },
                # should terminate the overpowering and active but just before is overpowering
                {
                    "name": "vtherm3",
                    "device_power": 100,
                    "is_device_active": True,
                    "is_over_climate": False,
                    "nb_underlying_entities": 1,
                    "on_percent": 1,
                    "is_overpowering_detected": False,
                },
            ],
            {"vtherm1": False, "vtherm2": True, "vtherm3": True},
        ),
    ],
)
async def test_central_power_manageer_calculate_shedding(
    hass: HomeAssistant,
    current_power,
    current_max_power,
    vtherm_configs,
    expected_results,
):
    """Test the calculate_shedding of the CentralPowerManager"""
    vtherm_api: VersatileThermostatAPI = MagicMock(spec=VersatileThermostatAPI)
    central_power_manager = CentralFeaturePowerManager(hass, vtherm_api)

    registered_calls = {}

    def register_call(vtherm, overpowering):
        """Register a call to set_overpowering"""
        registered_calls.update({vtherm.name: overpowering})

    vtherms = []
    for vtherm_config in vtherm_configs:
        vtherm = MagicMock(spec=BaseThermostat)
        vtherm.name = vtherm_config.get("name")
        vtherm.is_device_active = vtherm_config.get("is_device_active")
        vtherm.is_over_climate = vtherm_config.get("is_over_climate")
        vtherm.nb_underlying_entities = vtherm_config.get("nb_underlying_entities")
        if not vtherm_config.get("is_over_climate"):
            vtherm.proportional_algorithm = MagicMock()
            vtherm.proportional_algorithm.on_percent = vtherm_config.get("on_percent")

        vtherm.power_manager = MagicMock(spec=FeaturePowerManager)
        vtherm.power_manager._vtherm = vtherm

        vtherm.power_manager.is_overpowering_detected = vtherm_config.get(
            "is_overpowering_detected"
        )
        vtherm.power_manager.device_power = vtherm_config.get("device_power")

        async def mock_set_overpowering(overpowering, v=vtherm):
            register_call(v, overpowering)

        vtherm.power_manager.set_overpowering = mock_set_overpowering

        vtherms.append(vtherm)

    type(central_power_manager).current_max_power = PropertyMock(
        return_value=current_max_power
    )
    type(central_power_manager).current_power = PropertyMock(return_value=current_power)
    type(central_power_manager).is_configured = PropertyMock(return_value=True)

    with patch(
        "custom_components.versatile_thermostat.central_feature_power_manager.CentralFeaturePowerManager.find_all_vtherm_with_power_management_sorted_by_dtemp",
        return_value=vtherms,
    ):

        await central_power_manager.calculate_shedding()

        # Check registered calls
        assert registered_calls == expected_results


async def test_central_power_manager_power_event(hass: HomeAssistant):
    """Tests the Power sensor event"""
    vtherm_api: VersatileThermostatAPI = MagicMock(spec=VersatileThermostatAPI)
    central_power_manager = CentralFeaturePowerManager(hass, vtherm_api)

    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature is None
    assert central_power_manager.name == "centralPowerManager"

    # 2. post_init
    central_power_manager.post_init(
        {
            CONF_POWER_SENSOR: power_entity_id,
            CONF_MAX_POWER_SENSOR: max_power_entity_id,
            CONF_USE_POWER_FEATURE: use_power_feature,
            CONF_PRESET_POWER: 13,
        }
    )

    assert central_power_manager.is_configured == True
    assert central_power_manager.current_max_power is None
    assert central_power_manager.current_power is None
    assert central_power_manager.power_temperature == 13

    # 3. start listening
    central_power_manager.start_listening()
    assert len(central_power_manager._active_listener) == 2

    tz = get_tz(hass)  # pylint: disable=invalid-name
    now: datetime = datetime.now(tz=tz)
