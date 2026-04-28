/**
 * AnalizPaneli Sayfasi
 * =====================
 * Isletme dashboard sayfasi.
 * API endpointlerinden veri ceker ve grafik/tablo olarak gosterir.
 * Polling ile otomatik yenileme destegi.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  analizOzetGetir,
  saatlikZiyaretGetir,
  sonOturumlarGetir,
  canliAnalizGetir,
} from '../api';

import DashboardKartlari from '../components/DashboardKartlari';
import DuyguDagilimi from '../components/DuyguDagilimi';
import SaatlikGrafik from '../components/SaatlikGrafik';
import OturumTablosu from '../components/OturumTablosu';
import CanliOturumlar from '../components/CanliOturumlar';

const POLLING_ARALIGI_MS = 10000; // 10 saniye

export default function AnalizPaneli() {
  // ─── State ───
  const [ozet, setOzet] = useState(null);
  const [saatlikVeri, setSaatlikVeri] = useState(null);
  const [sonOturumlar, setSonOturumlar] = useState([]);
  const [canliOturumlar, setCanliOturumlar] = useState([]);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState(null);
  const [secilenTarih, setSecilenTarih] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [otomatikYenile, setOtomatikYenile] = useState(true);
  const [sonGuncelleme, setSonGuncelleme] = useState(null);

  const pollingRef = useRef(null);

  /**
   * Tum verileri tek seferde cek
   */
  const verileriGetir = useCallback(async (sessiz = false) => {
    if (!sessiz) setYukleniyor(true);
    setHata(null);

    try {
      const [ozetVeri, saatlikVeriler, oturumVerisi, canliVeri] = await Promise.all([
        analizOzetGetir(secilenTarih),
        saatlikZiyaretGetir(secilenTarih),
        sonOturumlarGetir(20),
        canliAnalizGetir(),
      ]);

      if (ozetVeri) setOzet(ozetVeri);
      if (saatlikVeriler) setSaatlikVeri(saatlikVeriler);
      if (oturumVerisi) setSonOturumlar(oturumVerisi);
      if (canliVeri) setCanliOturumlar(canliVeri.active_sessions || []);

      setSonGuncelleme(new Date());
    } catch (e) {
      setHata('Veriler alınırken hata oluştu. Backend çalışıyor mu?');
      console.error('[Dashboard] Hata:', e);
    } finally {
      setYukleniyor(false);
    }
  }, [secilenTarih]);

  // ─── İlk yükleme ve tarih değişiminde ───
  useEffect(() => {
    verileriGetir();
  }, [verileriGetir]);

  // ─── Otomatik yenileme (polling) ───
  useEffect(() => {
    if (otomatikYenile) {
      pollingRef.current = setInterval(() => {
        verileriGetir(true); // sessiz yenileme
      }, POLLING_ARALIGI_MS);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [otomatikYenile, verileriGetir]);

  // ─── Bugunun tarihi ───
  const bugunTarih = new Date().toISOString().split('T')[0];

  return (
    <div className="analiz-paneli-sayfa">
      {/* ─── Üst bar: Filtreler ─── */}
      <div className="analiz-ust-bar">
        <div className="analiz-baslik">
          <h2>📈 Analiz Paneli</h2>
          <span className="analiz-alt-baslik">
            İşletme duygu analizi dashboard
          </span>
        </div>

        <div className="analiz-filtreler">
          {/* Tarih seçici */}
          <div className="filtre-grubu">
            <label htmlFor="tarih-secici">Tarih:</label>
            <input
              id="tarih-secici"
              type="date"
              value={secilenTarih}
              onChange={(e) => setSecilenTarih(e.target.value)}
              max={bugunTarih}
              className="tarih-input"
            />
          </div>

          {/* Otomatik yenileme toggle */}
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

          {/* Son güncelleme zamanı */}
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
        {/* KPI Kartları */}
        <DashboardKartlari ozet={yukleniyor && !ozet ? null : ozet} />

        {/* Grafikler satırı */}
        <div className="analiz-grafik-satiri">
          <DuyguDagilimi dagilim={ozet?.emotion_distribution} />
          <SaatlikGrafik saatlikVeri={saatlikVeri} />
        </div>

        {/* Canlı Oturumlar */}
        <CanliOturumlar oturumlar={canliOturumlar} />

        {/* Son Oturumlar Tablosu */}
        <OturumTablosu oturumlar={sonOturumlar} />
      </div>
    </div>
  );
}
