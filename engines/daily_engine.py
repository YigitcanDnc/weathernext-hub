from typing import Dict, List, Any

def generate_daily_brief(current_data: Dict[str, Any], hourly_forecast: List[Dict[str, Any]], daily_forecast: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates personal, human-friendly daily briefing and lifestyle advice.
    """
    temp = current_data.get("temp", 18.0)
    feels_like = current_data.get("feels_like", temp)
    humidity = current_data.get("humidity", 50)
    wind_kmh = current_data.get("wind_kmh", 12)
    precip_prob_max = max([h.get("precip_prob", 0) for h in hourly_forecast[:18]], default=0)
    total_precip_24h = sum([h.get("precip_mm", 0) for h in hourly_forecast[:24]])
    min_temp_today = min([h.get("temp", temp) for h in hourly_forecast[:24]], default=temp)
    max_temp_today = max([h.get("temp", temp) for h in hourly_forecast[:24]], default=temp)

    # 1. Kıyafet Önerisi
    clothing_advice = []
    layer_level = "Orta"

    if feels_like < 0:
        layer_level = "Çok Kalın / Kışlık"
        clothing_advice.append("Ağır kışlık kaban/mont, atkı, eldiven ve termal içlik şart.")
    elif feels_like < 8:
        layer_level = "Kalın"
        clothing_advice.append("Sıcak tutan kalın mont, kazak ve rüzgar kesici dış katman önerilir.")
    elif feels_like < 15:
        layer_level = "Katmanlı (Soğan Zırhı)"
        clothing_advice.append("Hafif mont, trençkot veya hırka. Gün içi sıcaklık farkına karşı katmanlı giyinin.")
    elif feels_like < 23:
        layer_level = "Hafif / Mevsimlik"
        clothing_advice.append("Rahat pamuklu gömlek, tişört ve hafif bir ceket/sweatshirt yeterlidir.")
    else:
        layer_level = "İnce / Yazlık"
        clothing_advice.append("Nefes alabilen ince, keten/pamuklu kıyafetler ve güneş gözlüğü önerilir.")

    # 2. Şemsiye & Yağmurluk Tavsiyesi
    umbrella_needed = False
    umbrella_text = "Şemsiyeye gerek yok, hava genel olarak kuru."
    if total_precip_24h > 1.0 or precip_prob_max >= 50:
        umbrella_needed = True
        umbrella_text = "Mutlaka yanınıza şemsiye veya su geçirmez yağmurluk alın (Yağış ihtimali yüksek)."
    elif precip_prob_max >= 25:
        umbrella_text = "Çantanızda küçük bir şemsiye bulundurmakta fayda var (Kısa süreli çisenti ihtimali)."

    # 3. Günün 4 Zaman Dilimi Özeti
    # Dilimler: Sabah (06-11), Öğle (12-16), Akşam (17-21), Gece (22-05)
    periods = [
        {"name": "Sabah (08:00 - 12:00)", "temp_est": round(min_temp_today + (max_temp_today - min_temp_today) * 0.4, 1), "desc": "Serin ve canlı"},
        {"name": "Öğle (12:00 - 17:00)", "temp_est": round(max_temp_today, 1), "desc": "Günün en sıcak saatleri"},
        {"name": "Akşam (17:00 - 21:00)", "temp_est": round(min_temp_today + (max_temp_today - min_temp_today) * 0.5, 1), "desc": "Sıcaklık düşüşe geçiyor"},
        {"name": "Gece (21:00 - 05:00)", "temp_est": round(min_temp_today, 1), "desc": "Soğuk ve durağan"}
    ]

    # 4. Açık Hava Konforu & Aktivite Puanı (0-100)
    comfort_score = 100
    if feels_like < 10 or feels_like > 28:
        comfort_score -= abs(feels_like - 20) * 2.5
    if wind_kmh > 25:
        comfort_score -= (wind_kmh - 25) * 1.5
    if precip_prob_max > 40:
        comfort_score -= precip_prob_max * 0.4

    comfort_score = max(10, min(100, int(comfort_score)))

    if comfort_score >= 80:
        outdoor_activity = "Dış mekan sporları, yürüyüş ve açık hava programları için mükemmel bir gün."
    elif comfort_score >= 55:
        outdoor_activity = "Açık hava aktiviteleri uygun, rüzgar ve hafif serinliğe dikkat ederek planlanabilir."
    else:
        outdoor_activity = "Hava şartları zorlayıcı; kapalı mekan aktiviteleri veya korunaklı alanlar tercih edilmeli."

    return {
        "current": {
            "temp": temp,
            "feels_like": feels_like,
            "min_temp": min_temp_today,
            "max_temp": max_temp_today,
            "humidity": humidity,
            "wind_kmh": wind_kmh
        },
        "clothing": {
            "layer_level": layer_level,
            "advice": " ".join(clothing_advice)
        },
        "umbrella": {
            "needed": umbrella_needed,
            "text": umbrella_text,
            "precip_prob_max": precip_prob_max
        },
        "comfort": {
            "score": comfort_score,
            "outdoor_activity_advice": outdoor_activity
        },
        "periods": periods
    }
