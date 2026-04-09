from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_platform

from . import DOMAIN
from .effects import EFFECT_LIST

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Circuit Light platform."""
    async_add_entities([CircuitLight(hass, entry)])


class CircuitLight(LightEntity):
    """Representation of a Circuit Light."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the Circuit Light."""
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = entry.entry_id
        self._attr_effect = None
        self._unsub_state_change: Callable[[], None] | None = None
        self._effect_task: asyncio.Task[None] | None = None
        self._bulb_entities: list[str] = entry.data["bulb_entities"]

    @property
    def power_entity_id(self) -> str:
        """Return the power entity ID."""
        return self.entry.data["power_entity"]

    @property
    def bulb_entities(self) -> list[str]:
        """Return the bulb entity IDs."""
        return self.entry.data["bulb_entities"]

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        # Set initial effect from options if any
        if self.entry.options.get(ATTR_EFFECT):
            self._attr_effect = self.entry.options[ATTR_EFFECT]

        # Track state changes
        self._unsub_state_change = async_track_state_change_event(
            self.hass,
            [self.power_entity_id] + self.bulb_entities,
            self._async_state_changed,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        if self._unsub_state_change:
            self._unsub_state_change()
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass

    @callback
    def _async_state_changed(self, event: Any) -> None:
        """Handle state changes of tracked entities."""
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        power_state = self.hass.states.get(self.power_entity_id)
        if power_state is None:
            return False
        return power_state.state == STATE_ON

    @property
    def available(self) -> bool:
        """Return true if device is available."""
        power_state = self.hass.states.get(self.power_entity_id)
        if power_state is None:
            return False
        return power_state.state != STATE_UNAVAILABLE

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        brightness_values = []
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            brightness = state.attributes.get(ATTR_BRIGHTNESS)
            if brightness is not None:
                brightness_values.append(brightness)
        if not brightness_values:
            return None
        return round(sum(brightness_values) / len(brightness_values))

    @property
    def color_temp(self) -> float | None:
        """Return the color temperature in mireds."""
        color_temp_values = []
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            color_temp = state.attributes.get(ATTR_COLOR_TEMP)
            if color_temp is not None:
                color_temp_values.append(color_temp)
        if not color_temp_values:
            return None
        return sum(color_temp_values) / len(color_temp_values)

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the HS color value."""
        h_values = []
        s_values = []
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            hs_color = state.attributes.get(ATTR_HS_COLOR)
            if hs_color is not None:
                h_values.append(hs_color[0])
                s_values.append(hs_color[1])
        if not h_values or not s_values:
            return None
        return (sum(h_values) / len(h_values), sum(s_values) / len(s_values))

    @property
    def color_mode(self) -> ColorMode | str:
        """Return the color mode of the light."""
        color_modes = []
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            color_mode = state.attributes.get("color_mode")
            if color_mode is not None:
                color_modes.append(color_mode)
        if not color_modes:
            return ColorMode.ONOFF
        # Return the most common color mode
        return max(set(color_modes), key=color_modes.count)

    @property
    def supported_color_modes(self) -> set[ColorMode | str]:
        """Flag supported color modes."""
        supported_modes: set[ColorMode | str] = set()
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            # Get supported color modes from the bulb's attributes
            bulb_supported = state.attributes.get("supported_color_modes", set())
            if bulb_supported:
                supported_modes.update(bulb_supported)
            else:
                # Fallback: infer from color_mode if available
                color_mode = state.attributes.get("color_mode")
                if color_mode:
                    supported_modes.add(color_mode)
        if not supported_modes:
            supported_modes.add(ColorMode.ONOFF)
        return supported_modes

    @property
    def supported_features(self) -> LightEntityFeature:
        """Flag supported features."""
        features = LightEntityFeature(0)
        transition_supported = False
        for entity_id in self.bulb_entities:
            state = self.hass.states.get(entity_id)
            if state is None or state.state == STATE_UNAVAILABLE:
                continue
            # Get supported features from the bulb's attributes
            bulb_features = state.attributes.get("supported_features", 0)
            features |= LightEntityFeature(bulb_features)
            # Check if transition is supported
            if bulb_features & LightEntityFeature.TRANSITION:
                transition_supported = True
        # Always include EFFECT if we have effects
        features |= LightEntityFeature.EFFECT
        # Include TRANSITION if any bulb supports it
        if transition_supported:
            features |= LightEntityFeature.TRANSITION
        return features

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return EFFECT_LIST

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self._attr_effect

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Turn on power entity if it's off
        if not self.is_on:
            await self.hass.services.async_call(
                "homeassistant", "turn_on", {"entity_id": self.power_entity_id}, blocking=False
            )
            # Wait for power entity to turn on (timeout 5s)
            wait_start = time.time()
            while time.time() - wait_start < 5:
                if self.is_on:
                    break
                await asyncio.sleep(0.1)
            # Note: Timeout handling is implicit - we just continue after 5 seconds

        # Wait for at least one bulb to become available (timeout 5s)
        wait_start = time.time()
        while time.time() - wait_start < 5:
            available_bulbs = [
                entity_id
                for entity_id in self.bulb_entities
                if self.hass.states.get(entity_id)
                and self.hass.states.get(entity_id).state != STATE_UNAVAILABLE
            ]
            if available_bulbs:
                break
            await asyncio.sleep(0.1)
        # Note: Timeout handling is implicit - we just continue after 5 seconds

        # Handle effect
        if ATTR_EFFECT in kwargs and kwargs[ATTR_EFFECT] is not None:
            effect_name = kwargs[ATTR_EFFECT]
            if self._effect_task:
                self._effect_task.cancel()
                try:
                    await self._effect_task
                except asyncio.CancelledError:
                    pass
            self._attr_effect = effect_name
            self._effect_task = self.entry.async_create_background_task(
                self._run_effect(effect_name)
            )
            self.async_write_ha_state()
            return

        # Handle color/brightness/transition
        if any(
            key in kwargs
            for key in (ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_HS_COLOR, ATTR_TRANSITION)
        ):
            if self._effect_task:
                self._effect_task.cancel()
                try:
                    await self._effect_task
                except asyncio.CancelledError:
                    pass
            self._attr_effect = None
            # Turn on bulbs with provided kwargs
            await self.hass.services.async_call(
                "light", "turn_on", {**kwargs, "entity_id": self.bulb_entities}, blocking=False
            )
            self.async_write_ha_state()
            return

        # Bare turn on (no kwargs)
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass
        self._attr_effect = None
        # Turn on bulbs with last known brightness (default 255)
        last_brightness = self.entry.options.get(ATTR_BRIGHTNESS)
        if last_brightness is None:
            last_brightness = 255
        await self.hass.services.async_call(
            "light",
            "turn_on",
            {ATTR_BRIGHTNESS: last_brightness, "entity_id": self.bulb_entities},
            blocking=False,
        )
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        # Cancel any active effect
        if self._effect_task:
            self._effect_task.cancel()
            try:
                await self._effect_task
            except asyncio.CancelledError:
                pass
        self._attr_effect = None

        # Turn off power entity only
        await self.hass.services.async_call(
            "homeassistant", "turn_off", {"entity_id": self.power_entity_id}, blocking=False
        )
        self.async_write_ha_state()

    async def _run_effect(self, effect_name: str) -> None:
        """Run an effect."""
        from .effects import (
            effect_christmas_lights,
            effect_colour_cycle,
            effect_rainbow_chase,
            effect_colour_wipe,
            effect_strobe,
            effect_candle_flicker,
            effect_police,
            effect_warm_fade,
        )

        effect_map = {
            "Christmas Lights": effect_christmas_lights,
            "Colour Cycle": effect_colour_cycle,
            "Rainbow Chase": effect_rainbow_chase,
            "Colour Wipe": effect_colour_wipe,
            "Strobe": effect_strobe,
            "Candle Flicker": effect_candle_flicker,
            "Police": effect_police,
            "Warm Fade": effect_warm_fade,
        }

        effect_func = effect_map.get(effect_name)
        if effect_func:
            try:
                await effect_func(self)
            except asyncio.CancelledError:
                pass