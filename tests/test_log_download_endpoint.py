"""Tests for the HTTP log download endpoint."""

import logging
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from custom_components.versatile_thermostat.log_collector import (
    async_register_log_download_endpoint,
    VThermLogHandler,
)


class TestLogDownloadEndpoint(AioHTTPTestCase):
    """Tests for the HTTP download endpoint."""

    async def get_application(self):
        """Create the test application."""
        app = web.Application()
        
        # Create a temporary directory for logs
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        
        # Mock hass
        self.hass = MagicMock()
        self.hass.config.path = lambda p: str(Path(self.temp_dir) / p)
        self.hass.http = app
        
        # Register the endpoint
        await async_register_log_download_endpoint(self.hass)
        
        return app

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        super().tearDown()

    @unittest_run_loop
    async def test_download_valid_log_file(self):
        """Test downloading a valid log file."""
        # Create test log file
        log_dir = Path(self.temp_dir) / "www" / "versatile_thermostat"
        log_dir.mkdir(parents=True, exist_ok=True)
        test_content = "2025-03-15 10:00:00 [INFO] Test log entry"
        log_file = log_dir / "vtherm_logs_salon_20250315_100000.log"
        log_file.write_text(test_content)
        
        # Download the file
        resp = await self.client.request(
            "GET",
            "/api/versatile_thermostat/logs/vtherm_logs_salon_20250315_100000.log"
        )
        assert resp.status == 200
        content = await resp.text()
        assert content == test_content

    @unittest_run_loop
    async def test_download_invalid_filename(self):
        """Test that invalid filenames are rejected."""
        resp = await self.client.request(
            "GET",
            "/api/versatile_thermostat/logs/../../../etc/passwd"
        )
        assert resp.status == 400

    @unittest_run_loop
    async def test_download_nonexistent_file(self):
        """Test that nonexistent files return 404."""
        resp = await self.client.request(
            "GET",
            "/api/versatile_thermostat/logs/vtherm_logs_nonexistent_20250315_100000.log"
        )
        assert resp.status == 404

    @unittest_run_loop
    async def test_download_with_content_disposition(self):
        """Test that Content-Disposition header is set."""
        # Create test log file
        log_dir = Path(self.temp_dir) / "www" / "versatile_thermostat"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "vtherm_logs_bureau_20250315_200000.log"
        log_file.write_text("test")
        
        # Download and check headers
        resp = await self.client.request(
            "GET",
            "/api/versatile_thermostat/logs/vtherm_logs_bureau_20250315_200000.log"
        )
        assert resp.status == 200
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        assert "vtherm_logs_bureau_20250315_200000.log" in resp.headers.get("Content-Disposition", "")

    @unittest_run_loop
    async def test_endpoint_url_format(self):
        """Test that the endpoint URL follows the expected pattern."""
        # Create test log file
        log_dir = Path(self.temp_dir) / "www" / "versatile_thermostat"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "vtherm_logs_all_20250315_123456.log"
        log_file.write_text("log content")
        
        # Try standard filename
        resp = await self.client.request(
            "GET",
            "/api/versatile_thermostat/logs/vtherm_logs_all_20250315_123456.log"
        )
        assert resp.status == 200


class TestLogDownloadEndpointValidation:
    """Unit tests for filename validation logic."""

    def test_valid_filename_pattern(self):
        """Test that valid filenames match the pattern."""
        import re
        pattern = r"^vtherm_logs_[a-z0-9_]+_\d{8}_\d{6}\.log$"
        
        valid_names = [
            "vtherm_logs_salon_20250315_100000.log",
            "vtherm_logs_bureau_20250315_235959.log",
            "vtherm_logs_multi_switch_20250301_000001.log",
            "vtherm_logs_all_20250315_120000.log",
            "vtherm_logs_a_20250315_120000.log",
        ]
        
        for name in valid_names:
            assert re.match(pattern, name) is not None, f"Failed to match: {name}"

    def test_invalid_filename_patterns(self):
        """Test that invalid filenames don't match the pattern."""
        import re
        pattern = r"^vtherm_logs_[a-z0-9_]+_\d{8}_\d{6}\.log$"
        
        invalid_names = [
            "vtherm_logs_Salon_20250315_100000.log",  # uppercase
            "../../../etc/passwd",  # path traversal
            "vtherm_logs_salon_20250315_10000.log",  # wrong timestamp format
            "vtherm_logs_salon.log",  # missing timestamp
            "other_logs_salon_20250315_100000.log",  # wrong prefix
            "vtherm_logs_salon_20250315_100000.txt",  # wrong extension
        ]
        
        for name in invalid_names:
            assert re.match(pattern, name) is None, f"Should not match: {name}"
