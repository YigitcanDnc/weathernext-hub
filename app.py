import os
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from connectors.weather_service import WeatherService
from engines.daily_engine import generate_daily_brief, get_wmo_text

app = FastAPI(title="Hava & Yaşam — 81 İl & 972 İlçe Günlük Hava Durumu", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

weather_svc = WeatherService()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/manifest.json")
def get_manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"), media_type="application/manifest+json")

@app.get("/sw.js")
def get_sw():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")

@app.get("/icon.svg")
def get_icon():
    return FileResponse(os.path.join(STATIC_DIR, "icon.svg"), media_type="image/svg+xml")

@app.get("/turkey_locations.json")
def get_locations_json():
    return FileResponse(os.path.join(STATIC_DIR, "turkey_locations.json"))

@app.get("/api/locations")
def get_all_locations():
    return weather_svc.get_provinces()

@app.get("/api/forecast")
def get_daily_forecast(
    province: Optional[str] = "İstanbul",
    district: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    if lat is None or lon is None or not isinstance(lat, (int, float)):
        resolved = weather_svc.find_location(province, district)
        lat = resolved["lat"]
        lon = resolved["lon"]
        loc_name = resolved["name"]
    else:
        loc_name = f"{province or 'Konum'} ({lat:.3f}, {lon:.3f})"

    try:
        raw_forecast = weather_svc.get_forecast(lat, lon, loc_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hava durumu verisi alınamadı: {str(e)}")

    daily_brief = generate_daily_brief(raw_forecast["current"], raw_forecast["hourly"], raw_forecast["daily"])
    return {
        "location": raw_forecast["location"],
        "current": raw_forecast["current"],
        "brief": daily_brief,
        "hourly": raw_forecast["hourly"],
        "daily": raw_forecast["daily"]
    }

@app.get("/api/province-districts")
def get_province_districts(province: str = "İstanbul"):
    try:
        batch = weather_svc.get_province_districts_batch(province)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İlçe verileri alınamadı: {str(e)}")

    for item in batch:
        item["condition_text"] = get_wmo_text(item.get("weather_code", 0))
    return {"province": province, "districts": batch}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
