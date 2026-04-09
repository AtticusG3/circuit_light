# Circuit Light (Home Assistant Integration)

Circuit Light is a **virtual light** for Home Assistant that lets you control a *circuit power switch / relay* (the “master”, e.g. **Shelly**, **Sonoff**, or **Tasmota** devices) and a *group of bulb lights* as **one** `light` entity.

It is designed for setups where:

- **A circuit/relay controls power** to one or more smart bulbs, and you want a single entity that keeps everything in sync.
- **A “master” relay/switch/light** (e.g. **Shelly**, **Sonoff**, **Tasmota**) should turn on/off together with multiple bulbs.
- You want to **hide the underlying child entities** (power + bulbs) and expose only one “clean” light entity in the UI.

The integration is **config-flow based** (set up in the UI), has **local push updates** (it listens to state changes), and creates **one** `light` entity per config entry.

> Note: The screenshot in this README references `docs/screenshot.png`. If you don’t have that file in your checkout, you can remove this line or add a screenshot at that path.

## What it does

When you turn the Circuit Light entity on/off, it:

- **Turns the selected power entity on/off** (e.g., a `switch` controlling a relay, or a “master” `light`)
- **Turns the selected bulb lights on/off**
- **Forwards brightness/color/transition** service parameters to the bulb lights when you use the Circuit Light entity

It also includes a set of built-in **effects** (e.g. “Christmas Lights”, “Rainbow Chase”, “Candle Flicker”, etc.) that animate the selected bulbs.

## Typical use cases

- **Smart bulbs on a switched circuit**: keep a relay “always on” when the bulbs are used, but still be able to cut power cleanly when turning the virtual light off.
- **One light card for many entities**: control “power + bulbs” from a single dashboard tile and a single automation target.
- **Kid/guest friendly UI**: hide underlying entities so people don’t accidentally toggle the relay separately from the bulbs.

## Installation

### Install with HACS (custom repository)

1. In Home Assistant, open **HACS**.
2. Go to **⋮ → Custom repositories**.
3. Add this repository URL as an **Integration**.
4. Install **Circuit Light** from HACS.
5. Restart Home Assistant.
6. Add it via **Settings → Devices & services → Add integration → Circuit Light**.

### Manual install

1. Copy `custom_components/circuit_light/` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add it via **Settings → Devices & services → Add integration → Circuit Light**.

## Configuration

During setup you’ll be asked for:

- **Name**: the display name for the virtual light entity
- **Power entity**: a `switch` or `light` that represents “circuit power” / master control
- **Bulb entities**: one or more `light` entities to be controlled as the bulbs

### Options

After adding the integration, you can adjust options from the device/integration page:

- **Hide child entities**: when enabled (default), the selected power + bulb entities are hidden in the entity registry (hidden by the integration).

## Notes / limitations

- The Circuit Light entity is a **virtual wrapper** around existing entities; it does not talk to hardware directly.
- Availability and on/off state are derived from the selected **power entity** state.
- Effects run until changed/turned off, and will stop automatically when you turn the Circuit Light entity off.

## Support / links

- **Documentation**: `https://git.kevynwatkins.com/kevyn/circuit_light`
- **Issues**: `https://git.kevynwatkins.com/kevyn/circuit_light/issues`

