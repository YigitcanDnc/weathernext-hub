import os
import uvicorn
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from connectors.weather_service import WeatherService
from connectors.weathernext_bq import WeatherNextBigQueryConnector
from connectors.weathernext_gcs import WeatherNextGCSConnector
from engines.concrete_engine import analyze_concrete_forecast, evaluate_concrete_hour
from engines.transport_engine import analyze_transport_forecast, evaluate_transport_hour
from engines.daily_engine import generate_daily_brief

app = FastAPI(title="WeatherNext Operational Decision Hub - 81 İl & 972 İlçe", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

weather_svc = WeatherService()
bq_connector = WeatherNextBigQueryConnector()
gcs_connector = WeatherNextGCSConnector()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "WeatherNext Decision Hub API Running"}

@app.get("/turkey_locations.json")
def get_locations_json():
    loc_path = os.path.join(STATIC_DIR, "turkey_locations.json")
    if os.path.exists(loc_path):
        return FileResponse(loc_path)
    return weather_svc.get_provinces()

@app.get("/api/locations")
def get_all_locations():
    return weather_svc.get_provinces()

@app.get("/api/forecast")
def get_comprehensive_forecast(
    province: Optional[str] = "İstanbul",
    district: Optional[str] = None,
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    target_prov = province or city or "İstanbul"
    if lat is None or lon is None or not isinstance(lat, (int, float)):
        resolved = weather_svc.find_location(target_prov, district)
        lat = resolved["lat"]
        lon = resolved["lon"]
        loc_name = resolved["name"]
        prov_name = resolved.get("province", target_prov)
        dist_name = resolved.get("district", "İl Merkezi")
    else:
        loc_name = f"Koordinat ({lat:.4f}, {lon:.4f})"
        prov_name = target_prov
        dist_name = district or "Özel Konum"

    try:
        raw_forecast = weather_svc.get_forecast(lat, lon, loc_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hava durumu verisi alınamadı: {str(e)}")

    raw_forecast["location"]["province"] = prov_name
    raw_forecast["location"]["district"] = dist_name

    concrete_analysis = analyze_concrete_forecast(raw_forecast["hourly"])
    transport_analysis = analyze_transport_forecast(raw_forecast["hourly"])
    daily_brief = generate_daily_brief(raw_forecast["current"], raw_forecast["hourly"], raw_forecast["daily"])

    return {
        "location": raw_forecast["location"],
        "current": raw_forecast["current"],
        "concrete": concrete_analysis,
        "transport": transport_analysis,
        "daily": daily_brief,
        "hourly_raw": raw_forecast["hourly"][:36],
        "daily_raw": raw_forecast["daily"]
    }

@app.get("/api/province-districts")
def get_province_districts_overview(province: str = "İstanbul"):
    """
    Returns real-time weather + concrete pouring suitability + transport safety
    for ALL districts in the selected province in one batch.
    """
    try:
        batch_data = weather_svc.get_province_districts_batch(province)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İlçe verileri alınamadı: {str(e)}")

    enriched = []
    for d in batch_data:
        c_eval = evaluate_concrete_hour(d)
        t_eval = evaluate_transport_hour(d)
        enriched.append({
            **d,
            "concrete_score": c_eval["score"],
            "concrete_status": c_eval["status"],
            "concrete_badge": c_eval["badge_tr"],
            "evaporation_rate": c_eval["evaporation_rate"],
            "transport_score": t_eval["score"],
            "transport_level": t_eval["alert_level"],
            "transport_badge": t_eval["badge_tr"]
        })
    return {
        "province": province,
        "districts_count": len(enriched),
        "districts": enriched
    }

@app.get("/api/weathernext/integration")
def get_weathernext_integration(lat: float = 41.0082, lon: float = 28.9784):
    auth_status = bq_connector.is_authenticated()
    bq_sql = bq_connector.generate_site_forecast_sql(lat, lon)
    gcs_snippet = gcs_connector.get_python_snippet(lat, lon)

    return {
        "authenticated": auth_status,
        "email_status": "Access granted via WeatherNext approval email",
        "endpoints": {
            "bigquery_table": "weathernext-public.weathernext.operational_forecasts",
            "gcs_bucket": gcs_connector.bucket_uri,
            "earth_engine_asset": "projects/weathernext/assets/forecasts_latest"
        },
        "bigquery_sql_query": bq_sql,
        "gcs_zarr_code": gcs_snippet,
        "cli_command": "gcloud auth application-default login"
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
