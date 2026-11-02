import os
from typing import Dict, Any, Optional

class WeatherNextGCSConnector:
    """
    Connects to Google Cloud Storage WeatherNext Zarr archive.
    Default experimental bucket: gs://weathernext/weathernext_2_0_0/zarr
    """
    def __init__(self, bucket_uri: str = "gs://weathernext/weathernext_2_0_0/zarr"):
        self.bucket_uri = bucket_uri

    def get_python_snippet(self, lat: float, lon: float) -> str:
        """
        Returns ready-to-run Python script snippet to stream WeatherNext Zarr grid directly.
        """
        return f"""
import xarray as xr
import fsspec

# Google DeepMind WeatherNext Cloud Storage Zarr Stream
# Note: Ensure you are logged in with the approved Google Account
bucket_path = "{self.bucket_uri}"

# Open dataset lazily over GCS
mapper = fsspec.get_mapper(bucket_path, requester_pays=True)
ds = xr.open_zarr(mapper, consolidated=True)

# Select nearest grid point to target location: ({lat}, {lon})
site_ds = ds.sel(latitude={lat}, longitude={lon}, method="nearest")

print("Tahmin Değişkenleri:", list(site_ds.data_vars))
# Example: 2m Temperature and Total Precipitation
temp_2m = site_ds['temperature_2m'] - 273.15  # Kelvin to Celsius
print(temp_2m.values)
""".strip()
