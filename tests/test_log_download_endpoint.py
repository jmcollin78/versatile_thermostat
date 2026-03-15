"""Tests for the HTTP log download endpoint."""

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from custom_components.versatile_thermostat.log_collector import (
    LOG_OUTPUT_DIR,
)


class TestLogDownloadViewHandler:
    """Tests for the LogDownloadView HTTP handler."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for logs."""
        log_dir = tmp_path / "www" / "versatile_thermostat"
        log_dir.mkdir(parents=True, exist_ok=True)
        return tmp_path

    @pytest.fixture
    def mock_hass(self, temp_dir):
        """Create a mock hass object."""
        hass = MagicMock()
        hass.config.path = lambda p: str(temp_dir / p)
        return hass

    @pytest.fixture
    async def log_download_view(self, mock_hass):
        """Create a LogDownloadView instance for testing."""
        from homeassistant.components.http import HomeAssistantView

        class LogDownloadView(HomeAssistantView):
            """HTTP view for downloading log files."""

            url = "/api/versatile_thermostat/logs/{filename}"
            name = "api:versatile_thermostat:logs"
            requires_auth = True

            async def get(self, request: web.Request, filename: str) -> web.Response:
                """Serve a log file by name."""
                hass = request.app["hass"]

                # Validate filename to prevent path traversal attacks
                if not re.match(r"^vtherm_logs_[a-z0-9_]+_\d{8}_\d{6}\.log$", filename):
                    return web.Response(status=400, text="Invalid filename")

                log_dir = Path(hass.config.path(LOG_OUTPUT_DIR))
                filepath = log_dir / filename

                # Double-check that file is within the log directory (security)
                try:
                    filepath.resolve().relative_to(log_dir.resolve())
                except ValueError:
                    return web.Response(status=400, text="Invalid path")

                if not filepath.exists():
                    return web.Response(status=404, text="Log file not found")

                if not filepath.is_file():
                    return web.Response(status=404, text="Not a file")

                try:
                    return web.FileResponse(
                        filepath,
                        headers={
                            "Content-Type": "text/plain; charset=utf-8",
                            "Content-Disposition": f'attachment; filename="{filename}"',
                        },
                    )
                except FileNotFoundError:
                    return web.Response(status=404, text="Log file not found")
                except Exception as err:  # pylint: disable=broad-except
                    return web.Response(status=500, text=f"Error: {type(err).__name__}: {err}")

        return LogDownloadView()

    @pytest.mark.asyncio
    async def test_valid_log_file(self, temp_dir, mock_hass, log_download_view):
        """Test downloading a valid log file."""
        # Create a test log file
        log_file = temp_dir / "www" / "versatile_thermostat" / "vtherm_logs_salon_20250315_100000.log"
        log_content = "2025-03-15 10:00:00 [INFO] Test log entry"
        log_file.write_text(log_content)

        # Create mock request
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        # Test the GET handler
        response = await log_download_view.get(request, "vtherm_logs_salon_20250315_100000.log")

        assert response.status == 200
        assert response.headers["Content-Disposition"] == 'attachment; filename="vtherm_logs_salon_20250315_100000.log"'

    @pytest.mark.asyncio
    async def test_invalid_filename_path_traversal(self, mock_hass, log_download_view):
        """Test that path traversal attempts are rejected."""
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        # Test with path traversal attempt
        response = await log_download_view.get(request, "../../../etc/passwd")
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, mock_hass, log_download_view):
        """Test that nonexistent files return 404."""
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        response = await log_download_view.get(request, "vtherm_logs_nonexistent_20250315_100000.log")
        assert response.status == 404

    @pytest.mark.asyncio
    async def test_invalid_filename_uppercase(self, mock_hass, log_download_view):
        """Test that uppercase letters in filename are rejected."""
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        response = await log_download_view.get(request, "vtherm_logs_Salon_20250315_100000.log")
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_invalid_filename_extension(self, mock_hass, log_download_view):
        """Test that wrong file extension is rejected."""
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        response = await log_download_view.get(request, "vtherm_logs_salon_20250315_100000.txt")
        assert response.status == 400

    @pytest.mark.asyncio
    async def test_content_disposition_header(self, temp_dir, mock_hass, log_download_view):
        """Test that Content-Disposition header is properly set."""
        # Create a test log file
        log_file = temp_dir / "www" / "versatile_thermostat" / "vtherm_logs_bureau_20250315_200000.log"
        log_file.write_text("test content")

        # Create mock request
        request = MagicMock(spec=web.Request)
        request.app = {"hass": mock_hass}

        # Test the GET handler
        response = await log_download_view.get(request, "vtherm_logs_bureau_20250315_200000.log")

        assert response.status == 200
        disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in disposition
        assert "vtherm_logs_bureau_20250315_200000.log" in disposition


class TestLogDownloadEndpointValidation:
    """Unit tests for filename validation logic."""

    def test_valid_filename_pattern(self):
        """Test that valid filenames match the pattern."""
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
