""" Some usefull commons class """

# pylint: disable=line-too-long

import logging
import warnings
from types import MappingProxyType
from typing import Any, TypeVar

from .const import ServiceConfigurationError
from .underlyings import UnderlyingEntity

ConfigData = MappingProxyType[str, Any]
T = TypeVar("T", bound=UnderlyingEntity)

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
