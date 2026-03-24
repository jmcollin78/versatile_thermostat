"""In-memory log collector for Versatile Thermostat.

Captures all log records from the VTherm logger hierarchy into a ring buffer.
Provides filtering by thermostat name, log level and time window, and export
to a downloadable text file served from config/www/.
"""

from __future__ import annotations

import logging
import re
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from aiohttp import web
from homeassistant.components.http.auth import async_sign_path
from homeassistant.helpers.network import get_url

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.components.http import HomeAssistantView


def _parse_to_utc(value: datetime | str | None) -> datetime | None:
    """Convert a datetime or ISO string (assumed local) to UTC aware datetime.

    Uses homeassistant.util.dt when available (runtime), falls back to
    fromisoformat for unit tests.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            try:
                from homeassistant.util import dt as dt_util  # pylint: disable=import-outside-toplevel
                return dt_util.as_utc(value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
            except ImportError:
                return value.replace(tzinfo=timezone.utc)
        return value
    # str path
    try:
        from homeassistant.util import dt as dt_util  # pylint: disable=import-outside-toplevel
        parsed = dt_util.parse_datetime(value)
        if parsed is not None:
            return dt_util.as_utc(parsed)
    except ImportError:
        pass
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)

_LOGGER = logging.getLogger(__name__)

THERMOSTAT_PATTERN = re.compile(r"^(.+?) - ")

DEFAULT_MAX_AGE_HOURS = 4
DEFAULT_MAX_ENTRIES = 100_000
PURGE_EVERY_N = 1000
LOG_OUTPUT_DIR = "www/versatile_thermostat"
OLD_FILE_MAX_AGE_HOURS = 24

LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def _extract_thermostat_hint(message: str) -> str | None:
    """Extract the thermostat name from a log message following the '%s - ...' pattern."""
    match = THERMOSTAT_PATTERN.match(message)
    return match.group(1) if match else None


def _hint_matches_thermostat(hint_lower: str, name_lower: str) -> bool:
    """Check if a log hint belongs to the given thermostat name.

    Matches generically all formats where the thermostat name appears
    after a class prefix separated by '-':
      - '{name}'                                       (exact match)
      - '{Prefix}-{name}'                              (e.g. EMA-Salon)
      - '{Prefix}-{name}-{entity}'                     (e.g. VersatileThermostat-Salon-input_boolean.heater1)
    """
    if hint_lower == name_lower:
        return True
    suffix = "-" + name_lower
    # '{Prefix}-{name}'
    if hint_lower.endswith(suffix):
        return True
    # '{Prefix}-{name}-{entity}'
    if suffix + "-" in hint_lower:
        return True
    return False


def _short_logger_name(name: str) -> str:
    """Return only the last part of a dotted logger name."""
    return name.rsplit(".", 1)[-1]


class VThermLogger(logging.Logger):
    """Logger subclass that always feeds the collector regardless of the effective level.

    isEnabledFor() always returns True so that LogRecords are created for every
    call (debug, info, …).  In callHandlers(), the record is forwarded to the
    ring-buffer collector unconditionally, while the normal HA handler chain is
    only reached when the record level satisfies the configured effective level.
    This preserves the user's logger.yaml configuration for home-assistant.log
    while still capturing everything in the in-memory buffer.
    """

    _collector: ClassVar[VThermLogHandler | None] = None  # set by VThermLogHandler.__init__

    def isEnabledFor(self, level: int) -> bool:  # type: ignore[override]
        """Always return True so that LogRecords are always created."""
        return True

    def callHandlers(self, record: logging.LogRecord) -> None:
        """Send record to collector unconditionally; to other handlers only if level allows."""
        if VThermLogger._collector is not None:
            try:
                VThermLogger._collector.emit(record)
            except Exception:  # noqa: BLE001
                pass
        if record.levelno >= self.getEffectiveLevel():
            super().callHandlers(record)


def get_vtherm_logger(name: str) -> VThermLogger:
    """Return a VThermLogger for *name*, replacing the standard Logger in the Manager.

    Calls logging.getLogger(name) first so that the Manager sets up the parent
    chain correctly, then swaps the entry for a VThermLogger while preserving
    all attributes (level, handlers, parent, propagate, disabled).
    """
    manager = logging.Logger.manager
    existing = manager.loggerDict.get(name)
    if isinstance(existing, VThermLogger):
        return existing
    # Let the Manager create/retrieve the standard Logger (parent chain already set up)
    std = logging.getLogger(name)
    if isinstance(std, VThermLogger):
        return std
    vl = VThermLogger(name, std.level)
    vl.parent = std.parent  # type: ignore[assignment]
    vl.propagate = std.propagate
    vl.handlers = std.handlers
    vl.disabled = std.disabled
    manager.loggerDict[name] = vl
    return vl


@dataclass(slots=True)
class VThermLogEntry:
    """A single log entry stored in the ring buffer."""

    timestamp: datetime
    level: int
    logger_name: str
    message: str
    thermostat_hint: str | None


class VThermLogHandler(logging.Handler):
    """Custom logging handler that stores records in an in-memory ring buffer."""

    def __init__(
        self,
        max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
        max_entries: int = DEFAULT_MAX_ENTRIES,
    ):
        super().__init__(level=logging.DEBUG)
        self._max_age = timedelta(hours=max_age_hours)
        self._buffer: deque[VThermLogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()
        self._insert_count = 0
        # Register this handler as the collector for all VThermLogger instances
        VThermLogger._collector = self

    # --- Handler interface ---------------------------------------------------

    def emit(self, record: logging.LogRecord) -> None:
        """Store a log record in the buffer."""
        try:
            msg = self.format(record) if self.formatter else record.getMessage()
            entry = VThermLogEntry(
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc),
                level=record.levelno,
                logger_name=record.name,
                message=msg,
                thermostat_hint=_extract_thermostat_hint(msg),
            )
            with self._lock:
                self._buffer.append(entry)
                self._insert_count += 1
                if self._insert_count >= PURGE_EVERY_N:
                    self._purge_old_unlocked()
                    self._insert_count = 0
        except Exception:  # noqa: BLE001 – handler must never raise
            self.handleError(record)

    # --- Query interface -----------------------------------------------------

    def get_entries(
        self,
        thermostat_name: str | None = None,
        min_level: int = logging.DEBUG,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[VThermLogEntry]:
        """Return filtered entries from the buffer.

        Args:
            thermostat_name: If set, only entries whose thermostat_hint matches
                             (case-insensitive) OR entries without a hint are returned.
            min_level: Minimum log level (inclusive).
            start: Start of the time window (UTC aware datetime). Defaults to now - 60 min.
            end: End of the time window (UTC aware datetime). Defaults to now.
        """
        now = datetime.now(tz=timezone.utc)
        if end is None:
            end = now
        if start is None:
            start = end - timedelta(minutes=60)

        hint_lower = thermostat_name.lower() if thermostat_name else None

        with self._lock:
            entries = list(self._buffer)

        result: list[VThermLogEntry] = []
        for e in entries:
            if e.timestamp < start or e.timestamp > end:
                continue
            if e.level < min_level:
                continue
            if hint_lower is not None:
                if e.thermostat_hint is not None and not _hint_matches_thermostat(e.thermostat_hint.lower(), hint_lower):
                    continue
            result.append(e)
        return result

    # --- Purge ---------------------------------------------------------------

    def _purge_old_unlocked(self) -> None:
        """Remove entries older than max_age. Must be called with lock held."""
        cutoff = datetime.now(tz=timezone.utc) - self._max_age
        while self._buffer and self._buffer[0].timestamp < cutoff:
            self._buffer.popleft()

    def purge(self) -> None:
        """Public purge method."""
        with self._lock:
            self._purge_old_unlocked()

    # --- Buffer info ---------------------------------------------------------

    @property
    def size(self) -> int:
        """Return current number of entries."""
        with self._lock:
            return len(self._buffer)


# ---------------------------------------------------------------------------
# HTTP Endpoint for log downloads
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# HTTP Endpoint for log downloads
# ---------------------------------------------------------------------------


async def async_register_log_download_endpoint(hass: HomeAssistant) -> None:
    """Register the HTTP endpoint for log downloads.

    This creates a custom view to serve log files via /api/versatile_thermostat/logs/<filename>
    instead of using static /local/ paths, which ensures compatibility with reverse proxies
    and external domain configurations.
    """
    from homeassistant.components.http import HomeAssistantView  # pylint: disable=import-outside-toplevel

    # Define the view class here to have proper access to hass
    class LogDownloadView(HomeAssistantView):
        """HTTP view for downloading log files."""

        url = "/api/versatile_thermostat/logs/{filename}"
        name = "api:versatile_thermostat:logs"
        requires_auth = True

        async def get(self, request: web.Request, filename: str) -> web.Response:  # pylint: disable=unused-argument
            """Serve a log file by name.

            Args:
                request: The HTTP request
                filename: The log filename from the URL pattern

            Returns:
                HTTP response with file content or 404 if not found.
            """
            # Get hass from the request app context
            hass = request.app["hass"]

            # Validate filename to prevent path traversal attacks
            # Only allow valid log filenames: vtherm_logs_<name>_<timestamp>.log
            if not re.match(r"^vtherm_logs_[a-z0-9_]+_\d{8}_\d{6}\.log$", filename):
                _LOGGER.warning("Attempted to download invalid log filename: %s", filename)
                return web.Response(status=400, text="Invalid filename")

            log_dir = Path(hass.config.path(LOG_OUTPUT_DIR))
            filepath = log_dir / filename

            _LOGGER.debug("Download request for log file: %s", filename)
            _LOGGER.debug("Log directory: %s", log_dir)
            _LOGGER.debug("Full filepath: %s", filepath)

            # Double-check that file is within the log directory (security)
            try:
                filepath.resolve().relative_to(log_dir.resolve())
            except ValueError:
                _LOGGER.warning("Attempted to download file outside log directory: %s", filepath)
                return web.Response(status=400, text="Invalid path")

            if not filepath.exists():
                _LOGGER.warning("Log file does not exist: %s", filepath)
                _LOGGER.debug("Directory contents: %s", list(log_dir.glob("*.log")) if log_dir.exists() else "Directory doesn't exist")
                return web.Response(status=404, text="Log file not found")

            if not filepath.is_file():
                _LOGGER.warning("Path exists but is not a file: %s", filepath)
                return web.Response(status=404, text="Not a file")

            try:
                _LOGGER.debug("Reading log file: %s", filepath)
                # Use FileResponse which handles streaming and async automatically
                return web.FileResponse(
                    filepath,
                    headers={
                        "Content-Type": "text/plain; charset=utf-8",
                        "Content-Disposition": f'attachment; filename="{filename}"',
                    },
                )
            except FileNotFoundError:
                _LOGGER.warning("Log file was deleted since existence check: %s", filepath)
                return web.Response(status=404, text="Log file not found")
            except OSError as err:
                _LOGGER.error("OS error serving log file %s: %s", filepath, err)
                return web.Response(status=500, text=f"OS error: {err}")
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Unexpected error serving log file %s: %s", filepath, err)
                return web.Response(status=500, text=f"Error: {type(err).__name__}: {err}")

    if hass.http is not None:
        hass.http.register_view(LogDownloadView)
    else:
        _LOGGER.warning("HTTP server not available, log download endpoint not registered")


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def _format_entry(entry: VThermLogEntry) -> str:
    """Format a log entry as a single line."""
    ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    level = logging.getLevelName(entry.level).ljust(7)
    short_name = _short_logger_name(entry.logger_name).ljust(18)
    return f"{ts} {level} [{short_name}] {entry.message}"


def _format_header(
    thermostat_label: str,
    start: datetime,
    end: datetime,
    level_name: str,
    count: int,
    config_entry: dict | None = None,
) -> str:
    """Build the header block of the export file."""
    import json
    from homeassistant.util import dt as dt_util  # pylint: disable=import-outside-toplevel

    sep = "=" * 80
    now_str = dt_util.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    header = (
        f"{sep}\n"
        f"Versatile Thermostat - Log Export\n"
        f"Thermostat : {thermostat_label}\n"
        f"Period     : {start.strftime('%Y-%m-%d %H:%M:%S')} → {end.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"Level      : {level_name} and above\n"
        f"Entries    : {count}\n"
        f"Generated  : {now_str}\n"
    )

    if config_entry:
        header += f"\nConfiguration:\n" f"{json.dumps(config_entry, indent=2, default=str)}\n"

    header += f"{sep}\n"
    return header


def _cleanup_old_files(directory: Path, max_age_hours: int = OLD_FILE_MAX_AGE_HOURS) -> None:
    """Remove .log files older than *max_age_hours* in *directory*."""
    if not directory.is_dir():
        return
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=max_age_hours)
    for f in directory.glob("vtherm_logs_*.log"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
        except OSError:
            pass


async def async_export_logs(
    hass: HomeAssistant,
    handler: VThermLogHandler,
    thermostat_name: str | None = None,
    entity_id: str | None = None,
    log_level: str = "DEBUG",
    period_start: datetime | str | None = None,
    period_end: datetime | str | None = None,
    config_entry: dict | None = None,
) -> None:
    """Filter logs, write export file, send persistent notification."""
    from homeassistant.util import dt as dt_util  # pylint: disable=import-outside-toplevel

    min_level = LEVEL_MAP.get(log_level.upper(), logging.DEBUG)

    # Convert to UTC-aware datetime
    period_start = _parse_to_utc(period_start)
    period_end = _parse_to_utc(period_end)

    # Use dt_util for consistent time reference
    now_utc = dt_util.utcnow()

    # Apply defaults
    eff_end = period_end or now_utc
    eff_start = period_start or (eff_end - timedelta(minutes=60))

    entries = handler.get_entries(
        thermostat_name=thermostat_name,
        min_level=min_level,
        start=eff_start,
        end=eff_end,
    )

    # Label for the header
    if thermostat_name:
        label = f"{thermostat_name} ({entity_id})" if entity_id else thermostat_name
    else:
        label = "All thermostats"

    header = _format_header(label, eff_start, eff_end, log_level.upper(), len(entries), config_entry)
    body = "\n".join(_format_entry(e) for e in entries)
    content = header + "\n" + body + "\n"

    # Build output path
    safe_name = re.sub(r"[^a-z0-9_]", "_", (thermostat_name or "all").lower())
    ts_tag = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"vtherm_logs_{safe_name}_{ts_tag}.log"

    output_dir = Path(hass.config.path(LOG_OUTPUT_DIR))

    def _write() -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        filepath = output_dir / filename
        filepath.write_text(content, encoding="utf-8")
        _cleanup_old_files(output_dir)
        return filepath

    await hass.async_add_executor_job(_write)

    # Send persistent notification with a signed download link.
    # requires_auth=True on the view means a normal browser GET would get 401.
    # async_sign_path generates a time-limited token in the query string so the
    # link works without an Authorization header.  We also build an absolute URL
    # so the HA frontend SPA router does not intercept the click.
    # We use hass.config.external_url / internal_url (user-configured) instead
    # of get_url() which auto-detects and returns the Docker container IP.
    raw_path = f"/api/versatile_thermostat/logs/{filename}"
    try:
        signed_path = async_sign_path(
            hass,
            raw_path,
            timedelta(hours=OLD_FILE_MAX_AGE_HOURS),
        )
    except Exception:  # noqa: BLE001
        signed_path = raw_path
    base_url = hass.config.external_url or hass.config.internal_url
    if not base_url:
        try:
            base_url = get_url(hass)
        except Exception:  # noqa: BLE001
            base_url = ""
    # Strip trailing slash if present
    base_url = base_url.rstrip("/") if base_url else ""
    download_url = f"{base_url}{signed_path}"
    notif_msg = (
        f"**VTherm Log Export**\n\n"
        f"Thermostat: {label}\n"
        f"Period: {eff_start.strftime('%Y-%m-%d %H:%M')} → {eff_end.strftime('%Y-%m-%d %H:%M')} UTC\n"
        f"Level: {log_level.upper()}\n"
        f"Entries: {len(entries)}\n\n"
        f"Copy/paste the link below into your browser to download the log file:\n\n"
        f"{download_url}"
    )

    await hass.services.async_call(
        "persistent_notification",
        "create",
        {
            "title": "Versatile Thermostat - Logs Ready",
            "message": notif_msg,
            "notification_id": f"vtherm_logs_{safe_name}",
        },
    )
