import os
from typing import Dict, Any, Optional

class WeatherNextBigQueryConnector:
    """
    Connects to Google DeepMind WeatherNext BigQuery dataset.
    Default dataset: `weathernext-public.weathernext` or custom GCP project datasets.
    """
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._client = None

    def is_authenticated(self) -> bool:
        # Check whether Google application default credentials exist
        try:
            from google.auth import default
            credentials, project = default()
            return True
        except Exception:
            return False

    def get_client(self):
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    def generate_site_forecast_sql(self, lat: float, lon: float, start_date: str = "CURRENT_DATE()") -> str:
        """
        Generates standard geospatial SQL query to extract WeatherNext forecasts
        for a point geometry (e.g. Construction Site or Highway Corridor).
        """
        return f"""
-- WeatherNext Point Forecast Query for Site: ({lat}, {lon})
WITH site_point AS (
  SELECT ST_GEOGPOINT({lon}, {lat}) as geom
)
SELECT 
  forecast_reference_time,
  valid_time,
  temperature_2m_celsius,
  relative_humidity_2m_pct,
  total_precipitation_6h_mm,
  wind_u_component_10m,
  wind_v_component_10m,
  -- Calculate horizontal wind speed from (u, v) vectors
  SQRT(POW(wind_u_component_10m, 2) + POW(wind_v_component_10m, 2)) * 3.6 AS wind_speed_kmh,
  surface_solar_radiation_downwards
FROM `weathernext-public.weathernext.operational_forecasts` AS w, site_point
WHERE ST_DWITHIN(w.geography, site_point.geom, 5000) -- within 5km model grid
  AND DATE(forecast_reference_time) >= {start_date}
ORDER BY valid_time ASC
LIMIT 120;
""".strip()

    def run_query(self, query: str):
        if not self.is_authenticated():
            raise PermissionError("GCP kimlik doğrulama bulunamadı. Lütfen `gcloud auth application-default login` çalıştırın.")
        client = self.get_client()
        query_job = client.query(query)
        results = query_job.result()
        return [dict(row) for row in results]
