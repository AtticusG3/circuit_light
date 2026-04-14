from __future__ import annotations

import asyncio

import pytest

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant

from custom_components.circuit_light import effects as effects_mod


class _StopEffect(Exception):
    """Used to break infinite loops in effect coroutines."""


async def _sleep_stop(*_args, **_kwargs):
    raise _StopEffect


async def test_sleep_stop_helper_raises() -> None:
    with pytest.raises(_StopEffect):
        await _sleep_stop()


async def test_available_bulbs_filters_unavailable(hass: HomeAssistant) -> None:
    hass.states.async_set("light.a", "on")
    hass.states.async_set("light.b", STATE_UNAVAILABLE)
    assert effects_mod._available_bulbs(hass, ("light.a", "light.b", "light.c")) == ["light.a"]


@pytest.mark.parametrize(
    "effect_fn",
    [
        effects_mod.effect_christmas_lights,
        effects_mod.effect_colour_cycle,
        effects_mod.effect_rainbow_chase,
        effects_mod.effect_colour_wipe,
        effects_mod.effect_strobe,
        effects_mod.effect_candle_flicker,
        effects_mod.effect_police,
        effects_mod.effect_warm_fade,
    ],
)
async def test_each_effect_ticks_once_and_issues_service_calls(
    hass: HomeAssistant, monkeypatch, effect_fn
) -> None:
    # Two bulbs available; order matters (config-flow order), so keep tuple stable.
    hass.states.async_set("light.b1", "on")
    hass.states.async_set("light.b2", "on")

    calls: list[tuple[str, str, dict]] = []

    async def _spy(self, domain: str, service: str, service_data: dict | None = None, **kwargs):
        if domain == "light" and service in ("turn_on", "turn_off"):
            calls.append((domain, service, dict(service_data or {})))
        return None

    monkeypatch.setattr(type(hass.services), "async_call", _spy)
    stop_after = {
        effects_mod.effect_strobe: 2,        # on -> sleep -> off -> sleep
        effects_mod.effect_police: 2,        # first colors -> sleep -> swap -> sleep
        effects_mod.effect_warm_fade: 2,     # increasing -> sleep -> decreasing -> sleep
        effects_mod.effect_colour_wipe: 2,   # position increments; second loop triggers reset path
    }.get(effect_fn, 1)

    class _AIO:
        def __init__(self) -> None:
            self.calls = 0

        async def sleep(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls >= stop_after:
                raise _StopEffect
            return None

    monkeypatch.setattr(effects_mod, "asyncio", _AIO())

    # Make random deterministic for candle flicker.
    monkeypatch.setattr(effects_mod.random, "randint", lambda a, b: a)
    monkeypatch.setattr(effects_mod.random, "uniform", lambda a, b: a)
    if effect_fn is effects_mod.effect_warm_fade:
        # Make min/max kelvin equal so the decreasing branch reaches the <= min check quickly.
        monkeypatch.setattr(effects_mod, "color_temperature_mired_to_kelvin", lambda _m: 6500)

    with pytest.raises(_StopEffect):
        await effect_fn(hass, ("light.b1", "light.b2"))

    # Some effects may start with "turn_off" calls (colour_wipe/strobe), but every effect should
    # attempt at least one service call before the first sleep.
    assert calls


async def test_effects_handle_no_available_bulbs_branch(hass: HomeAssistant, monkeypatch) -> None:
    hass.states.async_set("light.b1", STATE_UNAVAILABLE)

    for fn in (
        effects_mod.effect_rainbow_chase,
        effects_mod.effect_colour_wipe,
        effects_mod.effect_candle_flicker,
        effects_mod.effect_police,
        effects_mod.effect_warm_fade,
    ):
        class _AIO:
            def __init__(self) -> None:
                self.calls = 0

            async def sleep(self, *_args, **_kwargs):
                self.calls += 1
                if self.calls >= 2:
                    raise _StopEffect
                return None

        monkeypatch.setattr(effects_mod, "asyncio", _AIO())
        with pytest.raises(_StopEffect):
            await fn(hass, ("light.b1",))


async def test_async_run_effect_noop_for_unknown_effect(hass: HomeAssistant) -> None:
    await effects_mod.async_run_effect(
        hass,
        effect_name="Not a real effect",
        bulb_entity_ids=("light.b1",),
    )
    await hass.async_block_till_done()

