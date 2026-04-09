from __future__ import annotations

import asyncio
import random
from typing import Any

from homeassistant.const import STATE_UNAVAILABLE


EFFECT_LIST = [
    "Christmas Lights",
    "Colour Cycle",
    "Rainbow Chase",
    "Colour Wipe",
    "Strobe",
    "Candle Flicker",
    "Police",
    "Warm Fade",
]


async def effect_christmas_lights(entity: Any) -> None:
    """Christmas Lights effect."""
    colors = [
        (0, 100),      # Red
        (60, 100),     # Green
        (50, 80),      # Gold
        (0, 0),        # White
    ]
    offset = 0

    while True:
        for i, entity_id in enumerate(entity.bulb_entities):
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            color_index = (i + offset) % len(colors)
            hue, sat = colors[color_index]

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": [float(hue), float(sat)],
                },
                blocking=False,
            )

        offset = (offset + 1) % len(colors)
        await asyncio.sleep(30)


async def effect_colour_cycle(entity: Any) -> None:
    """Colour Cycle effect."""
    hue = 0

    while True:
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": [float(hue), 100.0],
                },
                blocking=False,
            )

        hue = (hue + 1) % 360
        await asyncio.sleep(0.1)  # 100ms


async def effect_rainbow_chase(entity: Any) -> None:
    """Rainbow Chase effect."""
    bulb_count = len(entity.bulb_entities)
    if bulb_count == 0:
        return

    offset = 0

    while True:
        for i, entity_id in enumerate(entity.bulb_entities):
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            # Distribute hues evenly across bulbs
            hue = int((i * 360 / bulb_count) + offset) % 360

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": [float(hue), 100.0],
                },
                blocking=False,
            )

        offset = (offset + 1) % 360
        await asyncio.sleep(0.08)  # 80ms


async def effect_colour_wipe(entity: Any) -> None:
    """Colour Wipe effect."""
    colors = [0, 120, 240]  # Red, Green, Blue
    color_index = 0
    position = 0
    bulb_count = len(entity.bulb_entities)

    if bulb_count == 0:
        return

    while True:
        # Turn off all bulbs first
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            await entity.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": entity_id},
                blocking=False,
            )

        # Turn on current bulb with current color
        if position < bulb_count:
            entity_id = entity.bulb_entities[position]
            state = entity.hass.states.get(entity_id)
            if state is not None and state.state != STATE_UNAVAILABLE:
                await entity.hass.services.async_call(
                    "light",
                    "turn_on",
                    {
                        "entity_id": entity_id,
                        "hs_color": [float(colors[color_index]), 100.0],
                    },
                    blocking=False,
                )

        position += 1
        if position >= bulb_count:
            position = 0
            color_index = (color_index + 1) % len(colors)

        await asyncio.sleep(0.3)  # 300ms per bulb


async def effect_strobe(entity: Any) -> None:
    """Strobe effect."""
    while True:
        # Turn on all bulbs white at full brightness
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": [0, 0],
                    "brightness": 255,
                },
                blocking=False,
            )

        await asyncio.sleep(0.1)  # 100ms on

        # Turn off all bulbs
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            await entity.hass.services.async_call(
                "light",
                "turn_off",
                {"entity_id": entity_id},
                blocking=False,
            )

        await asyncio.sleep(0.1)  # 100ms off


async def effect_candle_flicker(entity: Any) -> None:
    """Candle Flicker effect."""
    while True:
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            # Warm white color temperature range (370-450 mireds)
            color_temp = random.randint(370, 450)
            # Random brightness variation
            brightness = random.randint(100, 255)
            # Random interval
            delay = random.uniform(0.05, 0.2)  # 50-200ms

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "color_temp": color_temp,
                    "brightness": brightness,
                },
                blocking=False,
            )

        await asyncio.sleep(delay)


async def effect_police(entity: Any) -> None:
    """Police effect."""
    bulb_count = len(entity.bulb_entities)
    if bulb_count == 0:
        return

    half = bulb_count // 2

    while True:
        # First half red, second half blue
        for i, entity_id in enumerate(entity.bulb_entities):
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            if i < half:
                # Red
                hs_color = [0, 100]
            else:
                # Blue
                hs_color = [240, 100]

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": hs_color,
                },
                blocking=False,
            )

        await asyncio.sleep(0.15)  # 150ms

        # Swap colors
        for i, entity_id in enumerate(entity.bulb_entities):
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            if i < half:
                # Blue
                hs_color = [240, 100]
            else:
                # Red
                hs_color = [0, 100]

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "hs_color": hs_color,
                },
                blocking=False,
            )

        await asyncio.sleep(0.15)  # 150ms


async def effect_warm_fade(entity: Any) -> None:
    """Warm Fade effect."""
    # Color temperature range: warm white (450 mireds) to cool white (153 mireds)
    min_temp = 153  # Cool white
    max_temp = 450  # Warm white
    current_temp = min_temp
    increasing = True

    while True:
        for entity_id in entity.bulb_entities:
            state = entity.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue

            await entity.hass.services.async_call(
                "light",
                "turn_on",
                {
                    "entity_id": entity_id,
                    "color_temp": current_temp,
                },
                blocking=False,
            )

        if increasing:
            current_temp += 5
            if current_temp >= max_temp:
                increasing = False
        else:
            current_temp -= 5
            if current_temp <= min_temp:
                increasing = True

        await asyncio.sleep(40)  # 4000ms per direction / 100 steps = 40ms per step