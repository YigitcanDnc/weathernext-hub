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
        """
        Resolves province and optional district from the 81-province / 972-district dataset.
        """
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
            # Check if province_query actually matches a district name directly
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
        """
        Fetches high-resolution meteorological forecast for lat/lon.
        """
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,precipitation,rain,wind_speed_10m,wind_gusts_10m,visibility,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,weather_code",
            "timezone": "auto",
            "forecast_days": 5
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
            "wind_kmh": cur.get("wind_speed_10m", 0.0),
            "wind_gust_kmh": cur.get("wind_gusts_10m", 0.0),
            "precip_mm": cur.get("precipitation", 0.0),
            "weather_code": cur.get("weather_code", 0)
        }

        hourly_raw = data.get("hourly", {})
        times = hourly_raw.get("time", [])
        temps = hourly_raw.get("temperature_2m", [])
        feels = hourly_raw.get("apparent_temperature", [])
        humids = hourly_raw.get("relative_humidity_2m", [])
        precip_probs = hourly_raw.get("precipitation_probability", [])
        precips = hourly_raw.get("precipitation", [])
        winds = hourly_raw.get("wind_speed_10m", [])
        gusts = hourly_raw.get("wind_gusts_10m", [])
        visibilities = hourly_raw.get("visibility", [])
        wcodes = hourly_raw.get("weather_code", [])

        hourly_parsed = []
        for i in range(min(72, len(times))):
            hourly_parsed.append({
                "time": times[i],
                "temp": temps[i] if i < len(temps) and temps[i] is not None else 0.0,
                "feels_like": feels[i] if i < len(feels) and feels[i] is not None else 0.0,
                "humidity": humids[i] if i < len(humids) and humids[i] is not None else 50,
                "precip_prob": precip_probs[i] if i < len(precip_probs) and precip_probs[i] is not None else 0,
                "precip_mm": precips[i] if i < len(precips) and precips[i] is not None else 0.0,
                "wind_kmh": winds[i] if i < len(winds) and winds[i] is not None else 0.0,
                "wind_gust_kmh": gusts[i] if i < len(gusts) and gusts[i] is not None else 0.0,
                "visibility_km": (visibilities[i] / 1000.0) if i < len(visibilities) and visibilities[i] else 10.0,
                "weather_code": wcodes[i] if i < len(wcodes) and wcodes[i] is not None else 0
            })

        daily_raw = data.get("daily", {})
        d_times = daily_raw.get("time", [])
        d_maxs = daily_raw.get("temperature_2m_max", [])
        d_mins = daily_raw.get("temperature_2m_min", [])
        d_precips = daily_raw.get("precipitation_sum", [])
        d_probs = daily_raw.get("precipitation_probability_max", [])

        daily_parsed = []
        for i in range(len(d_times)):
            daily_parsed.append({
                "date": d_times[i],
                "temp_max": d_maxs[i] if i < len(d_maxs) else 0,
                "temp_min": d_mins[i] if i < len(d_mins) else 0,
                "precip_sum": d_precips[i] if i < len(d_precips) else 0,
                "precip_prob_max": d_probs[i] if i < len(d_probs) else 0,
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
        """
        Fetches current weather for all districts of a given province in a single batch call.
        """
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
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,weather_code",
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
                "wind_gust_kmh": cur.get("wind_gusts_10m", 0.0),
                "precip_mm": cur.get("precipitation", 0.0),
                "weather_code": cur.get("weather_code", 0)
            })
        return results
