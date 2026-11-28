# Decisions

Adopted mechanisms and rejected approaches, with the reason. One row each; rewrite a row when the decision changes. Do not re-propose a rejected approach without new evidence.

## Adopted

| Decision | Reason |
| --- | --- |
| Features with a clear boundary are provided by plugins through `vtherm_api`; the core keeps generic contracts and hooks | Smaller, more maintainable core; alternative implementations without core changes |
| Proportional algorithms beyond TPI are plugins selected in the configuration | Advanced control (learned room models, other laws) evolves outside the core release cycle |
| Auto TPI learns with small bounded multiplicative steps on the TPI coefficients, without a thermal-model fit or an integral term | Light, predictable, understandable code; model-based regulation belongs to algorithm plugins |
| Agent memory in two tiers: versioned `.agents/context/` (current truth) and local `.agents/local/` (task work) | Long-term memory stays small and useful; session noise never reaches the repository |

## Rejected

| Approach | Why | Instead |
| --- | --- | --- |
| Model-based learning (thermal model fit) inside Auto TPI | Duplicates what algorithm plugins do, heavier code and behaviour harder to predict | Keep Auto TPI light; use an algorithm plugin for model-based control |
| Feature-specific code paths in the core for one plugin | Couples the core to plugin internals | A generic contract usable by any plugin |
