// Modular Weather Experience Engine:
// 1. Personalizable Profile & Card Visibility Presets (localStorage + JSON transfer)
// 2. Smart Weather Alert Banner (Storm / Wind / Frost / Heat / UV)
// 3. Rain Countdown & 12-Hour Precipitation Window Strip
// 4. Live Temperatures & Icons in Favorites Bar (single batch request)
// 5. Shareable 1080x1350 3D Diorama Weather Card (Canvas PNG export & Web Share)
// 6. Live Precipitation Radar (Leaflet + RainViewer animated frames)
// 7. Daylight Sun Arc, Golden Hour & Astronomical Moon Phase
// 8. Air Quality (European AQI, PM2.5, PM10) & Pollen Card (Open-Meteo Air Quality)
// 9. Departure-Time Route Weather Planner (OSRM + Open-Meteo batch ETA forecast)

(function () {
  const PROFILE_KEY = 'hava_durumu_profile_v1';

  const CARD_CATALOG = [
    { id: 'rainCountdown', label: 'Yağış Geri Sayımı & Penceresi', desc: 'Yağmurun başlangıç/bitiş saatleri ve 12 saatlik özet' },
    { id: 'airQuality', label: 'Hava Kalitesi (AQI) & Polen', desc: 'Avrupa AQI, PM2.5, PM10 ve alerji polen göstergesi' },
    { id: 'radar', label: 'Canlı Yağış Radarı', desc: 'İlçe odaklı animasyonlu canlı yağış haritası' },
    { id: 'sunMoon', label: 'Gün Işığı, Altın Saat & Ay Evresi', desc: 'Güneş yayı, gün uzunluğu, golden hour ve ay evresi' },
    { id: 'travelRoute', label: 'Güzergah / Seyahat Hava Durumu', desc: 'Çıkış saatine göre yol boyu saatlik hava tahmini' },
    { id: 'rainTimeline', label: 'Yağış Grafiği (24 Saat)', desc: 'Saatlik yağış olasılığı ve mm grafiği' },
    { id: 'hourly48', label: 'Saatlik Tahmin (48 Saat)', desc: 'Yatay 48 saatlik sıcaklık ve rüzgar akışı' },
    { id: 'dailyInsights', label: 'Günlük Hayat Kartları', desc: 'Düne göre fark, işe gidiş-geliş ve basınç konforu' },
    { id: 'multiDay', label: '7 / 15 Günlük Tahmin & Zaman Dilimleri', desc: 'Uzun vadeli WeatherNext 15 günlük görünüm' },
    { id: 'districts', label: 'İlçe İlçe Anlık Hava Durumu', desc: 'Seçili ilin tüm ilçelerinin anlık kartları' }
  ];

  const PROFILE_PRESETS = {
    standard: {
      name: 'Standart',
      cards: {
        rainCountdown: true, airQuality: true, radar: true, sunMoon: true,
        travelRoute: true, rainTimeline: true, hourly48: true, dailyInsights: true,
        multiDay: true, districts: true
      }
    },
    allergy: {
      name: 'Alerji & Sağlık',
      cards: {
        rainCountdown: true, airQuality: true, radar: false, sunMoon: true,
        travelRoute: false, rainTimeline: false, hourly48: true, dailyInsights: true,
        multiDay: true, districts: false
      }
    },
    outdoor: {
      name: 'Dışarıda Çalışan / Saha',
      cards: {
        rainCountdown: true, airQuality: true, radar: true, sunMoon: false,
        travelRoute: false, rainTimeline: true, hourly48: true, dailyInsights: true,
        multiDay: true, districts: true
      }
    },
    driver: {
      name: 'Sürücü & Seyahat',
      cards: {
        rainCountdown: true, airQuality: false, radar: true, sunMoon: false,
        travelRoute: true, rainTimeline: true, hourly48: true, dailyInsights: true,
        multiDay: true, districts: false
      }
    },
    photo: {
      name: 'Fotoğrafçı & Doğa',
      cards: {
        rainCountdown: true, airQuality: false, radar: true, sunMoon: true,
        travelRoute: true, rainTimeline: false, hourly48: true, dailyInsights: false,
        multiDay: true, districts: false
      }
    }
  };

  let activeProfile = loadProfile();
  let lastWeatherContext = null;
  let favLiveCache = { ts: 0, map: {} };

  // Radar state
  let radarMap = null;
  let radarMarker = null;
  let radarBaseLayer = null;
  let radarOverlayLayer = null;
  let radarFrames = [];
  let radarFrameIdx = 0;
  let radarTimer = null;
  let radarPlaying = false;

  // --- 1. PROFILE & CUSTOMIZABLE CARDS ---
  function loadProfile() {
    try {
      const raw = JSON.parse(localStorage.getItem(PROFILE_KEY) || 'null');
      if (raw && raw.cards) {
        return {
          displayName: raw.displayName || '',
          preset: raw.preset || 'standard',
          cards: { ...PROFILE_PRESETS.standard.cards, ...raw.cards }
        };
      }
    } catch {}
    return {
      displayName: '',
      preset: 'standard',
      cards: { ...PROFILE_PRESETS.standard.cards }
    };
  }

  function saveProfile(p) {
    activeProfile = p;
    try { localStorage.setItem(PROFILE_KEY, JSON.stringify(p)); } catch {}
    applyProfileLayout();
  }

  function applyProfileLayout() {
    const cards = activeProfile.cards || PROFILE_PRESETS.standard.cards;
    document.querySelectorAll('[data-card-id]').forEach(el => {
      const id = el.getAttribute('data-card-id');
      if (cards[id] === false) {
        el.classList.add('profile-hidden');
      } else {
        el.classList.remove('profile-hidden');
      }
    });

    const badge = document.getElementById('activeProfileBadge');
    if (badge) {
      const presetLabel = PROFILE_PRESETS[activeProfile.preset]?.name || 'Özel';
      badge.textContent = activeProfile.displayName
        ? activeProfile.displayName
        : (activeProfile.preset === 'standard' ? 'Kartlar' : presetLabel);
    }

    if (cards.radar !== false && radarMap) {
      setTimeout(() => radarMap.invalidateSize(), 120);
    }
  }

  window.openProfileDialog = function () {
    const dlg = document.getElementById('profileDialog');
    if (!dlg) return;
    renderProfileDialogUI();
    dlg.showModal();
    if (window.lucide) lucide.createIcons();
  };

  function renderProfileDialogUI() {
    const nameInput = document.getElementById('profileNameInput');
    if (nameInput) nameInput.value = activeProfile.displayName || '';

    const presetWrap = document.getElementById('profilePresetsGrid');
    if (presetWrap) {
      presetWrap.innerHTML = '';
      Object.entries(PROFILE_PRESETS).forEach(([key, preset]) => {
        const isSel = activeProfile.preset === key;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `px-3 py-2 rounded-xl text-xs font-semibold text-left border transition ${
          isSel
            ? 'bg-sky-500 text-white border-sky-500 shadow-sm'
            : 'sub-card hover:border-sky-500'
        }`;
        btn.textContent = preset.name;
        btn.onclick = () => {
          activeProfile = {
            ...activeProfile,
            preset: key,
            cards: { ...preset.cards }
          };
          saveProfile(activeProfile);
          renderProfileDialogUI();
          if (typeof showToast === 'function') showToast(`${preset.name} profili uygulandı`);
        };
        presetWrap.appendChild(btn);
      });
    }

    const togglesWrap = document.getElementById('profileCardToggles');
    if (togglesWrap) {
      togglesWrap.innerHTML = '';
      CARD_CATALOG.forEach(item => {
        const checked = activeProfile.cards[item.id] !== false;
        const row = document.createElement('label');
        row.className = 'sub-card rounded-2xl px-3.5 py-2.5 flex items-center justify-between gap-3 cursor-pointer hover:border-sky-500 transition';
        row.innerHTML = `
          <div class="min-w-0">
            <div class="text-xs font-bold">${item.label}</div>
            <div class="text-[11px] text-sec truncate">${item.desc}</div>
          </div>
          <input type="checkbox" ${checked ? 'checked' : ''} class="w-4 h-4 accent-sky-500 shrink-0 rounded">
        `;
        const cb = row.querySelector('input');
        cb.onchange = () => {
          activeProfile.preset = 'custom';
          activeProfile.cards[item.id] = cb.checked;
          saveProfile(activeProfile);
          renderProfileDialogUI();
        };
        togglesWrap.appendChild(row);
      });
    }
  }

  window.saveProfileDisplayName = function () {
    const input = document.getElementById('profileNameInput');
    if (!input) return;
    activeProfile.displayName = input.value.trim().slice(0, 24);
    saveProfile(activeProfile);
    if (typeof showToast === 'function') showToast('Profil adı kaydedildi');
  };

  window.exportProfileCode = async function () {
    const code = btoa(unescape(encodeURIComponent(JSON.stringify(activeProfile))));
    try {
      await navigator.clipboard.writeText(code);
      if (typeof showToast === 'function') showToast('Profil kodu panoya kopyalandı (diğer cihazda yapıştırabilirsiniz)');
    } catch {
      window.prompt('Profil kodunuzu kopyalayın:', code);
    }
  };

  window.importProfileCode = function () {
    const code = window.prompt('Diğer cihazdan aldığınız profil kodunu yapıştırın:');
    if (!code) return;
    try {
      const parsed = JSON.parse(decodeURIComponent(escape(atob(code.trim()))));
      if (!parsed || typeof parsed.cards !== 'object') throw new Error('invalid');
      saveProfile({
        displayName: String(parsed.displayName || '').slice(0, 24),
        preset: parsed.preset || 'custom',
        cards: { ...PROFILE_PRESETS.standard.cards, ...parsed.cards }
      });
      renderProfileDialogUI();
      if (typeof showToast === 'function') showToast('Profil ayarları içe aktarıldı');
    } catch {
      if (typeof showToast === 'function') showToast('Geçersiz profil kodu');
    }
  };

  // --- 2. SMART WEATHER ALERT BANNER ---
  function renderWeatherAlertBanner(cur, next24, daily, todayIdx) {
    const banner = document.getElementById('weatherAlertBanner');
    const listEl = document.getElementById('weatherAlertList');
    if (!banner || !listEl) return;

    const alerts = [];
    const maxWind24 = Math.max(cur.wind_speed_10m ?? 0, cur.wind_gusts_10m ?? 0, ...next24.map(h => h.wind || 0));
    const maxMm24 = Math.max(cur.precipitation ?? 0, ...next24.map(h => h.mm || 0));
    const hasStorm = [95, 96, 99].includes(cur.weather_code) || next24.some(h => [95, 96, 99].includes(h.code));
    const minTemp = daily.temperature_2m_min?.[todayIdx] ?? Math.min(...next24.map(h => h.temp));
    const maxTemp = daily.temperature_2m_max?.[todayIdx] ?? Math.max(...next24.map(h => h.temp));
    const uvMax = daily.uv_index_max?.[todayIdx] ?? 0;

    if (hasStorm || maxMm24 >= 8) {
      alerts.push({
        tone: 'bg-rose-500/15 border-rose-500/35 text-rose-700 dark:text-rose-300',
        icon: 'cloud-lightning',
        title: hasStorm ? 'Gök Gürültülü Fırtına Riski' : 'Kuvvetli Yağış Uyarısı',
        text: hasStorm
          ? 'Önümüzdeki saatlerde gök gürültülü sağanak bekleniyor. Açık alanlarda dikkatli olun.'
          : `Saatte ${maxMm24.toFixed(1)} mm'ye ulaşan kuvvetli yağış bekleniyor.`
      });
    }
    if (maxWind24 >= 45) {
      alerts.push({
        tone: 'bg-amber-500/15 border-amber-500/35 text-amber-800 dark:text-amber-300',
        icon: 'wind',
        title: 'Kuvvetli Rüzgar',
        text: `Rüzgar hızının saatte ${Math.round(maxWind24)} km/s seviyelerine çıkması bekleniyor.`
      });
    }
    if (minTemp <= 0) {
      alerts.push({
        tone: 'bg-cyan-500/15 border-cyan-500/35 text-cyan-800 dark:text-cyan-300',
        icon: 'snowflake',
        title: 'Don ve Buzlanma Riski',
        text: `Sıcaklık ${Math.round(minTemp)}°C'ye kadar düşebilir; gece ve sabah erken saatlerde buzlanmaya dikkat.`
      });
    }
    if (maxTemp >= 36) {
      alerts.push({
        tone: 'bg-orange-500/15 border-orange-500/35 text-orange-800 dark:text-orange-300',
        icon: 'flame',
        title: 'Aşırı Sıcaklık',
        text: `Gün içi sıcaklık ${Math.round(maxTemp)}°C'ye ulaşabilir; 11:00–16:00 arası doğrudan güneşten kaçının.`
      });
    }
    if (uvMax >= 8) {
      alerts.push({
        tone: 'bg-violet-500/15 border-violet-500/35 text-violet-800 dark:text-violet-300',
        icon: 'sun-medium',
        title: `Yüksek UV (${uvMax.toFixed(1)})`,
        text: 'Öğle saatlerinde yüksek UV radyasyonu bekleniyor. Güneş kremi ve gözlük önerilir.'
      });
    }

    if (alerts.length === 0) {
      banner.classList.add('hidden');
      listEl.innerHTML = '';
      return;
    }

    listEl.innerHTML = alerts.slice(0, 3).map(a => `
      <div class="rounded-2xl border px-4 py-2.5 flex items-start gap-2.5 text-xs ${a.tone}">
        <i data-lucide="${a.icon}" class="w-4 h-4 shrink-0 mt-0.5"></i>
        <div>
          <span class="font-extrabold">${a.title}:</span>
          <span class="ml-1 opacity-95">${a.text}</span>
        </div>
      </div>
    `).join('');
    banner.classList.remove('hidden');
  }

  // --- 3. RAIN COUNTDOWN & 12-HOUR WINDOW STRIP ---
  function renderRainCountdown(next24) {
    const headlineEl = document.getElementById('rainCountdownHeadline');
    const subEl = document.getElementById('rainCountdownSub');
    const badgeEl = document.getElementById('rainCountdownBadge');
    const barsEl = document.getElementById('rainCountdownBars');
    if (!headlineEl || !barsEl) return;

    const isWet = h => (h.prob >= 30 || h.mm >= 0.1);
    const firstWetIdx = next24.findIndex(isWet);

    if (firstWetIdx === -1) {
      headlineEl.textContent = 'Önümüzdeki 24 saat boyunca yağış beklenmiyor';
      subEl.textContent = 'Şemsiyeye gerek yok — hava kuru ve dış mekan planları için elverişli.';
      badgeEl.textContent = 'Kuru Hava';
      badgeEl.className = 'px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 shrink-0';
    } else if (firstWetIdx === 0) {
      const endIdx = next24.findIndex((h, idx) => idx > 0 && !isWet(h));
      if (endIdx === -1) {
        headlineEl.textContent = 'Şu an yağışlı — gün boyu aralıklarla sürmesi bekleniyor';
        subEl.textContent = 'Dışarı çıkarken şemsiye veya yağmurluk bulundurmanız önerilir.';
      } else {
        const endTime = next24[endIdx].time.split('T')[1].slice(0, 5);
        headlineEl.textContent = `Şu an yağışlı • ~${endIdx} saat sonra (${endTime}) dinmesi bekleniyor`;
        subEl.textContent = `Toplam ~${endIdx} saatlik yağış penceresi öngörülüyor.`;
      }
      badgeEl.textContent = 'Yağış Aktif';
      badgeEl.className = 'px-3 py-1 rounded-full text-xs font-bold bg-sky-500/20 text-sky-600 dark:text-sky-400 shrink-0';
    } else {
      let endIdx = firstWetIdx;
      while (endIdx + 1 < next24.length && isWet(next24[endIdx + 1])) endIdx++;
      const duration = endIdx - firstWetIdx + 1;
      const startTime = next24[firstWetIdx].time.split('T')[1].slice(0, 5);
      const stopTime = next24[Math.min(endIdx + 1, next24.length - 1)].time.split('T')[1].slice(0, 5);
      const peakMm = Math.max(...next24.slice(firstWetIdx, endIdx + 1).map(h => h.mm || 0));
      const peakProb = Math.max(...next24.slice(firstWetIdx, endIdx + 1).map(h => h.prob || 0));

      headlineEl.textContent = `Yağış ~${firstWetIdx} saat sonra (${startTime}) başlayıp ~${duration} saat sürecek`;
      subEl.textContent = `${startTime} – ${stopTime} penceresinde en yüksek olasılık %${peakProb}${peakMm >= 0.2 ? ` (maks. ${peakMm.toFixed(1)} mm/sa)` : ''} • Şemsiye önerilir.`;
      badgeEl.textContent = `${firstWetIdx} sa sonra`;
      badgeEl.className = 'px-3 py-1 rounded-full text-xs font-bold bg-amber-500/15 text-amber-700 dark:text-amber-300 shrink-0';
    }

    const slice12 = next24.slice(0, 12);
    barsEl.innerHTML = slice12.map(h => {
      const wet = isWet(h);
      const intensityCls = !wet
        ? 'bg-slate-400/20'
        : (h.mm >= 3 || h.prob >= 75 ? 'bg-blue-600' : (h.mm >= 0.8 || h.prob >= 50 ? 'bg-sky-500' : 'bg-sky-400/70'));
      const heightPct = !wet ? 18 : Math.min(100, Math.max(35, Math.round(h.prob)));
      return `
        <div class="flex flex-col items-center gap-1 flex-1 min-w-[26px]" title="${h.hourLabel}: %${h.prob} • ${h.mm.toFixed(1)} mm">
          <div class="w-full h-10 rounded-lg bg-slate-500/10 flex items-end overflow-hidden p-0.5">
            <div class="w-full rounded-md transition-all ${intensityCls}" style="height:${heightPct}%"></div>
          </div>
          <span class="text-[10px] font-semibold text-sec">${h.hourLabel === 'Şimdi' ? 'Şimdi' : h.hourLabel.slice(0, 2)}</span>
        </div>
      `;
    }).join('');
  }

  // --- 4. LIVE TEMPERATURES IN FAVORITES BAR ---
  window.refreshFavoriteLiveTemps = async function () {
    if (typeof loadFavorites !== 'function' || typeof allProvinces === 'undefined' || !allProvinces.length) return;
    const favs = loadFavorites();
    if (!favs.length) return;

    const coords = favs.map(f => {
      const prov = allProvinces.find(p => p.name === f.province);
      if (!prov) return null;
      const dist = f.district && f.district !== '__MERKEZ__'
        ? prov.districts.find(d => d.name === f.district)
        : null;
      return {
        key: f.key,
        lat: dist ? dist.lat : prov.lat,
        lon: dist ? dist.lon : prov.lon
      };
    }).filter(Boolean);

    if (!coords.length) return;

    const now = Date.now();
    const allCached = coords.every(c => favLiveCache.map[c.key]) && (now - favLiveCache.ts < 300000);
    if (!allCached) {
      try {
        const lats = coords.map(c => c.lat).join(',');
        const lons = coords.map(c => c.lon).join(',');
        const resp = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lons}&current=temperature_2m,weather_code,is_day&timezone=auto`);
        let data = await resp.json();
        if (!Array.isArray(data)) data = [data];
        const nextMap = { ...favLiveCache.map };
        coords.forEach((c, idx) => {
          const cur = data[idx]?.current;
          if (cur) {
            nextMap[c.key] = {
              temp: Math.round(cur.temperature_2m ?? 0),
              code: cur.weather_code ?? 0,
              isDay: cur.is_day ?? 1
            };
          }
        });
        favLiveCache = { ts: now, map: nextMap };
      } catch {
        return;
      }
    }

    document.querySelectorAll('#favoritesList [data-fav-key]').forEach(el => {
      const key = el.getAttribute('data-fav-key');
      const live = favLiveCache.map[key];
      const badge = el.querySelector('.fav-live-temp');
      if (!live || !badge) return;
      const meta = typeof getWeatherMeta === 'function' ? getWeatherMeta(live.code, live.isDay) : { icon: 'sun' };
      badge.innerHTML = `<i data-lucide="${meta.icon}" class="w-3 h-3 inline-block"></i> <span>${live.temp}°</span>`;
      badge.classList.remove('hidden');
      badge.classList.add('inline-flex');
    });
    if (window.lucide) lucide.createIcons();
  };

  // --- 5A. SHAREABLE 3D WEATHER CARD (1080x1350 PNG) ---
  const ATMO_PALETTES = {
    sunny: ['#0284c7', '#0ea5e9', '#38bdf8'],
    partly: ['#0369a1', '#2563eb', '#60a5fa'],
    cloudy: ['#334155', '#475569', '#64748b'],
    rainy: ['#1e3a5f', '#0f4c81', '#0284c7'],
    stormy: ['#1e1b4b', '#312e81', '#4338ca'],
    snowy: ['#1d4ed8', '#3b82f6', '#93c5fd'],
    foggy: ['#475569', '#64748b', '#94a3b8'],
    night: ['#0f172a', '#1e293b', '#312e81']
  };

  function drawRoundedRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function renderShareCardCanvas() {
    const canvas = document.getElementById('shareCardCanvas');
    if (!canvas) return;
    const W = 1080, H = 1350;
    canvas.width = W;
    canvas.height = H;
    const ctx = canvas.getContext('2d');

    const atmo = document.getElementById('heroCard')?.getAttribute('data-atmosphere') || 'sunny';
    const [c1, c2, c3] = ATMO_PALETTES[atmo] || ATMO_PALETTES.sunny;
    const grad = ctx.createLinearGradient(0, 0, W, H);
    grad.addColorStop(0, c1);
    grad.addColorStop(0.55, c2);
    grad.addColorStop(1, c3);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, W, H);

    const glow = ctx.createRadialGradient(W / 2, 740, 40, W / 2, 740, 460);
    glow.addColorStop(0, 'rgba(255,255,255,0.22)');
    glow.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, W, H);

    const locName = (document.getElementById('heroLocationName')?.textContent || 'Türkiye').trim();
    const temp = (document.getElementById('heroTemp')?.textContent || '--°').trim();
    const feels = (document.getElementById('heroFeelsLike')?.textContent || '').trim();
    const cond = (document.getElementById('heroCondition')?.textContent || '').trim();
    const hiLo = (document.getElementById('heroHighLow')?.textContent || '').trim();
    const wind = (document.getElementById('heroWind')?.textContent || '--').trim();
    const hum = (document.getElementById('heroHumidity')?.textContent || '--').trim();
    const uv = (document.getElementById('heroUV')?.textContent || '--').trim();
    const sunT = (document.getElementById('heroSunTimes')?.textContent || '--').trim();
    const dateStr = new Date().toLocaleDateString('tr-TR', { weekday: 'long', day: 'numeric', month: 'long' });

    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(255,255,255,0.85)';
    ctx.font = '600 30px Inter, system-ui, sans-serif';
    ctx.fillText(dateStr.toUpperCase(), W / 2, 92);

    ctx.fillStyle = '#ffffff';
    ctx.font = '800 54px Inter, system-ui, sans-serif';
    ctx.fillText(locName, W / 2, 162);

    ctx.font = '800 172px Inter, system-ui, sans-serif';
    ctx.fillText(temp, W / 2, 336);

    ctx.font = '700 40px Inter, system-ui, sans-serif';
    ctx.fillText(cond, W / 2, 398);

    ctx.fillStyle = 'rgba(255,255,255,0.88)';
    ctx.font = '500 28px Inter, system-ui, sans-serif';
    ctx.fillText(`${feels}  •  ${hiLo}`, W / 2, 446);

    const imgEl = document.getElementById('heroDioramaImg');
    if (imgEl && imgEl.complete && imgEl.naturalWidth > 0 && !document.getElementById('heroDioramaStage')?.classList.contains('hidden')) {
      const box = 560;
      const dx = (W - box) / 2;
      const dy = 472;
      try {
        ctx.drawImage(imgEl, dx, dy, box, box);
      } catch {}
    }

    const metrics = [
      { label: 'RÜZGAR', val: wind },
      { label: 'NEM', val: hum },
      { label: 'UV İNDEKSİ', val: uv },
      { label: 'GÜN DOĞUMU / BATIMI', val: sunT }
    ];
    const padX = 64, gap = 22, cardW = (W - padX * 2 - gap) / 2, cardH = 104, startY = 1054;
    metrics.forEach((m, idx) => {
      const col = idx % 2, row = Math.floor(idx / 2);
      const x = padX + col * (cardW + gap);
      const y = startY + row * (cardH + gap);
      drawRoundedRect(ctx, x, y, cardW, cardH, 24);
      ctx.fillStyle = 'rgba(255,255,255,0.16)';
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.22)';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.textAlign = 'left';
      ctx.fillStyle = 'rgba(255,255,255,0.78)';
      ctx.font = '600 20px Inter, system-ui, sans-serif';
      ctx.fillText(m.label, x + 28, y + 38);

      ctx.fillStyle = '#ffffff';
      ctx.font = '800 30px Inter, system-ui, sans-serif';
      ctx.fillText(m.val, x + 28, y + 80);
    });

    ctx.textAlign = 'center';
    ctx.fillStyle = 'rgba(255,255,255,0.72)';
    ctx.font = '600 22px Inter, system-ui, sans-serif';
    ctx.fillText('Hava Durumu • WeatherNext', W / 2, H - 30);
  }

  window.openShareCardDialog = function () {
    const dlg = document.getElementById('shareCardDialog');
    if (!dlg) return;
    renderShareCardCanvas();
    dlg.showModal();
    if (window.lucide) lucide.createIcons();
  };

  window.downloadShareCard = function () {
    const canvas = document.getElementById('shareCardCanvas');
    if (!canvas) return;
    const locSlug = (document.getElementById('heroLocationName')?.textContent || 'hava-durumu')
      .trim().toLowerCase().replace(/[^a-z0-9ğüşıöç]+/gi, '-');
    const a = document.createElement('a');
    a.download = `hava-durumu-${locSlug}.png`;
    a.href = canvas.toDataURL('image/png');
    a.click();
    if (typeof showToast === 'function') showToast('Hava kartı PNG olarak indirildi');
  };

  window.nativeShareCard = function () {
    const canvas = document.getElementById('shareCardCanvas');
    if (!canvas) return;
    canvas.toBlob(async (blob) => {
      if (!blob) return;
      const locName = (document.getElementById('heroLocationName')?.textContent || 'Hava Durumu').trim();
      const temp = (document.getElementById('heroTemp')?.textContent || '').trim();
      const file = new File([blob], 'hava-durumu-karti.png', { type: 'image/png' });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        try {
          await navigator.share({ title: `${locName} ${temp}`, text: `${locName} anlık hava durumu: ${temp}`, files: [file] });
          return;
        } catch {}
      }
      window.downloadShareCard();
    }, 'image/png');
  };

  // --- 5B. LIVE PRECIPITATION RADAR (LEAFLET OSM + RAINVIEWER) ---
  function isDarkSchemeActive() {
    const scheme = document.querySelector('meta[name="color-scheme"]')?.content || '';
    return scheme === 'dark' || (scheme !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  }

  window.syncRadarTheme = function () {
    const el = document.getElementById('radarMapContainer');
    if (!el) return;
    if (isDarkSchemeActive()) {
      el.classList.add('radar-dark-base');
    } else {
      el.classList.remove('radar-dark-base');
    }
  };

  async function initOrUpdateRadar(lat, lon, label) {
    const el = document.getElementById('radarMapContainer');
    if (!el || !window.L) return;

    window.syncRadarTheme();
    if (!radarMap) {
      radarMap = L.map(el, { zoomControl: true, scrollWheelZoom: false, minZoom: 4, maxZoom: 11 }).setView([lat, lon], 7);
      radarMap.createPane('basemapPane');
      radarMap.getPane('basemapPane').style.zIndex = 200;
      radarBaseLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        pane: 'basemapPane',
        maxZoom: 18,
        attribution: '&copy; OpenStreetMap &copy; RainViewer'
      }).addTo(radarMap);
      radarMarker = L.circleMarker([lat, lon], {
        radius: 7, color: '#ffffff', weight: 2, fillColor: '#0ea5e9', fillOpacity: 0.95
      }).addTo(radarMap).bindTooltip(label, { direction: 'top' });
      await loadRainViewerFrames();
    } else {
      const targetZoom = Math.min(Math.max(radarMap.getZoom(), 6), 7);
      radarMap.setView([lat, lon], targetZoom, { animate: true });
      if (radarMarker) {
        radarMarker.setLatLng([lat, lon]).setTooltipContent(label);
      }
      setTimeout(() => radarMap.invalidateSize(), 120);
    }
  }

  async function loadRainViewerFrames() {
    const tsEl = document.getElementById('radarFrameTime');
    try {
      const resp = await fetch('https://api.rainviewer.com/public/weather-maps.json');
      const data = await resp.json();
      const host = data.host || 'https://tilecache.rainviewer.com';
      const past = (data.radar?.past || []).map(f => ({ time: f.time, path: f.path, host, isNowcast: false }));
      const nowcast = (data.radar?.nowcast || []).map(f => ({ time: f.time, path: f.path, host, isNowcast: true }));
      radarFrames = [...past, ...nowcast];
      if (!radarFrames.length) {
        if (tsEl) tsEl.textContent = 'Radar verisi şu an yok';
        return;
      }
      const slider = document.getElementById('radarSlider');
      if (slider) {
        slider.min = 0;
        slider.max = radarFrames.length - 1;
      }
      radarFrameIdx = Math.max(0, past.length - 1);
      showRadarFrame(radarFrameIdx);
    } catch {
      if (tsEl) tsEl.textContent = 'Radar servisine şu an ulaşılamıyor';
    }
  }

  function showRadarFrame(idx) {
    if (!radarMap || !radarFrames.length || !window.L) return;
    radarFrameIdx = Math.max(0, Math.min(radarFrames.length - 1, idx));
    const frame = radarFrames[radarFrameIdx];
    const url = `${frame.host}${frame.path}/256/{z}/{x}/{y}/2/1_1.png`;
    if (radarOverlayLayer) radarMap.removeLayer(radarOverlayLayer);
    radarOverlayLayer = L.tileLayer(url, {
      tileSize: 256,
      maxNativeZoom: 7,
      maxZoom: 11,
      opacity: 0.72,
      zIndex: 10
    }).addTo(radarMap);

    const slider = document.getElementById('radarSlider');
    if (slider) slider.value = radarFrameIdx;

    const tsEl = document.getElementById('radarFrameTime');
    if (tsEl) {
      const d = new Date(frame.time * 1000);
      const tStr = d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
      tsEl.textContent = frame.isNowcast ? `${tStr} (Tahmin)` : `${tStr} (Canlı)`;
    }
  }

  window.seekRadarFrame = function (val) {
    showRadarFrame(Number(val));
  };

  window.toggleRadarPlay = function () {
    const btn = document.getElementById('radarPlayBtn');
    if (radarPlaying) {
      clearInterval(radarTimer);
      radarPlaying = false;
      if (btn) btn.innerHTML = '<i data-lucide="play" class="w-3.5 h-3.5"></i> Oynat';
    } else {
      if (!radarFrames.length) return;
      radarPlaying = true;
      if (btn) btn.innerHTML = '<i data-lucide="pause" class="w-3.5 h-3.5"></i> Durdur';
      radarTimer = setInterval(() => {
        showRadarFrame((radarFrameIdx + 1) % radarFrames.length);
      }, 650);
    }
    if (window.lucide) lucide.createIcons();
  };

  // --- 5C. DAYLIGHT SUN ARC, GOLDEN HOUR & MOON PHASE ---
  function computeMoonPhase(date) {
    const synodic = 29.53058867;
    const knownNewMoon = Date.UTC(2000, 0, 6, 18, 14, 0);
    const daysSince = (date.getTime() - knownNewMoon) / 86400000;
    let phase = (daysSince % synodic) / synodic;
    if (phase < 0) phase += 1;
    const illum = Math.round(((1 - Math.cos(phase * 2 * Math.PI)) / 2) * 100);

    let name = 'Yeni Ay';
    if (phase < 0.03 || phase >= 0.97) name = 'Yeni Ay';
    else if (phase < 0.22) name = 'Büyüyen Hilal';
    else if (phase < 0.28) name = 'İlk Dördün';
    else if (phase < 0.47) name = 'Büyüyen Şişkin Ay';
    else if (phase < 0.53) name = 'Dolunay';
    else if (phase < 0.72) name = 'Küçülen Şişkin Ay';
    else if (phase < 0.78) name = 'Son Dördün';
    else name = 'Küçülen Hilal';

    return { phase, illum, name };
  }

  function formatHM(totalMin) {
    const h = Math.floor(totalMin / 60);
    const m = Math.round(totalMin % 60);
    return `${h} sa ${m} dk`;
  }

  function shiftTimeStr(isoStr, deltaMin) {
    if (!isoStr) return '--:--';
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '--:--';
    d.setMinutes(d.getMinutes() + deltaMin);
    return d.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
  }

  function renderSunMoonCard(cur, daily, todayIdx) {
    const srIso = daily.sunrise?.[todayIdx];
    const ssIso = daily.sunset?.[todayIdx];
    const ySrIso = daily.sunrise?.[todayIdx - 1];
    const ySsIso = daily.sunset?.[todayIdx - 1];
    const arcEl = document.getElementById('sunArcSvgContainer');
    if (!arcEl || !srIso || !ssIso) return;

    const sr = new Date(srIso);
    const ss = new Date(ssIso);
    const now = cur.time ? new Date(cur.time) : new Date();
    const dayMin = Math.max(1, (ss - sr) / 60000);
    const elapsedMin = (now - sr) / 60000;
    const progress = Math.max(0, Math.min(1, elapsedMin / dayMin));
    const isDayNow = elapsedMin >= 0 && elapsedMin <= dayMin;

    let deltaLabel = '';
    if (ySrIso && ySsIso) {
      const yDayMin = (new Date(ySsIso) - new Date(ySrIso)) / 60000;
      const diff = Math.round(dayMin - yDayMin);
      if (diff !== 0) deltaLabel = ` (düne göre ${diff > 0 ? '+' : ''}${diff} dk)`;
    }

    const dayLenEl = document.getElementById('sunDayLength');
    if (dayLenEl) dayLenEl.textContent = `${formatHM(dayMin)}${deltaLabel}`;

    const goldenAmEl = document.getElementById('goldenHourAm');
    const goldenPmEl = document.getElementById('goldenHourPm');
    if (goldenAmEl) goldenAmEl.textContent = `${shiftTimeStr(srIso, 0)} – ${shiftTimeStr(srIso, 50)}`;
    if (goldenPmEl) goldenPmEl.textContent = `${shiftTimeStr(ssIso, -55)} – ${shiftTimeStr(ssIso, 0)}`;

    const t = progress;
    const sx = (1 - t) * (1 - t) * 24 + 2 * (1 - t) * t * 160 + t * t * 296;
    const sy = (1 - t) * (1 - t) * 116 + 2 * (1 - t) * t * -10 + t * t * 116;
    const srText = srIso.split('T')[1].slice(0, 5);
    const ssText = ssIso.split('T')[1].slice(0, 5);

    arcEl.innerHTML = `
      <svg viewBox="0 0 320 138" class="w-full max-w-[340px] mx-auto overflow-visible">
        <defs>
          <linearGradient id="sunArcGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#f59e0b" />
            <stop offset="50%" stop-color="#fbbf24" />
            <stop offset="100%" stop-color="#f97316" />
          </linearGradient>
        </defs>
        <line x1="12" y1="116" x2="308" y2="116" stroke="currentColor" stroke-opacity="0.18" stroke-dasharray="4 4" stroke-width="1.5" />
        <path d="M 24 116 Q 160 -10 296 116" fill="none" stroke="currentColor" stroke-opacity="0.15" stroke-width="3" stroke-linecap="round" />
        <path d="M 24 116 Q 160 -10 296 116" fill="none" stroke="url(#sunArcGrad)" stroke-width="3.5" stroke-linecap="round"
              pathLength="100" stroke-dasharray="${isDayNow ? (progress * 100).toFixed(1) : (elapsedMin > dayMin ? 100 : 0)} 100" />
        ${isDayNow ? `
          <circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="12" fill="#f59e0b" fill-opacity="0.25" />
          <circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="6.5" fill="#fbbf24" stroke="#ffffff" stroke-width="2" />
        ` : ''}
        <text x="24" y="133" font-size="11" font-weight="700" text-anchor="middle" fill="currentColor" fill-opacity="0.75">${srText}</text>
        <text x="296" y="133" font-size="11" font-weight="700" text-anchor="middle" fill="currentColor" fill-opacity="0.75">${ssText}</text>
      </svg>
    `;

    const moon = computeMoonPhase(now);
    const moonNameEl = document.getElementById('moonPhaseName');
    const moonIllumEl = document.getElementById('moonIllumination');
    const moonSvgEl = document.getElementById('moonPhaseSvg');
    if (moonNameEl) moonNameEl.textContent = moon.name;
    if (moonIllumEl) moonIllumEl.textContent = `Aydınlanma: %${moon.illum}`;
    if (moonSvgEl) {
      const k = Math.cos(moon.phase * 2 * Math.PI);
      const rx = Math.abs(k) * 20;
      const waxing = moon.phase <= 0.5;
      const sweepOuter = waxing ? 1 : 0;
      const sweepInner = waxing ? (k > 0 ? 0 : 1) : (k > 0 ? 1 : 0);
      moonSvgEl.innerHTML = `
        <svg viewBox="0 0 48 48" class="w-11 h-11 shrink-0">
          <circle cx="24" cy="24" r="20" fill="#1e293b" stroke="rgba(148,163,184,0.35)" stroke-width="1.5" />
          ${moon.illum > 2 ? `<path d="M 24 4 A 20 20 0 0 ${sweepOuter} 24 44 A ${rx.toFixed(1)} 20 0 0 ${sweepInner} 24 4 Z" fill="#fef3c7" />` : ''}
        </svg>
      `;
    }
  }

  // --- 6. AIR QUALITY (AQI) & POLLEN CARD ---
  function getAqiMeta(aqi) {
    if (aqi <= 20) return { label: 'Çok İyi', cls: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400', bar: 'bg-emerald-500' };
    if (aqi <= 40) return { label: 'İyi', cls: 'bg-lime-500/15 text-lime-700 dark:text-lime-400', bar: 'bg-lime-500' };
    if (aqi <= 60) return { label: 'Orta', cls: 'bg-amber-500/15 text-amber-700 dark:text-amber-300', bar: 'bg-amber-500' };
    if (aqi <= 80) return { label: 'Hassas', cls: 'bg-orange-500/15 text-orange-700 dark:text-orange-300', bar: 'bg-orange-500' };
    return { label: 'Kötü', cls: 'bg-rose-500/15 text-rose-700 dark:text-rose-300', bar: 'bg-rose-500' };
  }

  function getPollenLevel(val) {
    if (val == null || val < 1) return { txt: 'Düşük', cls: 'text-emerald-600 dark:text-emerald-400' };
    if (val < 20) return { txt: 'Hafif', cls: 'text-lime-600 dark:text-lime-400' };
    if (val < 60) return { txt: 'Orta', cls: 'text-amber-600 dark:text-amber-300' };
    return { txt: 'Yüksek', cls: 'text-rose-600 dark:text-rose-400' };
  }

  let aqiCache = { key: '', ts: 0, data: null };
  let aqiInFlightKey = '';
  let aqiReqToken = 0;

  function applyAirQualityUI(data) {
    const scoreEl = document.getElementById('aqiScoreValue');
    if (!scoreEl) return;
    const c = data.current || {};
    const aqi = Math.round(c.european_aqi ?? 0);
    const meta = getAqiMeta(aqi);

    scoreEl.textContent = aqi;
    const badgeEl = document.getElementById('aqiStatusBadge');
    if (badgeEl) {
      badgeEl.textContent = meta.label;
      badgeEl.className = `px-3 py-1 rounded-full text-xs font-bold ${meta.cls}`;
    }
    const barEl = document.getElementById('aqiProgressBar');
    if (barEl) {
      barEl.className = `h-full rounded-full transition-all ${meta.bar}`;
      barEl.style.width = `${Math.min(100, Math.max(8, aqi))}%`;
    }

    const setTxt = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };
    setTxt('aqiPm25', c.pm2_5 != null ? `${c.pm2_5.toFixed(1)} µg/m³` : '--');
    setTxt('aqiPm10', c.pm10 != null ? `${c.pm10.toFixed(1)} µg/m³` : '--');
    setTxt('aqiNo2', c.nitrogen_dioxide != null ? `${c.nitrogen_dioxide.toFixed(1)} µg/m³` : '--');
    setTxt('aqiO3', c.ozone != null ? `${Math.round(c.ozone)} µg/m³` : '--');

    const pollens = [
      { name: 'Çimen', val: c.grass_pollen ?? 0 },
      { name: 'Zeytin', val: c.olive_pollen ?? 0 },
      { name: 'Huş', val: c.birch_pollen ?? 0 },
      { name: 'Pelin', val: c.mugwort_pollen ?? 0 }
    ];
    const topPollen = pollens.reduce((a, b) => (b.val > a.val ? b : a), pollens[0]);
    const pLvl = getPollenLevel(topPollen.val);
    const pollenGrid = document.getElementById('pollenSummaryGrid');
    if (pollenGrid) {
      pollenGrid.innerHTML = pollens.map(p => {
        const lv = getPollenLevel(p.val);
        return `
          <div class="sub-card rounded-xl px-2.5 py-2 flex items-center justify-between text-xs">
            <span class="text-sec">${p.name}</span>
            <span class="font-bold ${lv.cls}">${lv.txt}</span>
          </div>
        `;
      }).join('');
    }
    const noteEl = document.getElementById('aqiHealthTip');
    if (noteEl) {
      noteEl.textContent = aqi > 60
        ? 'Hava kalitesi hassas gruplar için düşük; uzun süreli yoğun dış mekan egzersizini sınırlayın.'
        : (topPollen.val >= 20
          ? `Hava kalitesi iyi ancak ${topPollen.name.toLowerCase()} poleni belirgin (${pLvl.txt}). Alerjisi olanlar tedbirli olmalı.`
          : 'Hava kalitesi temiz ve polen yoğunluğu düşük. Dış mekan aktiviteleri için elverişli.');
    }
  }

  window.loadAirQuality = async function (lat, lon, opts = {}) {
    const scoreEl = document.getElementById('aqiScoreValue');
    if (!scoreEl || lat == null || lon == null) return;
    const coordKey = `${Number(lat).toFixed(3)},${Number(lon).toFixed(3)}`;
    const now = Date.now();
    if (aqiCache.key === coordKey && aqiCache.data && (now - aqiCache.ts < 300000)) {
      applyAirQualityUI(aqiCache.data);
      return;
    }
    if (opts.reuseInFlight && aqiInFlightKey === coordKey) {
      return;
    }

    const token = ++aqiReqToken;
    aqiInFlightKey = coordKey;
    try {
      const url = `https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${lat}&longitude=${lon}&current=european_aqi,pm2_5,pm10,nitrogen_dioxide,ozone,grass_pollen,birch_pollen,olive_pollen,mugwort_pollen,ragweed_pollen&timezone=auto`;
      const resp = await fetch(url);
      const data = await resp.json();
      if (token !== aqiReqToken) return;
      aqiCache = { key: coordKey, ts: Date.now(), data };
      applyAirQualityUI(data);
    } catch {
      if (token === aqiReqToken) scoreEl.textContent = '--';
    } finally {
      if (aqiInFlightKey === coordKey) aqiInFlightKey = '';
    }
  };

  // --- 7. DEPARTURE-TIME ROUTE / TRAVEL WEATHER PLANNER ---
  function populateRouteDatalist() {
    const dl = document.getElementById('routeLocationsDatalist');
    if (!dl || typeof searchIndex === 'undefined' || !searchIndex.length || dl.childElementCount > 0) return;
    const frag = document.createDocumentFragment();
    searchIndex.forEach(item => {
      const opt = document.createElement('option');
      const isDist = item.district && item.district !== '__MERKEZ__';
      opt.value = isDist ? `${item.district} (${item.province})` : `${item.province} (İl Merkezi)`;
      frag.appendChild(opt);
    });
    dl.appendChild(frag);

    const depInput = document.getElementById('routeDepartureTime');
    if (depInput && !depInput.value) {
      const now = new Date();
      now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
      depInput.value = now.toISOString().slice(0, 16);
    }
    const fromInput = document.getElementById('routeFromInput');
    if (fromInput && !fromInput.value && typeof currentProvince !== 'undefined' && currentProvince) {
      fromInput.value = currentDistrict
        ? `${currentDistrict.name} (${currentProvince.name})`
        : `${currentProvince.name} (İl Merkezi)`;
    }
  }

  function toRouteCoord(item) {
    const prov = allProvinces.find(p => p.name === item.province);
    if (!prov) return null;
    const isDist = item.district && item.district !== '__MERKEZ__';
    const dist = isDist ? prov.districts.find(d => d.name === item.district) : null;
    return {
      label: isDist ? `${item.district} (${item.province})` : item.province,
      lat: dist ? dist.lat : prov.lat,
      lon: dist ? dist.lon : prov.lon
    };
  }

  function resolveRouteLocationInput(rawText) {
    if (!rawText || typeof searchIndex === 'undefined') return null;
    const normFn = typeof normalizeTr === 'function' ? normalizeTr : (s => String(s || '').toLowerCase());
    const norm = normFn(rawText.trim());
    if (!norm) return null;

    for (const item of searchIndex) {
      const isDist = item.district && item.district !== '__MERKEZ__';
      const formatted = isDist ? `${item.district} (${item.province})` : `${item.province} (İl Merkezi)`;
      if (normFn(formatted) === norm || normFn(item.title) === norm) return toRouteCoord(item);
    }
    let best = null;
    for (const item of searchIndex) {
      const pNorm = normFn(item.province);
      const dNorm = item.district && item.district !== '__MERKEZ__' ? normFn(item.district) : '';
      if (pNorm === norm || dNorm === norm) return toRouteCoord(item);
      if (!best && (item.norm.includes(norm) || pNorm.startsWith(norm) || (dNorm && dNorm.startsWith(norm)))) {
        best = item;
      }
    }
    return best ? toRouteCoord(best) : null;
  }

  function nearestTurkishPlace(lat, lon) {
    let bestLabel = `${lat.toFixed(2)}, ${lon.toFixed(2)}`, minKm = Infinity;
    if (typeof allProvinces === 'undefined' || typeof haversineKm !== 'function') return bestLabel;
    for (const p of allProvinces) {
      for (const d of p.districts) {
        const km = haversineKm(lat, lon, d.lat, d.lon);
        if (km < minKm) {
          minKm = km;
          bestLabel = `${d.name} (${p.name})`;
        }
      }
    }
    return bestLabel;
  }

  window.useCurrentLocationForRoute = function () {
    const fromInput = document.getElementById('routeFromInput');
    if (!fromInput || typeof currentProvince === 'undefined' || !currentProvince) return;
    fromInput.value = currentDistrict
      ? `${currentDistrict.name} (${currentProvince.name})`
      : `${currentProvince.name} (İl Merkezi)`;
  };

  window.calculateTravelRouteWeather = async function () {
    const fromTxt = document.getElementById('routeFromInput')?.value || '';
    const toTxt = document.getElementById('routeToInput')?.value || '';
    const depVal = document.getElementById('routeDepartureTime')?.value || '';
    const resultEl = document.getElementById('routeResultsContainer');
    const summaryEl = document.getElementById('routeSummaryBar');
    if (!resultEl || !summaryEl) return;

    const origin = resolveRouteLocationInput(fromTxt);
    const dest = resolveRouteLocationInput(toTxt);
    if (!origin || !dest) {
      if (typeof showToast === 'function') showToast('Lütfen geçerli bir kalkış ve varış il/ilçe seçin');
      return;
    }

    const depDate = depVal ? new Date(depVal) : new Date();
    if (isNaN(depDate.getTime())) return;

    summaryEl.classList.remove('hidden');
    summaryEl.textContent = 'Güzergah ve yol boyu saatlik hava tahmini hesaplanıyor...';
    resultEl.innerHTML = '';

    let totalKm = 0;
    let totalSec = 0;
    const waypoints = [];

    try {
      const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${origin.lon},${origin.lat};${dest.lon},${dest.lat}?overview=full&geometries=geojson`;
      const resp = await fetch(osrmUrl);
      const osrm = await resp.json();
      const route = osrm.routes?.[0];
      if (!route || !route.geometry?.coordinates?.length) throw new Error('no-route');
      totalKm = route.distance / 1000;
      totalSec = route.duration;
      const coords = route.geometry.coordinates;
      const stopsCount = totalKm < 120 ? 4 : (totalKm < 450 ? 5 : 6);
      for (let i = 0; i < stopsCount; i++) {
        const frac = i / (stopsCount - 1);
        const cIdx = Math.min(coords.length - 1, Math.round(frac * (coords.length - 1)));
        const [lon, lat] = coords[cIdx];
        const eta = new Date(depDate.getTime() + frac * totalSec * 1000);
        const label = i === 0 ? origin.label : (i === stopsCount - 1 ? dest.label : nearestTurkishPlace(lat, lon));
        waypoints.push({ lat, lon, eta, label, km: Math.round(frac * totalKm) });
      }
    } catch {
      totalKm = typeof haversineKm === 'function' ? haversineKm(origin.lat, origin.lon, dest.lat, dest.lon) * 1.22 : 250;
      totalSec = (totalKm / 85) * 3600;
      const stopsCount = totalKm < 150 ? 4 : 5;
      for (let i = 0; i < stopsCount; i++) {
        const frac = i / (stopsCount - 1);
        const lat = origin.lat + (dest.lat - origin.lat) * frac;
        const lon = origin.lon + (dest.lon - origin.lon) * frac;
        const eta = new Date(depDate.getTime() + frac * totalSec * 1000);
        const label = i === 0 ? origin.label : (i === stopsCount - 1 ? dest.label : nearestTurkishPlace(lat, lon));
        waypoints.push({ lat, lon, eta, label, km: Math.round(frac * totalKm) });
      }
    }

    try {
      const lats = waypoints.map(w => w.lat.toFixed(4)).join(',');
      const lons = waypoints.map(w => w.lon.toFixed(4)).join(',');
      const fcUrl = `https://api.open-meteo.com/v1/forecast?latitude=${lats}&longitude=${lons}&hourly=temperature_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,is_day&timezone=auto&forecast_days=7`;
      const resp = await fetch(fcUrl);
      let data = await resp.json();
      if (!Array.isArray(data)) data = [data];

      const riskStops = [];
      const htmlStops = waypoints.map((wp, idx) => {
        const hourly = data[idx]?.hourly || {};
        const times = hourly.time || [];
        const localIsoPrefix = new Date(wp.eta.getTime() - wp.eta.getTimezoneOffset() * 60000).toISOString().slice(0, 13);
        let hIdx = times.findIndex(t => t.startsWith(localIsoPrefix));
        if (hIdx < 0) hIdx = 0;

        const temp = Math.round(hourly.temperature_2m?.[hIdx] ?? 0);
        const prob = hourly.precipitation_probability?.[hIdx] ?? 0;
        const mm = hourly.precipitation?.[hIdx] ?? 0;
        const wind = Math.round(hourly.wind_speed_10m?.[hIdx] ?? 0);
        const code = hourly.weather_code?.[hIdx] ?? 0;
        const isDay = hourly.is_day?.[hIdx] ?? 1;
        const meta = typeof getWeatherMeta === 'function' ? getWeatherMeta(code, isDay) : { icon: 'sun', text: '' };
        const etaStr = wp.eta.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
        const hasRisk = prob >= 40 || mm >= 0.3 || wind >= 45 || temp <= 1;
        if (hasRisk) riskStops.push(`${wp.label} (${etaStr})`);

        return `
          <div class="sub-card rounded-2xl p-3.5 flex flex-col justify-between gap-2 border ${hasRisk ? 'border-amber-500/40' : 'border-transparent'}">
            <div class="flex items-center justify-between gap-2">
              <span class="px-2 py-0.5 rounded-lg bg-sky-500/15 text-sky-600 dark:text-sky-400 text-[11px] font-extrabold">${etaStr}</span>
              <span class="text-[10px] font-semibold text-sec">${wp.km} km</span>
            </div>
            <div class="text-xs font-bold leading-snug">${wp.label}</div>
            <div class="flex items-center justify-between pt-1">
              <div class="flex items-center gap-1.5">
                <i data-lucide="${meta.icon}" class="w-5 h-5 text-sky-500"></i>
                <span class="text-xl font-extrabold">${temp}°</span>
              </div>
              <div class="text-right text-[11px] text-sec">
                <div class="${prob >= 40 ? 'text-sky-500 font-bold' : ''}">%${prob} yağış</div>
                <div>${wind} km/s</div>
              </div>
            </div>
            <div class="text-[11px] text-sec truncate">${meta.text}${mm >= 0.2 ? ` • ${mm.toFixed(1)} mm` : ''}</div>
          </div>
        `;
      }).join('');

      const durH = Math.floor(totalSec / 3600);
      const durM = Math.round((totalSec % 3600) / 60);
      summaryEl.innerHTML = `
        <div class="flex flex-wrap items-center justify-between gap-2">
          <span class="font-bold">Toplam ~${Math.round(totalKm)} km • Tahmini Süre: ${durH > 0 ? `${durH} sa ` : ''}${durM} dk</span>
          <span class="text-xs ${riskStops.length ? 'text-amber-600 dark:text-amber-400 font-semibold' : 'text-emerald-600 dark:text-emerald-400 font-semibold'}">
            ${riskStops.length ? `Dikkat edilmesi gereken geçişler: ${riskStops.slice(0, 2).join(', ')}` : 'Güzergah boyunca belirgin hava riski görünmüyor'}
          </span>
        </div>
      `;
      resultEl.innerHTML = htmlStops;
      if (window.lucide) lucide.createIcons();
    } catch {
      summaryEl.textContent = 'Güzergah hava tahmini şu an alınamadı.';
    }
  };

  // --- MAIN LIFECYCLE HOOKS ---
  window.onWeatherDataRendered = function (ctx) {
    lastWeatherContext = ctx;
    renderWeatherAlertBanner(ctx.cur, ctx.next24, ctx.daily, ctx.todayDailyIdx);
    renderRainCountdown(ctx.next24);
    renderSunMoonCard(ctx.cur, ctx.daily, ctx.todayDailyIdx);
    window.loadAirQuality(ctx.lat, ctx.lon, { reuseInFlight: true });
    initOrUpdateRadar(ctx.lat, ctx.lon, ctx.displayLabel);
    populateRouteDatalist();
    window.refreshFavoriteLiveTemps();
    applyProfileLayout();
  };

  window.initExtraFeatures = function () {
    applyProfileLayout();
    populateRouteDatalist();

    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        e.preventDefault();
        if (typeof openSearchDialog === 'function') openSearchDialog();
      }
    });
  };
})();
