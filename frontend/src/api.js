/**
 * API Servis Katmani
 * ====================
 * Tum backend REST cagrilari tek dosyada toplanir.
 * Her fonksiyon async/await ile calisiyor ve hata durumunda null dondurur.
 */

const API_URL = 'http://localhost:8000';

/**
 * Model listesini getir
 */
export async function modellerGetir() {
  try {
    const yanit = await fetch(`${API_URL}/models`);
    const veri = await yanit.json();
    return veri.models || [];
  } catch (hata) {
    console.error('[API] Model listesi alinamadi:', hata);
    return [];
  }
}

/**
 * Analiz ozet bilgilerini getir
 * @param {string|null} tarih — YYYY-MM-DD formatinda (null = bugun)
 * @param {number|null} kameraId — Kamera DB id
 */
export async function analizOzetGetir(tarih = null, kameraId = null) {
  try {
    const params = new URLSearchParams();
    if (tarih) params.set('target_date', tarih);
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/overview?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Analiz ozeti alinamadi:', hata);
    return null;
  }
}

/**
 * Saatlik ziyaret verilerini getir
 */
export async function saatlikZiyaretGetir(tarih = null, kameraId = null) {
  try {
    const params = new URLSearchParams();
    if (tarih) params.set('target_date', tarih);
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/hourly-visits?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Saatlik veriler alinamadi:', hata);
    return null;
  }
}

/**
 * Son oturumlar listesini getir
 */
export async function sonOturumlarGetir(limit = 20, kameraId = null) {
  try {
    const params = new URLSearchParams();
    params.set('limit', limit);
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/recent-sessions?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Son oturumlar alinamadi:', hata);
    return [];
  }
}

/**
 * Canli analiz verilerini getir
 */
export async function canliAnalizGetir(kameraId = null) {
  try {
    const params = new URLSearchParams();
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/live?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Canli analiz alinamadi:', hata);
    return null;
  }
}

/**
 * Saglik kontrolu
 */
export async function saglikKontrolGetir() {
  try {
    const yanit = await fetch(`${API_URL}/health`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Saglik kontrolu basarisiz:', hata);
    return null;
  }
}

/**
 * Dunku ozet verilerini getir (karsilastirma icin)
 */
export async function dunOzetGetir(kameraId = null) {
  try {
    const params = new URLSearchParams();
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/compare-yesterday?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Dun ozet alinamadi:', hata);
    return null;
  }
}

/**
 * Saatlik duygu trendi verilerini getir
 */
export async function saatlikDuyguTrendGetir(tarih = null, kameraId = null) {
  try {
    const params = new URLSearchParams();
    if (tarih) params.set('target_date', tarih);
    if (kameraId) params.set('camera_id', kameraId);

    const yanit = await fetch(`${API_URL}/analytics/emotion-hourly-trend?${params}`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Saatlik duygu trendi alinamadi:', hata);
    return null;
  }
}

/**
 * Filtre seceneklerini getir (sube + kamera listesi)
 */
export async function filtreSeceneklerGetir() {
  try {
    const yanit = await fetch(`${API_URL}/analytics/filters`);
    return await yanit.json();
  } catch (hata) {
    console.error('[API] Filtre secenekleri alinamadi:', hata);
    return { branches: [], cameras: [] };
  }
}
