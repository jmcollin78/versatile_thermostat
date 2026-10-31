# Versatile Thermostat + Home Assistant MCP

This documentation describes how to add LLM/MCP tools to **Versatile Thermostat (VTherm)** through Home Assistant's official MCP server.

The provided `llm.py` file exposes:

- 4 read/diagnostic and history tools;
- 3 simple action tools: temperature, preset and HVAC mode;
- 2 read-only TPI tools and 1 explicit TPI write tool;
- descriptions and instructions usable in **French and English**;
- links to the VTherm documentation, log collector and log analyzer for troubleshooting.

> The file does not create its own MCP server. It uses Home Assistant's native LLM platform, and the official **Model Context Protocol Server** then publishes these tools to MCP clients.

---

## 1. File to install

Copy the following four files to the integration directory:

```text
/config/custom_components/versatile_thermostat/llm.py
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
```

Install these modules from the same revision. For a manual update, replace `llm.py`, `tpi_history.py` and `tpi_identification.py` together: `TPIHistory` owns one thermostat's Home Assistant context and sources, while `TPIIdentification` owns its grid and analysis parameters. This internal class organization preserves the existing MCP tools and calculations.

Directory structure:

```text
/config/custom_components/versatile_thermostat/
├── __init__.py
├── climate.py
├── const.py
├── manifest.json
├── ...
├── llm.py
├── recorder_export.py
├── tpi_history.py
└── tpi_identification.py
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
assist__versatile_thermostat__get_history
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

The three climate actions above apply these safeguards (the TPI action is described separately):

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
set_tpi_coefficients
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

For installation and configuration of the official Home Assistant MCP server, see the [Home Assistant reference documentation](https://www.home-assistant.io/integrations/mcp_server/).

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
assist__versatile_thermostat__get_history
assist__versatile_thermostat__set_temperature
assist__versatile_thermostat__set_preset
assist__versatile_thermostat__set_hvac_mode
assist__versatile_thermostat__check_tpi_optimization
assist__versatile_thermostat__analyze_tpi_coefficients
assist__versatile_thermostat__set_tpi_coefficients
```

The complete catalog has six read tools and four write tools. With **Read only**, only the six read tools remain visible.

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
/config/custom_components/versatile_thermostat/recorder_export.py
/config/custom_components/versatile_thermostat/tpi_history.py
/config/custom_components/versatile_thermostat/tpi_identification.py
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

# TPI coefficient optimization from history

A simple request is enough, for example: “Are the parents' bedroom thermostat coefficients optimal?” or “Are my coefficients well tuned?”. Tool descriptions guide the assistant to the read-only TPI check and calculation, resolving the room name when needed. Users need not name tools or supply an `entity_id`, and dashboard access is not a prerequisite. The selected connector must expose `check_tpi_optimization` and `analyze_tpi_coefficients`: rephrasing cannot make missing tools available. Results remain exploratory estimates, not proof of an optimum.

Three tools complement the existing tools:

| Tool (suffix `versatile_thermostat__…`) | Access | Stage |
| --- | --- | --- |
| `check_tpi_optimization` | Read-only | 1/3 — check |
| `analyze_tpi_coefficients` | Read-only | 2/3 — analysis |
| `set_tpi_coefficients` | Explicit write | 3/3 — optional application |

Read tools take only `entity_id`. The client announces each stage before calling; no background work is simulated. Every response contains `stage`, `stage_number`, `stage_total` and `state_changed`.

Analysis requires classic TPI (`proportional_function=tpi`), with no configured Auto-TPI, active learning or continuous external compensation. This version supports `over_switch` with one or more physical switches. Recorded ON durations are integrated and averaged using VTherm's equal power share convention `device_power / N`, including staggered phases and subminute transitions. Absolute heater power is unnecessary. This convention does not measure unequal individual heater powers.

For `over_climate`, `over_valve` and climate valve regulation, the response explicitly returns `eligible: false`, `supported: false`, `reason: unsupported_thermostat_type`: analysis is not yet available for this type. Ambiguous virtual commands are also rejected; there is no blind `hvac_action` fallback.

Recorder supplies at most the **last 14 days**. At least **7 days of actually usable minutes** are required after exclusions. Inside/outside sensors come from effective VTherm configuration, including central configuration. Results detail `sources`, `history_requested_days`, `history_available_days`, `history_usable_days`, exclusions and current settings. No Recorder retention period is assumed.

The response includes `applicability_note` (FR/EN): coefficients are exploratory estimates derived from the analyzed period, with suitability under other conditions not established. Rerun the analysis on a representative period if heating conditions or household use change substantially, or regulation deteriorates, before considering an adjustment. Outdoor temperature changes alone do not require recalculation.

The Kalman comparison is disabled in the MCP response: simulations show that coefficients within bounds can still be inaccurate. `experimental_estimator` reports `unavailable` with reason `experimental_model_not_validated_for_application`, without running or returning Kalman coefficients. The estimator remains available for offline research, rejecting values outside `[0, 10]` (internal) and `[0, 1]` (external), insufficient excitation and unstable estimates. Clipping never turns a failed fit into a usable result. These screens do not prove reliability; OLS remains exploratory and application is never automatic. Bootstrap intervals remain uncalibrated and are not truncated to service bounds.

Temperatures use a one-minute grid and causal hold limited to 60 minutes. Unlike the reference script's outdoor interpolation, no future measurement is used. HA binary states persist until their next event; `unknown`/`unavailable` invalidate the interval. Physical and diagnostic safety, power-shedding and window sensors are read through Recorder because climate diagnostic sections are often unrecorded. A required missing exclusion source causes refusal. Non-`heat` HVAC periods, active protections, open windows and missing data are excluded. Each resolution reports excluded window cycles. This version requires VTherm configured in °C; source sensors in °F are converted to °C.

The model preserves `ΔT = g × (T_ext - T_int) + B × u + q`, `coef_ext = g/B`, `A = 1-g` and `coef_int = (A-exp(-dt/tau_cl))/B`. Preferred convergence remains **6 h**, with the 3/4/5/6/8/10/12 h table returned. Real `cycle_min` is primary, alongside 10/20/30/60-minute fits, with an explicit fallback to the nearest valid resolution. Each fit requires 40 cycles, 80% valid minutes and the reference physical bounds. Missing bins never silently become longer cycles.

Chronological 70% training / 30% validation, OLS `numpy.linalg.lstsq`, MAE, RMSE, ΔT R² and conditioning are retained. Temporal bootstrap uses 1000 repetitions, 24-hour blocks and seed `20261030`; gaps do not compress the blocks. Approximate 95% confidence intervals are returned. Fewer than 30 accepted physical repetitions causes `bootstrap_failed`. Nonphysical fits or condition numbers ≥1000 are rejected; 100–1000 requires caution. Low R² alone is not a rejection criterion. Relative `coef_ext` span above 25%, fewer than three resolutions or a wide CI trigger warnings. `recommendation_reliable: false` means the candidate must not be described as reliable. No CSV, plot, report or other file is required or generated; pandas/matplotlib dependencies are not added.

Analysis **never applies** coefficients. Present results, limitations and comparison, then await the user's decision. An explicit direct change needs no history or analysis:

```json
{"entity_id": "climate.thermostat_salon", "coef_int": 0.35, "coef_ext": 0.025}
```

At least one coefficient is required; partial updates are supported. VTherm service ranges: `0 <= coef_int <= 10`, `0 <= coef_ext <= 1`, finite values only. The tool rechecks Assist exposure, classic TPI, authenticated user and `CONTROL`, then calls only `versatile_thermostat.set_tpi_parameters` with that context. Existing central-configuration and lock restrictions remain enforced by the service. The service may persist settings; the tool never writes a ConfigEntry directly.

`large_change` means an absolute delta of **0.15 for coef_int**, **0.01 for coef_ext**, or a relative delta of **50%** (any change from zero is large). These are confirmation thresholds, not thermal safety guarantees. The tool returns `large_change_confirmation_required`, `confirmation_required: true`, comparison and a `confirmation_token`, without writing. After additional explicit user confirmation, repeat the same values with `confirm_large_change: true` and the token. It expires after 10 minutes and is bound to the user, thermostat and exact comparison; changing current settings invalidates it.

After calling, values are reread from the loaded VTherm object, including after reload: `previous`, `requested`, `applied`. Failures after a service call return `state_changed: null` and require verification; they do not claim nothing changed. Pre-call refusals state that no coefficient was changed. Never bypass a refusal with generic services.

MCP **Read only** retains both analysis tools and hides `set_tpi_coefficients`, like the other actions.

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


---

## Recorder history: CSV exports and charts

For “Make a professional annotated graph of the kitchen thermostat over 48 h”, the assistant is guided to `get_history`, then client-side chart creation after fetching every page. ApexCharts/Lovelace YAML is offered only when dashboard configuration is explicitly requested. SmartPI climate history can be plotted even though TPI coefficient analysis rejects SmartPI. Annotations must come from recorded events; the tool does not expose historical SmartPI power or physical relay histories. Current values cannot reconstruct these series. If `get_history` is absent from the connector catalog, the assistant must explain that limitation.

The read-only `versatile_thermostat__get_history` tool sends the MCP client recorded history of the VTherm climate entity: state, measured temperature, target, HVAC action and preset, when recorded. It supports all VTherm types independently of TPI analysis. It does not expose the entire Recorder or associated sensor and relay histories.

The client (ChatGPT, Claude, Gemini, Codex, etc.) retrieves the data and creates CSV files or charts according to its capabilities. Examples: “Export one week of living-room history as CSV” or “Plot office temperature and target over two days”.

Parameters: `entity_id`, `start_time`, `end_time` (ISO 8601 with timezone), `offset` (default 0) and `limit` (default 500, maximum 500). A period spans at most 14 days; split longer periods. Fetch every page using `next_offset` and identical bounds until `null`. Results include `rows`, `total_rows`, `next_offset`, `pagination_complete`, UTC timestamps and available recorded attributes. Pagination is not a frozen Recorder snapshot.

Only VTherms still exposed to Assist are accessible, with an authenticated user holding read permission. Points represent recorded changes, not regular samples; Recorder may carry a state forward to the period start. Missing fields remain `null`, and `unknown`/`unavailable` stay explicit. Retention, exclusions and outages may limit data; completed pagination does not guarantee complete history. The client must disclose these limits and never invent missing values. No configuration is changed.
