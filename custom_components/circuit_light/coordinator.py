from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    ATTR_RGB_COLOR,
    ATTR_XY_COLOR,
    ColorMode,
    LightEntityFeature,
)
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_COLOR_TEMP_MIREDS,
    CONF_BULB_ENTITIES,
    CONF_POWER_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BulbSnapshot:
    entity_id: str
    state: str | None
    attributes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CircuitLightSnapshot:
    power_entity_id: str
    bulb_entity_ids: tuple[str, ...]
    power_state: str | None
    bulbs: tuple[BulbSnapshot, ...]


class CircuitLightCoordinator(DataUpdateCoordinator[CircuitLightSnapshot]):
    """Push-updated coordinator that snapshots underlying entity states."""

    def __init__(self, hass: HomeAssistant, *, entry_id: str, entry_data: dict[str, Any]) -> None:
        super().__init__(hass, logger=_LOGGER, name=f"{DOMAIN}-{entry_id}")
        self._power_entity_id: str = entry_data[CONF_POWER_ENTITY]
        self._bulb_entity_ids: tuple[str, ...] = tuple(entry_data[CONF_BULB_ENTITIES])
        self._unsub: Any | None = None

    @property
    def power_entity_id(self) -> str:
        return self._power_entity_id

    @property
    def bulb_entity_ids(self) -> tuple[str, ...]:
        return self._bulb_entity_ids

    async def async_config_entry_first_refresh(self) -> None:
        await super().async_config_entry_first_refresh()
        self._unsub = async_track_state_change_event(
            self.hass,
            [self._power_entity_id, *self._bulb_entity_ids],
            self._async_state_changed,
        )

    async def async_shutdown(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _async_update_data(self) -> CircuitLightSnapshot:
        power_state_obj = self.hass.states.get(self._power_entity_id)
        bulbs: list[BulbSnapshot] = []
        for entity_id in self._bulb_entity_ids:
            st = self.hass.states.get(entity_id)
            bulbs.append(
                BulbSnapshot(
                    entity_id=entity_id,
                    state=None if st is None else st.state,
                    attributes={} if st is None else dict(st.attributes),
                )
            )

        return CircuitLightSnapshot(
            power_entity_id=self._power_entity_id,
            bulb_entity_ids=self._bulb_entity_ids,
            power_state=None if power_state_obj is None else power_state_obj.state,
            bulbs=tuple(bulbs),
        )

    @callback
    def _async_state_changed(self, _event: Any) -> None:
        self.async_set_updated_data(self._snapshot_now())

    def _snapshot_now(self) -> CircuitLightSnapshot:
        power_state_obj = self.hass.states.get(self._power_entity_id)
        bulbs: list[BulbSnapshot] = []
        for entity_id in self._bulb_entity_ids:
            st = self.hass.states.get(entity_id)
            bulbs.append(
                BulbSnapshot(
                    entity_id=entity_id,
                    state=None if st is None else st.state,
                    attributes={} if st is None else dict(st.attributes),
                )
            )
        return CircuitLightSnapshot(
            power_entity_id=self._power_entity_id,
            bulb_entity_ids=self._bulb_entity_ids,
            power_state=None if power_state_obj is None else power_state_obj.state,
            bulbs=tuple(bulbs),
        )


def snapshot_is_on(data: CircuitLightSnapshot | None) -> bool:
    return data is not None and data.power_state == STATE_ON


def snapshot_available(data: CircuitLightSnapshot | None) -> bool:
    return data is not None and data.power_state not in (None, STATE_UNAVAILABLE)


def snapshot_brightness(data: CircuitLightSnapshot | None) -> int | None:
    if data is None:
        return None
    values: list[int] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        b = bulb.attributes.get(ATTR_BRIGHTNESS)
        if isinstance(b, int):
            values.append(b)
    return None if not values else round(sum(values) / len(values))


def snapshot_color_temp(data: CircuitLightSnapshot | None) -> float | None:
    if data is None:
        return None
    values: list[float] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        ct_mireds = bulb.attributes.get(ATTR_COLOR_TEMP_MIREDS)
        if isinstance(ct_mireds, (int, float)):
            values.append(float(ct_mireds))
            continue
        ct_kelvin = bulb.attributes.get(ATTR_COLOR_TEMP_KELVIN)
        if isinstance(ct_kelvin, (int, float)) and ct_kelvin > 0:
            # Convert kelvin -> mireds for the legacy `color_temp` property.
            values.append(1_000_000.0 / float(ct_kelvin))
    return None if not values else sum(values) / len(values)


def snapshot_color_temp_kelvin(data: CircuitLightSnapshot | None) -> int | None:
    """Return average color temperature in kelvin, if available."""
    if data is None:
        return None
    values: list[float] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        ct_kelvin = bulb.attributes.get(ATTR_COLOR_TEMP_KELVIN)
        if isinstance(ct_kelvin, (int, float)) and ct_kelvin > 0:
            values.append(float(ct_kelvin))
            continue
        ct_mireds = bulb.attributes.get(ATTR_COLOR_TEMP_MIREDS)
        if isinstance(ct_mireds, (int, float)) and ct_mireds > 0:
            values.append(1_000_000.0 / float(ct_mireds))
    return None if not values else round(sum(values) / len(values))


def snapshot_min_color_temp_kelvin(data: CircuitLightSnapshot | None) -> int | None:
    if data is None:
        return None
    values: list[int] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        v = bulb.attributes.get("min_color_temp_kelvin")
        if isinstance(v, int):
            values.append(v)
    return None if not values else min(values)


def snapshot_max_color_temp_kelvin(data: CircuitLightSnapshot | None) -> int | None:
    if data is None:
        return None
    values: list[int] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        v = bulb.attributes.get("max_color_temp_kelvin")
        if isinstance(v, int):
            values.append(v)
    return None if not values else max(values)


def snapshot_xy_color(data: CircuitLightSnapshot | None) -> tuple[float, float] | None:
    if data is None:
        return None
    x: list[float] = []
    y: list[float] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        xy = bulb.attributes.get(ATTR_XY_COLOR)
        if (
            isinstance(xy, (list, tuple))
            and len(xy) == 2
            and isinstance(xy[0], (int, float))
            and isinstance(xy[1], (int, float))
        ):
            x.append(float(xy[0]))
            y.append(float(xy[1]))
    return None if not x else (sum(x) / len(x), sum(y) / len(y))


def snapshot_rgb_color(data: CircuitLightSnapshot | None) -> tuple[int, int, int] | None:
    if data is None:
        return None
    r: list[int] = []
    g: list[int] = []
    b: list[int] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        rgb = bulb.attributes.get(ATTR_RGB_COLOR)
        if (
            isinstance(rgb, (list, tuple))
            and len(rgb) == 3
            and all(isinstance(v, int) for v in rgb)
        ):
            r.append(rgb[0])
            g.append(rgb[1])
            b.append(rgb[2])
    return None if not r else (round(sum(r) / len(r)), round(sum(g) / len(g)), round(sum(b) / len(b)))


def snapshot_hs_color(data: CircuitLightSnapshot | None) -> tuple[float, float] | None:
    if data is None:
        return None
    h: list[float] = []
    s: list[float] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        hsv = bulb.attributes.get(ATTR_HS_COLOR)
        if (
            isinstance(hsv, (list, tuple))
            and len(hsv) == 2
            and isinstance(hsv[0], (int, float))
            and isinstance(hsv[1], (int, float))
        ):
            h.append(float(hsv[0]))
            s.append(float(hsv[1]))
    return None if not h else (sum(h) / len(h), sum(s) / len(s))


def snapshot_supported_color_modes(data: CircuitLightSnapshot | None) -> set[ColorMode | str]:
    if data is None:
        return {ColorMode.ONOFF}
    out: set[ColorMode | str] = set()
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        scm = bulb.attributes.get("supported_color_modes")
        if isinstance(scm, (list, set, tuple)):
            out.update(scm)
        else:
            cm = bulb.attributes.get("color_mode")
            if cm is not None:
                out.add(cm)
    return out or {ColorMode.ONOFF}


def snapshot_color_mode(data: CircuitLightSnapshot | None) -> ColorMode | str:
    if data is None:
        return ColorMode.ONOFF
    modes: list[ColorMode | str] = []
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        cm = bulb.attributes.get("color_mode")
        if cm is not None:
            modes.append(cm)
    if not modes:
        return ColorMode.ONOFF
    return max(set(modes), key=modes.count)


def snapshot_supported_features(data: CircuitLightSnapshot | None) -> LightEntityFeature:
    if data is None:
        return LightEntityFeature(0)
    features = LightEntityFeature(0)
    transition_supported = False
    for bulb in data.bulbs:
        if bulb.state in (None, STATE_UNAVAILABLE):
            continue
        raw = bulb.attributes.get("supported_features", 0)
        if isinstance(raw, int):
            features |= LightEntityFeature(raw)
            if raw & LightEntityFeature.TRANSITION:
                transition_supported = True
    features |= LightEntityFeature.EFFECT
    if transition_supported:
        features |= LightEntityFeature.TRANSITION
    return features

