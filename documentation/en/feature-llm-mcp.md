# Versatile Thermostat + Home Assistant MCP

This documentation describes how to add LLM/MCP tools to **Versatile Thermostat (VTherm)** through Home Assistant's official MCP server.

The provided `llm.py` file exposes:

- 3 read/diagnostic tools;
- 3 simple action tools: temperature, preset and HVAC mode;
- descriptions and instructions usable in **French and English**;
- links to the VTherm documentation, log collector and log analyzer for troubleshooting.

> The file does not create its own MCP server. It uses Home Assistant's native LLM platform, and the official **Model Context Protocol Server** then publishes these tools to MCP clients.

---

## 1. File to install

Copy `llm.py` to:

```text
/config/custom_components/versatile_thermostat/llm.py
```

Directory structure:

```text
/config/custom_components/versatile_thermostat/
├── __init__.py
├── climate.py
├── const.py
├── manifest.json
├── ...
└── llm.py
```

There is no need to modify `manifest.json` to declare the `llm` platform.

Home Assistant discovers integration platforms dynamically and loads `llm.py` on demand when an LLM API needs the integration's tools.

After copying the file, perform a **full restart of Home Assistant**.

> Warning: if `llm.py` was added manually to a VTherm installation managed by HACS, a future HACS update may replace the integration directory. Keep a copy of the file until it is integrated into the VTherm project itself.

---

## 2. Exposed tools

With the `assist` LLM API, the Home Assistant MCP server adds the `assist__` prefix to tools.

### Read-only — level 1

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
```

### Actions — level 2A

```text
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
```

The first three tools are marked:

```python
read_only=True
destructive=False
idempotent=True
open_world=False
```

The three action tools are marked:

```python
read_only=False
destructive=False
idempotent=True
open_world=False
```

They actually modify the thermostat state, but only through the standard Home Assistant `climate.*` services.

---

## 3. `list_vtherms`

This tool only lists VTherm entities that are:

- loaded in Home Assistant;
- in the `climate` domain;
- associated with a Versatile Thermostat configuration entry;
- exposed to Assist.

For each thermostat, it returns, among other things:

```text
entity_id
name
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
min_temperature
max_temperature
target_temperature_step
hvac_modes
preset_modes
thermostat_type
messages
```

Simplified example:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat",
  "hvac_action": "heating",
  "preset_mode": "comfort",
  "current_temperature": 18.7,
  "target_temperature": 19.5,
  "target_minus_current": 0.8,
  "hvac_modes": ["heat", "off"],
  "preset_modes": ["none", "frost", "eco", "comfort", "boost"]
}
```

---

## 4. `get_status`

`get_status` returns the complete raw state of the VTherm entity:

```text
entity_id
state
last_changed
last_updated
attributes
```

`attributes` contains the Home Assistant attributes and the VTherm-specific attributes available on the entity.

This tool is useful when the agent needs information that was not extracted into the structured diagnostic output.

---

## 5. `diagnose`

`diagnose` is the preferred tool for requests such as:

- "Why is my thermostat not heating?"
- "Why is it idle?"
- "Is it being shed?"
- "Is there a window-related issue?"
- "Why did VTherm stop?"
- "Debug the living-room thermostat."
- "Diagnose why this VTherm is not heating."

It returns, among other things:

### Current state

```text
hvac_mode
hvac_action
preset_mode
current_temperature
target_temperature
target_minus_current
hvac_modes
preset_modes
```

### VTherm reasons

The file prioritizes information calculated by VTherm itself:

```text
specific_states.messages
hvac_off_reason
hvac_mode_reason
should_device_be_active
device_actives
unavailable_underlying_entities
temperature_slope
is_sleeping
is_recalculate_scheduled
```

The goal is to prevent the model from inventing a cause based only on the difference between the current temperature and the target temperature.

### Diagnostic sections

When available, the following sections are returned in full:

```text
configuration
current_state
requested_state
specific_states
preset_temperatures
presence_manager
motion_manager
power_manager
window_manager
safety_manager
auto_start_stop_manager
lock_manager
heating_failure_detection
vtherm_over_switch
vtherm_over_climate
vtherm_over_valve
```

A section that is absent from the entity is simply not returned.

---

## 6. VTherm documentation and troubleshooting

The `diagnose` result also contains `support_resources` with both French **and** English resources:

```text
documentation_fr
documentation_en
reference_fr
reference_en
log_collector_fr
log_collector_en
log_analyzer
official_repository
log_download_action
```

Main links:

- French documentation: https://www.versatile-thermostat.org/fr/
- English documentation: https://www.versatile-thermostat.org/en/
- French reference: https://www.versatile-thermostat.org/fr/docs/reference/
- English reference: https://www.versatile-thermostat.org/en/docs/reference/
- French log collector: https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/
- English log collector: https://www.versatile-thermostat.org/en/docs/feature-logs-collector/
- Log analyzer: https://www.versatile-thermostat.org/fr/debugger/
- Official VTherm repository: https://github.com/jmcollin78/versatile_thermostat

For complex debugging, the prompt supplied to the LLM asks it to:

1. use the information returned by VTherm first;
2. not invent a cause that is not present in the data;
3. consult the French or English documentation matching the language of the request if the client has Web access;
4. suggest the log collector and then the log analyzer if the instantaneous state is not enough to reach a conclusion.

### Important

`llm.py` **does not download Web pages itself**.

It provides URLs and instructions to the LLM client. If the client being used (Codex, Gemini, Claude, etc.) has Web access, it can consult the documentation. Otherwise, it can at least provide the links to the user.

The versatile-thermostat.org website itself states that it is a community website and specifies that the official source of the project remains the VTherm GitHub repository.

---

## 7. Log collector

VTherm provides the action:

```text
versatile_thermostat.download_logs
```

The `llm.py` file does not execute this action automatically; it reports it as a troubleshooting resource.

Home Assistant example:

```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.thermostat_salon
  log_level: DEBUG
```

The resulting file can then be loaded into the analyzer:

```text
https://www.versatile-thermostat.org/fr/debugger/
```

---

# Level 2 — actions

## 8. `set_temperature`

Uses:

```text
climate.set_temperature
```

MCP parameters:

```json
{
  "entity_id": "climate.thermostat_salon",
  "temperature": 19.5
}
```

Before the call, the tool checks:

- that the VTherm is exposed to Assist;
- that an authenticated Home Assistant user is associated with the call;
- that the user has permission to control this entity;
- that the requested temperature remains within the thermostat's min/max values when they are available.

The result contains:

```text
success
action
requested
state_after_call
note
```

`state_after_call` allows the model to verify the state immediately after the command.

VTherm may then change the effective state according to its own rules: central mode, window, power shedding, safety, preset, auto start/stop, regulation, etc.

---

## 9. `set_preset`

Uses:

```text
climate.set_preset_mode
```

Parameters:

```json
{
  "entity_id": "climate.thermostat_salon",
  "preset": "comfort"
}
```

Before the action, the requested preset must appear in:

```text
preset_modes
```

for the targeted entity.

A model therefore cannot arbitrarily request a preset that is not available on that thermostat.

---

## 10. `set_hvac_mode`

Uses:

```text
climate.set_hvac_mode
```

Parameters:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "heat"
}
```

The mode must be present in:

```text
hvac_modes
```

To turn off a thermostat when `off` is supported:

```json
{
  "entity_id": "climate.thermostat_salon",
  "hvac_mode": "off"
}
```

The file deliberately exposes no `toggle` tool: the desired state must be explicit.

---

## 11. Action safety

Level 2 tools apply several safeguards:

1. only VTherm entities exposed to Assist;
2. a Home Assistant user context is mandatory for write operations;
3. `CONTROL` permission is checked;
4. presets and HVAC modes are validated against the real entity;
5. the temperature range is validated;
6. only standard `climate.*` services are used;
7. no VTherm internal configuration is modified;
8. no TPI, power shedding, window, safety or algorithm setting is changed.

Actions are marked `read_only=False`, which allows the Home Assistant MCP server to hide them when its **Read only** option is enabled.

---

# Installing the official Home Assistant MCP server

## 12. Enable the MCP server

In Home Assistant:

```text
Settings
→ System
→ AI
→ Model Context Protocol
```

Enable the MCP server if necessary.

It can also be added through:

```text
Settings
→ Devices & services
→ Add integration
→ Model Context Protocol Server
```

Home Assistant then provides an MCP URL, typically on a local network:

```text
http://homeassistant.local:8123/api/mcp
```

---

## 13. Recommended MCP server configuration

In the **Model Context Protocol Server** options:

```text
Expose all LLM APIs      : OFF (recommended to limit the exposed surface)
Control Home Assistant   : Assist / Device control
Require administrator    : ON
Read only                : OFF to use level 2
```

### If `Read only` is enabled

The action tools:

```text
set_temperature
set_preset
set_hvac_mode
```

are filtered out of the MCP catalog because they are declared `read_only=False`.

The diagnostic tools remain available.

This is useful when you temporarily want to return to level 1 operation without modifying `llm.py`.

---

## 14. Expose VTherm entities to Assist

The tools only access thermostats exposed to Assist.

In Home Assistant, expose the required entities, for example:

```text
climate.thermostat_salon
climate.thermostat_cuisine
climate.thermostat_salle
```

There is no need to expose every device in the home.

---

# Connecting to Codex

## 15. Add the MCP server

```bash
codex mcp add homeassistant \
  --url http://homeassistant.local:8123/api/mcp
```

Codex opens Home Assistant in the browser for OAuth authentication.

Verification:

```bash
codex mcp list
```

Example:

```text
homeassistant  http://homeassistant.local:8123/api/mcp  enabled
```

---

## 16. Check VTherm tools

Prompt:

```text
Use only the homeassistant MCP server.
List all tools available on this server whose name contains
versatile_thermostat. Do not perform any action.
```

With level 2A, the following should be available:

```text
assist__versatile_thermostat__list_vtherms
assist__versatile_thermostat__get_status
assist__versatile_thermostat__diagnose
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
```

If only the first three appear, check that the MCP **Read only** option is not enabled.

---

# Example questions

## 17. French — read and diagnose

```text
Liste mes Versatile Thermostat et donne-moi leur température actuelle,
leur consigne et leur état de chauffe.
```

```text
Diagnostique climate.thermostat_salon et explique pourquoi il ne chauffe pas.
N'invente aucune cause non présente dans les données VTherm.
```

```text
Pourquoi le thermostat du salon est-il idle alors que la température est
inférieure à la consigne ? Regarde aussi le délestage, la sécurité et les fenêtres.
```

```text
Fais un diagnostic de climate.thermostat_salon. Si les données ne suffisent pas,
indique quelle documentation VTherm consulter et rappelle-moi comment utiliser
le collecteur et l'analyseur de logs.
```

---

## 18. French — actions

```text
Mets la consigne du thermostat du salon à 19,5 °C.
```

```text
Passe climate.thermostat_salon en preset comfort.
```

```text
Passe climate.thermostat_salon en mode HVAC off.
```

```text
Remets climate.thermostat_salon en mode heat puis affiche son état.
```

---

## 19. English — read and diagnose

```text
List my Versatile Thermostats and show their current temperature,
target temperature and HVAC action.
```

```text
Diagnose climate.thermostat_salon and explain why it is not heating.
Do not infer a cause that is not supported by the VTherm diagnostic data.
```

```text
Debug climate.thermostat_salon. Check power shedding, safety, window detection,
auto start/stop and unavailable underlying entities.
```

```text
If the current diagnostic data is not enough, tell me which VTherm documentation
page or log-analysis workflow I should use next.
```

---

## 20. English — actions

```text
Set climate.thermostat_salon to 19.5 °C.
```

```text
Set climate.thermostat_salon preset to comfort.
```

```text
Set climate.thermostat_salon HVAC mode to off.
```

---

# Troubleshooting

## 21. No VTherm tool appears

Check:

1. that the file exists here:

   ```text
   /config/custom_components/versatile_thermostat/llm.py
   ```

2. Home Assistant has been restarted;
3. VTherm is loaded normally;
4. at least one VTherm `climate` entity is exposed to Assist;
5. the Assist/Device control API is exposed by the MCP server;
6. the MCP client has reconnected after the restart.

The `llm.py` platform is loaded on demand: the absence of a startup message in Home Assistant does not necessarily mean that it was not detected.

---

## 22. Read tools appear but action tools do not

Check the option:

```text
Model Context Protocol Server → Read only
```

For level 2A:

```text
Read only = OFF
```

---

## 23. An action is rejected

The tool result normally indicates the reason:

- no authenticated user context;
- insufficient permission;
- temperature outside the allowed range;
- preset does not exist;
- HVAC mode not supported;
- error returned by the Home Assistant service.

Use `list_vtherms` or `get_status` to retrieve the values actually supported by the entity.

---

# Intentional limitations of level 2

The file does not allow modification of:

```text
TPI
SmartPI / internal regulation
regulation coefficients
power limits
power-shedding priorities
window bypass
safety
central configuration
underlying entity configuration
persistent VTherm configuration
```

These functions would belong to a later level and would require additional safeguards.

---

# Technical references

- Home Assistant — Model Context Protocol Server  
  https://www.home-assistant.io/integrations/mcp_server/

- Home Assistant Core — `climate` LLM platform  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/llm.py

- Home Assistant Core — `Tool`, `ToolResult`, `ToolAnnotations` API  
  https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/llm.py

- Home Assistant Core — `climate` services  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/climate/

- Home Assistant Core — MCP Server configuration (`read_only`, `require_admin`)  
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/mcp_server/config_flow.py

- Versatile Thermostat — official repository  
  https://github.com/jmcollin78/versatile_thermostat

- Versatile Thermostat — reference documentation  
  https://www.versatile-thermostat.org/fr/docs/reference/

- Versatile Thermostat — log collector  
  https://www.versatile-thermostat.org/fr/docs/feature-logs-collector/

- Versatile Thermostat — log analyzer  
  https://www.versatile-thermostat.org/fr/debugger/
