/**
 * CanliTespit Sayfasi
 * ====================
 * Mevcut App.jsx'teki kamera + WebSocket mantigi buraya tasindi.
 * Degisen tek sey: camera_code desteği ve tracked_face_id islenmesi.
 */

import { useState, useRef, useCallback, useEffect } from 'react';

// ─── Bilesenler ───
import WebcamView from '../components/WebcamView';
import EmotionPanel from '../components/EmotionPanel';
import ProbabilityBar from '../components/ProbabilityBar';
import EmotionTimeline from '../components/EmotionTimeline';
import ModelSelector from '../components/ModelSelector';
import FaceListPanel from '../components/FaceListPanel';

// ─── Sabitler ───
const WS_URL = 'ws://localhost:8000/ws/predict';
const API_URL = 'http://localhost:8000';
const KARE_ARALIGI_MS = 83;
const MAKS_GECMIS_NOKTASI = 360;

export default function CanliTespit() {
  // ─── State ───
  const [aktifMi, setAktifMi] = useState(false);
  const [baglantiDurumu, setBaglantiDurumu] = useState('disconnected');
  const [yuzler, setYuzler] = useState([]);
  const [seciliYuzIndeksi, setSeciliYuzIndeksi] = useState(0);
  const [gecmis, setGecmis] = useState([]);
  const [fps, setFps] = useState(0);
  const [mevcutModeller, setMevcutModeller] = useState([]);
  const [seciliModel, setSeciliModel] = useState(null);
  const [kameraKodu, setKameraKodu] = useState('CAM001');
  const [aktifMusteriSayisi, setAktifMusteriSayisi] = useState(0);

  // ─── Refs ───
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const bekliyorRef = useRef(false);
  const kareSayaciRef = useRef(0);
  const fpsZamanlayiciRef = useRef(null);
  const seciliModelRef = useRef(null);
  const kameraKoduRef = useRef('CAM001');
  const baslatiliyorRef = useRef(false);

  // ─── Ref sync'leri ───
  useEffect(() => {
    seciliModelRef.current = seciliModel;
  }, [seciliModel]);

  useEffect(() => {
    kameraKoduRef.current = kameraKodu;
  }, [kameraKodu]);

  /**
   * Startup: Backend'den model listesini cek
   */
  useEffect(() => {
    fetch(`${API_URL}/models`)
      .then(res => res.json())
      .then(data => {
        if (data.models && data.models.length > 0) {
          setMevcutModeller(data.models);
          setSeciliModel(data.models[0].name);
        }
      })
      .catch(err => console.error('[Modeller] Liste alinamadi:', err));
  }, []);

  /**
   * FPS sayaci
   */
  const fpsSayaciniBaslat = useCallback(() => {
    kareSayaciRef.current = 0;
    fpsZamanlayiciRef.current = setInterval(() => {
      setFps(kareSayaciRef.current);
      kareSayaciRef.current = 0;
    }, 1000);
  }, []);

  const fpsSayaciniDurdur = useCallback(() => {
    if (fpsZamanlayiciRef.current) {
      clearInterval(fpsZamanlayiciRef.current);
      fpsZamanlayiciRef.current = null;
    }
    setFps(0);
  }, []);

  /**
   * Temizlik
   */
  const temizle = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.onloadedmetadata = null;
      videoRef.current.srcObject = null;
    }

    fpsSayaciniDurdur();
    bekliyorRef.current = false;
  }, [fpsSayaciniDurdur]);

  /**
   * WebSocket baglantisi kur
   */
  const webSocketBaglan = useCallback(() => {
    setBaglantiDurumu('connecting');

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Baglandi');
      setBaglantiDurumu('connected');
    };

    ws.onmessage = (event) => {
      try {
        const veri = JSON.parse(event.data);

        if (veri.success && veri.faces && veri.faces.length > 0) {
          setYuzler(veri.faces);

          setSeciliYuzIndeksi(onceki =>
            onceki >= veri.faces.length ? 0 : onceki
          );

          // ─── Aktif musteri sayisi ───
          if (veri.active_customer_count !== undefined) {
            setAktifMusteriSayisi(veri.active_customer_count);
          }

          // ─── Zaman cizelgesine ekle (ilk yuzun verileri) ───
          const birincil = veri.faces[0];
          setGecmis(onceki => {
            const yeniNokta = {
              timestamp: Date.now(),
              probabilities: birincil.probabilities,
            };
            const guncellenmis = [...onceki, yeniNokta];
            if (guncellenmis.length > MAKS_GECMIS_NOKTASI) {
              return guncellenmis.slice(guncellenmis.length - MAKS_GECMIS_NOKTASI);
            }
            return guncellenmis;
          });

          kareSayaciRef.current++;
        } else {
          setYuzler([]);
        }

        bekliyorRef.current = false;
      } catch (hata) {
        console.error('[WS] Parse hatasi:', hata);
        bekliyorRef.current = false;
      }
    };

    ws.onclose = () => {
      console.log('[WS] Baglanti kesildi');
      setBaglantiDurumu('disconnected');
    };

    ws.onerror = (hata) => {
      console.error('[WS] Hata:', hata);
      setBaglantiDurumu('disconnected');
    };

    return ws;
  }, []);

  /**
   * Kare yakalama
   */
  const kareYakalamayiBaslat = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    intervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const ws = wsRef.current;

      if (!video || !ws || ws.readyState !== WebSocket.OPEN) return;
      if (video.videoWidth === 0 || video.videoHeight === 0) return;
      if (bekliyorRef.current) return;

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      const base64 = canvas.toDataURL('image/jpeg', 0.7);

      bekliyorRef.current = true;
      const mesaj = JSON.stringify({
        model: seciliModelRef.current,
        camera_code: kameraKoduRef.current,
        frame: base64,
      });
      ws.send(mesaj);
    }, KARE_ARALIGI_MS);
  }, []);

  /**
   * Kamerayi baslat
   */
  const baslat = useCallback(async () => {
    if (baslatiliyorRef.current) return;
    baslatiliyorRef.current = true;

    try {
      temizle();
      webSocketBaglan();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;
      bekliyorRef.current = false;
      setGecmis([]);
      setYuzler([]);
      setSeciliYuzIndeksi(0);
      setAktifMusteriSayisi(0);

      const video = videoRef.current;
      if (video) {
        video.srcObject = stream;

        try {
          await video.play();
        } catch (oynatmaHatasi) {
          console.warn('[Video] Autoplay engellendi:', oynatmaHatasi);
        }

        kareYakalamayiBaslat();
        fpsSayaciniBaslat();
      }

      setAktifMi(true);
    } catch (hata) {
      console.error('[Kamera] Erisim hatasi:', hata);
      alert('Kameraya erişilemedi. Lütfen tarayıcı izinlerini kontrol edin.');
    } finally {
      baslatiliyorRef.current = false;
    }
  }, [temizle, webSocketBaglan, kareYakalamayiBaslat, fpsSayaciniBaslat]);

  /**
   * Kamerayi durdur
   */
  const durdur = useCallback(() => {
    temizle();
    setAktifMi(false);
    setYuzler([]);
    setBaglantiDurumu('disconnected');
    setAktifMusteriSayisi(0);
  }, [temizle]);

  /**
   * Bilesen temizligi (unmount)
   */
  useEffect(() => {
    return () => {
      temizle();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Baglanti durumu metni ───
  const durumMetni = {
    connected: 'Bağlı',
    connecting: 'Bağlanıyor...',
    disconnected: 'Bağlı Değil',
  };

  // ─── Secili yuzun verileri ───
  const seciliYuz = yuzler.length > 0 ? yuzler[seciliYuzIndeksi] || yuzler[0] : null;

  return (
    <div className="canli-tespit-sayfa">
      {/* ─── Üst bar: Bağlantı + Kamera Kodu + Aktif Müşteri ─── */}
      <div className="tespit-ust-bar">
        <div className={`connection-status ${baglantiDurumu}`}>
          <span className="dot" />
          {durumMetni[baglantiDurumu]}
        </div>

        <div className="kamera-kodu-alani">
          <label htmlFor="camera-code-input">Kamera Kodu:</label>
          <input
            id="camera-code-input"
            type="text"
            value={kameraKodu}
            onChange={(e) => setKameraKodu(e.target.value.toUpperCase())}
            className="kamera-kodu-input"
            disabled={aktifMi}
          />
        </div>

        {aktifMi && (
          <div className="aktif-musteri-rozeti">
            <span className="aktif-musteri-dot" />
            <span>{aktifMusteriSayisi} aktif müşteri</span>
          </div>
        )}
      </div>

      {/* ─── Main Grid: Kamera + Sidebar ─── */}
      <div className="main-grid">
        {/* Sol: Webcam */}
        <WebcamView
          videoRef={videoRef}
          faces={yuzler}
          isActive={aktifMi}
          fps={fps}
          onStart={baslat}
          onStop={durdur}
        />

        {/* Sag: Sidebar */}
        <div className="sidebar">
          <ModelSelector
            selectedModel={seciliModel}
            onModelChange={setSeciliModel}
            models={mevcutModeller}
          />
          <FaceListPanel
            faces={yuzler}
            selectedFaceIndex={seciliYuzIndeksi}
            onSelectFace={setSeciliYuzIndeksi}
          />
          <EmotionPanel
            emotion={seciliYuz?.emotion}
            confidence={seciliYuz?.confidence}
            emoji={seciliYuz?.emoji}
            emotionTr={seciliYuz?.emotion_tr}
          />
          <ProbabilityBar probabilities={seciliYuz?.probabilities || null} />
        </div>
      </div>

      {/* ─── Alt: Timeline ─── */}
      <div className="bottom-section">
        <EmotionTimeline history={gecmis} />
      </div>
    </div>
  );
}
