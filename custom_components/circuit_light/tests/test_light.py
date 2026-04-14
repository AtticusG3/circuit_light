from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.components.light import EFFECT_OFF

from homeassistant.helpers import entity_registry as er

from custom_components.circuit_light.effects import EFFECT_LIST


async def test_light_entity_uses_coordinator_data(hass: HomeAssistant, setup_integration) -> None:
    state = hass.states.get("light.circuit_light")
    # Entity id is created by HA; for custom components, default entity_id is derived from name/title.
    # To avoid brittle assumptions about entity_id generation, locate it by unique_id.
    entity_reg = er.async_get(hass)
    reg_entry = next(
        e
        for e in entity_reg.entities.values()
        if e.config_entry_id == setup_integration.entry_id and e.domain == "light"
    )
    state = hass.states.get(reg_entry.entity_id)
    assert state is not None

    # Power is 'on' from conftest, so combined should be on.
    assert state.state == "on"

    # Brightness should be the average of 100 and 200 (rounds to 150).
    assert state.attributes.get("brightness") == 150


async def _get_parent_light_entity_id(hass: HomeAssistant, config_entry_id: str) -> str:
    entity_reg = er.async_get(hass)
    reg_entry = next(
        e
        for e in entity_reg.entities.values()
        if e.config_entry_id == config_entry_id and e.domain == "light"
    )
    return reg_entry.entity_id


async def test_effect_list_exact_and_no_effect_off(hass: HomeAssistant, setup_integration) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None

    assert state.attributes["effect_list"] == EFFECT_LIST
    assert EFFECT_OFF not in state.attributes["effect_list"]


async def test_effect_reports_effect_off_when_inactive(hass: HomeAssistant, setup_integration) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None

    assert state.attributes.get("effect") == EFFECT_OFF


async def test_starting_effect_sets_effect_state_and_restricts_color_mode(
    hass: HomeAssistant, setup_integration
) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Rainbow Chase"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("effect") == "Rainbow Chase"
    assert state.attributes.get("color_mode") in ("onoff", "brightness")


async def test_switching_effects_cancels_previous_task_cleanly(
    hass: HomeAssistant, setup_integration, monkeypatch
) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Rainbow Chase"},
        blocking=True,
    )
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Colour Wipe"},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Let background tasks tick at least once.
    await asyncio.sleep(0)

    # We should not end up with multiple overlapping effect tasks; the entity should
    # reflect the most recent effect selection.
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("effect") == "Colour Wipe"


async def test_static_turn_on_cancels_effect_before_applying_static_state(
    hass: HomeAssistant, setup_integration, monkeypatch
) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)

    # Start an effect.
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Colour Cycle"},
        blocking=True,
    )

    # Now request a static state (brightness), which must cancel the effect first.
    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "brightness": 123},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("effect") == EFFECT_OFF


async def test_turn_off_cancels_effect(hass: HomeAssistant, setup_integration) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Strobe"},
        blocking=True,
    )
    await hass.services.async_call(
        "light",
        "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes.get("effect") == EFFECT_OFF


async def test_effects_use_kelvin_color_temp_fields(
    hass: HomeAssistant, setup_integration, monkeypatch
) -> None:
    entity_id = await _get_parent_light_entity_id(hass, setup_integration.entry_id)

    calls: list[tuple[str, str, dict]] = []
    orig_async_call = type(hass.services).async_call

    async def _spy(self, domain: str, service: str, service_data: dict | None = None, **kwargs):
        if domain == "light" and service == "turn_on":
            calls.append((domain, service, dict(service_data or {})))
        return await orig_async_call(self, domain, service, service_data, **kwargs)

    monkeypatch.setattr(type(hass.services), "async_call", _spy)

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": entity_id, "effect": "Candle Flicker"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0)

    # If the effect did tick, it must use the Kelvin service field, not legacy mireds.
    for _domain, _service, data in calls:
        assert "color_temp" not in data
        if "color_temp_kelvin" in data:
            assert isinstance(data["color_temp_kelvin"], int)

