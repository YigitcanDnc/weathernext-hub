import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("ee_datasets")

_EE_MOD_CACHE: Dict[Tuple[str, float, float, int], Tuple[float, Dict[str, Any]]] = {}
_TTL_REALTIME = 1800   # 30 minutes for CAMS/S5P & FIRMS
_TTL_CLIMATE = 86400   # 24 hours for 10-year ERA5-Land climate normal


class EarthEngineInsightsClient:
    """
    Modular Google Earth Engine environmental dataset queries reusing WeatherNextClient auth:
    - dust: ECMWF/CAMS/NRT (aerosol optical depth 550nm) + COPERNICUS/S5P/NRTI/L3_AER_AI
    - fire: NASA/LANCE/SNPP_VIIRS/C2 (with FIRMS fallback) within 50 km radius
    - climate: ECMWF/ERA5_LAND/MONTHLY_AGGR 10-year (2015-2025) monthly temperature & precip normal
    """

    def __init__(self, weathernext_client):
        self.wn_client = weathernext_client
        self.last_error: Optional[str] = None

    def get_insights(self, lat: float, lon: float, modules: List[str]) -> Dict[str, Any]:
        if not self.wn_client.init_earth_engine():
            self.last_error = self.wn_client.last_error or "Earth Engine bağlantısı kurulamadı."
            return {"available": False, "error": self.last_error, "modules": {}}

        lat_r = round(float(lat), 2)
        lon_r = round(float(lon), 2)
        now = datetime.now(timezone.utc)
        now_ts = time.time()
        out_modules: Dict[str, Any] = {}

        for mod in modules:
            if mod not in ("dust", "fire", "climate"):
                continue
            month_key = now.month if mod == "climate" else 0
            ckey = (mod, lat_r, lon_r, month_key)
            cached = _EE_MOD_CACHE.get(ckey)
            if cached and cached[0] > now_ts:
                out_modules[mod] = cached[1]
                continue

            try:
                if mod == "dust":
                    res = self._query_dust(lat_r, lon_r, now)
                    ttl = _TTL_REALTIME
                elif mod == "fire":
                    res = self._query_fire(lat_r, lon_r, now)
                    ttl = _TTL_REALTIME
                else:
                    res = self._query_climate(lat_r, lon_r, now.month)
                    ttl = _TTL_CLIMATE

                _EE_MOD_CACHE[ckey] = (now_ts + ttl, res)
                out_modules[mod] = res
            except Exception as e:
                logger.warning("EE module %s failed at (%s, %s): %s", mod, lat_r, lon_r, e)
                out_modules[mod] = {"ok": False, "error": str(e)}

        return {
            "available": True,
            "lat": lat_r,
            "lon": lon_r,
            "modules": out_modules,
        }

    def _query_dust(self, lat: float, lon: float, now: datetime) -> Dict[str, Any]:
        import ee

        point = ee.Geometry.Point([lon, lat])
        end_str = (now + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S")
        start_cams = (now - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%S")
        start_s5p = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")

        aod_550 = None
        try:
            cams_img = (
                ee.ImageCollection("ECMWF/CAMS/NRT")
                .filterDate(start_cams, end_str)
                .select(["total_aerosol_optical_depth_at_550nm_surface"])
                .sort("system:time_start", False)
                .first()
            )
            cams_dict = cams_img.reduceRegion(ee.Reducer.first(), point, 45000).getInfo() or {}
            raw_aod = cams_dict.get("total_aerosol_optical_depth_at_550nm_surface")
            if raw_aod is not None:
                aod_550 = round(float(raw_aod), 3)
        except Exception as e:
            logger.debug("CAMS AOD lookup skipped: %s", e)

        uvai = None
        try:
            region = point.buffer(25000)
            s5p_img = (
                ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_AER_AI")
                .filterBounds(region)
                .filterDate(start_s5p, end_str)
                .select(["absorbing_aerosol_index"])
                .median()
            )
            s5p_dict = s5p_img.reduceRegion(ee.Reducer.median(), region, 10000).getInfo() or {}
            raw_ai = s5p_dict.get("absorbing_aerosol_index")
            if raw_ai is not None:
                uvai = round(float(raw_ai), 2)
        except Exception as e:
            logger.debug("Sentinel-5P UVAI lookup skipped: %s", e)

        if aod_550 is None and uvai is None:
            return {"ok": False, "error": "Güncel uydu aerosol verisi alınamadı"}

        score = max(aod_550 or 0.0, ((uvai or 0.0) * 0.35) if (uvai or 0.0) > 0 else 0.0)
        if score >= 0.70 or (uvai is not None and uvai >= 2.0):
            level, desc = "Yoğun Toz Taşınımı", "Belirgin Sahra tozu / aerosol yükü tespit edildi; hassas gruplar dikkatli olmalı."
        elif score >= 0.40 or (uvai is not None and uvai >= 1.0):
            level, desc = "Orta Sahra Tozu", "Atmosferde orta düzeyde toz ve ince partikül taşınımı gözleniyor."
        elif score >= 0.20 or (uvai is not None and uvai >= 0.3):
            level, desc = "Hafif Aerosol", "Hafif düzeyde atmosferik toz / pus mevcut."
        else:
            level, desc = "Temiz Atmosfer", "Uydu ölçümlerine göre çöl tozu veya yoğun aerosol taşınımı görünmüyor."

        return {
            "ok": True,
            "aod_550": aod_550,
            "uv_aerosol_index": uvai,
            "level": level,
            "summary": desc,
            "source": "ECMWF CAMS NRT + Sentinel-5P",
        }

    def _query_fire(self, lat: float, lon: float, now: datetime) -> Dict[str, Any]:
        import ee

        region = ee.Geometry.Point([lon, lat]).buffer(50000)  # 50 km radius
        end_str = (now + timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%S")
        start_str = (now - timedelta(hours=72)).strftime("%Y-%m-%dT%H:%M:%S")

        hotspot_count = 0
        max_frp = None
        max_temp_k = None
        source_name = "NASA SNPP VIIRS (375m)"

        viirs_ic = (
            ee.ImageCollection("NASA/LANCE/SNPP_VIIRS/C2")
            .filterDate(start_str, end_str)
            .filterBounds(region)
        )
        viirs_size = int(viirs_ic.size().getInfo() or 0)
        if viirs_size > 0:
            viirs_img = viirs_ic.select(["Bright_TI4", "MaxFRP"]).max()
            stats = viirs_img.reduceRegion(
                reducer=ee.Reducer.count().combine(ee.Reducer.max(), sharedInputs=True),
                geometry=region,
                scale=375,
                maxPixels=1_000_000,
            ).getInfo() or {}
            hotspot_count = int(stats.get("Bright_TI4_count") or 0)
            if stats.get("MaxFRP_max") is not None:
                max_frp = round(float(stats["MaxFRP_max"]), 1)
            if stats.get("Bright_TI4_max") is not None:
                max_temp_k = round(float(stats["Bright_TI4_max"]), 1)
        else:
            source_name = "NASA FIRMS MODIS (1 km)"
            firms_ic = (
                ee.ImageCollection("FIRMS")
                .filterDate(start_str, end_str)
                .filterBounds(region)
            )
            if int(firms_ic.size().getInfo() or 0) > 0:
                firms_img = firms_ic.select(["T21", "confidence"]).max()
                stats = firms_img.reduceRegion(
                    reducer=ee.Reducer.count().combine(ee.Reducer.max(), sharedInputs=True),
                    geometry=region,
                    scale=1000,
                    maxPixels=1_000_000,
                ).getInfo() or {}
                hotspot_count = int(stats.get("T21_count") or 0)
                if stats.get("T21_max") is not None:
                    max_temp_k = round(float(stats["T21_max"]), 1)

        if hotspot_count == 0:
            status = "Temiz (0 Nokta)"
            summary = "50 km çevrede son 72 saatte uydu tarafından aktif yangın / ısı anomalisi algılanmadı."
        elif hotspot_count <= 2:
            status = f"{hotspot_count} Isı Noktası"
            summary = "50 km çevrede sınırlı sayıda termal anomali tespit edildi (anız/bölgesel ısı kaynağı olabilir)."
        else:
            status = f"Aktif Anomali ({hotspot_count})"
            summary = "50 km yarıçapında birden fazla aktif termal nokta algılandı; yerel duman ve orman yangını riskine dikkat."

        return {
            "ok": True,
            "hotspot_count": hotspot_count,
            "max_frp_mw": max_frp,
            "max_brightness_k": max_temp_k,
            "radius_km": 50,
            "status": status,
            "summary": summary,
            "source": source_name,
        }

    def _query_climate(self, lat: float, lon: float, month: int) -> Dict[str, Any]:
        import ee

        point = ee.Geometry.Point([lon, lat])
        era5_mean = (
            ee.ImageCollection("ECMWF/ERA5_LAND/MONTHLY_AGGR")
            .filterDate("2015-01-01", "2026-01-01")
            .filter(ee.Filter.calendarRange(month, month, "month"))
            .select(["temperature_2m", "total_precipitation_sum"])
            .mean()
        )
        vals = era5_mean.reduceRegion(ee.Reducer.first(), point, 10000).getInfo() or {}
        t_kelvin = vals.get("temperature_2m")
        p_meters = vals.get("total_precipitation_sum")

        if t_kelvin is None:
            return {"ok": False, "error": "ERA5-Land iklim verisi bulunamadı"}

        normal_temp_c = round(float(t_kelvin) - 273.15, 1)
        normal_precip_mm = round(float(p_meters) * 1000.0, 1) if p_meters is not None else None

        return {
            "ok": True,
            "month": month,
            "normal_temp_c": normal_temp_c,
            "normal_precip_mm": normal_precip_mm,
            "period": "2015–2025",
            "source": "ECMWF ERA5-Land",
        }
