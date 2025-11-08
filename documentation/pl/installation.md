# How to Install Versatile Thermostat?

## HACS Installation (Recommended)

1. Install [HACS](https://hacs.xyz/). This way, you will automatically receive updates.
2. The Versatile Thermostat integration is now available directly from the HACS interface (Integrations tab).
3. Search for and install "Versatile Thermostat" in HACS and click "Install".
4. Restart Home Assistant.
5. Then, you can add a Versatile Thermostat integration in the Settings / Integrations page. Add as many thermostats as needed (usually one per radiator or group of radiators that need to be controlled, or per pump in the case of a centralized heating system).

## Manual Installation

1. Using your tool of choice, open your Home Assistant configuration directory (where you will find `configuration.yaml`).
2. If you don't have a `custom_components` directory, you need to create one.
3. Inside the `custom_components` directory, create a new folder called `versatile_thermostat`.
4. Download _all_ files from the `custom_components/versatile_thermostat/` directory (folder) in this repository.
5. Place the downloaded files in the new folder you created.
6. Restart Home Assistant.
7. Configure the new Versatile Thermostat integration.