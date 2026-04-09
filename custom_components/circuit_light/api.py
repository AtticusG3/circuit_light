from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


class ApiError(Exception):
    """Base exception for Circuit Light API errors."""


class ApiAuthError(ApiError):
    """Raised when authentication is invalid/expired."""


class ApiConnectionError(ApiError):
    """Raised when a connection error occurs."""


class ApiRateLimitError(ApiError):
    """Raised when rate limited by upstream."""


class ApiValidationError(ApiError):
    """Raised when input validation fails."""


@dataclass(frozen=True, slots=True)
class CircuitLightConfig:
    """Validated Circuit Light configuration."""

    name: str
    power_entity_id: str
    bulb_entity_ids: tuple[str, ...]


async def async_validate_config(
    hass: HomeAssistant,
    *,
    name: str,
    power_entity_id: str,
    bulb_entity_ids: list[str],
) -> CircuitLightConfig:
    """Validate config against HA registries/state and return a normalized config.

    This integration has no external API; validation ensures selected entities exist.
    """
    entity_reg = er.async_get(hass)

    if not _entity_exists(hass, entity_reg, power_entity_id):
        raise ApiValidationError("invalid_power_entity")

    normalized_bulbs: list[str] = []
    for bulb_id in bulb_entity_ids:
        if not _entity_exists(hass, entity_reg, bulb_id):
            raise ApiValidationError("invalid_bulb_entities")
        normalized_bulbs.append(bulb_id)

    # Preserve user ordering (important for sequential effects).
    return CircuitLightConfig(
        name=name.strip(),
        power_entity_id=power_entity_id,
        bulb_entity_ids=tuple(normalized_bulbs),
    )


def _entity_exists(
    hass: HomeAssistant,
    entity_reg: er.EntityRegistry,
    entity_id: str,
) -> bool:
    return entity_reg.async_get(entity_id) is not None or hass.states.get(entity_id) is not None

