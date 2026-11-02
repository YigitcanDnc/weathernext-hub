import math
from typing import Dict, List, Any

def calculate_evaporation_rate(air_temp_c: float, rel_humidity_pct: float, wind_speed_kmh: float, concrete_temp_c: float = None) -> float:
    """
    Calculates the rate of evaporation from fresh concrete surface based on ACI 305R Metric Formula.
    E = [ (Tc + 18)^2.5 - (r * (Ta + 18)^2.5) ] * (V + 4) * 10^-6 * 5 (kg/m^2/h)
    """
    if concrete_temp_c is None:
        # Default estimation: concrete is usually 2-3°C warmer than air in mild temps, capped realistically
        concrete_temp_c = max(air_temp_c, 20.0)

    r = max(0.01, min(1.0, rel_humidity_pct / 100.0))
    tc_term = max(0.0, concrete_temp_c + 18.0) ** 2.5
    ta_term = max(0.0, air_temp_c + 18.0) ** 2.5
    v = max(0.0, wind_speed_kmh)

    # ACI metric formulation
    e = ((tc_term - (r * ta_term)) * (v + 4.0)) * 5.0e-6
    return max(0.0, round(e, 3))

def evaluate_concrete_hour(hour_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates concrete pouring suitability for a specific hour according to TS EN 206 / ACI 305R / ACI 306R.
    """
    temp = hour_data.get("temp", 15.0)
    humidity = hour_data.get("humidity", 50.0)
    wind_kmh = hour_data.get("wind_kmh", 10.0)
    wind_gust_kmh = hour_data.get("wind_gust_kmh", wind_kmh * 1.3)
    precip_mm = hour_data.get("precip_mm", 0.0)
    precip_prob = hour_data.get("precip_prob", 0)

    # 1. Evaporation Rate (Plastik Rötre Çatlağı Riski)
    evap_rate = calculate_evaporation_rate(temp, humidity, wind_kmh)

    risks = []
    recommendations = []
    status = "EXCELLENT" # EXCELLENT, ACCEPTABLE, CAUTION, PROHIBITED
    score = 100 # 0-100 index

    # Yağış Değerlendirmesi
    if precip_mm > 1.5 or precip_prob >= 70:
        status = "PROHIBITED"
        score -= 70
        risks.append("Şiddetli Yağış Riski (Taze beton yüzeyinde şerbet akması ve su/çimento oranı bozulması)")
        recommendations.append("Dökümü erteleyin veya su geçirmez koruyucu branda/çadır hazırlayın.")
    elif precip_mm > 0.2 or precip_prob >= 40:
        if status != "PROHIBITED":
            status = "CAUTION"
        score -= 35
        risks.append("Olası Çisenti/Yağmur (Yüzey kalitesini etkileyebilir)")
        recommendations.append("Döküm yüzeyini örtmek için hazır naylon/branda bulundurun.")

    # Don ve Soğuk Hava (TS EN 206 / ACI 306R)
    if temp < 0:
        status = "PROHIBITED"
        score -= 80
        risks.append(f"Don Tehlikesi ({temp:.1f}°C): Taze beton donarsa mukavemet %50'ye varan oranda düşer.")
        recommendations.append("Döküm yapılmamalıdır. Mutlaka dökülecekse sıcak karışım, antifriz/hızlandırıcı katkı ve ısıtmalı kür gerekir.")
    elif temp < 5:
        if status != "PROHIBITED":
            status = "CAUTION"
        score -= 40
        risks.append(f"Düşük Sıcaklık ({temp:.1f}°C): Çimento hidratasyonu çok yavaşlar, priz süresi 2-3 katına çıkar.")
        recommendations.append("Priz hızlandırıcı katkı kullanın, kalıpları ve döküm yüzeyini termal battaniyelerle izole edin.")

    # Aşırı Sıcaklık (ACI 305R)
    if temp >= 35:
        if status != "PROHIBITED":
            status = "CAUTION"
        score -= 45
        risks.append(f"Aşırı Sıcak ({temp:.1f}°C): Hızlı priz alma, işlenebilirlik kaybı ve soğuk derz riski.")
        recommendations.append("Gündüz dökümünden kaçının. Gece veya sabah erken saatleri tercih edin, geciktirici katkı uygulayın.")
    elif temp >= 30:
        score -= 20
        risks.append(f"Yüksek Sıcaklık ({temp:.1f}°C): Su kaybı hızlanır.")
        recommendations.append("Transmikserde beton bekleme süresini <45 dakikaya indirin.")

    # Buharlaşma & Plastik Rötre Çatlağı
    if evap_rate >= 1.0:
        if status != "PROHIBITED":
            status = "CAUTION"
        score -= 35
        risks.append(f"Kritik Buharlaşma Hızı ({evap_rate:.2f} kg/m²/saat): Şiddetli plastik rötre çatlağı riski!")
        recommendations.append("Dökümden hemen sonra buharlaşma önleyici kür membranı uygulayın, rüzgar perdesi kurun veya sisleme yapın.")
    elif evap_rate >= 0.5:
        score -= 15
        risks.append(f"Yüksek Buharlaşma ({evap_rate:.2f} kg/m²/saat): Yüzey kuruması hızlı.")
        recommendations.append("Beton yüzeyini perdah sonrası hemen ıslak çul veya membran ile örtün.")

    # Rüzgar ve Vinç / Pompa Güvenliği
    if wind_gust_kmh >= 45 or wind_kmh >= 38:
        if status != "PROHIBITED":
            status = "CAUTION"
        score -= 30
        risks.append(f"Şiddetli Rüzgar/Hamle ({wind_gust_kmh:.0f} km/s): Kule vinç ve beton pompası bom operasyon limiti!")
        recommendations.append("Vinç ve pompa bomu çalışma limitlerini kontrol edin; İSG kuralları gereği yüksekte çalışmayı durdurmayı değerlendirin.")

    score = max(0, min(100, score))

    if score >= 85 and status != "PROHIBITED" and status != "CAUTION":
        status = "EXCELLENT"
        badge_tr = "İdeal Döküm Şartları"
        color = "green"
    elif score >= 60 and status != "PROHIBITED":
        status = "ACCEPTABLE"
        badge_tr = "Uygun Şartlar"
        color = "blue"
    elif status == "CAUTION" or (score >= 35 and status != "PROHIBITED"):
        status = "CAUTION"
        badge_tr = "Önlem Alınarak Dökülebilir"
        color = "amber"
    else:
        status = "PROHIBITED"
        badge_tr = "Döküm Yapılamaz / Riskli"
        color = "red"

    return {
        "status": status,
        "badge_tr": badge_tr,
        "color": color,
        "score": score,
        "evaporation_rate": evap_rate,
        "risks": risks,
        "recommendations": recommendations,
    }

def analyze_concrete_forecast(hourly_forecast: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes an extended forecast (e.g. 24-72 hours) and finds optimal concrete pouring windows.
    """
    evaluated_hours = []
    optimal_windows = []
    current_window = None

    for i, h in enumerate(hourly_forecast):
        res = evaluate_concrete_hour(h)
        item = {
            "time": h.get("time"),
            "temp": h.get("temp"),
            "humidity": h.get("humidity"),
            "wind_kmh": h.get("wind_kmh"),
            "precip_prob": h.get("precip_prob"),
            "precip_mm": h.get("precip_mm"),
            **res
        }
        evaluated_hours.append(item)

        # Detect continuous suitable windows (duration >= 3 hours)
        is_suitable = res["status"] in ["EXCELLENT", "ACCEPTABLE"]
        if is_suitable:
            if current_window is None:
                current_window = {
                    "start_time": h.get("time"),
                    "end_time": h.get("time"),
                    "hours_count": 1,
                    "avg_score": res["score"],
                    "min_temp": h.get("temp"),
                    "max_temp": h.get("temp")
                }
            else:
                current_window["end_time"] = h.get("time")
                current_window["hours_count"] += 1
                current_window["avg_score"] = (current_window["avg_score"] + res["score"]) / 2
                current_window["min_temp"] = min(current_window["min_temp"], h.get("temp"))
                current_window["max_temp"] = max(current_window["max_temp"], h.get("temp"))
        else:
            if current_window and current_window["hours_count"] >= 3:
                optimal_windows.append(current_window)
            current_window = None

    if current_window and current_window["hours_count"] >= 3:
        optimal_windows.append(current_window)

    # Next 24 hours overall assessment
    first_24 = evaluated_hours[:24] if len(evaluated_hours) >= 24 else evaluated_hours
    avg_24_score = sum(x["score"] for x in first_24) / max(1, len(first_24))
    has_freeze_next_48h = any(x["temp"] < 0 for x in evaluated_hours[:48])
    has_rain_next_24h = any(x["precip_mm"] > 1.0 or x["precip_prob"] > 60 for x in first_24)

    return {
        "summary": {
            "overall_score_24h": round(avg_24_score, 1),
            "freeze_risk_48h": has_freeze_next_48h,
            "rain_risk_24h": has_rain_next_24h,
            "total_optimal_windows": len(optimal_windows)
        },
        "optimal_windows": optimal_windows,
        "hourly_evaluation": evaluated_hours
    }
