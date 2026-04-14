from __future__ import annotations

import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from homeassistant.components.light import EFFECT_OFF


async def test_turn_on_with_effect_off_cancels_effect_and_returns(
    hass: HomeAssistant, setup_integration
) -> None:
    entity_reg = er.async_get(hass)
    parent = next(
        e
        for e in entity_reg.entities.values()
        if e.config_entry_id == setup_integration.entry_id and e.domain == "light"
    ).entity_id

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": parent, "effect": "Rainbow Chase"},
        blocking=True,
    )
    await hass.async_block_till_done()
    await asyncio.sleep(0)

    await hass.services.async_call(
        "light",
        "turn_on",
        {"entity_id": parent, "effect": EFFECT_OFF},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(parent)
    assert state is not None
    assert state.attributes.get("effect") == EFFECT_OFF


async def test_bare_turn_on_calls_power_and_bulbs(hass: HomeAssistant, setup_integration, monkeypatch) -> None:
    entity_reg = er.async_get(hass)
    parent = next(
        e
        for e in entity_reg.entities.values()
        if e.config_entry_id == setup_integration.entry_id and e.domain == "light"
    ).entity_id

    calls: list[tuple[str, str, dict]] = []
    orig_async_call = type(hass.services).async_call

    async def _spy(self, domain: str, service: str, service_data: dict | None = None, **kwargs):
        calls.append((domain, service, dict(service_data or {})))
        return await orig_async_call(self, domain, service, service_data, **kwargs)

    monkeypatch.setattr(type(hass.services), "async_call", _spy)

    await hass.services.async_call("light", "turn_on", {"entity_id": parent}, blocking=True)
    await hass.async_block_till_done()

    assert ("switch", "turn_on", {"entity_id": "switch.relay"}) in calls
    assert ("light", "turn_on", {"entity_id": ["light.bulb_1", "light.bulb_2"]}) in calls

