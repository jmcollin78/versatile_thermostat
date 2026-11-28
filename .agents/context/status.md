# Status: long-running workstreams

Index of multi-step work only (at most 60 lines). One to three lines per item: goal, state, next step. Task details live in local task folders; finished items move to `decisions.md`. Contract details: `plugin-api.md`.

## Externalization roadmap (core -> plugins)

| Feature | State | Next step |
| --- | --- | --- |
| Heating failure detection | Contract available in `vtherm_api`; the core manager is still instantiated by the core | Plugin parity, then remove `feature_heating_failure_detection_manager.py` and its config, translations, docs and tests |
| Auto start/stop | Decision delegated through the existing contract | Remove the remaining core code paths |
| Auto fan (`over_climate`) | Runtime accesses exist in the core; legacy logic still in `thermostat_climate.py` | Move the logic to a plugin, then delete it from the core |
| Humidity | Candidate: only feeds `current_humidity` and one attribute section | Contract to publish humidity and attributes |
| Lock | Candidate: self-contained, but guarded by a decorator and service checks in the core | Generic command and service gate hook |
| Repair of incorrect device state | Candidate: per-cycle consistency check behind a flag | Uses the existing feature manager contract |
| Timed preset | Candidate: timers and two services | State calculation must accept a preset override from a manager |
| Analytics (`llm/`, TPI history and identification, recorder export) | Candidates: read attributes and the recorder only | Separate integration reading public state |
| `over_climate` self-regulation (`pi_algorithm.py`) | Candidate: pure algorithm coupled to the regulated temperature send path | Build on the setpoint modifier contract |
| Window, motion, presence, power | Candidates | Need a contract to feed target or hvac-mode overrides into the state calculation and read access to runtime state |
| Auto TPI | Candidate | Needs contracts for learning-state storage, services and attributes |

## Contract gaps blocking further extraction

- Feature attributes are read with `getattr` (`add_custom_attributes` is not part of the feature manager interface).
- No contract for config-flow steps, config-entry migration, entity or binary sensor creation, or services.
- The runtime interface gives no read access to preset, window, motion or presence state, nor to the power budget beyond overpowering.
- Some published hooks (calibration offset modifier, valve write hook, recalibration cause, plugin UI registry) have no consumer in the core.
