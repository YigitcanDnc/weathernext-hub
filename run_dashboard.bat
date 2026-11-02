@echo off
title WeatherNext Operasyonel Karar Destek Merkezi
cd /d "%~dp0"
echo ============================================================
echo   Google DeepMind WeatherNext Karar Destek Merkezi
echo   - Beton Dokumu & Santiye Guvenlik Yonetimi
echo   - Ulasim, Yol & Lojistik Risk Degerlendirmesi
echo   - Kisisel Gunluk Asistan & Yasam
echo ============================================================
echo.
echo Sunucu baslatiliyor...
echo Tarayicinizda su adresi acin: http://localhost:8000
echo.
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
