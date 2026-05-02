"""External-weather provider + auto-trigger for the coast.

Provides current weather (temp / wind / UV / lightning) so the
operator dashboard can react proactively instead of waiting for a
camera signal. Two providers ship:

- ``MockWeatherProvider`` — deterministic, no network. Default in
  tests and demos.
- ``OpenWeatherProvider`` — real API call via ``httpx``. Activates
  when ``OPENWEATHER_API_KEY`` is set in the environment. Returns a
  best-effort merge of the One Call API's "current" + "alerts"
  blocks. (NOAA / other providers are easy to add by following the
  same Protocol.)

A small auto-trigger rule set inspects each new snapshot and, if
warranted, calls into ``broadcast.record()`` with a stock message.
The broadcast is logged in the audit trail just like an operator
click would have logged it; downstream PA / SMS integration is
deployment-specific.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Protocol

from . import broadcast


@dataclass(frozen=True)
class WeatherSnapshot:
    """Best-effort current weather at a coast site."""

    ts_unix: float
    air_temp_c: float | None
    wind_speed_mps: float | None
    wind_dir_deg: float | None
    uv_index: float | None
    cloud_cover: float | None
    lightning_strikes_5min: int
    forecast_summary: str
    provider: str
    location_lat: float | None = None
    location_lon: float | None = None


class WeatherProvider(Protocol):
    """Pull the current weather for one fixed location."""

    def fetch(
        self, *, lat: float, lon: float,
    ) -> WeatherSnapshot: ...

    def name(self) -> str: ...


# ---------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------


@dataclass
class MockWeatherProvider:
    """Deterministic provider — for tests and demos.

    Override fields after construction to simulate different
    conditions; ``fetch()`` returns a snapshot reflecting the current
    field values.
    """

    air_temp_c: float = 24.0
    wind_speed_mps: float = 4.0
    wind_dir_deg: float = 180.0
    uv_index: float = 5.0
    cloud_cover: float = 0.3
    lightning_strikes_5min: int = 0
    forecast_summary: str = "fair"

    def fetch(self, *, lat: float, lon: float) -> WeatherSnapshot:
        return WeatherSnapshot(
            ts_unix=time.time(),
            air_temp_c=self.air_temp_c,
            wind_speed_mps=self.wind_speed_mps,
            wind_dir_deg=self.wind_dir_deg,
            uv_index=self.uv_index,
            cloud_cover=self.cloud_cover,
            lightning_strikes_5min=int(self.lightning_strikes_5min),
            forecast_summary=self.forecast_summary,
            provider="mock",
            location_lat=lat,
            location_lon=lon,
        )

    def name(self) -> str:
        return "mock"


# ---------------------------------------------------------------------
# OpenWeather provider
# ---------------------------------------------------------------------


class WeatherProviderUnavailable(RuntimeError):
    """Raised when a real provider can't be reached."""


@dataclass
class OpenWeatherProvider:
    """Real OpenWeather One Call 3.0 provider.

    Requires ``OPENWEATHER_API_KEY`` env var. Deliberately
    best-effort — any HTTP failure raises
    :class:`WeatherProviderUnavailable` and the caller can fall back
    to ``MockWeatherProvider``.
    """

    api_key: str
    timeout_s: float = 5.0

    @classmethod
    def from_env(cls) -> "OpenWeatherProvider":
        key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
        if not key:
            raise WeatherProviderUnavailable(
                "OPENWEATHER_API_KEY is not set in environment"
            )
        return cls(api_key=key)

    def fetch(self, *, lat: float, lon: float) -> WeatherSnapshot:
        try:
            import httpx
        except ImportError as exc:
            raise WeatherProviderUnavailable(
                "httpx is required for OpenWeatherProvider"
            ) from exc
        try:
            url = "https://api.openweathermap.org/data/3.0/onecall"
            params = {
                "lat": str(lat),
                "lon": str(lon),
                "exclude": "minutely,hourly,daily",
                "appid": self.api_key,
                "units": "metric",
            }
            r = httpx.get(url, params=params, timeout=self.timeout_s)
            r.raise_for_status()
            payload = r.json()
        except Exception as exc:
            raise WeatherProviderUnavailable(
                f"openweather fetch failed: {exc}"
            ) from exc

        cur = payload.get("current") or {}
        alerts = payload.get("alerts") or []
        # OpenWeather "alerts" are textual; here we just count
        # any alert mentioning "lightning" or "thunder" as 1.
        lightning = 0
        for a in alerts:
            ev = (a.get("event") or "").lower()
            desc = (a.get("description") or "").lower()
            if "lightning" in ev or "thunder" in ev or "thunder" in desc:
                lightning += 1
        weather_arr = cur.get("weather") or []
        summary = (
            weather_arr[0].get("description") if weather_arr
            else "no description"
        )
        return WeatherSnapshot(
            ts_unix=time.time(),
            air_temp_c=cur.get("temp"),
            wind_speed_mps=cur.get("wind_speed"),
            wind_dir_deg=cur.get("wind_deg"),
            uv_index=cur.get("uvi"),
            cloud_cover=(cur.get("clouds") or 0) / 100.0,
            lightning_strikes_5min=lightning,
            forecast_summary=str(summary),
            provider="openweather",
            location_lat=lat,
            location_lon=lon,
        )

    def name(self) -> str:
        return "openweather"


# ---------------------------------------------------------------------
# Auto-trigger rules
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class WeatherTrigger:
    """One auto-broadcast that fired in response to a snapshot."""

    kind: str
    message: str
    reason: str


# Tunable thresholds.
DEFAULT_UV_HIGH = 8.0
DEFAULT_WIND_HIGH_MPS = 12.0
DEFAULT_TEMP_HOT_C = 32.0


def evaluate(
    snap: WeatherSnapshot,
    *,
    uv_high: float = DEFAULT_UV_HIGH,
    wind_high_mps: float = DEFAULT_WIND_HIGH_MPS,
    temp_hot_c: float = DEFAULT_TEMP_HOT_C,
) -> list[WeatherTrigger]:
    """Map a snapshot to zero-or-more broadcast triggers.

    Pure function — does NOT call broadcast.record. The caller is
    responsible for actuation, which keeps the rule set easy to
    test in isolation.
    """
    out: list[WeatherTrigger] = []
    if snap.lightning_strikes_5min > 0:
        out.append(WeatherTrigger(
            kind="lightning",
            message="Lightning detected nearby - clear water and pier immediately.",
            reason=f"lightning_strikes_5min={snap.lightning_strikes_5min}",
        ))
        out.append(WeatherTrigger(
            kind="clear_water",
            message="Clear the swim zone - lightning advisory in force.",
            reason="lightning",
        ))
    if snap.uv_index is not None and snap.uv_index >= uv_high:
        out.append(WeatherTrigger(
            kind="shade_advisory",
            message=(
                f"UV index {snap.uv_index:.1f} - encourage shade, water, "
                "and SPF 50+ on exposed skin."
            ),
            reason=f"uv_index={snap.uv_index}",
        ))
    if snap.wind_speed_mps is not None and snap.wind_speed_mps >= wind_high_mps:
        out.append(WeatherTrigger(
            kind="clear_water",
            message=(
                f"High wind {snap.wind_speed_mps:.1f} m/s - tighten "
                "swim-zone watch; consider closing the swim line."
            ),
            reason=f"wind_speed_mps={snap.wind_speed_mps}",
        ))
    if (
        snap.air_temp_c is not None and snap.air_temp_c >= temp_hot_c
        and snap.uv_index is not None and snap.uv_index >= 6.0
    ):
        out.append(WeatherTrigger(
            kind="general_announcement",
            message=(
                f"Air temperature {snap.air_temp_c:.0f} C with UV "
                f"{snap.uv_index:.1f} - hydration / shade advisory."
            ),
            reason="hot_and_sunny",
        ))
    return out


def actuate(
    triggers: list[WeatherTrigger],
    *,
    operator_id: str = "weather_auto",
) -> list[broadcast.BroadcastEntry]:
    """Record each trigger in the broadcast audit log.

    Side-effecting wrapper. Returns the audit-log entries actually
    appended (some may be deduplicated later by the broadcast layer
    if we add that — for now every call records).
    """
    entries: list[broadcast.BroadcastEntry] = []
    for t in triggers:
        try:
            entries.append(broadcast.record(
                kind=t.kind, message=t.message, operator_id=operator_id,
            ))
        except ValueError:
            continue
    return entries


# ---------------------------------------------------------------------
# Latest-snapshot cache (process-local, thread-safe)
# ---------------------------------------------------------------------


_LATEST: WeatherSnapshot | None = None
_LATEST_LOCK = Lock()


def cache_latest(snap: WeatherSnapshot) -> None:
    global _LATEST
    with _LATEST_LOCK:
        _LATEST = snap


def latest() -> WeatherSnapshot | None:
    with _LATEST_LOCK:
        return _LATEST


def reset() -> None:
    """Test-only — clear the cache."""
    global _LATEST
    with _LATEST_LOCK:
        _LATEST = None


def default_provider() -> WeatherProvider:
    """Pick a real provider if OPENWEATHER_API_KEY is set, else mock."""
    try:
        return OpenWeatherProvider.from_env()
    except WeatherProviderUnavailable:
        return MockWeatherProvider()


# Suppress unused-import warning for ``field`` (kept for callers).
_ = field


__all__ = [
    "DEFAULT_TEMP_HOT_C",
    "DEFAULT_UV_HIGH",
    "DEFAULT_WIND_HIGH_MPS",
    "MockWeatherProvider",
    "OpenWeatherProvider",
    "WeatherProvider",
    "WeatherProviderUnavailable",
    "WeatherSnapshot",
    "WeatherTrigger",
    "actuate",
    "cache_latest",
    "default_provider",
    "evaluate",
    "latest",
    "reset",
]
