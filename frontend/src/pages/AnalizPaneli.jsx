/**
 * AnalizPaneli Sayfasi
 * =====================
 * Profesyonel isletme analytics dashboard.
 * Tum yeni bilesenler, filtreler, export ve modal destegi.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  analizOzetGetir,
  saatlikZiyaretGetir,
  sonOturumlarGetir,
  canliAnalizGetir,
  dunOzetGetir,
  saatlikDuyguTrendGetir,
  filtreSeceneklerGetir,
} from '../api';

import DashboardKartlari from '../components/DashboardKartlari';
import DuyguDagilimi from '../components/DuyguDagilimi';
import SaatlikGrafik from '../components/SaatlikGrafik';
import OturumTablosu from '../components/OturumTablosu';
import CanliOturumlar from '../components/CanliOturumlar';
import MemnuniyetSkoru from '../components/MemnuniyetSkoru';
import SaatlikDuyguTrendi from '../components/SaatlikDuyguTrendi';
import EnYogunSaat from '../components/EnYogunSaat';
import OturumDetayModal from '../components/OturumDetayModal';
import AkilliUyarilar from '../components/AkilliUyarilar';
import GunlukOzet from '../components/GunlukOzet';
import VeriKalitesi from '../components/VeriKalitesi';
import GizlilikPaneli from '../components/GizlilikPaneli';

const POLLING_ARALIGI_MS = 10000;

export default function AnalizPaneli() {
  // ─── State ───
  const [ozet, setOzet] = useState(null);
  const [dunOzet, setDunOzet] = useState(null);
  const [saatlikVeri, setSaatlikVeri] = useState(null);
  const [saatlikDuyguTrend, setSaatlikDuyguTrend] = useState(null);
  const [sonOturumlar, setSonOturumlar] = useState([]);
  const [canliOturumlar, setCanliOturumlar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [secilenTarih, setSecilenTarih] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [otomatikYenile, setOtomatikYenile] = useState(true);
  const [sonGuncelleme, setSonGuncelleme] = useState(null);

  // ─── Filtre state ───
  const [subeler, setSubeler] = useState([]);
  const [kameralar, setKameralar] = useState([]);
  const [secilenSube, setSecilenSube] = useState('');
  const [secilenKamera, setSecilenKamera] = useState('');

  // ─── Modal state ───
  const [detayOturum, setDetayOturum] = useState(null);

  const pollingRef = useRef(null);

  // ─── Filtreleri yükle (bir kez) ───
  useEffect(() => {
    filtreSeceneklerGetir().then(veri => {
      if (veri) {
        setSubeler(veri.branches || []);
        setKameralar(veri.cameras || []);
      }
    });
  }, []);

  // ─── Seçili kamera ID ───
  const kameraId = secilenKamera || null;

  /**
   * Tum verileri tek seferde cek
   */
  const verileriGetir = useCallback(async (sessiz = false) => {
    if (!sessiz) setYukleniyor(true);
    setHata(null);

    try {
      const [ozetVeri, dunVeri, saatlikVeriler, duyguTrend, oturumVerisi, canliVeri] =
        await Promise.all([
          analizOzetGetir(secilenTarih, kameraId),
          dunOzetGetir(kameraId),
          saatlikZiyaretGetir(secilenTarih, kameraId),
          saatlikDuyguTrendGetir(secilenTarih, kameraId),
          sonOturumlarGetir(30, kameraId),
          canliAnalizGetir(kameraId),
        ]);

      if (ozetVeri) setOzet(ozetVeri);
      if (dunVeri) setDunOzet(dunVeri);
      if (saatlikVeriler) setSaatlikVeri(saatlikVeriler);
      if (duyguTrend) setSaatlikDuyguTrend(duyguTrend);
      if (oturumVerisi) setSonOturumlar(oturumVerisi);
      if (canliVeri) setCanliOturumlar(canliVeri.active_sessions || []);

      setSonGuncelleme(new Date());
    } catch (e) {
      setHata('Veriler alınırken hata oluştu. Backend çalışıyor mu?');
      console.error('[Dashboard] Hata:', e);
    } finally {
      setYukleniyor(false);
    }
  }, [secilenTarih, kameraId]);

  // ─── İlk yükleme ve tarih/kamera değişiminde ───
  useEffect(() => {
    verileriGetir();
  }, [verileriGetir]);

  // ─── Otomatik yenileme (polling) ───
  useEffect(() => {
    if (otomatikYenile) {
      pollingRef.current = setInterval(() => {
        verileriGetir(true);
      }, POLLING_ARALIGI_MS);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [otomatikYenile, verileriGetir]);

  // ─── Şubeye göre kameraları filtrele ───
  const filtrelenmisKameralar = secilenSube
    ? kameralar.filter(k => String(k.branch_id) === String(secilenSube))
    : kameralar;

  // ─── Export fonksiyonları ───
  const csvExport = () => {
    if (!sonOturumlar || sonOturumlar.length === 0) return;

    const basliklar = [
      'Session ID', 'Takip Kimliği', 'Kamera ID', 'Başlangıç', 'Bitiş',
      'Süre (s)', 'Baskın Duygu', 'Ort. Güven', 'Toplam Tespit', 'Durum'
    ];

    const satirlar = sonOturumlar.map(o => [
      o.id,
      o.tracked_face_id || '',
      o.camera_id,
      o.start_time || '',
      o.end_time || '',
      o.duration_seconds ?? '',
      o.dominant_emotion || '',
      o.average_confidence != null ? Math.round(o.average_confidence * 100) : '',
      o.total_detections ?? '',
      o.session_status || '',
    ].join(','));

    const csv = [basliklar.join(','), ...satirlar].join('\n');
    dosyaIndir(csv, 'oturumlar.csv', 'text/csv');
  };

  const jsonExport = () => {
    if (!sonOturumlar || sonOturumlar.length === 0) return;
    const json = JSON.stringify(sonOturumlar, null, 2);
    dosyaIndir(json, 'oturumlar.json', 'application/json');
  };

  function dosyaIndir(icerik, dosyaAdi, tip) {
    const blob = new Blob([icerik], { type: tip });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = dosyaAdi;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  // ─── Bugünün tarihi ───
  const bugunTarih = new Date().toISOString().split('T')[0];

  return (
    <div className="analiz-paneli-sayfa">
      {/* ─── Üst bar: Filtreler ─── */}
      <div className="analiz-ust-bar">
        <div className="analiz-baslik">
          <h2>📈 Analiz Paneli</h2>
          <span className="analiz-alt-baslik">
            İşletme müşteri deneyimi analiz dashboard'u
          </span>
        </div>

        <div className="analiz-filtreler">
          {/* Tarih */}
          <div className="filtre-grubu">
            <label htmlFor="tarih-secici">📅 Tarih:</label>
            <input
              id="tarih-secici"
              type="date"
              value={secilenTarih}
              onChange={(e) => setSecilenTarih(e.target.value)}
              max={bugunTarih}
              className="tarih-input"
            />
          </div>

          {/* Şube */}
          {subeler.length > 0 && (
            <div className="filtre-grubu">
              <label htmlFor="sube-secici">🏢 Şube:</label>
              <select
                id="sube-secici"
                className="filtre-select"
                value={secilenSube}
                onChange={(e) => {
                  setSecilenSube(e.target.value);
                  setSecilenKamera('');
                }}
              >
                <option value="">Tümü</option>
                {subeler.map(s => (
                  <option key={s.id} value={s.id}>
                    {s.name} {s.city ? `(${s.city})` : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Kamera */}
          {filtrelenmisKameralar.length > 0 && (
            <div className="filtre-grubu">
              <label htmlFor="kamera-secici">📷 Kamera:</label>
              <select
                id="kamera-secici"
                className="filtre-select"
                value={secilenKamera}
                onChange={(e) => setSecilenKamera(e.target.value)}
              >
                <option value="">Tümü</option>
                {filtrelenmisKameralar.map(k => (
                  <option key={k.id} value={k.id}>
                    {k.camera_name} ({k.camera_code})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Otomatik yenileme */}
          <button
            className={`oto-yenile-btn ${otomatikYenile ? 'aktif' : ''}`}
            onClick={() => setOtomatikYenile(!otomatikYenile)}
            title={otomatikYenile ? 'Otomatik yenileme açık' : 'Otomatik yenileme kapalı'}
          >
            {otomatikYenile ? '🔄 Otomatik' : '⏸️ Duraklatıldı'}
          </button>

          {/* Manuel yenile */}
          <button
            className="yenile-btn"
            onClick={() => verileriGetir()}
            disabled={yukleniyor}
          >
            🔃 Yenile
          </button>

          {/* Son güncelleme */}
          {sonGuncelleme && (
            <span className="son-guncelleme">
              Son: {sonGuncelleme.toLocaleTimeString('tr-TR')}
            </span>
          )}
        </div>
      </div>

      {/* ─── Hata mesajı ─── */}
      {hata && (
        <div className="hata-mesaji">
          ⚠️ {hata}
        </div>
      )}

      {/* ─── İçerik ─── */}
      <div className="analiz-icerik">
        {/* KPI Kartları (6 adet) */}
        <DashboardKartlari
          ozet={yukleniyor && !ozet ? null : ozet}
          dunOzet={dunOzet}
        />

        {/* Grafikler satırı: Duygu Dağılımı + Saatlik Yoğunluk */}
        <div className="analiz-grafik-satiri">
          <DuyguDagilimi dagilim={ozet?.emotion_distribution} />
          <SaatlikGrafik saatlikVeri={saatlikVeri} />
        </div>

        {/* Grafikler satırı 2: Saatlik Duygu Trendi + Insight kartları */}
        <div className="analiz-grafik-satiri">
          <SaatlikDuyguTrendi trendVeri={saatlikDuyguTrend} />
          <div className="analiz-insight-kolon">
            <MemnuniyetSkoru dagilim={ozet?.emotion_distribution} />
            <EnYogunSaat
              saatlikVeri={saatlikVeri}
              dagilim={ozet?.emotion_distribution}
            />
          </div>
        </div>

        {/* Uyarılar + Günlük Özet satırı */}
        <div className="analiz-grafik-satiri">
          <AkilliUyarilar ozet={ozet} oturumlar={sonOturumlar} />
          <GunlukOzet ozet={ozet} saatlikVeri={saatlikVeri} />
        </div>

        {/* Canlı Oturumlar */}
        <CanliOturumlar oturumlar={canliOturumlar} />

        {/* Son Oturumlar Tablosu + Export */}
        <OturumTablosu
          oturumlar={sonOturumlar}
          onDetayAc={setDetayOturum}
          onExportCSV={csvExport}
          onExportJSON={jsonExport}
        />

        {/* Alt bilgi satırı: Veri Kalitesi + Gizlilik */}
        <div className="analiz-grafik-satiri">
          <VeriKalitesi ozet={ozet} oturumlar={sonOturumlar} />
          <GizlilikPaneli />
        </div>
      </div>

      {/* ─── Oturum Detay Modalı ─── */}
      <OturumDetayModal
        oturum={detayOturum}
        onKapat={() => setDetayOturum(null)}
      />
    </div>
  );
}
