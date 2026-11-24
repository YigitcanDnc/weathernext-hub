import os
import json
import httpx
from typing import Dict, List, Any, Optional

LOCATIONS_FILE = os.path.join(os.path.dirname(__file__), "turkey_locations.json")

def load_turkey_locations() -> List[Dict[str, Any]]:
    if os.path.exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

TURKEY_PROVINCES = load_turkey_locations()


class WeatherService:
    def __init__(self):
        self.client = httpx.Client(timeout=15.0)
        self.provinces = TURKEY_PROVINCES

    def get_provinces(self) -> List[Dict[str, Any]]:
        return self.provinces

    def find_location(self, province_query: Optional[str] = None, district_query: Optional[str] = None) -> Dict[str, Any]:
        if not province_query:
            province_query = "İstanbul"

        pq = province_query.strip().lower()
        selected_prov = None

        for p in self.provinces:
            if p["name"].lower() == pq or str(p["plate"]) == pq:
                selected_prov = p
                break

        if not selected_prov:
            for p in self.provinces:
                if pq in p["name"].lower():
                    selected_prov = p
                    break

        if not selected_prov:
            for p in self.provinces:
                for d in p.get("districts", []):
                    if d["name"].lower() == pq:
                        return {
                            "name": f"{p['name']} / {d['name']}",
                            "province": p["name"],
                            "district": d["name"],
                            "plate": p["plate"],
                            "lat": d["lat"],
                            "lon": d["lon"]
                        }

        if selected_prov:
            if district_query and district_query.strip().lower() not in ["merkez", "il merkezi", "all", ""]:
                dq = district_query.strip().lower()
                for d in selected_prov.get("districts", []):
                    if d["name"].lower() == dq or dq in d["name"].lower():
                        return {
                            "name": f"{selected_prov['name']} / {d['name']}",
                            "province": selected_prov["name"],
                            "district": d["name"],
                            "plate": selected_prov["plate"],
                            "lat": d["lat"],
                            "lon": d["lon"]
                        }
            return {
                "name": f"{selected_prov['name']} (İl Merkezi)",
                "province": selected_prov["name"],
                "district": "İl Merkezi",
                "plate": selected_prov["plate"],
                "lat": selected_prov["lat"],
                "lon": selected_prov["lon"]
            }

        return {
            "name": "İstanbul (İl Merkezi)",
            "province": "İstanbul",
            "district": "İl Merkezi",
            "plate": 34,
            "lat": 41.0082,
            "lon": 28.9784
        }

    def get_forecast(self, lat: float, lon: float, location_name: str = "Konum") -> Dict[str, Any]:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,rain,snowfall,wind_speed_10m,wind_gusts_10m,visibility,uv_index,weather_code,is_day",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,wind_speed_10m,wind_gusts_10m,pressure_msl,weather_code",
            "timezone": "auto",
            "forecast_days": 7
        }

        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        cur = data.get("current", {})
        current_parsed = {
            "time": cur.get("time"),
            "temp": cur.get("temperature_2m", 15.0),
            "feels_like": cur.get("apparent_temperature", 15.0),
            "humidity": cur.get("relative_humidity_2m", 50),
            "is_day": cur.get("is_day", 1),
            "wind_kmh": cur.get("wind_speed_10m", 0.0),
            "wind_gust_kmh": cur.get("wind_gusts_10m", 0.0),
            "precip_mm": cur.get("precipitation", 0.0),
            "pressure_hpa": cur.get("pressure_msl", 1013.0),
            "weather_code": cur.get("weather_code", 0)
        }

        hourly_raw = data.get("hourly", {})
        times = hourly_raw.get("time", [])
        hourly_parsed = []
        for i in range(min(48, len(times))):
            hourly_parsed.append({
                "time": times[i],
                "temp": hourly_raw.get("temperature_2m", [0])[i],
                "feels_like": hourly_raw.get("apparent_temperature", [0])[i],
                "humidity": hourly_raw.get("relative_humidity_2m", [50])[i],
                "precip_prob": hourly_raw.get("precipitation_probability", [0])[i] or 0,
                "precip_mm": hourly_raw.get("precipitation", [0])[i] or 0.0,
                "snow_cm": hourly_raw.get("snowfall", [0])[i] or 0.0,
                "wind_kmh": hourly_raw.get("wind_speed_10m", [0])[i] or 0.0,
                "wind_gust_kmh": hourly_raw.get("wind_gusts_10m", [0])[i] or 0.0,
                "uv_index": hourly_raw.get("uv_index", [0])[i] or 0.0,
                "weather_code": hourly_raw.get("weather_code", [0])[i] or 0,
                "is_day": hourly_raw.get("is_day", [1])[i]
            })

        daily_raw = data.get("daily", {})
        d_times = daily_raw.get("time", [])
        daily_parsed = []
        for i in range(len(d_times)):
            daily_parsed.append({
                "date": d_times[i],
                "weather_code": daily_raw.get("weather_code", [0])[i],
                "temp_max": daily_raw.get("temperature_2m_max", [0])[i],
                "temp_min": daily_raw.get("temperature_2m_min", [0])[i],
                "sunrise": daily_raw.get("sunrise", [""])[i],
                "sunset": daily_raw.get("sunset", [""])[i],
                "uv_max": daily_raw.get("uv_index_max", [0])[i],
                "precip_sum": daily_raw.get("precipitation_sum", [0])[i],
                "precip_prob_max": daily_raw.get("precipitation_probability_max", [0])[i],
                "wind_max": daily_raw.get("wind_speed_10m_max", [0])[i]
            })

        return {
            "location": {
                "name": location_name,
                "latitude": lat,
                "longitude": lon,
                "timezone": data.get("timezone", "Europe/Istanbul")
            },
            "current": current_parsed,
            "hourly": hourly_parsed,
            "daily": daily_parsed
        }

    def get_province_districts_batch(self, province_name: str) -> List[Dict[str, Any]]:
        pq = province_name.strip().lower()
        selected_prov = None
        for p in self.provinces:
            if p["name"].lower() == pq or str(p["plate"]) == pq:
                selected_prov = p
                break
        if not selected_prov:
            return []

        districts = selected_prov.get("districts", [])
        if not districts:
            return []

        lats = ",".join(str(d["lat"]) for d in districts)
        lons = ",".join(str(d["lon"]) for d in districts)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lats,
            "longitude": lons,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code,is_day",
            "timezone": "auto"
        }
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            payload = [payload]

        results = []
        for idx, d in enumerate(districts):
            item = payload[idx] if idx < len(payload) else {}
            cur = item.get("current", {})
            results.append({
                "district": d["name"],
                "province": selected_prov["name"],
                "lat": d["lat"],
                "lon": d["lon"],
                "temp": cur.get("temperature_2m", 15.0),
                "feels_like": cur.get("apparent_temperature", 15.0),
                "humidity": cur.get("relative_humidity_2m", 50),
                "wind_kmh": cur.get("wind_speed_10m", 0.0),
                "precip_mm": cur.get("precipitation", 0.0),
                "weather_code": cur.get("weather_code", 0),
                "is_day": cur.get("is_day", 1)
            })
        return results
