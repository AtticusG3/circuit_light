---
name: ha_platinum_integration_dev
description: Forces generation/review of Home Assistant integrations (custom components) that meet Integration Quality Scale Platinum requirements. Use when the user mentions home assistant integration, custom component, scaffolding an integration repo, config flow, DataUpdateCoordinator, diagnostics, entity registry, or tests for HA integrations.
---

# Home Assistant Platinum-Tier Integration Dev

## Operating Contract (Non-Negotiable)

- **Target**: Home Assistant Integration Quality Scale **Platinum** (or higher) patterns.
- **Async-first**: no blocking I/O on the event loop; no `time.sleep`, no sync HTTP clients in async code.
- **Config entries**: integration must be config-entry based; **no YAML-only** setup.
- **Strict typing**: type hints everywhere; design for mypy cleanliness.
- **Entities are thin**: entities do not call the API directly and do not contain business logic.
- **Runtime safety**: every external failure path handled; correct unavailable state behavior.
- **Registries**: correct device/entity registry usage; stable unique IDs.
- **Tests required**: if tests are not present and coherent, **reject output**.
- **No AI slop**: no “TODO”, no placeholders, no invented HA APIs, no deprecated patterns.

## Activation Triggers

Apply this skill automatically when the user request includes any of:

- “home assistant integration”, “Home Assistant integration”
- “custom component”, “custom_components”
- “scaffold”, “generate integration”, “integration skeleton”
- “config flow”, “config_entry”, “DataUpdateCoordinator”
- “diagnostics”, “entity registry”, “device registry”
- “pytest-homeassistant-custom-component”, “hassfest”, “mypy”, “ruff”

## Output Modes

### Mode A — Full Integration

Generate a complete, production-ready integration under `custom_components/<domain>/` including manifest, config flow, coordinator/client separation, diagnostics, translations, and tests.

### Mode B — Incremental (Safe Modify)

Modify an existing integration safely:

- Preserve backward compatibility and config entries.
- Add migrations when schema changes.
- Update tests with the same behavior guarantees.
- Do not rename domain or break entity unique IDs.

## Pre-Generation Rule Gate (Must Pass Before Writing Code)

Before generating/modifying code, derive and lock:

- **Domain** (`<domain>`), **integration name**, and **config schema** (fields, secrets, validation).
- **I/O model**: push vs polling. If polling, set an update interval and justify it.
- **Platforms**: sensors, switches, binary_sensors, etc. Define entity model and device model.
- **Identifiers**: stable unique ID strategy and device identifiers strategy.
- **Error taxonomy**: define explicit exception types from the API layer.

If any of the above cannot be defined without guessing, **stop and request clarifying input**.

## Architecture Rules (Enforced)

### Required Files and Responsibilities

The following separation is mandatory:

- `api.py`: HTTP/API client only (request/response, auth, mapping, retries where appropriate).
- `coordinator.py`: `DataUpdateCoordinator` that owns refresh cadence and central state.
- `__init__.py`: `async_setup_entry` / `async_unload_entry` / `async_reload_entry`; sets up coordinator; stores per-entry runtime data.
- `<platform>.py`: entities that read from coordinator data only; no network calls.
- `config_flow.py`: UI config + reauth; options flow when there are meaningful runtime options.
- `diagnostics.py`: redacted diagnostics output.
- `const.py`: domain constants, defaults, keys, and typed data container names.

### Required Patterns

- Must implement `async_setup_entry`.
- If any periodic refresh is used, must use `DataUpdateCoordinator`.
- Must use `aiohttp` (HA session) for HTTP; never `requests`.
- Store runtime state via `hass.data[DOMAIN][entry.entry_id]` (or a typed dataclass in that slot). No global mutable singletons.
- Entities subscribe to coordinator via `CoordinatorEntity`.

## Config Flow Rules (Enforced)

- UI config is required via `ConfigFlow`.
- Must validate credentials/endpoint in the flow using the API client.
- Must implement **reauth** if auth can expire or be revoked.
- Must implement **options flow** if there are settings like update interval, units, or feature toggles.
- Must use `voluptuous` schemas appropriately and ensure input is validated.
- Never store secrets in plaintext logs or diagnostics.

## Entity Rules (Enforced)

- Every entity must have a stable `unique_id`.
- Every device-backed entity must set `device_info` with stable identifiers.
- Entity state and attributes must not perform I/O.
- Use correct `device_class`, `state_class`, `native_unit_of_measurement`, and `EntityCategory` when applicable.
- Entity creation must be deterministic across restarts; no dynamic creation without registry alignment.

## Error Handling Rules (Enforced)

- Define explicit exceptions in `api.py`:
  - `ApiAuthError` (reauth)
  - `ApiConnectionError` (transient network)
  - `ApiRateLimitError` (backoff)
  - `ApiError` (unexpected server / parse)
- Coordinator must:
  - Convert transient errors into `UpdateFailed`
  - Trigger reauth flows on auth failures where appropriate
  - Mark entities unavailable via coordinator state (do not manually set availability in each entity)
- Never crash setup on transient API failure; degrade gracefully.

## Performance Rules (Enforced)

- No I/O in entity properties.
- Batch API calls when possible; coordinator fetches all required data per refresh.
- Respect rate limiting; implement backoff and/or server hints when provided.
- Avoid excessive registry writes.

## Scaffold Generator (Required Output Shape)

When generating a new integration, output a full structure:

```
custom_components/<domain>/
  __init__.py
  manifest.json
  config_flow.py
  coordinator.py
  api.py
  const.py
  <platform>.py
  diagnostics.py
  strings.json
  translations/en.json
  tests/
    __init__.py
    conftest.py
    test_config_flow.py
    test_coordinator.py
    test_<platform>.py
```

All files must be **fully implemented** and internally consistent. No stubs.

## Testing Enforcement (Hard Fail If Missing)

The integration must include a coherent test suite:

- Use `pytest` and `pytest-homeassistant-custom-component`.
- Must cover:
  - config flow success + failure + reauth
  - coordinator refresh success + failure paths
  - entity state updates from coordinator data
- API must be mocked; tests must never hit the network.
- Prefer snapshot-like assertions on state/attributes only when stable.

## Validation Layer (Self-Check Before Final Output)

Run this checklist against the produced code. If any item fails, **regenerate the failing section**.

- [ ] No blocking calls in async context (no sync HTTP, no `time.sleep`, no file I/O in loop)
- [ ] `async_setup_entry` exists and is the primary setup path
- [ ] Coordinator mediates all data access; entities do not call API
- [ ] Every entity has `unique_id`
- [ ] Device info/identifiers correct where applicable
- [ ] Config flow validates; supports reauth; options flow when applicable
- [ ] `manifest.json` valid and consistent with code
- [ ] `strings.json` and `translations/en.json` present and consistent
- [ ] Diagnostics redacts secrets and identifiers as appropriate
- [ ] Tests exist and are coherent for flow/coordinator/platform

## Guardrails Against Hallucinations / Deprecated Patterns

- Only use Home Assistant APIs that are known current and common in core integrations:
  - `ConfigFlow`, `OptionsFlow`, `async_setup_entry`
  - `DataUpdateCoordinator`, `CoordinatorEntity`
  - `entity_platform`, `config_entries`, `device_registry`, `entity_registry`
  - `diagnostics`
- Do not invent helper functions, decorators, or modules that do not exist in HA.
- Do not use deprecated patterns (YAML-only setup, polling without coordinator, direct `hass` I/O from entities).
- Do not include placeholders (“TODO”, “TBD”, “IMPLEMENT ME”).

## Machine-Readable Rules

Use `.cursor/skills/ha_platinum_integration_dev/rules.json` as the authoritative rule set. Treat any `severity="error"` violation as a hard stop.

## Reference Implementation Example

Use `.cursor/skills/ha_platinum_integration_dev/reference/` as the canonical example output and as a consistency oracle for structure, patterns, and test shape.
