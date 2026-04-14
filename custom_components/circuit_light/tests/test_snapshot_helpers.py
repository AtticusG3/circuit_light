from __future__ import annotations

import pytest

from homeassistant.components.light import ColorMode, LightEntityFeature
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE

from custom_components.circuit_light.coordinator import (
    BulbSnapshot,
    CircuitLightSnapshot,
    snapshot_available,
    snapshot_brightness,
    snapshot_color_mode,
    snapshot_color_temp,
    snapshot_color_temp_kelvin,
    snapshot_hs_color,
    snapshot_is_on,
    snapshot_max_color_temp_kelvin,
    snapshot_min_color_temp_kelvin,
    snapshot_rgb_color,
    snapshot_supported_color_modes,
    snapshot_supported_features,
    snapshot_xy_color,
)


def _snap(*bulbs: BulbSnapshot, power_state: str | None = STATE_ON) -> CircuitLightSnapshot:
    return CircuitLightSnapshot(
        power_entity_id="switch.relay",
        bulb_entity_ids=tuple(b.entity_id for b in bulbs),
        power_state=power_state,
        bulbs=tuple(bulbs),
    )


def test_snapshot_availability_and_on_state() -> None:
    assert snapshot_is_on(None) is False
    assert snapshot_available(None) is False

    assert snapshot_is_on(_snap(power_state=STATE_ON)) is True
    assert snapshot_available(_snap(power_state=STATE_ON)) is True
    assert snapshot_available(_snap(power_state=None)) is False
    assert snapshot_available(_snap(power_state=STATE_UNAVAILABLE)) is False


def test_snapshot_brightness_averages_and_skips_unavailable() -> None:
    data = _snap(
        BulbSnapshot("light.a", "on", {"brightness": 100}),
        BulbSnapshot("light.b", STATE_UNAVAILABLE, {"brightness": 200}),
        BulbSnapshot("light.c", "on", {"brightness": 201}),
    )
    assert snapshot_brightness(data) == 150
    assert snapshot_brightness(_snap(BulbSnapshot("light.a", STATE_UNAVAILABLE, {}))) is None
    assert snapshot_brightness(None) is None


def test_snapshot_color_temp_mireds_and_kelvin_conversion() -> None:
    data = _snap(
        BulbSnapshot("light.a", "on", {"color_temp": 200.0}),
        BulbSnapshot("light.b", "on", {"color_temp_kelvin": 4000}),
        BulbSnapshot("light.c", STATE_UNAVAILABLE, {"color_temp": 100.0}),
    )
    # average of 200 mired + (1_000_000 / 4000 = 250 mired) => 225
    assert snapshot_color_temp(data) == 225.0
    assert snapshot_color_temp(None) is None


def test_snapshot_color_temp_kelvin_prefers_kelvin_and_converts_mireds() -> None:
    data = _snap(
        BulbSnapshot("light.a", "on", {"color_temp_kelvin": 4000}),
        BulbSnapshot("light.b", "on", {"color_temp": 250}),
        BulbSnapshot("light.c", STATE_UNAVAILABLE, {"color_temp_kelvin": 1234}),
    )
    # 4000K and 1_000_000/250=4000K -> avg 4000K
    assert snapshot_color_temp_kelvin(data) == 4000
    assert snapshot_color_temp_kelvin(None) is None


def test_snapshot_min_max_color_temp_kelvin() -> None:
    data = _snap(
        BulbSnapshot("light.a", "on", {"min_color_temp_kelvin": 2000, "max_color_temp_kelvin": 6000}),
        BulbSnapshot("light.b", "on", {"min_color_temp_kelvin": 2500, "max_color_temp_kelvin": 5500}),
        BulbSnapshot("light.c", STATE_UNAVAILABLE, {"min_color_temp_kelvin": 1000, "max_color_temp_kelvin": 7000}),
    )
    assert snapshot_min_color_temp_kelvin(data) == 2000
    assert snapshot_max_color_temp_kelvin(data) == 6000
    assert snapshot_min_color_temp_kelvin(None) is None
    assert snapshot_max_color_temp_kelvin(None) is None


def test_snapshot_color_xy_rgb_hs_and_modes() -> None:
    data = _snap(
        BulbSnapshot(
            "light.a",
            "on",
            {
                "xy_color": (0.1, 0.2),
                "rgb_color": (10, 20, 30),
                "hs_color": (100.0, 50.0),
                "supported_color_modes": [ColorMode.RGB, ColorMode.HS],
                "color_mode": ColorMode.RGB,
                "supported_features": int(LightEntityFeature.TRANSITION),
            },
        ),
        BulbSnapshot(
            "light.b",
            "on",
            {
                "xy_color": [0.3, 0.4],
                "rgb_color": [40, 50, 60],
                "hs_color": [200, 25],
                "color_mode": ColorMode.HS,
                "supported_features": 0,
            },
        ),
        BulbSnapshot("light.c", STATE_UNAVAILABLE, {"xy_color": (0.9, 0.9)}),
    )

    assert snapshot_xy_color(data) == pytest.approx((0.2, 0.3))
    assert snapshot_rgb_color(data) == (25, 35, 45)
    assert snapshot_hs_color(data) == (150.0, 37.5)
    assert snapshot_xy_color(None) is None
    assert snapshot_rgb_color(None) is None
    assert snapshot_hs_color(None) is None

    assert snapshot_supported_color_modes(data) >= {ColorMode.RGB, ColorMode.HS}
    assert snapshot_supported_color_modes(None) == {ColorMode.ONOFF}

    # Most common color_mode in this snapshot is a tie; set() + max(count) returns one of them.
    assert snapshot_color_mode(data) in (ColorMode.RGB, ColorMode.HS)
    assert snapshot_color_mode(None) == ColorMode.ONOFF

    feats = snapshot_supported_features(data)
    assert feats & LightEntityFeature.EFFECT
    assert feats & LightEntityFeature.TRANSITION
    assert snapshot_supported_features(None) == LightEntityFeature(0)

