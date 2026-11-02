from typing import Dict, List, Any

def evaluate_transport_hour(hour_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates highway, transit, and logistics risks for an hour.
    """
    temp = hour_data.get("temp", 15.0)
    humidity = hour_data.get("humidity", 50.0)
    wind_kmh = hour_data.get("wind_kmh", 10.0)
    wind_gust_kmh = hour_data.get("wind_gust_kmh", wind_kmh * 1.3)
    precip_mm = hour_data.get("precip_mm", 0.0)
    precip_prob = hour_data.get("precip_prob", 0)
    visibility_km = hour_data.get("visibility_km", 10.0)

    risks = []
    recommendations = []
    score = 100
    alert_level = "NORMAL" # NORMAL, MODERATE, HIGH, SEVERE

    # 1. Gizli Buzlanma ve Don Riski (Black Ice)
    if -3.0 <= temp <= 1.5 and (precip_mm > 0.1 or humidity >= 85):
        score -= 50
        alert_level = "HIGH"
        risks.append(f"Gizli Buzlanma Riski ({temp:.1f}°C): Viyadük, köprü ve rüzgar alan kavşaklarda zemin aniden buz tutabilir.")
        recommendations.append("Takip mesafesini 3 katına çıkarın, viyadük ve gölgede kalan virajlarda ani fren/manevradan kaçının.")
    elif temp < -3.0:
        score -= 40
        alert_level = "HIGH"
        risks.append(f"Don ve Kar/Buz Riski ({temp:.1f}°C): Karayolu sürtünme katsayısı kritik seviyede düşebilir.")
        recommendations.append("Kış lastiği / zincir donanımı kontrol edilmeli, ağır vasıtalar için rampa geçişleri planlanmalı.")

    # 2. Şiddetli Yan Rüzgar & Fırtına (Ağır Vasıta ve Köprü Güvenliği)
    if wind_gust_kmh >= 70:
        score -= 50
        alert_level = "SEVERE"
        risks.append(f"Kritik Fırtına/Yan Rüzgar ({wind_gust_kmh:.0f} km/s hamle): Yüksek kasalı kamyon, TIR ve boş dorselerde devrilme riski!")
        recommendations.append("Köprü geçişlerinde ve açık otoban viyadüklerinde hız düşürün; brandalı/hafif yük taşımalarını bekletin.")
    elif wind_gust_kmh >= 50 or wind_kmh >= 40:
        score -= 25
        if alert_level not in ["SEVERE", "HIGH"]:
            alert_level = "MODERATE"
        risks.append(f"Kuvvetli Rüzgar ({wind_gust_kmh:.0f} km/s hamle): Direksiyon hakimiyeti zorlaşabilir, yan rüzgar savrulması.")
        recommendations.append("İki elle direksiyon tutuşu ve şerit takip güvenliğine dikkat edin.")

    # 3. Şiddetli Yağış & Aquaplaning (Suda Kızaklama)
    if precip_mm >= 10.0:
        score -= 45
        alert_level = "HIGH"
        risks.append(f"Aşırı Sağanak Yağış ({precip_mm:.1f} mm/s): Su birikintileri ve Aquaplaning (kızaklama) tehlikesi!")
        recommendations.append("Hızı en az %30 azaltın, lastik diş derinliği zayıf araçları yola çıkarmayın.")
    elif precip_mm >= 3.0:
        score -= 20
        if alert_level == "NORMAL":
            alert_level = "MODERATE"
        risks.append(f"Kuvvetli Yağış ({precip_mm:.1f} mm/s): Fren mesafesi uzar, sprey etkisi görüşü bozar.")
        recommendations.append("Farları açık tutun ve silecek hızını artırın.")

    # 4. Sis ve Düşük Görüş Mesafesi
    if visibility_km < 1.0 or (humidity >= 94 and wind_kmh < 10 and temp < 14):
        score -= 35
        if alert_level not in ["SEVERE", "HIGH"]:
            alert_level = "HIGH"
        risks.append("Yoğun Sis ve Düşük Görüş Mesafesi: Erken fark etme mesafesi 100 metrenin altına inebilir.")
        recommendations.append("Sis farlarını yakın, uzun farları yakmayın (yansıma yapar), dörtlüleri gereksiz yakıp trafiği yanıltmayın.")
    elif visibility_km < 3.0 or (humidity >= 88 and wind_kmh < 12):
        score -= 15
        if alert_level == "NORMAL":
            alert_level = "MODERATE"
        risks.append("Pus ve Kısıtlı Görüş.")
        recommendations.append("Kısa huzmeli farları kullanın.")

    score = max(0, min(100, score))

    color_map = {
        "NORMAL": "green",
        "MODERATE": "amber",
        "HIGH": "orange",
        "SEVERE": "red"
    }

    badge_map = {
        "NORMAL": "Yol & Sürüş Şartları Güvenli",
        "MODERATE": "Dikkatli Sürüş Gereklidir",
        "HIGH": "Yüksek Risk / Zorlu Karayolu",
        "SEVERE": "Tehlikeli Şartlar / Seyahat Ertelenmeli"
    }

    return {
        "alert_level": alert_level,
        "badge_tr": badge_map[alert_level],
        "color": color_map[alert_level],
        "score": score,
        "risks": risks,
        "recommendations": recommendations,
        "wind_gust_kmh": wind_gust_kmh,
        "visibility_km": visibility_km
    }

def analyze_transport_forecast(hourly_forecast: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes transit and route safety over time.
    """
    evaluated_hours = []
    severe_periods = []

    for h in hourly_forecast:
        res = evaluate_transport_hour(h)
        item = {
            "time": h.get("time"),
            "temp": h.get("temp"),
            "wind_kmh": h.get("wind_kmh"),
            "precip_mm": h.get("precip_mm"),
            **res
        }
        evaluated_hours.append(item)

        if res["alert_level"] in ["HIGH", "SEVERE"]:
            severe_periods.append({
                "time": h.get("time"),
                "level": res["alert_level"],
                "reason": res["risks"][0] if res["risks"] else "Kritik hava koşulu"
            })

    first_24 = evaluated_hours[:24] if len(evaluated_hours) >= 24 else evaluated_hours
    avg_score = sum(x["score"] for x in first_24) / max(1, len(first_24))

    return {
        "summary": {
            "safety_score_24h": round(avg_score, 1),
            "severe_hours_count": len([x for x in first_24 if x["alert_level"] in ["HIGH", "SEVERE"]]),
            "black_ice_risk": any("Buzlanma" in " ".join(x["risks"]) for x in first_24),
            "storm_crosswind_risk": any("Yan Rüzgar" in " ".join(x["risks"]) for x in first_24),
            "fog_risk": any("Sis" in " ".join(x["risks"]) for x in first_24)
        },
        "critical_periods": severe_periods[:6],
        "hourly_evaluation": evaluated_hours
    }
