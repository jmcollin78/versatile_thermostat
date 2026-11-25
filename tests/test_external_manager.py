# pylint: disable=protected-access, missing-function-docstring
"""Unit tests of the ExternalManager collection protocol (Requirements 7.1)."""

from unittest.mock import MagicMock, patch

from custom_components.versatile_thermostat.external_manager import ExternalManager


def _make_manager(factories: list[tuple[str, object]]) -> tuple[ExternalManager, list]:
    """Build an ExternalManager and load one fake manager per (name, manager) factory."""
    vtherm = MagicMock()
    ext = ExternalManager(vtherm)

    api = MagicMock()
    mock_factories = []
    for name, manager in factories:
        factory = MagicMock()
        factory.name = name
        factory.supports.return_value = True
        factory.create.return_value = manager
        mock_factories.append(factory)
    api.get_feature_manager_factories.return_value = mock_factories

    with patch(
        "custom_components.versatile_thermostat.external_manager.VersatileThermostatAPI.get_vtherm_api",
        return_value=api,
    ):
        ext.load_feature_managers({})
    return ext, [m for _, m in factories]


def test_empty_collection():
    ext = ExternalManager(MagicMock())
    assert len(ext) == 0
    assert not ext
    assert list(ext) == []
    assert not ext.has_manager("any")


def test_one_manager():
    m1 = MagicMock()
    ext, _ = _make_manager([("a", m1)])
    assert len(ext) == 1
    assert bool(ext) is True
    assert list(ext) == [m1]
    assert ext.has_manager("a")
    assert not ext.has_manager("b")


def test_several_managers_order_and_len():
    m1, m2, m3 = MagicMock(), MagicMock(), MagicMock()
    ext, _ = _make_manager([("a", m1), ("b", m2), ("c", m3)])
    assert len(ext) == 3
    assert [m for m in ext] == [m1, m2, m3]
    assert ext.has_manager("a") and ext.has_manager("b") and ext.has_manager("c")
    assert not ext.has_manager("d")


# --- Loading (Requirements 3.1, 3.2, 3.3, 3.5, 3.6, 7.2) ---

_API_PATH = "custom_components.versatile_thermostat.external_manager.VersatileThermostatAPI.get_vtherm_api"
_LOGGER_PATH = "custom_components.versatile_thermostat.external_manager._LOGGER"


def _factory(name: str, manager=None, supports=True):
    factory = MagicMock()
    factory.name = name
    if isinstance(supports, Exception):
        factory.supports.side_effect = supports
    else:
        factory.supports.return_value = supports
    factory.create.return_value = manager if manager is not None else MagicMock()
    return factory


def _load(ext: ExternalManager, factories: list, entry_infos=None):
    api = MagicMock()
    api.get_feature_manager_factories.return_value = factories
    with patch(_API_PATH, return_value=api):
        return ext.load_feature_managers(entry_infos if entry_infos is not None else {})


def test_load_new_factory_creates_and_post_inits_manager():
    vtherm = MagicMock()
    ext = ExternalManager(vtherm)
    manager = MagicMock()
    factory = _factory("a", manager)
    infos = {"k": "v"}

    new = _load(ext, [factory], infos)

    assert new == [manager]
    assert list(ext) == [manager]
    assert ext.has_manager("a")
    factory.supports.assert_called_once_with(vtherm)
    factory.create.assert_called_once_with(vtherm)
    manager.post_init.assert_called_once_with(infos)


def test_load_already_loaded_factory_is_not_duplicated():
    ext = ExternalManager(MagicMock())
    manager = MagicMock()
    factory = _factory("a", manager)

    assert _load(ext, [factory]) == [manager]
    factory.create.reset_mock()

    # Second pass (async_startup): same factory plus a new one
    manager_b = MagicMock()
    factory_b = _factory("b", manager_b)
    new = _load(ext, [factory, factory_b])

    assert new == [manager_b]
    assert list(ext) == [manager, manager_b]
    assert len(ext) == 2
    factory.create.assert_not_called()


def test_load_factory_not_supported_is_skipped():
    ext = ExternalManager(MagicMock())
    factory = _factory("a", supports=False)

    assert _load(ext, [factory]) == []
    assert len(ext) == 0
    assert not ext.has_manager("a")
    factory.create.assert_not_called()


def test_load_factory_failing_stages_logs_and_continues():
    ext = ExternalManager(MagicMock())

    f_supports = _factory("bad_supports", supports=RuntimeError("boom supports"))

    f_create = _factory("bad_create")
    f_create.create.side_effect = RuntimeError("boom create")

    bad_post_init = MagicMock()
    bad_post_init.post_init.side_effect = RuntimeError("boom post_init")
    f_post_init = _factory("bad_post_init", bad_post_init)

    good = MagicMock()
    f_good = _factory("good", good)

    with patch(_LOGGER_PATH) as logger:
        new = _load(ext, [f_supports, f_create, f_post_init, f_good])

    assert new == [good]
    assert list(ext) == [good]
    assert ext.has_manager("good")
    for name in ("bad_supports", "bad_create", "bad_post_init"):
        assert not ext.has_manager(name)

    assert logger.error.call_count == 3
    logged = [call.args for call in logger.error.call_args_list]
    for name in ("bad_supports", "bad_create", "bad_post_init"):
        assert any(name in args for args in logged)


def test_load_failing_factory_can_be_retried_later():
    ext = ExternalManager(MagicMock())
    manager = MagicMock()
    factory = _factory("a", manager)
    factory.create.side_effect = [RuntimeError("first"), manager]

    with patch(_LOGGER_PATH):
        assert _load(ext, [factory]) == []
    assert _load(ext, [factory]) == [manager]
    assert ext.has_manager("a")


def test_load_api_absent_creates_nothing():
    ext = ExternalManager(MagicMock())
    with patch(_API_PATH, return_value=None):
        assert ext.load_feature_managers({}) == []
    assert len(ext) == 0


def test_load_api_without_get_feature_manager_factories_creates_nothing():
    ext = ExternalManager(MagicMock())
    with patch(_API_PATH, return_value=MagicMock(spec=[])):
        assert ext.load_feature_managers({}) == []
    assert len(ext) == 0
