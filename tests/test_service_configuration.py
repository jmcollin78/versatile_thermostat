# pylint: disable=wildcard-import, unused-wildcard-import, protected-access, unused-argument, line-too-long

""" Test the parsing of the central boiler service configuration """
import pytest

from custom_components.versatile_thermostat.commons import check_and_extract_service_configuration
from custom_components.versatile_thermostat.const import ServiceConfigurationError

TEMPLATE = "{{ state_attr('climate.hc1','current_temperature') | float + 1 }}"


def test_service_config_legacy_formats_unchanged():
    """Strings without a template give exactly the same dict as before"""
    assert check_and_extract_service_configuration("switch.x/switch.turn_on") == {
        "service_domain": "switch",
        "service_name": "turn_on",
        "entity_domain": "switch",
        "entity_name": "x",
        "entity_id": "switch.x",
        "data": {},
    }
    assert check_and_extract_service_configuration("climate.x/climate.set_hvac_mode/hvac_mode:heat") == {
        "service_domain": "climate",
        "service_name": "set_hvac_mode",
        "entity_domain": "climate",
        "entity_name": "x",
        "entity_id": "climate.x",
        "attribute_name": "hvac_mode",
        "attribute_value": "heat",
        "data": {"hvac_mode": "heat"},
    }
    assert check_and_extract_service_configuration("climate.x/climate.set_temperature/temperature: 23 ") == {
        "service_domain": "climate",
        "service_name": "set_temperature",
        "entity_domain": "climate",
        "entity_name": "x",
        "entity_id": "climate.x",
        "attribute_name": "temperature",
        "attribute_value": "23",
        "data": {"temperature": "23"},
    }
    assert check_and_extract_service_configuration(None) == {}
    assert not check_and_extract_service_configuration("switch.x/switch.turn_on").get("is_template")


def test_service_config_legacy_extra_parts_unchanged():
    """Legacy strings with extra '/' or ':' keep their previous behavior"""
    # a 4th part was silently ignored (no data)
    assert check_and_extract_service_configuration("switch.x/switch.turn_on/a:b/c")["data"] == {}
    # a second ':' was an error
    with pytest.raises(ServiceConfigurationError):
        check_and_extract_service_configuration("climate.x/climate.set_temperature/temperature:1:2")


def test_service_config_template_value():
    """A template is kept as is in the value"""
    ret = check_and_extract_service_configuration(f"climate.hc1/climate.set_temperature/temperature:{TEMPLATE}")
    assert ret["attribute_name"] == "temperature"
    assert ret["attribute_value"] == TEMPLATE
    assert ret["data"] == {"temperature": TEMPLATE}
    assert ret["is_template"] is True
    assert ret["entity_id"] == "climate.hc1"
    assert ret["service_name"] == "set_temperature"


def test_service_config_template_with_slash_and_colon():
    """A template can contain '/' and ':'"""
    value = "{{ (states('sensor.a') | float / 2) }}"
    ret = check_and_extract_service_configuration(f"climate.hc1/climate.set_temperature/temperature:{value}")
    assert ret["data"] == {"temperature": value}
    assert ret["is_template"] is True

    value = "{{ {'a': 1}['a'] + states('sensor.a')[0:1] | float }}"
    ret = check_and_extract_service_configuration(f"climate.hc1/climate.set_temperature/temperature:{value}")
    assert ret["data"] == {"temperature": value}
    assert ret["is_template"] is True


def test_service_config_block_template_value():
    """A block-only template ({% ... %}) is detected as a template"""
    value = "{% if is_state('input_boolean.eco', 'on') %}18{% else %}21{% endif %}"
    ret = check_and_extract_service_configuration(f"climate.hc1/climate.set_temperature/temperature:{value}")
    assert ret["data"] == {"temperature": value}
    assert ret["is_template"] is True

    value = "{% set t = states('sensor.a') | float(20) %}{{ t / 2 }}"
    ret = check_and_extract_service_configuration(f"climate.hc1/climate.set_temperature/temperature:{value}")
    assert ret["data"] == {"temperature": value}
    assert ret["is_template"] is True


@pytest.mark.parametrize(
    "bad",
    [
        "switch.x",
        "switch/switch.turn_on",
        "switch.x/turn_on",
        "switch.x/switch.turn_on/",
        "switch.x/switch.turn_on/temperature:",
        "switch.x/switch.turn_on/:5",
        "switch.x/switch.turn_on/temperature",
    ],
)
def test_service_config_errors(bad):
    """Existing error cases still raise"""
    with pytest.raises(ServiceConfigurationError):
        check_and_extract_service_configuration(bad)
