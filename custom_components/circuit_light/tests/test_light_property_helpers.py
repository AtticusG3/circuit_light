from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant

from custom_components.circuit_light.light import CircuitLight


async def test_light_properties_delegate_to_snapshot_helpers(hass: HomeAssistant, setup_integration) -> None:
    entry = setup_integration
    coordinator = hass.data["circuit_light"][entry.entry_id].coordinator

    # Add richer attributes to the underlying bulbs so properties have data.
    hass.states.async_set(
        "light.bulb_1",
        "on",
        {
            "brightness": 100,
            "color_temp_kelvin": 4000,
            "min_color_temp_kelvin": 2000,
            "max_color_temp_kelvin": 6000,
            "hs_color": (10.0, 20.0),
            "xy_color": (0.1, 0.2),
            "rgb_color": (1, 2, 3),
            "supported_color_modes": ["rgb"],
            "color_mode": "rgb",
        },
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0)

    ent = CircuitLight(entry, coordinator)
    assert ent.color_temp_kelvin == 4000
    assert ent.min_color_temp_kelvin == 2000
    assert ent.max_color_temp_kelvin == 6000
    assert ent.hs_color is not None
    assert ent.xy_color is not None
    assert ent.rgb_color is not None


async def test_cancel_effect_task_handles_cancelled_error(hass: HomeAssistant, setup_integration, monkeypatch) -> None:
    entry = setup_integration
    coordinator = hass.data["circuit_light"][entry.entry_id].coordinator
    ent = CircuitLight(entry, coordinator)

    async def _never():
        await asyncio.sleep(999)

    task = hass.async_create_task(_never())
    ent._attr_effect = "Rainbow Chase"
    ent._effect_task = task

    wrote: list[bool] = []
    monkeypatch.setattr(ent, "async_write_ha_state", lambda: wrote.append(True))

    await ent._async_cancel_effect_task()
    assert wrote

