# Technical Specification: New Auto TPI Configuration Options

## 1. Overview
This feature introduces two new configuration options for the Auto TPI learning mechanism in Versatile Thermostat:
1.  **`auto_tpi_keep_ext_learning`**: Allows the "Learning Finished" state to be reached (triggering config updates) as soon as the **Indoor** coefficient is stable (50 cycles), ignoring the stability of the **Outdoor** coefficient. This is useful when outdoor temperature variations are insufficient to reach 50 cycles quickly.
2.  **`auto_tpi_continuous_learning`**: When enabled, the system continues to update the configuration with learned parameters silently (without sending notifications) after the learning is considered finished. This prevents notification spam while ensuring the configuration stays up-to-date.

## 2. Modified Files

### A. Constants (`custom_components/versatile_thermostat/const.py`)
Add new configuration keys:
*   `CONF_AUTO_TPI_KEEP_EXT_LEARNING = "auto_tpi_keep_ext_learning"`
*   `CONF_AUTO_TPI_CONTINUOUS_LEARNING = "auto_tpi_continuous_learning"`

### B. Configuration Schema (`custom_components/versatile_thermostat/config_schema.py`)
Update `STEP_AUTO_TPI_1_SCHEMA` to include the two new boolean fields:
*   `vol.Optional(CONF_AUTO_TPI_KEEP_EXT_LEARNING, default=False): cv.boolean`
*   `vol.Optional(CONF_AUTO_TPI_CONTINUOUS_LEARNING, default=False): cv.boolean`

### C. Initialization & Migration (`custom_components/versatile_thermostat/__init__.py`)
Update `async_migrate_entry` to inject default values (`False`) for these new keys into existing config entries during migration (Version update or minor version check).

### D. Logic Implementation (`custom_components/versatile_thermostat/base_thermostat.py`)
Modify `BaseThermostat.post_init` and `BaseThermostat.async_control_heating`.

**Logic Changes:**
1.  **Initialization**: Read the new parameters from `self._entry_infos` in `post_init`.
2.  **Learning Finished Criteria**:
    In `async_control_heating`, modify the `learning_finished` evaluation:
    ```python
    int_finished = self._auto_tpi_manager.int_cycles >= 50
    ext_finished = self._auto_tpi_manager.ext_cycles >= 50
    
    if self._auto_tpi_keep_ext_learning:
        learning_finished = int_finished
    else:
        learning_finished = int_finished and ext_finished
    ```
3.  **Notification Logic**:
    Wrap the notification block with a check for `continuous_learning`:
    ```python
    if learning_finished and enable_update_config:
        # ... update config logic ...
        
        # Only notify if Continuous Learning is DISABLED
        if enable_notification and not self._auto_tpi_continuous_learning:
            # ... send notification ...
    ```

### E. Translations (`custom_components/versatile_thermostat/translations/`)
Add label and description strings for `auto_tpi_keep_ext_learning` and `auto_tpi_continuous_learning` in `en.json` and `fr.json`.

### F. Documentation (`dev_tests/auto_tpi_internal_doc.md`)
Update the internal documentation to reflect the new parameters and the modified "Learning Finished" logic.

## 3. Execution Plan

1.  **Modify `const.py`**: Add constants.
2.  **Modify `config_schema.py`**: Add fields to schema.
3.  **Modify `__init__.py`**: Add migration logic.
4.  **Modify Translations**: Update `en.json` and `fr.json`.
5.  **Modify `base_thermostat.py`**: Implement core logic changes.
6.  **Update Documentation**: Update internal doc.