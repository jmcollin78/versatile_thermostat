""" Some usefull commons class """

# pylint: disable=line-too-long

import logging
import warnings

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_registry as er

from .const import ServiceConfigurationError, DOMAIN

_LOGGER = logging.getLogger(__name__)


def round_to_nearest(n: float, x: float) -> float:
    """Round a number to the nearest x (which should be decimal but not null)
    Example:
        nombre1 = 3.2
        nombre2 = 4.7
        x = 0.3

        nombre_arrondi1 = round_to_nearest(nombre1, x)
        nombre_arrondi2 = round_to_nearest(nombre2, x)

        print(nombre_arrondi1)  # Output: 3.3
        print(nombre_arrondi2)  # Output: 4.6
    """
    assert x > 0
    return round(n * (1 / x)) / (1 / x)


def check_and_extract_service_configuration(service_config) -> dict:
    """Raise a ServiceConfigurationError. In return you have a dict formatted like follows.
    Example if you call with 'climate.central_boiler/climate.set_temperature/temperature:10':
    {
        "service_domain": "climate",
        "service_name": "set_temperature",
        "entity_id": "climate.central_boiler",
        "entity_domain": "climate",
        "entity_name": "central_boiler",
        "data": {
            "temperature": "10"
        },
        "attribute_name": "temperature",
        "attribute_value: "10"
    }

    For this example 'switch.central_boiler/switch.turn_off' you will have this:
    {
        "service_domain": "switch",
        "service_name": "turn_off",
        "entity_id": "switch.central_boiler",
        "entity_domain": "switch",
        "entity_name": "central_boiler",
        "data": { },
    }

    All values are striped (white space are removed) and are string
    """

    ret = {}

    if service_config is None:
        return ret

    parties = service_config.split("/")
    if len(parties) < 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. Service {service_config} should be formatted with: 'entity_name/service_name[/data]'. See README for more information."
        )
    entity_id = parties[0]
    service_name = parties[1]

    service_infos = service_name.split(".")
    if len(service_infos) != 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. The service {service_config} should be formatted like: 'domain.service_name' (ex: 'switch.turn_on'). See README for more information."
        )

    ret.update(
        {
            "service_domain": service_infos[0].strip(),
            "service_name": service_infos[1].strip(),
        }
    )

    entity_infos = entity_id.split(".")
    if len(entity_infos) != 2:
        raise ServiceConfigurationError(
            f"Incorrect service configuration. The entity_id {entity_id} should be formatted like: 'domain.entity_name' (ex: 'switch.central_boiler_switch'). See README for more information."
        )

    ret.update(
        {
            "entity_domain": entity_infos[0].strip(),
            "entity_name": entity_infos[1].strip(),
            "entity_id": entity_id.strip(),
        }
    )

    if len(parties) == 3:
        data = parties[2]
        if len(data) > 0:
            data_infos = None
            data_infos = data.split(":")
            if (
                len(data_infos) != 2
                or len(data_infos[0]) <= 0
                or len(data_infos[1]) <= 0
            ):
                raise ServiceConfigurationError(
                    f"Incorrect service configuration. The data {data} should be formatted like: 'attribute:value' (ex: 'value:25'). See README for more information."
                )

            ret.update(
                {
                    "attribute_name": data_infos[0].strip(),
                    "attribute_value": data_infos[1].strip(),
                    "data": {data_infos[0].strip(): data_infos[1].strip()},
                }
            )
        else:
            raise ServiceConfigurationError(
                f"Incorrect service configuration. The data {data} should be formatted like: 'attribute:value' (ex: 'value:25'). See README for more information."
            )
    else:
        ret.update({"data": {}})

    _LOGGER.debug(
        "check_and_extract_service_configuration(%s) gives '%s'", service_config, ret
    )
    return ret


def deprecated(message):
    """A decorator to indicate that the method/attribut is deprecated"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} is deprecated: {message}",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


def write_event_log(logger: logging.Logger, vtherm: "BaseThermostat", message: str):
    """Write an event log entry for the thermostat."""
    logger.info("")
    logger.info("---------------------> NEW EVENT: %s - %s --------------------------------------------------------------", vtherm, message)


async def cleanup_orphan_entity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    domain: str,
    device_name: str,
    unique_id_suffix: str,
) -> None:
    """Remove an orphan entity from entity registry if it exists but is no longer needed.

    This generic function can be used for any entity type that needs to be
    conditionally created/removed based on configuration changes.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry for the thermostat.
        domain: The entity domain (e.g., "sensor", "binary_sensor", "switch").
        device_name: The device name used to build the unique_id.
        unique_id_suffix: The suffix appended to the device name (e.g., "auto_tpi_learning").
    """
    registry = er.async_get(hass)
    # Build the expected unique_id for the entity
    expected_unique_id = f"{device_name}_{unique_id_suffix}"

    # Find entity by unique_id within this config entry
    entity_id = registry.async_get_entity_id(
        domain, DOMAIN, expected_unique_id
    )

    if entity_id:
        entity_entry = registry.async_get(entity_id)
        if entity_entry and entity_entry.config_entry_id == entry.entry_id:
            _LOGGER.debug(
                "Removing orphan %s entity %s from registry (feature disabled)",
                domain,
                entity_id
            )
            registry.async_remove(entity_id)
