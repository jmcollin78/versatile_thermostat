# Running tests

Use the project's development environment with `requirements_test.txt` installed.
Run commands from the repository root.

```sh
pytest -p no:sugar
```

The project pytest configuration disables the optional `respx` plugin before it
can import `httpx`; Home Assistant installs its compatibility aliases during
pytest startup. `-p no:sugar` disables the optional terminal formatter. The
default suite, including GitHub Actions, skips tests marked `scientific`.
Each skip reports that `--run-scientific` is required. Fast contract, permission,
refusal and integration tests remain enabled, subject to their existing Home
Assistant version requirements. The CI workflows and their timeout are unchanged.

Run scientific validation explicitly before changing a calculation or estimator:

```sh
pytest -p no:sugar --run-scientific -m scientific
```

To run both the default suite and scientific tests:

```sh
pytest -p no:sugar --run-scientific
```

Currently the marker covers 18 cases in `test_tpi_identification_safety.py`:
16 physical-simulation cases with real experimental Kalman fitting, the
`weak_heater` refusal case, and train/validation independence checked through two
complete fits. Other fast refusal cases remain in the default suite. Merely
selecting `-m scientific` does not opt in; `--run-scientific` is also required.

These are synthetic scientific regression checks, not evidence of reliable
parameters for a real room. Keep their assertions and record results separately
from the default CI result. No permanent `skip` decorator needs to be removed to
run them locally. Public MCP analysis continues to keep Kalman disabled.
