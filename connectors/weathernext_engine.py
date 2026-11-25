import os
import math
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("weathernext")

# In-memory TTL cache: (lat_r, lon_r) -> (expires_at, payload)
_CACHE: Dict[Tuple[float, float], Tuple[float, Dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 1800  # 30 minutes

# Default Earth Engine WeatherNext collections (priority order: WeatherNext 3 0.1deg -> WeatherNext 2 Mean)
DEFAULT_EE_COLLECTIONS = [
    "projects/gcp-public-data-weathernext/assets/weathernext_3_0_0_0p1deg",
    "projects/gcp-public-data-weathernext/assets/weathernext_2_0_0_mean",
    "projects/gcp-public-data-weathernext/assets/weathernext_2_0_0",
]


class WeatherNextClient:
    """
    Connects to Google DeepMind WeatherNext datasets via Google Earth Engine (preferred for
    low-latency point queries & WeatherNext 3 1-hour 0.1deg ensemble percentiles) or BigQuery.
    """

    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        self.ee_initialized = False
        self.active_collection: Optional[str] = None
        self.band_map: Dict[str, str] = {}
        self.last_error: Optional[str] = None

    def init_earth_engine(self) -> bool:
        if self.ee_initialized:
            return True
        try:
            import ee
            # Support Service Account JSON (for Cloud Run) or ADC / user Earth Engine credentials
            sa_key = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
            if sa_key and os.path.exists(sa_key):
                from google.oauth2 import service_account
                scopes = ["https://www.googleapis.com/auth/earthengine"]
                creds = service_account.Credentials.from_service_account_file(sa_key, scopes=scopes)
                ee.Initialize(credentials=creds, project=self.project_id)
            else:
                if self.project_id:
                    ee.Initialize(project=self.project_id)
                else:
                    ee.Initialize()
            self.ee_initialized = True
            self.last_error = None
            return True
        except Exception as e:
            self.last_error = str(e)
            logger.warning("Earth Engine initialization failed: %s", e)
            return False

    def discover_collection(self) -> Optional[Dict[str, Any]]:
        """
        Probes WeatherNext Earth Engine collections accessible to the authenticated account
        and auto-maps band names (temperature, precipitation, wind, dewpoint, pressure, cloud).
        """
        if not self.init_earth_engine():
            return None

        import ee

        custom_col = os.environ.get("WEATHERNEXT_EE_COLLECTION")
        candidates = [custom_col] + DEFAULT_EE_COLLECTIONS if custom_col else DEFAULT_EE_COLLECTIONS

        for col_id in candidates:
            if not col_id:
                continue
            try:
                ic = ee.ImageCollection(col_id)
                # Grab the most recent image metadata
                latest = ic.sort("system:time_start", False).first()
                info = latest.getInfo()
                if not info:
                    continue
                bands = [b["id"] for b in info.get("bands", [])]
                props = info.get("properties", {})
                self.active_collection = col_id
                self.band_map = self._map_bands(bands)
                return {
                    "collection": col_id,
                    "bands_count": len(bands),
                    "sample_bands": bands[:24],
                    "mapped_bands": self.band_map,
                    "properties": {k: props.get(k) for k in list(props.keys())[:15]},
                }
            except Exception as e:
                self.last_error = f"{col_id}: {e}"
                continue
        return None

    @staticmethod
    def _map_bands(bands: List[str]) -> Dict[str, str]:
        """
        Matches WeatherNext 2 / 3 band names flexibly (e.g., 2m_temperature_mean, temperature_2m_mean, etc.).
        """
        low = {b.lower(): b for b in bands}

        def pick(patterns: List[str]) -> Optional[str]:
            for pat in patterns:
                for bl, orig in low.items():
                    if pat == bl:
                        return orig
            for pat in patterns:
                for bl, orig in low.items():
                    if pat in bl:
                        return orig
            return None

        mapping = {
            "temp_mean": pick(["2m_temperature_mean", "temperature_2m_mean", "2m_temperature", "temperature_2m"]),
            "temp_p10": pick(["2m_temperature_p10", "temperature_2m_p10"]),
            "temp_p50": pick(["2m_temperature_p50", "temperature_2m_p50"]),
            "temp_p90": pick(["2m_temperature_p90", "temperature_2m_p90"]),
            "dew_mean": pick(["2m_dewpoint_temperature_mean", "dewpoint_2m_mean", "2m_dewpoint", "dew_point"]),
            "precip_mean": pick(["total_precipitation_1hr_mean", "total_precipitation_6hr_mean", "total_precipitation_mean", "total_precipitation"]),
            "precip_p10": pick(["total_precipitation_1hr_p10", "total_precipitation_6hr_p10", "total_precipitation_p10"]),
            "precip_p50": pick(["total_precipitation_1hr_p50", "total_precipitation_6hr_p50", "total_precipitation_p50"]),
            "precip_p90": pick(["total_precipitation_1hr_p90", "total_precipitation_6hr_p90", "total_precipitation_p90"]),
            "u10_mean": pick(["10m_u_component_of_wind_mean", "u_component_of_wind_10m_mean", "10m_u_component_of_wind"]),
            "v10_mean": pick(["10m_v_component_of_wind_mean", "v_component_of_wind_10m_mean", "10m_v_component_of_wind"]),
            "wind_speed_mean": pick(["10m_wind_speed_mean", "wind_speed_10m_mean"]),
            "pressure_mean": pick(["mean_sea_level_pressure_mean", "mean_sea_level_pressure", "surface_pressure_mean"]),
            "cloud_mean": pick(["total_cloud_cover_mean", "total_cloud_cover", "cloud_cover_mean"]),
        }
        return {k: v for k, v in mapping.items() if v}

    @staticmethod
    def _kelvin_to_c(val: Optional[float]) -> Optional[float]:
        if val is None:
            return None
        return round(val - 273.15, 2) if val > 150.0 else round(val, 2)

    @staticmethod
    def _precip_to_mm(val: Optional[float]) -> float:
        if val is None or val < 0:
            return 0.0
        # WeatherNext / ERA5 total precipitation is commonly stored in meters (m); convert to mm
        return round(val * 1000.0, 2) if val < 0.5 else round(val, 2)

    def get_point_forecast(self, lat: float, lon: float, hours: int = 72) -> Optional[Dict[str, Any]]:
        """
        Fetches real Google WeatherNext forecast timeseries for (lat, lon) via Earth Engine.
        Returns normalized hourly/step forecast with ensemble percentiles (mean, p10, p90).
        """
        cache_key = (round(lat, 2), round(lon, 2))
        now_ts = time.time()
        cached = _CACHE.get(cache_key)
        if cached and cached[0] > now_ts:
            return cached[1]

        if not self.active_collection:
            discovered = self.discover_collection()
            if not discovered:
                return None

        import ee

        try:
            ic = ee.ImageCollection(self.active_collection)

            # Determine latest initialization run (init_time / start_time property if present)
            latest_img = ic.sort("system:time_start", False).first()
            latest_props = latest_img.getInfo().get("properties", {})

            init_key = None
            for candidate_key in ["init_time", "start_time", "forecast_reference_time"]:
                if candidate_key in latest_props:
                    init_key = candidate_key
                    break

            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            end_ms = int((datetime.now(timezone.utc) + timedelta(hours=hours)).timestamp() * 1000)

            if init_key:
                latest_init_val = latest_props[init_key]
                filtered = ic.filter(ee.Filter.eq(init_key, latest_init_val))
            else:
                filtered = ic.filterDate(now_ms - 6 * 3600 * 1000, end_ms)

            selected_bands = list(set(self.band_map.values()))
            if not selected_bands:
                return None

            point = ee.Geometry.Point([lon, lat])
            scale = 11000 if "0p1deg" in self.active_collection else 27000

            # Extract pixel values across the forecast run in a single Earth Engine call
            raw_table = filtered.select(selected_bands).getRegion(point, scale).getInfo()
            if not raw_table or len(raw_table) < 2:
                return None

            header = raw_table[0]
            col_idx = {name: idx for idx, name in enumerate(header)}

            def read_val(row, logical_key: str) -> Optional[float]:
                band_name = self.band_map.get(logical_key)
                if not band_name or band_name not in col_idx:
                    return None
                v = row[col_idx[band_name]]
                return float(v) if v is not None else None

            steps = []
            for row in raw_table[1:]:
                t_ms = row[col_idx["time"]]
                if t_ms is None:
                    continue
                dt_utc = datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc)
                temp_mean = self._kelvin_to_c(read_val(row, "temp_mean"))
                temp_p10 = self._kelvin_to_c(read_val(row, "temp_p10"))
                temp_p90 = self._kelvin_to_c(read_val(row, "temp_p90"))
                dew_mean = self._kelvin_to_c(read_val(row, "dew_mean"))

                precip_mean = self._precip_to_mm(read_val(row, "precip_mean"))
                precip_p10 = self._precip_to_mm(read_val(row, "precip_p10"))
                precip_p90 = self._precip_to_mm(read_val(row, "precip_p90"))

                u10 = read_val(row, "u10_mean")
                v10 = read_val(row, "v10_mean")
                ws = read_val(row, "wind_speed_mean")
                if ws is not None:
                    wind_kmh = round(ws * 3.6, 1)
                elif u10 is not None and v10 is not None:
                    wind_kmh = round(math.hypot(u10, v10) * 3.6, 1)
                else:
                    wind_kmh = None

                p_raw = read_val(row, "pressure_mean")
                pressure_hpa = round(p_raw / 100.0, 1) if p_raw and p_raw > 2000 else (round(p_raw, 1) if p_raw else None)

                cloud_raw = read_val(row, "cloud_mean")
                cloud_pct = round(cloud_raw * 100.0, 0) if cloud_raw is not None and cloud_raw <= 1.0 else cloud_raw

                steps.append({
                    "time_utc": dt_utc.isoformat(),
                    "timestamp_ms": t_ms,
                    "temp_mean": temp_mean,
                    "temp_p10": temp_p10,
                    "temp_p90": temp_p90,
                    "dew_point_mean": dew_mean,
                    "precip_mm_mean": precip_mean,
                    "precip_mm_p10": precip_p10,
                    "precip_mm_p90": precip_p90,
                    "wind_kmh_mean": wind_kmh,
                    "pressure_hpa_mean": pressure_hpa,
                    "cloud_pct_mean": cloud_pct,
                })

            steps.sort(key=lambda x: x["timestamp_ms"])

            result = {
                "source": "google_weathernext",
                "model": self.active_collection.split("/")[-1],
                "collection": self.active_collection,
                "init_time": str(latest_props.get(init_key, "")) if init_key else "",
                "lat": lat,
                "lon": lon,
                "steps_count": len(steps),
                "has_percentiles": "temp_p10" in self.band_map and "temp_p90" in self.band_map,
                "steps": steps,
            }

            _CACHE[cache_key] = (now_ts + CACHE_TTL_SECONDS, result)
            return result
        except Exception as e:
            self.last_error = str(e)
            logger.exception("WeatherNext Earth Engine query failed: %s", e)
            return None
