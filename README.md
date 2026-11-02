# Google DeepMind WeatherNext — Operasyonel Karar Destek Merkezi (81 İl & 972 İlçe)

Google DeepMind'ın yeni nesil yapay zeka tabanlı küresel hava tahmin modeli **WeatherNext** veri setlerine dayalı, Türkiye'nin **81 ili ve 972 ilçesinin tamamını** kapsayan operasyonel ve kişisel karar destek sistemi.

🌐 **Canlı Uzaktan Erişim (Web / Mobil / Saha):**
👉 **[https://yigitcandnc.github.io/weathernext-hub/](https://yigitcandnc.github.io/weathernext-hub/)**

---

## 🎯 Ana Fonksiyonel Modüller

### 1. 🏗️ Beton Dökümü & Şantiye Güvenliği (`engines/concrete_engine.py`)
* **TS EN 206, ACI 305R (Sıcak Hava) ve ACI 306R (Soğuk Hava)** standartlarına göre modellenmiştir.
* **Plastik Rötre Çatlağı:** ACI metrik buharlaşma hızı formülü ile saatlik hesaplanır.
* **Don Riski & Priz Süresi:** Döküm sonrası 48 saatlik don tehlikesi taranır.
* **Optimal Döküm Pencereleri:** Yağışsız ve uygun buharlaşmalı kesintisiz 3+ saatlik döküm aralıklarını otomatik tespit eder.
* **Kule Vinç & Pompa Limiti:** Rüzgar hamle hızı >45 km/s olduğunda İSG güvenlik uyarısı verir.

### 2. 🏘️ 81 İl & 972 İlçe Karşılaştırma Matrisi
* Plaka kodlu 81 il ve 972 ilçenin tamamı için koordinat bazlı analiz.
* Seçilen ilin tüm ilçeleri için tek seferde (Batch API) anlık sıcaklık, nem, rüzgar, yağış, **Beton Döküm Puanı** ve **Ulaşım Güvenlik Durumu** karşılaştırması.

### 3. 🚚 Ulaşım, Yol & Lojistik Güvenliği (`engines/transport_engine.py`)
* **Gizli Buzlanma (Black Ice):** Köprü ve viyadükler için don ve nem eşleşmesi.
* **Şiddetli Yan Rüzgar:** Yüksek kasalı kamyon, TIR ve boş dorseler için devrilme tehlikesi analizi.
* **Aquaplaning & Görüş:** Şiddetli sağanak birikintileri ve sis seviyeleri.

### 4. ☕ Kişisel Günlük Asistan (`engines/daily_engine.py`)
* **Termal Konfor & Katmanlı Giyim:** Günün sıcaklık salınımına göre akıllı kıyafet önerisi.
* **Şemsiye / Yağmurluk:** Gün içi yağış ihtimallerine göre net yönlendirme.
* **4 Zaman Dilimi Özeti:** Sabah, Öğle, Akşam ve Gece hava seyri.

### 5. 🛰️ WeatherNext Cloud Bağlantısı (`connectors/`)
* Seçilen ilçenin koordinatına özel dinamik **BigQuery Geospatial SQL** (`ST_DWITHIN`) ve **Cloud Storage Zarr** (`xarray`) kod üretimi.

---

## 🚀 Çalıştırma Seçenekleri

### Seçenek A: Uzaktan Doğrudan Erişim (GitHub Pages)
Herhangi bir kurulum gerektirmeden telefon, tablet veya bilgisayardan doğrudan erişin:
**[https://yigitcandnc.github.io/weathernext-hub/](https://yigitcandnc.github.io/weathernext-hub/)**

### Seçenek B: Yerel FastAPI Sunucusu
```bash
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
veya Windows'ta `run_dashboard.bat` dosyasına çift tıklayın.
