"""Tests for the VTherm log collector module."""
# pylint: disable=line-too-long

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.versatile_thermostat.log_collector import (
    VThermLogEntry,
    VThermLogHandler,
    VThermLogger,
    get_vtherm_logger,
    _extract_thermostat_hint,
    _format_entry,
    _format_header,
    _cleanup_old_files,
    async_export_logs,
)


# ---------------------------------------------------------------------------
# Unit tests: _extract_thermostat_hint
# ---------------------------------------------------------------------------

class TestExtractThermostatHint:
    """Tests for the thermostat hint extraction from log messages."""

    def test_standard_pattern(self):
        assert _extract_thermostat_hint("Salon - Temperature changed to 21.5°C") == "Salon"

    def test_pattern_with_spaces(self):
        assert _extract_thermostat_hint("Bureau Étage - HVAC mode is heat") == "Bureau Étage"

    def test_no_match(self):
        assert _extract_thermostat_hint("Initializing integration") is None

    def test_empty_string(self):
        assert _extract_thermostat_hint("") is None

    def test_dash_only(self):
        assert _extract_thermostat_hint(" - something") is None


# ---------------------------------------------------------------------------
# Unit tests: VThermLogHandler
# ---------------------------------------------------------------------------

class TestVThermLogHandler:
    """Tests for the ring buffer handler."""

    def _make_record(self, msg: str, level: int = logging.DEBUG, ts: float | None = None):
        record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None,
        )
        if ts is not None:
            record.created = ts
        return record

    def test_emit_stores_entry(self):
        handler = VThermLogHandler(max_entries=100)
        handler.emit(self._make_record("Salon - test"))
        assert handler.size == 1

    def test_max_entries_eviction(self):
        handler = VThermLogHandler(max_entries=5)
        for i in range(10):
            handler.emit(self._make_record(f"Salon - msg {i}"))
        assert handler.size == 5

    def test_purge_old_entries(self):
        handler = VThermLogHandler(max_age_hours=1, max_entries=10000)
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).timestamp()
        handler.emit(self._make_record("Salon - old", ts=old_ts))
        handler.emit(self._make_record("Salon - recent"))
        handler.purge()
        assert handler.size == 1

    def test_hint_extraction(self):
        handler = VThermLogHandler()
        handler.emit(self._make_record("Bureau - some log"))
        entries = handler.get_entries()
        assert entries[0].thermostat_hint == "Bureau"

    def test_filter_by_thermostat(self):
        handler = VThermLogHandler()
        handler.emit(self._make_record("Salon - msg1"))
        handler.emit(self._make_record("Bureau - msg2"))
        handler.emit(self._make_record("Global init message"))
        entries = handler.get_entries(thermostat_name="Salon")
        # Should include "Salon" entries + entries without hint
        assert len(entries) == 2
        hints = [e.thermostat_hint for e in entries]
        assert "Salon" in hints
        assert None in hints

    def test_filter_by_thermostat_with_prefix(self):
        """Logs from underlyings use VersatileThermostat-Name-entity format."""
        handler = VThermLogHandler()
        handler.emit(self._make_record("VersatileThermostat-Salon - msg from thermostat"))
        handler.emit(self._make_record("VersatileThermostat-Salon-input_boolean.heater1 - msg from underlying"))
        handler.emit(self._make_record("Salon - msg with name only"))
        handler.emit(self._make_record("Bureau - should not match"))
        entries = handler.get_entries(thermostat_name="Salon")
        assert len(entries) == 3
        messages = [e.message for e in entries]
        assert any("from thermostat" in m for m in messages)
        assert any("from underlying" in m for m in messages)
        assert any("name only" in m for m in messages)

    def test_filter_by_thermostat_with_various_prefixes(self):
        """Logs from EMA, SafetyManager, WindowManager etc. must match."""
        handler = VThermLogHandler()
        handler.emit(self._make_record("EMA-Multi-switch - timestamp=..."))
        handler.emit(self._make_record("SafetyManager-Multi-switch - checking safety"))
        handler.emit(self._make_record("WindowManager-Multi-switch - Window auto is on"))
        handler.emit(self._make_record("HeatingFailureDetectionManager-Multi-switch - disabled"))
        handler.emit(self._make_record("Bureau - should not match"))
        entries = handler.get_entries(thermostat_name="Multi-switch")
        messages = [e.message for e in entries]
        assert any("EMA-Multi-switch" in m for m in messages)
        assert any("SafetyManager-Multi-switch" in m for m in messages)
        assert any("WindowManager-Multi-switch" in m for m in messages)
        assert any("HeatingFailureDetectionManager-Multi-switch" in m for m in messages)
        assert not any("Bureau" in m for m in messages)

    def test_filter_by_thermostat_no_false_positive_with_prefix(self):
        """Prefixed logs for 'Multi-switch' must NOT match when searching 'Salon'."""
        handler = VThermLogHandler()
        handler.emit(self._make_record("Multi-switch - msg1"))
        handler.emit(self._make_record("VersatileThermostat-Multi-switch - msg2"))
        handler.emit(self._make_record("EMA-Multi-switch - msg3"))
        handler.emit(self._make_record("Salon - msg4"))
        entries = handler.get_entries(thermostat_name="Salon")
        hints = [e.thermostat_hint for e in entries]
        assert "Salon" in hints
        assert "Multi-switch" not in hints
        assert "VersatileThermostat-Multi-switch" not in hints
        assert "EMA-Multi-switch" not in hints

    def test_filter_by_level(self):
        handler = VThermLogHandler()
        handler.emit(self._make_record("Salon - debug", logging.DEBUG))
        handler.emit(self._make_record("Salon - info", logging.INFO))
        handler.emit(self._make_record("Salon - warning", logging.WARNING))
        entries = handler.get_entries(min_level=logging.WARNING)
        assert len(entries) == 1
        assert entries[0].level == logging.WARNING

    def test_filter_by_time_window(self):
        handler = VThermLogHandler()
        now = datetime.now(tz=timezone.utc)
        ts_old = (now - timedelta(minutes=30)).timestamp()
        ts_recent = (now - timedelta(minutes=5)).timestamp()
        handler.emit(self._make_record("Salon - old", ts=ts_old))
        handler.emit(self._make_record("Salon - recent", ts=ts_recent))
        entries = handler.get_entries(
            start=now - timedelta(minutes=10),
            end=now,
        )
        assert len(entries) == 1
        assert "recent" in entries[0].message

    def test_filter_combined(self):
        handler = VThermLogHandler()
        now = datetime.now(tz=timezone.utc)
        ts = (now - timedelta(minutes=5)).timestamp()
        handler.emit(self._make_record("Salon - debug", logging.DEBUG, ts))
        handler.emit(self._make_record("Salon - info", logging.INFO, ts))
        handler.emit(self._make_record("Bureau - info", logging.INFO, ts))
        entries = handler.get_entries(
            thermostat_name="Salon",
            min_level=logging.INFO,
            start=now - timedelta(minutes=10),
            end=now,
        )
        assert len(entries) == 1
        assert entries[0].thermostat_hint == "Salon"
        assert entries[0].level == logging.INFO

    def test_empty_buffer(self):
        handler = VThermLogHandler()
        assert handler.get_entries() == []

    def test_thermostat_filter_case_insensitive(self):
        handler = VThermLogHandler()
        handler.emit(self._make_record("Salon - msg"))
        entries = handler.get_entries(thermostat_name="salon")
        assert len(entries) == 1

    def test_periodic_purge_in_emit(self):
        """Verify that purge occurs every PURGE_EVERY_N inserts."""
        handler = VThermLogHandler(max_age_hours=1, max_entries=100000)
        old_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).timestamp()
        # Insert one old entry
        handler.emit(self._make_record("old", ts=old_ts))
        # Insert PURGE_EVERY_N - 1 more (total will be PURGE_EVERY_N triggering purge)
        for i in range(999):
            handler.emit(self._make_record(f"msg {i}"))
        # Old entry should be purged now
        entries = handler.get_entries(
            start=datetime.now(tz=timezone.utc) - timedelta(hours=3),
            end=datetime.now(tz=timezone.utc),
        )
        assert all("old" != e.message for e in entries if e.thermostat_hint is None)


# ---------------------------------------------------------------------------
# Unit tests: VThermLogger + get_vtherm_logger
# ---------------------------------------------------------------------------

class TestVThermLogger:
    """Tests for the VThermLogger subclass and its factory."""

    def _unique_name(self, suffix: str) -> str:
        """Return a unique logger name to avoid cross-test pollution."""
        import uuid
        return f"custom_components.versatile_thermostat._test_{suffix}_{uuid.uuid4().hex[:8]}"

    def test_get_vtherm_logger_returns_vtherm_instance(self):
        """get_vtherm_logger must return a VThermLogger, not a plain Logger."""
        name = self._unique_name("type")
        logger = get_vtherm_logger(name)
        assert isinstance(logger, VThermLogger)

    def test_get_vtherm_logger_idempotent(self):
        """Calling get_vtherm_logger twice returns the same instance."""
        name = self._unique_name("idemp")
        l1 = get_vtherm_logger(name)
        l2 = get_vtherm_logger(name)
        assert l1 is l2

    def test_is_enabled_for_always_true(self):
        """VThermLogger.isEnabledFor must always return True regardless of level."""
        name = self._unique_name("enabled")
        logger = get_vtherm_logger(name)
        logger.setLevel(logging.WARNING)
        assert logger.isEnabledFor(logging.DEBUG) is True
        assert logger.isEnabledFor(logging.INFO) is True
        assert logger.isEnabledFor(logging.WARNING) is True

    def test_collector_receives_debug_when_level_is_warning(self):
        """Buffer must receive DEBUG records even when the logger is set to WARNING."""
        handler = VThermLogHandler()
        name = self._unique_name("collect_debug")
        logger = get_vtherm_logger(name)
        logger.setLevel(logging.WARNING)

        logger.debug("Salon - debug should be collected")
        logger.warning("Salon - warning should be collected")

        entries = handler.get_entries()
        messages = [e.message for e in entries]
        assert any("debug should be collected" in m for m in messages)
        assert any("warning should be collected" in m for m in messages)

    def test_normal_handlers_respect_effective_level(self):
        """Normal handlers (not the collector) must NOT receive records below the effective level."""
        handler = VThermLogHandler()
        name = self._unique_name("ha_level")
        logger = get_vtherm_logger(name)
        logger.setLevel(logging.WARNING)
        logger.propagate = False  # isolate from root

        # Attach a spy handler to verify what it receives
        spy = logging.handlers_spy = []
        class SpyHandler(logging.Handler):
            def emit(self, record):
                spy.append(record.levelno)
        spy_handler = SpyHandler(level=logging.DEBUG)
        logger.addHandler(spy_handler)

        logger.debug("Salon - should NOT reach spy")
        logger.info("Salon - should NOT reach spy")
        logger.warning("Salon - SHOULD reach spy")

        assert logging.DEBUG not in spy
        assert logging.INFO not in spy
        assert logging.WARNING in spy

        logger.removeHandler(spy_handler)

    def test_collector_not_registered_before_handler_creation(self):
        """VThermLogger._collector is None until a VThermLogHandler is instantiated."""
        original = VThermLogger._collector
        VThermLogger._collector = None
        name = self._unique_name("no_collector")
        logger = get_vtherm_logger(name)
        logger.setLevel(logging.WARNING)
        # Must not raise even without a collector
        logger.debug("Salon - no collector yet")
        # Restore
        VThermLogger._collector = original

    def test_handler_sets_collector_on_init(self):
        """Creating a VThermLogHandler registers it as the class-level collector."""
        h = VThermLogHandler()
        assert VThermLogger._collector is h


# ---------------------------------------------------------------------------
# Unit tests: format helpers
# ---------------------------------------------------------------------------

class TestFormatHelpers:
    """Tests for format functions."""

    def test_format_entry(self):
        entry = VThermLogEntry(
            timestamp=datetime(2025, 3, 14, 10, 23, 45, 123000, tzinfo=timezone.utc),
            level=logging.INFO,
            logger_name="custom_components.versatile_thermostat.base_thermostat",
            message="Salon - Temperature is 21°C",
            thermostat_hint="Salon",
        )
        line = _format_entry(entry)
        assert "2025-03-14 10:23:45.123" in line
        assert "INFO" in line
        assert "[base_thermostat   ]" in line
        assert "Salon - Temperature is 21°C" in line

    def test_format_header(self):
        header = _format_header(
            thermostat_label="Salon (climate.salon)",
            start=datetime(2025, 3, 14, 8, 0, tzinfo=timezone.utc),
            end=datetime(2025, 3, 14, 10, 0, tzinfo=timezone.utc),
            level_name="INFO",
            count=42,
        )
        assert "Salon (climate.salon)" in header
        assert "INFO and above" in header
        assert "42" in header


# ---------------------------------------------------------------------------
# Unit tests: file cleanup
# ---------------------------------------------------------------------------

class TestFileCleanup:
    """Tests for old file cleanup."""

    def test_cleanup_removes_old_files(self, tmp_path):
        old_file = tmp_path / "vtherm_logs_salon_20250101_000000.log"
        old_file.write_text("old")
        # Set modification time to 48h ago
        old_mtime = time.time() - 48 * 3600
        import os
        os.utime(old_file, (old_mtime, old_mtime))

        recent_file = tmp_path / "vtherm_logs_bureau_20250314_100000.log"
        recent_file.write_text("recent")

        _cleanup_old_files(tmp_path, max_age_hours=24)

        assert not old_file.exists()
        assert recent_file.exists()

    def test_cleanup_ignores_non_matching_files(self, tmp_path):
        other_file = tmp_path / "other.log"
        other_file.write_text("data")
        old_mtime = time.time() - 48 * 3600
        import os
        os.utime(other_file, (old_mtime, old_mtime))

        _cleanup_old_files(tmp_path, max_age_hours=24)
        assert other_file.exists()

    def test_cleanup_nonexistent_dir(self):
        _cleanup_old_files(Path("/nonexistent/dir"))


# ---------------------------------------------------------------------------
# Integration test: async_export_logs
# ---------------------------------------------------------------------------

class TestAsyncExportLogs:
    """Tests for the full export flow."""

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.log_collector.async_sign_path", side_effect=lambda _h, path, _t: path + "?authSig=fake")
    async def test_export_creates_file_and_notification(self, _mock_sign, tmp_path):
        handler = VThermLogHandler()
        # Insert test logs
        record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Salon - Test log entry",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        hass = MagicMock()
        hass.config.path = lambda p: str(tmp_path / p)
        hass.config.external_url = "http://localhost:8123"
        hass.config.internal_url = None
        hass.async_add_executor_job = AsyncMock(side_effect=lambda fn, *a: fn(*a) if not a else fn())
        hass.services.async_call = AsyncMock()

        # Fix: async_add_executor_job should just call the function
        async def run_executor(fn, *args):
            return fn(*args) if args else fn()
        hass.async_add_executor_job = run_executor

        await async_export_logs(
            hass=hass,
            handler=handler,
            thermostat_name="Salon",
            entity_id="climate.salon",
            log_level="INFO",
        )

        # Check file was created
        output_dir = tmp_path / "www" / "versatile_thermostat"
        files = list(output_dir.glob("vtherm_logs_salon_*.log"))
        assert len(files) == 1

        content = files[0].read_text()
        assert "Salon (climate.salon)" in content
        assert "Test log entry" in content
        assert "INFO and above" in content

        # Check notification was sent
        hass.services.async_call.assert_called_once()
        call_args = hass.services.async_call.call_args
        assert call_args[0][0] == "persistent_notification"
        assert call_args[0][1] == "create"
        assert "Copy/paste" in call_args[0][2]["message"]

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.log_collector.async_sign_path", side_effect=lambda _h, path, _t: path + "?authSig=fake")
    async def test_export_all_thermostats(self, _mock_sign, tmp_path):
        handler = VThermLogHandler()
        record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=logging.DEBUG,
            pathname="",
            lineno=0,
            msg="Salon - debug msg",
            args=(),
            exc_info=None,
        )
        handler.emit(record)

        hass = MagicMock()
        hass.config.path = lambda p: str(tmp_path / p)
        hass.config.external_url = "http://localhost:8123"
        hass.config.internal_url = None
        hass.services.async_call = AsyncMock()

        async def run_executor(fn, *args):
            return fn(*args) if args else fn()
        hass.async_add_executor_job = run_executor

        await async_export_logs(
            hass=hass,
            handler=handler,
            thermostat_name=None,
            entity_id=None,
            log_level="DEBUG",
        )

        output_dir = tmp_path / "www" / "versatile_thermostat"
        files = list(output_dir.glob("vtherm_logs_all_*.log"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "All thermostats" in content

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.log_collector.async_sign_path", side_effect=lambda _h, path, _t: path + "?authSig=fake")
    async def test_export_no_entries(self, _mock_sign, tmp_path):
        handler = VThermLogHandler()

        hass = MagicMock()
        hass.config.path = lambda p: str(tmp_path / p)
        hass.config.external_url = "http://localhost:8123"
        hass.config.internal_url = None
        hass.services.async_call = AsyncMock()

        async def run_executor(fn, *args):
            return fn(*args) if args else fn()
        hass.async_add_executor_job = run_executor

        await async_export_logs(
            hass=hass,
            handler=handler,
            thermostat_name="Unknown",
            log_level="ERROR",
        )

        output_dir = tmp_path / "www" / "versatile_thermostat"
        files = list(output_dir.glob("vtherm_logs_unknown_*.log"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Entries    : 0" in content

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.log_collector.async_sign_path", side_effect=lambda _h, path, _t: path + "?authSig=fake")
    async def test_export_with_period(self, _mock_sign, tmp_path):
        handler = VThermLogHandler()
        now = datetime.now(tz=timezone.utc)

        # Insert old and recent records
        old_record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Salon - old entry",
            args=(),
            exc_info=None,
        )
        old_record.created = (now - timedelta(hours=2)).timestamp()
        handler.emit(old_record)

        recent_record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Salon - recent entry",
            args=(),
            exc_info=None,
        )
        recent_record.created = (now - timedelta(minutes=10)).timestamp()
        handler.emit(recent_record)

        hass = MagicMock()
        hass.config.path = lambda p: str(tmp_path / p)
        hass.config.external_url = "http://localhost:8123"
        hass.config.internal_url = None
        hass.services.async_call = AsyncMock()

        async def run_executor(fn, *args):
            return fn(*args) if args else fn()
        hass.async_add_executor_job = run_executor

        await async_export_logs(
            hass=hass,
            handler=handler,
            thermostat_name="Salon",
            entity_id="climate.salon",
            log_level="INFO",
            period_start=now - timedelta(minutes=30),
            period_end=now,
        )

        output_dir = tmp_path / "www" / "versatile_thermostat"
        files = list(output_dir.glob("vtherm_logs_salon_*.log"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "recent entry" in content
        assert "old entry" not in content

    @pytest.mark.asyncio
    @patch("custom_components.versatile_thermostat.log_collector.async_sign_path", side_effect=lambda _h, path, _t: path + "?authSig=fake")
    async def test_export_with_config_entry(self, _mock_sign, tmp_path):
        """Test that config_entry is included in the export header when provided."""
        now = datetime.now(tz=timezone.utc)
        handler = VThermLogHandler()

        # Add a test log entry
        record = logging.LogRecord(
            name="custom_components.versatile_thermostat.base_thermostat",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test log message",
            args=(),
            exc_info=None,
        )
        record.created = now.timestamp()
        handler.emit(record)

        hass = MagicMock()
        hass.config.path = lambda p: str(tmp_path / p)
        hass.config.external_url = "http://localhost:8123"
        hass.config.internal_url = None
        hass.services.async_call = AsyncMock()

        async def run_executor(fn, *args):
            return fn(*args) if args else fn()
        hass.async_add_executor_job = run_executor

        # Test config entry - use simple types only to avoid serialization issues
        config_entry = {
            "name": "TestThermostat",
            "temp_sensor": "sensor.temp",
            "ac_mode": False,
            "cycle_min": 5,
        }

        await async_export_logs(
            hass=hass,
            handler=handler,
            thermostat_name="Salon",
            entity_id="climate.salon",
            log_level="DEBUG",
            config_entry=config_entry,
        )

        output_dir = tmp_path / "www" / "versatile_thermostat"
        files = list(output_dir.glob("vtherm_logs_salon_*.log"))
        assert len(files) == 1
        content = files[0].read_text()

        # Verify configuration is in the header
        assert "Configuration:" in content
        assert "TestThermostat" in content
        assert "sensor.temp" in content
        assert "false" in content.lower()  # ac_mode: false shown in JSON
