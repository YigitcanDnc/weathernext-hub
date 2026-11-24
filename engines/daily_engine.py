from typing import Dict, List, Any

WMO_DESCRIPTIONS_TR = {
    0: "Açık ve Güneşli",
    1: "Çoğunlukla Açık",
    2: "Parçalı Bulutlu",
    3: "Çok Bulutlu / Kapalı",
    45: "Sisli",
    48: "Kırağılı Sis",
    51: "Hafif Çisenti",
    53: "Orta Şiddetli Çisenti",
    55: "Yoğun Çisenti",
    61: "Hafif Yağmurlu",
    63: "Orta Şiddetli Yağmur",
    65: "Kuvvetli Yağmur",
    71: "Hafif Kar Yağışlı",
    73: "Orta Şiddetli Kar",
    75: "Yoğun Kar Yağışlı",
    80: "Hafif Sağanak Yağış",
    81: "Sağanak Yağışlı",
    82: "Şiddetli Sağanak",
    95: "Gök Gürültülü Fırtına",
    96: "Dolu İhtimalli Fırtına",
    99: "Şiddetli Fırtına ve Dolu"
}


def get_wmo_text(code: int) -> str:
    return WMO_DESCRIPTIONS_TR.get(code, "Değişken Bulutlu")


def generate_daily_brief(current_data: Dict[str, Any], hourly_forecast: List[Dict[str, Any]], daily_forecast: List[Dict[str, Any]]) -> Dict[str, Any]:
    temp = current_data.get("temp", 18.0)
    feels_like = current_data.get("feels_like", temp)
    wind_kmh = current_data.get("wind_kmh", 12)
    next_24 = hourly_forecast[:24]

    precip_prob_max = max([h.get("precip_prob", 0) for h in next_24], default=0)
    total_precip_24h = sum([h.get("precip_mm", 0) for h in next_24])
    min_temp_today = min([h.get("temp", temp) for h in next_24], default=temp)
    max_temp_today = max([h.get("temp", temp) for h in next_24], default=temp)

    # Rain hours in next 24h
    rain_hours = [
        {
            "time": h["time"],
            "prob": h.get("precip_prob", 0),
            "mm": h.get("precip_mm", 0.0),
            "snow_cm": h.get("snow_cm", 0.0)
        }
        for h in next_24
        if (h.get("precip_prob", 0) >= 25 or h.get("precip_mm", 0.0) >= 0.1)
    ]

    # Clothing recommendation
    if feels_like < 2:
        layer_level = "Kalın Kışlık"
        clothing_advice = "Kalın kaban veya mont, atkı, bere ve eldiven ile çıkın."
    elif feels_like < 10:
        layer_level = "Kışlık / Mont"
        clothing_advice = "Sıcak tutan mont, kazak ve rüzgar kesici dış katman ideal."
    elif feels_like < 17:
        layer_level = "Katmanlı Giyim"
        clothing_advice = "Hafif mont, trençkot veya hırka. Gün içi sıcaklık farkına karşı katmanlı giyinin."
    elif feels_like < 24:
        layer_level = "Mevsimlik / Rahat"
        clothing_advice = "Gömlek veya tişört yeterli; akşam serinliği için ince bir ceket bulundurun."
    else:
        layer_level = "Yazlık / İnce"
        clothing_advice = "Nefes alan pamuklu/keten kıyafetler ve güneş gözlüğü tercih edin."

    # Umbrella advice
    umbrella_needed = total_precip_24h >= 0.5 or precip_prob_max >= 45
    if umbrella_needed:
        umbrella_text = f"Yanınıza şemsiye alın. Gün içinde yağış ihtimali %{precip_prob_max} seviyesine çıkıyor."
    elif precip_prob_max >= 25:
        umbrella_text = "Kısa süreli hafif çisenti görülebilir, çantada küçük bir şemsiye iyi olabilir."
    else:
        umbrella_text = "Önümüzdeki 24 saat boyunca yağış beklenmiyor, şemsiyeye gerek yok."

    return {
        "condition_text": get_wmo_text(current_data.get("weather_code", 0)),
        "current": {
            "temp": temp,
            "feels_like": feels_like,
            "min_temp": min_temp_today,
            "max_temp": max_temp_today,
            "wind_kmh": wind_kmh
        },
        "rain_hours": rain_hours,
        "clothing": {
            "layer_level": layer_level,
            "advice": clothing_advice
        },
        "umbrella": {
            "needed": umbrella_needed,
            "text": umbrella_text,
            "precip_prob_max": precip_prob_max
        }
    }
