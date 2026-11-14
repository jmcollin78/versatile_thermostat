"""Evidence-based eligibility of the native fixed-coefficient TPI model."""

from .auto_tpi_manager import AutoTpiManager
from .prop_algo_tpi import TpiAlgorithm
from .prop_handler_tpi import TPIHandler
from .tpi_identification import IdentificationError


class TPIRegulation:
    """Inspect loaded control objects, never infer activity from stored options."""

    def __init__(self, thermostat):
        self.thermostat = thermostat
        self.evidence = {
            "detected_regulation": "unknown",
            "compatible": False,
            "analysis_mode": "fixed_coefficients",
            "model_limitation": None,
            "blocking_criterion": None,
            "missing_information": [],
            "proportional_function": getattr(thermostat, "proportional_function", None),
            "auto_tpi_learning_active": None,
            "continuous_kext_enabled_at_runtime": None,
            "continuous_kext_affects_regulation": None,
        }

    def _refuse(self, criterion, *missing):
        self.evidence.update(
            blocking_criterion=criterion, missing_information=list(missing)
        )
        error = IdentificationError("not_classic_tpi")
        error.regulation = self.evidence
        raise error

    def check(self, *, allow_adaptive=False):
        """Return evidence or refuse before accessing Recorder or writing anything.

        Native TPIHandler applies learned parameters only during main learning,
        but AutoTpiManager._learn_kext_continuous also persists Kext independently
        via async_update_learning_data. Temporary cycle exclusions and zero sample
        counts cannot prove that this enabled path stays inactive during analysis.
        """
        t = self.thermostat
        selected = self.evidence["proportional_function"]
        if not isinstance(selected, str) or not selected:
            self._refuse("missing_proportional_function", "proportional_function")
        if selected != "tpi":
            self.evidence["detected_regulation"] = selected
            self._refuse("non_tpi_algorithm_selected")
        handler = getattr(t, "_algo_handler", None)
        algorithm = getattr(t, "prop_algorithm", None)
        # Exact native types: a plugin subclass can override the synchronization
        # invariant, so mere selection/configuration of 'tpi' is insufficient.
        if type(handler) is not TPIHandler or type(algorithm) is not TpiAlgorithm:
            self._refuse("unverified_tpi_runtime", "native TPIHandler and TpiAlgorithm")
        self.evidence["detected_regulation"] = "tpi"
        manager = getattr(t, "auto_tpi_manager", None)
        if (
            type(manager) is not AutoTpiManager
            or handler.auto_tpi_manager is not manager
        ):
            self._refuse("unverified_auto_tpi_state", "native AutoTpiManager")
        state = getattr(manager, "state", None)
        stored_learning = getattr(state, "autolearn_enabled", None)
        if type(stored_learning) is not bool:
            self._refuse("inconsistent_auto_tpi_state", "boolean autolearn_enabled")
        learning = manager.learning_active
        continuous = getattr(manager, "_continuous_kext", None)
        if (
            type(learning) is not bool
            or type(stored_learning) is not bool
            or learning != stored_learning
        ):
            self._refuse(
                "inconsistent_auto_tpi_state",
                "boolean learning_active/autolearn_enabled",
            )
        self.evidence["auto_tpi_learning_active"] = learning
        if type(continuous) is not bool:
            self._refuse(
                "unverified_continuous_kext_state", "boolean runtime continuous_kext"
            )
        self.evidence["continuous_kext_enabled_at_runtime"] = continuous
        self.evidence["continuous_kext_affects_regulation"] = continuous
        if learning or continuous:
            self.evidence["detected_regulation"] = (
                "auto_tpi" if learning else "tpi_continuous_kext"
            )
            criterion = (
                "auto_tpi_learning_active"
                if learning
                else "continuous_kext_can_update_coefficients"
            )
            self.evidence["model_limitation"] = criterion
            if allow_adaptive:
                self.evidence["analysis_mode"] = "adaptive_exploratory"
                return self.evidence
            self._refuse(criterion)
        self.evidence.update(compatible=True, detected_regulation="classic_tpi")
        return self.evidence
