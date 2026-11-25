"""
Google DeepMind WeatherNext Live Access Verifier
Tests Earth Engine & BigQuery access for your approved Google Account and pulls
a live sample forecast for Istanbul (41.0082, 28.9784).
"""
import os
import sys
import json
from connectors.weathernext_engine import WeatherNextClient


def main():
    project_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GOOGLE_CLOUD_PROJECT")
    print("=" * 64)
    print("  Google DeepMind WeatherNext Canlı Bağlantı Testi")
    print("=" * 64)
    if project_id:
        print(f"GCP Project ID: {project_id}")

    client = WeatherNextClient(project_id=project_id)
    print("\n[1/2] Earth Engine WeatherNext koleksiyonları kontrol ediliyor...")
    info = client.discover_collection()
    if not info:
        print(f"HATA: Earth Engine erişimi kurulamadı -> {client.last_error}")
        print("\nÇözüm:")
        print("  1. `earthengine authenticate` çalıştırın (onaylanan Google hesabınızla giriş yapın)")
        print("  2. GCP Project ID'nizi verin: `python verify_weathernext.py <PROJE_ID>`")
        sys.exit(1)

    print("BAŞARILI! Aktif WeatherNext Koleksiyonu bulundu:")
    print(json.dumps(info, indent=2, ensure_ascii=False))

    print("\n[2/2] İstanbul (41.0082, 28.9784) için canlı WeatherNext tahmini çekiliyor...")
    fc = client.get_point_forecast(41.0082, 28.9784, hours=48)
    if not fc:
        print(f"HATA: Tahmin verisi çekilemedi -> {client.last_error}")
        sys.exit(1)

    print(f"Model: {fc['model']} | Toplam adım: {fc['steps_count']} | Ensemble (P10-P90): {fc['has_percentiles']}")
    for step in fc["steps"][:6]:
        print(
            f"  {step['time_utc'][:16]}Z | "
            f"Sıcaklık: {step['temp_mean']}°C (P10:{step['temp_p10']}° / P90:{step['temp_p90']}°) | "
            f"Yağış: {step['precip_mm_mean']} mm (P90:{step['precip_mm_p90']} mm) | "
            f"Rüzgar: {step['wind_kmh_mean']} km/s"
        )


if __name__ == "__main__":
    main()
