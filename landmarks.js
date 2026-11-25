// Curated iconic landmark mapping for all 81 Turkish provinces & 45+ iconic districts.
// Photos are fetched dynamically with CORS support via Turkish Wikipedia Action API (pageimages).

const PROVINCE_LANDMARKS = {
  'Adana': { page: 'Taşköprü (Adana)', label: 'Taşköprü ve Seyhan' },
  'Adıyaman': { page: 'Nemrut Dağı', label: 'Nemrut Dağı' },
  'Afyonkarahisar': { page: 'Afyonkarahisar Kalesi', label: 'Afyonkarahisar Kalesi' },
  'Ağrı': { page: 'İshak Paşa Sarayı', label: 'İshak Paşa Sarayı' },
  'Amasya': { page: 'Yalıboyu Evleri', label: 'Yalıboyu Evleri ve Yeşilırmak' },
  'Ankara': { page: 'Anıtkabir', label: 'Anıtkabir' },
  'Antalya': { page: 'Kaleiçi', label: 'Antalya Kaleiçi' },
  'Artvin': { page: 'Karagöl (Borçka)', label: 'Artvin Karagöl' },
  'Aydın': { page: 'Güvercinada', label: 'Güvercinada' },
  'Balıkesir': { page: 'Balıkesir Saat Kulesi', label: 'Balıkesir Saat Kulesi' },
  'Bilecik': { page: 'Şeyh Edebali Türbesi', label: 'Şeyh Edebali Türbesi' },
  'Bingöl': { page: 'Yüzen Ada (Bingöl)', label: 'Bingöl Yüzen Adalar' },
  'Bitlis': { page: 'Nemrut Krater Gölü', label: 'Nemrut Krater Gölü' },
  'Bolu': { page: 'Abant Gölü', label: 'Abant Gölü' },
  'Burdur': { page: 'Salda Gölü', label: 'Salda Gölü' },
  'Bursa': { page: 'Bursa Ulu Camii', label: 'Bursa Ulu Camii ve Uludağ' },
  'Çanakkale': { page: 'Çanakkale Şehitleri Anıtı', label: 'Çanakkale Şehitler Abidesi' },
  'Çankırı': { page: 'Çankırı Kalesi', label: 'Çankırı Kalesi' },
  'Çorum': { page: 'Hattuşaş', label: 'Hattuşaş' },
  'Denizli': { page: 'Pamukkale', label: 'Pamukkale Travertenleri' },
  'Diyarbakır': { page: 'On Gözlü Köprü', label: 'On Gözlü Köprü ve Surlar' },
  'Edirne': { page: 'Selimiye Camii', label: 'Selimiye Camii' },
  'Elazığ': { page: 'Harput Kalesi', label: 'Harput Kalesi' },
  'Erzincan': { page: 'Girlevik Şelalesi', label: 'Girlevik Şelalesi' },
  'Erzurum': { page: 'Çifte Minareli Medrese', label: 'Çifte Minareli Medrese' },
  'Eskişehir': { page: 'Porsuk Çayı', label: 'Porsuk Çayı ve Adalar' },
  'Gaziantep': { page: 'Gaziantep Kalesi', label: 'Gaziantep Kalesi' },
  'Giresun': { page: 'Giresun Kalesi', label: 'Giresun Kalesi ve Adası' },
  'Gümüşhane': { page: 'Karaca Mağarası', label: 'Karaca Mağarası' },
  'Hakkari': { page: 'Cilo Dağı', label: 'Cilo Dağları' },
  'Hatay': { page: 'Antakya', label: 'Antakya ve Asi Nehri' },
  'Isparta': { page: 'Eğirdir Gölü', label: 'Eğirdir Gölü' },
  'Mersin': { page: 'Kızkalesi', label: 'Kızkalesi' },
  'İstanbul': { page: 'Galata Kulesi', label: 'Galata Kulesi' },
  'İzmir': { page: 'İzmir Saat Kulesi', label: 'İzmir Saat Kulesi' },
  'Kars': { page: 'Ani Harabeleri', label: 'Ani Ören Yeri' },
  'Kastamonu': { page: 'Kastamonu Kalesi', label: 'Kastamonu Kalesi' },
  'Kayseri': { page: 'Erciyes Dağı', label: 'Erciyes Dağı' },
  'Kırklareli': { page: 'İğneada Longoz Ormanları', label: 'İğneada Longoz Ormanları' },
  'Kırşehir': { page: 'Cacabey Medresesi', label: 'Cacabey Medresesi' },
  'Kocaeli': { page: 'İzmit Saat Kulesi', label: 'İzmit Saat Kulesi' },
  'Konya': { page: 'Mevlana Müzesi', label: 'Mevlana Müzesi' },
  'Kütahya': { page: 'Kütahya Kalesi', label: 'Kütahya Kalesi' },
  'Malatya': { page: 'Levent Vadisi', label: 'Levent Vadisi' },
  'Manisa': { page: 'Spil Dağı', label: 'Spil Dağı' },
  'Kahramanmaraş': { page: 'Kahramanmaraş Kalesi', label: 'Kahramanmaraş Kalesi' },
  'Mardin': { page: 'Mardin', label: 'Tarihi Mardin Taş Evleri' },
  'Muğla': { page: 'Ölüdeniz', label: 'Ölüdeniz ve Muğla Kıyıları' },
  'Muş': { page: 'Murat Köprüsü', label: 'Tarihi Murat Köprüsü' },
  'Nevşehir': { page: 'Kapadokya', label: 'Kapadokya Peri Bacaları' },
  'Niğde': { page: 'Niğde Kalesi', label: 'Niğde Kalesi ve Saat Kulesi' },
  'Ordu': { page: 'Boztepe (Ordu)', label: 'Ordu Boztepe' },
  'Rize': { page: 'Ayder Yaylası', label: 'Ayder Yaylası' },
  'Sakarya': { page: 'Sapanca Gölü', label: 'Sapanca Gölü' },
  'Samsun': { page: 'Onur Anıtı', label: 'Samsun Onur Anıtı' },
  'Siirt': { page: 'Veysel Karani Türbesi', label: 'Siirt Botan Vadisi' },
  'Sinop': { page: 'Sinop Kalesi', label: 'Sinop Kalesi ve Liman' },
  'Sivas': { page: 'Sivas Divriği Ulu Camii ve Darüşşifası', label: 'Divriği Ulu Camii' },
  'Tekirdağ': { page: 'Tekirdağ', label: 'Tekirdağ Sahili' },
  'Tokat': { page: 'Tokat Saat Kulesi', label: 'Tokat Saat Kulesi' },
  'Trabzon': { page: 'Sümela Manastırı', label: 'Sümela Manastırı' },
  'Tunceli': { page: 'Munzur Vadisi Milli Parkı', label: 'Munzur Vadisi' },
  'Şanlıurfa': { page: 'Balıklıgöl', label: 'Balıklıgöl' },
  'Uşak': { page: 'Ulubey Kanyonu', label: 'Ulubey Kanyonu' },
  'Van': { page: 'Akdamar Adası', label: 'Akdamar Adası ve Van Gölü' },
  'Yozgat': { page: 'Yozgat Saat Kulesi', label: 'Yozgat Saat Kulesi' },
  'Zonguldak': { page: 'Gökgöl Mağarası', label: 'Zonguldak Kıyıları' },
  'Aksaray': { page: 'Hasan Dağı', label: 'Hasan Dağı' },
  'Bayburt': { page: 'Bayburt Kalesi', label: 'Bayburt Kalesi' },
  'Karaman': { page: 'Karaman Kalesi', label: 'Karaman Kalesi' },
  'Kırıkkale': { page: 'Çeşnigir Köprüsü', label: 'Çeşnigir Köprüsü' },
  'Batman': { page: 'Hasankeyf', label: 'Hasankeyf' },
  'Şırnak': { page: 'Cudi Dağı', label: 'Cudi Dağı' },
  'Bartın': { page: 'Amasra', label: 'Amasra Yarımadası' },
  'Ardahan': { page: 'Çıldır Gölü', label: 'Çıldır Gölü' },
  'Iğdır': { page: 'Ağrı Dağı', label: 'Ağrı Dağı' },
  'Yalova': { page: 'Yürüyen Köşk', label: 'Yürüyen Köşk' },
  'Karabük': { page: 'Safranbolu', label: 'Safranbolu Evleri' },
  'Kilis': { page: 'Ravanda Kalesi', label: 'Ravanda Kalesi' },
  'Osmaniye': { page: 'Karatepe-Aslantaş', label: 'Karatepe-Aslantaş' },
  'Düzce': { page: 'Akçakoca', label: 'Düzce ve Akçakoca' }
};

const DISTRICT_LANDMARKS = {
  'İstanbul::Kadıköy': { page: 'Haydarpaşa Garı', label: 'Haydarpaşa ve Kadıköy' },
  'İstanbul::Üsküdar': { page: 'Kız Kulesi', label: 'Kız Kulesi ve Üsküdar' },
  'İstanbul::Beşiktaş': { page: 'Ortaköy Camii', label: 'Ortaköy ve Boğaziçi' },
  'İstanbul::Fatih': { page: 'Ayasofya', label: 'Ayasofya ve Tarihi Yarımada' },
  'İstanbul::Beyoğlu': { page: 'Galata Kulesi', label: 'Galata Kulesi' },
  'İstanbul::Adalar': { page: 'Büyükada', label: 'Prens Adaları' },
  'İstanbul::Sarıyer': { page: 'Rumeli Hisarı', label: 'Rumeli Hisarı' },
  'İstanbul::Eyüpsultan': { page: 'Eyüp Sultan Camii', label: 'Eyüpsultan ve Haliç' },
  'Muğla::Bodrum': { page: 'Bodrum Kalesi', label: 'Bodrum Kalesi' },
  'Muğla::Fethiye': { page: 'Ölüdeniz', label: 'Ölüdeniz (Fethiye)' },
  'Muğla::Marmaris': { page: 'Marmaris Kalesi', label: 'Marmaris Koyu' },
  'Muğla::Datça': { page: 'Knidos', label: 'Knidos ve Datça' },
  'Trabzon::Çaykara': { page: 'Uzungöl', label: 'Uzungöl' },
  'Trabzon::Maçka': { page: 'Sümela Manastırı', label: 'Sümela Manastırı' },
  'Antalya::Alanya': { page: 'Alanya Kalesi', label: 'Alanya Kalesi' },
  'Antalya::Kaş': { page: 'Kaş, Antalya', label: 'Kaş Kıyıları' },
  'Antalya::Manavgat': { page: 'Manavgat Şelalesi', label: 'Manavgat ve Side' },
  'Antalya::Kemer': { page: 'Olimpos, Kemer', label: 'Kemer ve Olimpos' },
  'Nevşehir::Ürgüp': { page: 'Ürgüp', label: 'Ürgüp Peri Bacaları' },
  'Nevşehir::Avanos': { page: 'Avanos', label: 'Avanos ve Kızılırmak' },
  'İzmir::Selçuk': { page: 'Efes', label: 'Efes Antik Kenti' },
  'İzmir::Çeşme': { page: 'Çeşme Kalesi', label: 'Çeşme Kalesi' },
  'İzmir::Foça': { page: 'Foça', label: 'Foça Sahili' },
  'İzmir::Urla': { page: 'Urla', label: 'Urla Yarımadası' },
  'İzmir::Bergama': { page: 'Pergamon', label: 'Bergama Akropolü' },
  'Denizli::Pamukkale': { page: 'Pamukkale', label: 'Pamukkale Travertenleri' },
  'Karabük::Safranbolu': { page: 'Safranbolu', label: 'Safranbolu Evleri' },
  'Mersin::Silifke': { page: 'Cennet ve Cehennem Obrukları', label: 'Silifke ve Kızkalesi' },
  'Mersin::Tarsus': { page: 'Tarsus Şelalesi', label: 'Tarsus Şelalesi' },
  'Şanlıurfa::Halfeti': { page: 'Halfeti', label: 'Batık Şehir Halfeti' },
  'Van::Gevaş': { page: 'Akdamar Adası', label: 'Akdamar Adası' },
  'Rize::Çamlıhemşin': { page: 'Zilkale', label: 'Zilkale ve Fırtına Vadisi' },
  'Aydın::Kuşadası': { page: 'Güvercinada', label: 'Kuşadası Güvercinada' },
  'Aydın::Didim': { page: 'Apollon Tapınağı (Didim)', label: 'Didim Apollon Tapınağı' },
  'Balıkesir::Ayvalık': { page: 'Cunda Adası', label: 'Ayvalık ve Cunda' },
  'Çanakkale::Eceabat': { page: 'Çanakkale Şehitleri Anıtı', label: 'Gelibolu Şehitler Abidesi' },
  'Çanakkale::Bozcaada': { page: 'Bozcaada', label: 'Bozcaada Kalesi' },
  'Çanakkale::Gökçeada': { page: 'Gökçeada', label: 'Gökçeada' },
  'Kocaeli::Gebze': { page: 'Osmangazi Köprüsü', label: 'Osmangazi Köprüsü' },
  'Niğde::Çamardı': { page: 'Aladağlar', label: 'Aladağlar (Çamardı)' },
  'Erzurum::Palandöken': { page: 'Palandöken Dağı', label: 'Palandöken' },
  'Kars::Sarıkamış': { page: 'Sarıkamış', label: 'Sarıkamış' },
  'Bursa::Mudanya': { page: 'Mudanya', label: 'Mudanya Sahili' },
  'Bursa::İznik': { page: 'İznik Gölü', label: 'İznik Gölü ve Surları' },
  'Amasya::Merzifon': { page: 'Merzifon', label: 'Merzifon' },
  'Bartın::Amasra': { page: 'Amasra', label: 'Amasra Kalesi' },
  'Artvin::Borçka': { page: 'Karagöl (Borçka)', label: 'Borçka Karagöl' },
  'Mardin::Midyat': { page: 'Midyat', label: 'Midyat Taş Konakları' },
  'Adıyaman::Kahta': { page: 'Nemrut Dağı', label: 'Nemrut Dağı (Kahta)' },
  'Ağrı::Doğubayazıt': { page: 'İshak Paşa Sarayı', label: 'İshak Paşa Sarayı' },
  'Bolu::Mudurnu': { page: 'Mudurnu', label: 'Mudurnu Tarihi Evleri' }
};

const LANDMARK_MEM_CACHE = new Map();
const LANDMARK_STORAGE_KEY = 'hava_landmark_cache_v1';

function readLandmarkStorage() {
  try {
    return JSON.parse(localStorage.getItem(LANDMARK_STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function writeLandmarkStorage(key, val) {
  try {
    const store = readLandmarkStorage();
    const keys = Object.keys(store);
    if (keys.length > 60) delete store[keys[0]];
    store[key] = val;
    localStorage.setItem(LANDMARK_STORAGE_KEY, JSON.stringify(store));
  } catch {}
}

async function queryWikipediaThumb(pageTitle) {
  const url = `https://tr.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(pageTitle)}&prop=pageimages&piprop=thumbnail&pithumbsize=1200&redirects=1&format=json&origin=*`;
  const resp = await fetch(url);
  if (!resp.ok) return null;
  const json = await resp.json();
  const pages = json?.query?.pages || {};
  for (const page of Object.values(pages)) {
    if (page?.thumbnail?.source) {
      return page.thumbnail.source;
    }
  }
  return null;
}

async function fetchLandmarkPhoto(provinceName, districtName) {
  if (!provinceName) return null;
  const distClean = districtName && districtName !== '__MERKEZ__' ? districtName : null;
  const cacheKey = `${provinceName}::${distClean || '__MERKEZ__'}`;

  if (LANDMARK_MEM_CACHE.has(cacheKey)) {
    return LANDMARK_MEM_CACHE.get(cacheKey);
  }

  const stored = readLandmarkStorage()[cacheKey];
  if (stored && stored.url) {
    LANDMARK_MEM_CACHE.set(cacheKey, stored);
    return stored;
  }

  const candidates = [];
  if (distClean && DISTRICT_LANDMARKS[cacheKey]) {
    candidates.push(DISTRICT_LANDMARKS[cacheKey]);
  }
  if (PROVINCE_LANDMARKS[provinceName]) {
    candidates.push(PROVINCE_LANDMARKS[provinceName]);
  }
  candidates.push({ page: provinceName, label: provinceName });

  // Deduplicate by page
  const seen = new Set();
  for (const cand of candidates) {
    if (!cand || seen.has(cand.page)) continue;
    seen.add(cand.page);
    try {
      const thumbUrl = await queryWikipediaThumb(cand.page);
      if (thumbUrl) {
        const result = { url: thumbUrl, label: cand.label };
        LANDMARK_MEM_CACHE.set(cacheKey, result);
        writeLandmarkStorage(cacheKey, result);
        return result;
      }
    } catch {}
  }

  return null;
}
