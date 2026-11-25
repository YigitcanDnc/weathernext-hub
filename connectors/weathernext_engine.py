import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("weathernext")

# In-memory TTL caches
_CACHE: Dict[Tuple[float, float, int], Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes

_LATEST_INIT_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
LATEST_INIT_TTL_SECONDS = 900  # 15 minutes

WEATHERNEXT_3_COL = "projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_0p1deg"

WN3_BANDS = [
    "temperature_2m_mean",
    "temperature_2m_p10",
    "temperature_2m_p50",
    "temperature_2m_p90",
    "dewpoint_temperature_2m_mean",
    "total_precipitation_1hr_mean",
    "total_precipitation_1hr_p10",
    "total_precipitation_1hr_p50",
    "total_precipitation_1hr_p90",
    "wind_speed_10m_mean",
    "mean_sea_level_pressure_mean",
    "total_cloud_cover_mean",
]


class WeatherNextClient:
    """
    Fast, date-filtered Google DeepMind WeatherNext 3 (0.1deg, 1-hour native resolution,
    precomputed P10/P50/P90 ensemble percentiles) client over Google Earth Engine.
    """

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = (
            project_id
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCP_PROJECT")
            or "weathernext-daily-hub"
        )
        self.ee_initialized = False
        self.active_collection: Optional[str] = None
        self.last_error: Optional[str] = None

    def init_earth_engine(self) -> bool:
        if self.ee_initialized:
            return True
        try:
            import ee
            sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if sa_key and os.path.exists(sa_key):
                from google.oauth2 import service_account
                scopes = ["https://www.googleapis.com/auth/earthengine.readonly"]
                creds = service_account.Credentials.from_service_account_file(sa_key, scopes=scopes)
                ee.Initialize(credentials=creds, project=self.project_id)
            else:
                ee.Initialize(project=self.project_id)
            self.ee_initialized = True
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning("Earth Engine initialization failed: %s", e)
            return False

    def _get_recent_window(self) -> Tuple[str, str]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%S")
        end = (now + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
        return start, end

    def _get_latest_init_info(self, col_id: str) -> Optional[Dict[str, Any]]:
        now_ts = time.time()
        cached = _LATEST_INIT_CACHE.get(col_id)
        if cached and cached[0] > now_ts:
            return cached[1]

        import ee
        start, end = self._get_recent_window()
        recent_ic = ee.ImageCollection(col_id).filterDate(start, end)
        latest = recent_ic.sort("start_time", False).first().getInfo()
        if not latest:
            return None

        bands = [b["id"] for b in latest.get("bands", [])]
        props = latest.get("properties", {})
        info = {
            "collection": col_id,
            "model": col_id.split("/")[-1],
            "latest_init_time": props.get("start_time"),
            "bands_count": len(bands),
            "sample_bands": [b for b in bands if b.endswith("_mean")][:12],
        }
        _LATEST_INIT_CACHE[col_id] = (now_ts + LATEST_INIT_TTL_SECONDS, info)
        return info

    def discover_collection(self) -> Optional[Dict[str, Any]]:
        """
        Probes WeatherNext 3 using a narrow recent date window so Earth Engine never scans
        multi-year archives.
        """
        if not self.init_earth_engine():
            return None

        col_id = os.environ.get("WEATHERNEXT_EE_COLLECTION", WEATHERNEXT_3_COL)
        try:
            info = self._get_latest_init_info(col_id)
            if not info:
                self.last_error = "Son 36 saatte WeatherNext görüntüsü bulunamadı."
                return None
            self.active_collection = col_id
            return info
        except Exception as e:
            self.last_error = str(e)
            return None

    @staticmethod
    def _kelvin_to_c(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        return round(val - 273.15, 2) if val > 150.0 else round(val, 2)

    @staticmethod
    def _precip_to_mm(val: Optional[float]) -> float:
        if val is None or val < 0:
            return 0.0
        # WeatherNext 3 total_precipitation_1hr is in meters (m) -> convert to mm
        return round(val * 1000.0, 2)

    @staticmethod
    def _parse_valid_time_from_id(img_id: str, fallback_ms: int) -> Tuple[datetime, int]:
        """
        WeatherNext image IDs follow `YYYYMMDDHHMM_YYYYMMDDHHMM` (initTime_validTime).
        """
        try:
            parts = img_id.split("_")
            if len(parts) >= 2 and len(parts[-1]) == 12:
                dt = datetime.strptime(parts[-1], "%Y%m%d%H%M").replace(tzinfo=timezone.utc)
                return dt, int(dt.timestamp() * 1000)
        except Exception:
            pass
        dt = datetime.fromtimestamp(fallback_ms / 1000.0, tz=timezone.utc)
        return dt, fallback_ms

    def get_point_forecast(self, lat: float, lon: float, hours: int = 48) -> Optional[Dict[str, Any]]:
        """
        Fetches real Google DeepMind WeatherNext 3 (0.1deg, 1-hour) forecast for (lat, lon)
        with mean + P10/P50/P90 ensemble statistics.
        """
        cache_key = (round(lat, 2), round(lon, 2), hours)
        now_ts = time.time()
        cached = _CACHE.get(cache_key)
        if cached and cached[0] > now_ts:
            return cached[1]

        if not self.init_earth_engine():
            return None

        import ee

        col_id = os.environ.get("WEATHERNEXT_EE_COLLECTION", WEATHERNEXT_3_COL)
        try:
            init_info = self._get_latest_init_info(col_id)
            if not init_info or not init_info.get("latest_init_time"):
                self.last_error = "Güncel WeatherNext koşusu bulunamadı."
                return None

            latest_init = init_info["latest_init_time"]
            start, end = self._get_recent_window()
            recent_ic = ee.ImageCollection(col_id).filterDate(start, end)
            run_ic = (
                recent_ic
                .filter(ee.Filter.eq("start_time", latest_init))
                .filter(ee.Filter.lte("forecast_hour", hours))
                .select(WN3_BANDS)
            )

            point = ee.Geometry.Point([lon, lat])
            raw_table = run_ic.getRegion(point, 11000).getInfo()
            if not raw_table or len(raw_table) < 2:
                self.last_error = "Seçili koordinat için veri dönmedi."
                return None

            header = raw_table[0]
            col_idx = {name: idx for idx, name in enumerate(header)}

            def get_num(row, key: str) -> Optional[float]:
                idx = col_idx.get(key)
                if idx is None or row[idx] is None:
                    return None
                return float(row[idx])

            steps = []
            for row in raw_table[1:]:
                img_id = str(row[col_idx["id"]])
                t_ms_fallback = int(row[col_idx["time"]] or 0)
                dt_valid, valid_ms = self._parse_valid_time_from_id(img_id, t_ms_fallback)

                ws_ms = get_num(row, "wind_speed_10m_mean")
                p_pa = get_num(row, "mean_sea_level_pressure_mean")
                cloud = get_num(row, "total_cloud_cover_mean")

                steps.append({
                    "time_utc": dt_valid.isoformat(),
                    "timestamp_ms": valid_ms,
                    "temp_mean": self._kelvin_to_c(get_num(row, "temperature_2m_mean")),
                    "temp_p10": self._kelvin_to_c(get_num(row, "temperature_2m_p10")),
                    "temp_p50": self._kelvin_to_c(get_num(row, "temperature_2m_p50")),
                    "temp_p90": self._kelvin_to_c(get_num(row, "temperature_2m_p90")),
                    "dew_point_mean": self._kelvin_to_c(get_num(row, "dewpoint_temperature_2m_mean")),
                    "precip_mm_mean": self._precip_to_mm(get_num(row, "total_precipitation_1hr_mean")),
                    "precip_mm_p10": self._precip_to_mm(get_num(row, "total_precipitation_1hr_p10")),
                    "precip_mm_p50": self._precip_to_mm(get_num(row, "total_precipitation_1hr_p50")),
                    "precip_mm_p90": self._precip_to_mm(get_num(row, "total_precipitation_1hr_p90")),
                    "wind_kmh_mean": round(ws_ms * 3.6, 1) if ws_ms is not None else None,
                    "pressure_hpa_mean": round(p_pa / 100.0, 1) if p_pa is not None else None,
                    "cloud_pct_mean": round(cloud * 100.0) if cloud is not None and cloud <= 1.0 else cloud,
                })

            steps.sort(key=lambda x: x["timestamp_ms"])
            self.active_collection = col_id

            result = {
                "source": "google_weathernext",
                "model": col_id.split("/")[-1],
                "collection": col_id,
                "init_time": latest_init,
                "lat": lat,
                "lon": lon,
                "steps_count": len(steps),
                "has_percentiles": True,
                "steps": steps,
            }

            _CACHE[cache_key] = (now_ts + CACHE_TTL_SECONDS, result)
            return result
        except Exception as e:
            self.last_error = str(e)
            logger.exception("WeatherNext 3 query failed: %s", e)
            return None
