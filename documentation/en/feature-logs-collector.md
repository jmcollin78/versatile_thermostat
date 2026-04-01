# Download Past Logs - Diagnosis and Troubleshooting

- [Download Past Logs - Diagnosis and Troubleshooting](#download-past-logs---diagnosis-and-troubleshooting)
  - [Why retrieve logs?](#why-retrieve-logs)
  - [How to access this feature](#how-to-access-this-feature)
  - [Calling the action from Home Assistant](#calling-the-action-from-home-assistant)
    - [Option 1: From the user interface (UI)](#option-1-from-the-user-interface-ui)
    - [Option 2: From a script or automation](#option-2-from-a-script-or-automation)
  - [Available parameters](#available-parameters)
    - [Explanation of log levels](#explanation-of-log-levels)
  - [Receiving and downloading the file](#receiving-and-downloading-the-file)
  - [Log file format and content](#log-file-format-and-content)
  - [Practical examples](#practical-examples)
    - [Example 1: Debug abnormal temperature over 30 minutes](#example-1-debug-abnormal-temperature-over-30-minutes)
    - [Example 2: Validate that presence is correctly detected](#example-2-validate-that-presence-is-correctly-detected)
    - [Example 3: Check all thermostats over a short period](#example-3-check-all-thermostats-over-a-short-period)
  - [Advanced configuration](#advanced-configuration)
  - [Usage tips](#usage-tips)

## Why retrieve logs?

Versatile Thermostat logs (_event journal_) record all changes and actions performed by the thermostat. They are useful for:

- **Diagnosing a malfunction**: Understanding why the thermostat is not behaving as expected
- **Analyzing abnormal behavior**: Verifying thermostat decisions over a given period
- **Debugging a configuration**: Validating that sensors and actions are properly detected
- **Reporting an issue**: Providing a history to developers to assist with debugging

The **log download** feature provides an easy way to retrieve logs from a specific period, filtered according to your needs.

**Helpful tip**: When requesting support, you will need to provide logs from when your problem occurred. Using this feature is recommended since logs are collected independently of the log level configured in Home Assistant (unlike the native HA logging system).

## How to access this feature

The `versatile_thermostat.download_logs` action is available in Home Assistant via:

1. **Automations** (Scripts > Automations)
2. **Scripts** (Scripts > Scripts)
3. **Developer Controls** (Settings > Developer Tools > Services)
4. **The control interface of certain integrations** (depending on your Home Assistant version)

## Calling the action from Home Assistant

### Option 1: From the user interface (UI)

To call the action from Developer Tools:

1. Go to **Settings** → **Developer Tools**
2. **Actions** tab (formerly called **Services**) → select `versatile_thermostat: Download logs`
3. Fill in the desired parameters (see section below)
4. Click **Call Service**

A **persistent notification** will then display with a download link for the file.

### Option 2: From a script or automation

Example call in an automation or YAML script:

```yaml
action: versatile_thermostat.download_logs
metadata: {}
data:
  entity_id: climate.living_room        # Optional: replace with your thermostat
  log_level: INFO                       # Optional: DEBUG (default), INFO, WARNING, ERROR
  period_start: "2025-03-14T08:00:00"   # Optional: ISO format (datetime)
  period_end: "2025-03-14T10:00:00"     # Optional: ISO format (datetime)
```

## Available parameters

| Parameter      | Required? | Possible values                     | Default            | Description                                                            |
| -------------- | --------- | ----------------------------------- | ------------------ | ---------------------------------------------------------------------- |
| `entity_id`    | No        | `climate.xxx` or absent             | All VTherm         | Specific thermostat targeted. If absent, includes all thermostats.     |
| `log_level`    | No        | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `DEBUG`            | Minimum severity level. All logs at this level and above are included. |
| `period_start` | No        | ISO datetime (ex: `2025-03-14...`)  | 60 minutes ago     | Start of extraction period. ISO format with date and time.             |
| `period_end`   | No        | ISO datetime (ex: `2025-03-14...`)  | Now (current time) | End of extraction period. ISO format with date and time.               |

### Explanation of log levels

- **DEBUG**: Detailed diagnostic messages (TPI calculation speed, intermediate values, etc.). Very verbose.
- **INFO**: General information (state changes, thermostat decisions, feature activations).
- **WARNING**: Warnings (preconditions not met, abnormal values detected).
- **ERROR**: Errors (sensor failures, unhandled exceptions).

**Tip**: Start with `INFO` for initial analysis, then switch to `DEBUG` if you need more details.

## Receiving and downloading the file

After calling the action, a **persistent notification** is displayed containing:

- A summary of the export (thermostat, period, level, number of entries)
- A **download URL** to copy/paste into your browser

The URL is an **absolute signed link** (with an authentication token valid for 24 hours). Due to a limitation of the Home Assistant frontend, **the link cannot be clicked directly** from the notification — you must **copy and paste it** into a new browser tab to trigger the download.

The downloaded file is a `.log` file named for example:
```
vtherm_logs_living_room_20250314_102500.log
```

The file is temporarily stored on your Home Assistant server in the folder accessible over the local network (under `config/www/versatile_thermostat/`).

> **Note**: Old log files (> 24h) are automatically deleted from the server.

> **Important**: For the download URL to be correct, you must configure your internal or external URL in **Settings > System > Network** in Home Assistant. Otherwise, the URL may contain the Docker container's internal IP address.

## Log file format and content

The file contains:

1. **A header** with export information:
   ```
   ================================================================================
   Versatile Thermostat - Log Export
   Thermostat : Living Room (climate.living_room)
   Period     : 2025-03-14 08:00:00 → 2025-03-14 10:00:00 UTC
   Level      : INFO and above
   Entries    : 342
   Generated  : 2025-03-14 10:25:03 UTC
   ================================================================================
   ```

2. **Log entries**, one per line, with:
   - Timestamp (date + UTC time)
   - Level (`[INFO]`, `[DEBUG]`, `[WARNING]`, `[ERROR]`)
   - Python module name (where the log was generated)
   - Message

Example entry:
```
2025-03-14 08:25:12.456 INFO    [base_thermostat    ] Living Room - Current temperature is 20.5°C
2025-03-14 08:30:00.001 INFO    [prop_algo_tpi      ] Living Room - TPI calculated on_percent=0.45
2025-03-14 08:30:00.123 WARNING [safety_manager     ] Living Room - No temperature update for 35 min
```

You can then **analyze this file** with:
- A standard text editor
- A Python script to process the data
- A tool like `grep`, `awk`, `sed`, etc. to filter manually

## Practical examples

### Example 1: Debug abnormal temperature over 30 minutes

**Objective**: Understand why the Living Room thermostat is managing its temperature poorly.

**Action to call**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.living_room
  log_level: DEBUG              # We want all the details
  period_start: "2025-03-14T14:00:00"
  period_end: "2025-03-14T14:30:00"
```

**File analysis**:
- Search for "Current temperature", "Target temperature" to see the evolution
- Search for "TPI calculated" to see the activation percentage calculation
- Search for "WARNING" or "ERROR" to identify anomalies

---

### Example 2: Validate that presence is correctly detected

**Objective**: Verify that the presence sensor has properly changed the thermostat state.

**Action to call**:
```yaml
action: versatile_thermostat.download_logs
data:
  entity_id: climate.office
  log_level: INFO
  period_start: "2025-03-15T12:00:00"      # Start of period (ISO format)
  period_end: "2025-03-15T14:00:00"        # End of period
```

**File analysis**:
- Search for messages containing "presence" or "motion"
- Verify that preset changes are properly logged

---

### Example 3: Check all thermostats over a short period

**Objective**: Retrieve a global history of all thermostats for one hour, filtered to warnings and errors.

**Action to call**:
```yaml
action: versatile_thermostat.download_logs
data:
  log_level: WARNING            # No entity_id → all VTherm
  period_start: "2025-03-15T13:00:00"
  period_end: "2025-03-15T14:00:00"
```

**File analysis**:
- The file will include all WARNING and ERROR logs from all thermostats
- Useful for checking that no abnormal alerts have occurred

---

## Advanced configuration

By default, logs are stored in memory for **4 hours** on your Home Assistant server. You can adjust this duration in `configuration.yaml`:

```yaml
versatile_thermostat:
  log_buffer_max_age_hours: 6   # Keep logs for 6 hours instead of 4
```

You can specify **any positive integer** (in hours) according to your needs. Here are some examples with an estimate of memory consumption:

| Duration | 10 VTherm Scenario | 20 VTherm Scenario |
| -------- | ------------------ | ------------------ |
| **1 h**  | ~0.5-1 MB          | ~2-5 MB            |
| **2 h**  | ~1-2 MB            | ~4-10 MB           |
| **4 h**  | ~2-5 MB            | ~8-20 MB           |
| **6 h**  | ~3-7 MB            | ~12-30 MB          |
| **8 h**  | ~4-10 MB           | ~16-40 MB          |
| **24 h** | Capped at 40-50 MB | Capped at 40-50 MB |

> **Note**: Increasing retention duration consumes more memory on your server. An automatic safeguard limits total consumption to ~40-50 MB maximum.

---

## Usage tips

1. **Start with INFO level**: Less noise, easier to read
2. **Target a specific thermostat**: More relevant than all VTherm
3. **Reduce the period**: Rather than 24h, download just the problematic period
4. **Use the website for analysis**: The [Versatile Thermostat website](https://www.versatile-thermostat.org/) allows you to analyze your logs and plot curves. It is an essential complement to this feature
5. **Use processing tools**: `grep`, `sed`, `awk`, or Python to analyze large files
6. **Keep the header**: Useful for providing context when reporting an issue

---
