# Centralized Control

- [Centralized Control](#centralized-control)
  - [Configuration of Centralized Control](#configuration-of-centralized-control)
  - [Usage](#usage)

This feature allows you to control all your _VTherms_ from a single control point.
A typical use case is when you leave for an extended period and want to set all your _VTherms_ to frost protection, and when you return, you want to set them back to their initial state.

Centralized control is done from a special _VTherm_ called centralized configuration. See [here](creation.md#centralized-configuration) for more information.

## Configuration of Centralized Control

If you have set up a centralized configuration, you will have a new entity named `select.central_mode` that allows you to control all _VTherms_ with a single action.

![central_mode](images/central-mode.png)

This entity appears as a list of choices containing the following options:
1. `Auto`: the 'normal' mode where each _VTherm_ operates autonomously,
2. `Stopped`: all _VTherms_ are turned off (`hvac_off`),
3. `Heat only`: all _VTherms_ are set to heating mode if supported, otherwise they are stopped,
4. `Cool only`: all _VTherms_ are set to cooling mode if supported, otherwise they are stopped,
5. `Frost protection`: all _VTherms_ are set to frost protection mode if supported, otherwise they are stopped.

## Usage

For a _VTherm_ to be controllable centrally, its configuration attribute named `use_central_mode` must be true. This attribute is available in the configuration page `Main Attributes`.

![central_mode](images/use-central-mode.png)

This means you can control all _VTherms_ (those explicitly designated) with a single control.