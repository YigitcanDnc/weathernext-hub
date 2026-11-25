// Curated 81-province & 51-district landmark catalog for AI-generated 45° isometric 3D miniature dioramas.
// Zero real photographs — uses live Gemini Nano Banana 2.1 `/api/diorama` when enabled,
// falling back to pre-generated 3D diorama assets or clean atmospheric gradients.

const PROVINCE_LANDMARKS = {
  'Adana': { label: 'Taşköprü ve Seyhan' },
  'Adıyaman': { label: 'Nemrut Dağı' },
  'Afyonkarahisar': { label: 'Afyonkarahisar Kalesi' },
  'Ağrı': { label: 'İshak Paşa Sarayı' },
  'Amasya': { label: 'Yalıboyu Evleri ve Yeşilırmak' },
  'Ankara': { label: 'Anıtkabir' },
  'Antalya': { label: 'Antalya Kaleiçi ve Yivli Minare' },
  'Artvin': { label: 'Artvin Karagöl' },
  'Aydın': { label: 'Güvercinada' },
  'Balıkesir': { label: 'Balıkesir Saat Kulesi' },
  'Bilecik': { label: 'Şeyh Edebali Türbesi' },
  'Bingöl': { label: 'Bingöl Yüzen Adalar' },
  'Bitlis': { label: 'Nemrut Krater Gölü' },
  'Bolu': { label: 'Abant Gölü' },
  'Burdur': { label: 'Salda Gölü' },
  'Bursa': { label: 'Bursa Ulu Camii ve Uludağ' },
  'Çanakkale': { label: 'Çanakkale Şehitler Abidesi' },
  'Çankırı': { label: 'Çankırı Kalesi' },
  'Çorum': { label: 'Hattuşaş Aslanlı Kapı' },
  'Denizli': { label: 'Pamukkale Travertenleri' },
  'Diyarbakır': { label: 'On Gözlü Köprü ve Surlar' },
  'Edirne': { label: 'Selimiye Camii' },
  'Elazığ': { label: 'Harput Kalesi' },
  'Erzincan': { label: 'Girlevik Şelalesi' },
  'Erzurum': { label: 'Çifte Minareli Medrese' },
  'Eskişehir': { label: 'Porsuk Çayı ve Adalar' },
  'Gaziantep': { label: 'Gaziantep Kalesi' },
  'Giresun': { label: 'Giresun Kalesi ve Adası' },
  'Gümüşhane': { label: 'Karaca Mağarası ve Dağlar' },
  'Hakkari': { label: 'Cilo Dağları' },
  'Hatay': { label: 'Antakya ve Asi Nehri' },
  'Isparta': { label: 'Eğirdir Gölü ve Lavanta Bahçeleri' },
  'Mersin': { label: 'Kızkalesi' },
  'İstanbul': { label: 'Galata Kulesi ve Boğaziçi' },
  'İzmir': { label: 'İzmir Saat Kulesi' },
  'Kars': { label: 'Ani Ören Yeri' },
  'Kastamonu': { label: 'Kastamonu Kalesi ve Saat Kulesi' },
  'Kayseri': { label: 'Erciyes Dağı ve Kayseri Kalesi' },
  'Kırklareli': { label: 'İğneada Longoz Ormanları' },
  'Kırşehir': { label: 'Cacabey Medresesi' },
  'Kocaeli': { label: 'İzmit Saat Kulesi' },
  'Konya': { label: 'Mevlana Müzesi' },
  'Kütahya': { label: 'Kütahya Kalesi ve Çini Kule' },
  'Malatya': { label: 'Levent Vadisi' },
  'Manisa': { label: 'Spil Dağı ve Muradiye' },
  'Kahramanmaraş': { label: 'Kahramanmaraş Kalesi' },
  'Mardin': { label: 'Tarihi Mardin Taş Evleri' },
  'Muğla': { label: 'Ölüdeniz ve Muğla Kıyıları' },
  'Muş': { label: 'Tarihi Murat Köprüsü' },
  'Nevşehir': { label: 'Kapadokya Peri Bacaları ve Balonlar' },
  'Niğde': { label: 'Niğde Kalesi ve Saat Kulesi' },
  'Ordu': { label: 'Ordu Boztepe' },
  'Rize': { label: 'Ayder Yaylası' },
  'Sakarya': { label: 'Sapanca Gölü' },
  'Samsun': { label: 'Samsun Onur Anıtı' },
  'Siirt': { label: 'Siirt Botan Vadisi' },
  'Sinop': { label: 'Sinop Kalesi ve Liman' },
  'Sivas': { label: 'Divriği Ulu Camii' },
  'Tekirdağ': { label: 'Tekirdağ Sahili' },
  'Tokat': { label: 'Tokat Saat Kulesi ve Hıdırlık Köprüsü' },
  'Trabzon': { label: 'Sümela Manastırı' },
  'Tunceli': { label: 'Munzur Vadisi' },
  'Şanlıurfa': { label: 'Balıklıgöl' },
  'Uşak': { label: 'Ulubey Kanyonu' },
  'Van': { label: 'Akdamar Adası ve Van Gölü' },
  'Yozgat': { label: 'Yozgat Saat Kulesi' },
  'Zonguldak': { label: 'Zonguldak Fener ve Kıyılar' },
  'Aksaray': { label: 'Hasan Dağı ve Ihlara Vadisi' },
  'Bayburt': { label: 'Bayburt Kalesi' },
  'Karaman': { label: 'Karaman Kalesi' },
  'Kırıkkale': { label: 'Çeşnigir Köprüsü' },
  'Batman': { label: 'Hasankeyf' },
  'Şırnak': { label: 'Cudi Dağı' },
  'Bartın': { label: 'Amasra Yarımadası' },
  'Ardahan': { label: 'Çıldır Gölü' },
  'Iğdır': { label: 'Ağrı Dağı' },
  'Yalova': { label: 'Yürüyen Köşk' },
  'Karabük': { label: 'Safranbolu Evleri' },
  'Kilis': { label: 'Ravanda Kalesi' },
  'Osmaniye': { label: 'Karatepe-Aslantaş' },
  'Düzce': { label: 'Düzce ve Akçakoca Ceneviz Kalesi' }
};

const DISTRICT_LANDMARKS = {
  'İstanbul::Kadıköy': { label: 'Haydarpaşa Garı ve Kadıköy' },
  'İstanbul::Üsküdar': { label: 'Kız Kulesi ve Üsküdar' },
  'İstanbul::Beşiktaş': { label: 'Ortaköy Camii ve Boğaz Köprüsü' },
  'İstanbul::Fatih': { label: 'Ayasofya ve Tarihi Yarımada' },
  'İstanbul::Beyoğlu': { label: 'Galata Kulesi' },
  'İstanbul::Adalar': { label: 'Büyükada ve Faytonlu Sahil' },
  'İstanbul::Sarıyer': { label: 'Rumeli Hisarı' },
  'İstanbul::Eyüpsultan': { label: 'Eyüpsultan ve Pierre Loti' },
  'Muğla::Bodrum': { label: 'Bodrum Kalesi ve Yat Limanı' },
  'Muğla::Fethiye': { label: 'Ölüdeniz (Fethiye)' },
  'Muğla::Marmaris': { label: 'Marmaris Kalesi ve Koyu' },
  'Muğla::Datça': { label: 'Knidos ve Datça Yarımadası' },
  'Trabzon::Çaykara': { label: 'Uzungöl' },
  'Trabzon::Maçka': { label: 'Sümela Manastırı' },
  'Antalya::Alanya': { label: 'Alanya Kalesi ve Kızılkule' },
  'Antalya::Kaş': { label: 'Kaş Kıyıları ve Antik Tiyatro' },
  'Antalya::Manavgat': { label: 'Manavgat Şelalesi ve Side' },
  'Antalya::Kemer': { label: 'Kemer ve Olimpos Dağı' },
  'Nevşehir::Ürgüp': { label: 'Ürgüp Peri Bacaları' },
  'Nevşehir::Avanos': { label: 'Avanos ve Kızılırmak' },
  'İzmir::Selçuk': { label: 'Efes Antik Kenti' },
  'İzmir::Çeşme': { label: 'Çeşme Kalesi ve Alaçatı' },
  'İzmir::Foça': { label: 'Foça Sahili ve Yel Değirmenleri' },
  'İzmir::Urla': { label: 'Urla İskelesi ve Bağlar' },
  'İzmir::Bergama': { label: 'Bergama Akropolü' },
  'Denizli::Pamukkale': { label: 'Pamukkale Travertenleri' },
  'Karabük::Safranbolu': { label: 'Safranbolu Tarihi Evleri' },
  'Mersin::Silifke': { label: 'Silifke Kalesi ve Kızkalesi' },
  'Mersin::Tarsus': { label: 'Tarsus Şelalesi' },
  'Şanlıurfa::Halfeti': { label: 'Batık Şehir Halfeti' },
  'Van::Gevaş': { label: 'Akdamar Adası' },
  'Rize::Çamlıhemşin': { label: 'Zilkale ve Fırtına Vadisi' },
  'Aydın::Kuşadası': { label: 'Kuşadası Güvercinada' },
  'Aydın::Didim': { label: 'Didim Apollon Tapınağı' },
  'Balıkesir::Ayvalık': { label: 'Ayvalık ve Cunda Adası' },
  'Çanakkale::Eceabat': { label: 'Gelibolu Şehitler Abidesi' },
  'Çanakkale::Bozcaada': { label: 'Bozcaada Kalesi' },
  'Çanakkale::Gökçeada': { label: 'Gökçeada Kayalıkları' },
  'Kocaeli::Gebze': { label: 'Osmangazi Köprüsü ve Eskihisar Kalesi' },
  'Niğde::Çamardı': { label: 'Aladağlar Zirveleri (Çamardı)' },
  'Erzurum::Palandöken': { label: 'Palandöken Kayak Zirvesi' },
  'Kars::Sarıkamış': { label: 'Sarıkamış Çam Ormanları' },
  'Bursa::Mudanya': { label: 'Mudanya Sahili' },
  'Bursa::İznik': { label: 'İznik Gölü ve Surları' },
  'Amasya::Merzifon': { label: 'Merzifon Kara Mustafa Paşa Camii' },
  'Bartın::Amasra': { label: 'Amasra Kalesi ve Kemere Köprüsü' },
  'Artvin::Borçka': { label: 'Borçka Karagöl' },
  'Mardin::Midyat': { label: 'Midyat Taş Konakları' },
  'Adıyaman::Kahta': { label: 'Nemrut Dağı (Kahta)' },
  'Ağrı::Doğubayazıt': { label: 'İshak Paşa Sarayı' },
  'Bolu::Mudurnu': { label: 'Mudurnu Tarihi Evleri ve Saat Kulesi' }
};

const PREGENERATED_DIORAMAS = {
  'İzmir': './dioramas/izmir.webp',
  'İstanbul': './dioramas/istanbul.webp',
  'Niğde': './dioramas/nigde.webp'
};

const DIORAMA_BLOB_CACHE = new Map();

function resolveLandmarkInfo(provinceName, districtName) {
  if (!provinceName) return { key: '', label: '', isDistrictSpecific: false };
  const distClean = districtName && districtName !== '__MERKEZ__' ? districtName : null;
  const distKey = distClean ? `${provinceName}::${distClean}` : null;

  if (distKey && DISTRICT_LANDMARKS[distKey]) {
    return {
      key: distKey,
      label: DISTRICT_LANDMARKS[distKey].label,
      isDistrictSpecific: true
    };
  }
  const provEntry = PROVINCE_LANDMARKS[provinceName];
  return {
    key: `${provinceName}::__MERKEZ__`,
    label: provEntry ? provEntry.label : provinceName,
    isDistrictSpecific: false
  };
}

async function fetchAIDiorama(provinceName, districtName, atmosphere, apiBase) {
  if (!provinceName) return null;
  const info = resolveLandmarkInfo(provinceName, districtName);
  const atmo = atmosphere || 'partly';
  const memKey = `${info.key}::${atmo}`;

  if (DIORAMA_BLOB_CACHE.has(memKey)) {
    return DIORAMA_BLOB_CACHE.get(memKey);
  }

  // 1. Try live Gemini AI Diorama endpoint on Cloud Run / local backend
  if (apiBase) {
    try {
      const qs = new URLSearchParams({
        province: provinceName,
        landmark: info.label,
        atmosphere: atmo
      });
      if (districtName && districtName !== '__MERKEZ__') {
        qs.set('district', districtName);
      }
      const resp = await fetch(`${apiBase}/api/diorama?${qs.toString()}`);
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const res = { url, label: info.label, isLiveAI: true };
        DIORAMA_BLOB_CACHE.set(memKey, res);
        return res;
      }
    } catch {}
  }

  // 2. Fallback to pre-generated 3D isometric AI showcase dioramas (district -> province fallback)
  if (PREGENERATED_DIORAMAS[provinceName]) {
    const provLabel = PROVINCE_LANDMARKS[provinceName]?.label || info.label;
    const res = {
      url: PREGENERATED_DIORAMAS[provinceName],
      label: info.isDistrictSpecific ? `${provLabel} (${provinceName})` : provLabel,
      isLiveAI: false
    };
    DIORAMA_BLOB_CACHE.set(memKey, res);
    return res;
  }

  // 3. No real photo fallback — keep minimalist atmospheric backdrop cleanly
  return null;
}
