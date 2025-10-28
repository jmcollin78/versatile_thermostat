#import logging
from types import MappingProxyType
from typing import Any, TypeVar

from .underlyings import UnderlyingEntity

ConfigData = MappingProxyType[str, Any]
T = TypeVar("T", bound=UnderlyingEntity)

# _LOGGER = logging.getLogger(__name__)