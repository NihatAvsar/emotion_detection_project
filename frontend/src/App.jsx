/**
 * Gerçek Zamanlı Yüz Duygu Analizi — Ana Uygulama
 * ==================================================
 * Bu bileşen tüm uygulamayı yönetir:
 *
 * 1. WebSocket bağlantısı (ws://localhost:8000/ws/predict)
 * 2. getUserMedia ile kamera erişimi
 * 3. ~12 FPS frame yakalama ve backend'e gönderme
 * 4. Back-pressure: yanıt gelene kadar yeni frame göndermeme
 * 5. Son 30 saniye duygu geçmişi tutma
 * 6. Tüm alt bileşenleri render etme
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import './index.css';

// ─── Bileşenler ───
import WebcamView from './components/WebcamView';
import EmotionPanel from './components/EmotionPanel';
import ProbabilityBar from './components/ProbabilityBar';
import EmotionTimeline from './components/EmotionTimeline';
import ModelSelector from './components/ModelSelector';

// ─── Sabitler ───
const WS_URL = 'ws://localhost:8000/ws/predict';
const API_URL = 'http://localhost:8000';
const FRAME_INTERVAL_MS = 83;         // ~12 FPS (1000/12 ≈ 83ms)
const TIMELINE_DURATION_S = 30;       // 30 saniyelik geçmiş
const MAX_HISTORY_POINTS = 360;       // 30s * 12fps = 360 kayıt

function App() {
  // ─── State ───
  const [isActive, setIsActive] = useState(false);              // Kamera açık mı?
  const [connectionStatus, setConnectionStatus] = useState('disconnected'); // ws durumu
  const [faces, setFaces] = useState([]);                       // Tespit edilen yüzler
  const [dominantEmotion, setDominantEmotion] = useState(null); // Baskın duygu
  const [probabilities, setProbabilities] = useState(null);     // Olasılıklar
  const [history, setHistory] = useState([]);                   // Zaman çizelgesi
  const [fps, setFps] = useState(0);                            // FPS sayacı
  const [availableModels, setAvailableModels] = useState([]);   // Model listesi
  const [selectedModel, setSelectedModel] = useState(null);     // Seçili model

  // ─── Refs ───
  const videoRef = useRef(null);
  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const waitingRef = useRef(false);      // Back-pressure flag
  const frameCountRef = useRef(0);
  const fpsTimerRef = useRef(null);
  const selectedModelRef = useRef(null);  // Interval içinde güncel model

  // ─── selectedModel değiştiğinde ref'i güncelle ───
  useEffect(() => {
    selectedModelRef.current = selectedModel;
  }, [selectedModel]);

  /**
   * Startup: Backend'den model listesini çek
   */
  useEffect(() => {
    fetch(`${API_URL}/models`)
      .then(res => res.json())
      .then(data => {
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          setSelectedModel(data.models[0].name);
        }
      })
      .catch(err => console.error('[Models] Liste alınamadı:', err));
  }, []);

  /**
   * FPS sayacını güncelle (her saniye)
   */
  const startFpsCounter = useCallback(() => {
    frameCountRef.current = 0;
    fpsTimerRef.current = setInterval(() => {
      setFps(frameCountRef.current);
      frameCountRef.current = 0;
    }, 1000);
  }, []);

  const stopFpsCounter = useCallback(() => {
    if (fpsTimerRef.current) {
      clearInterval(fpsTimerRef.current);
      fpsTimerRef.current = null;
    }
    setFps(0);
  }, []);

  /**
   * WebSocket bağlantısı kur
   */
  const connectWebSocket = useCallback(() => {
    setConnectionStatus('connecting');

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Bağlandı');
      setConnectionStatus('connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.success && data.faces && data.faces.length > 0) {
          // ─── Yüz verileri ───
          setFaces(data.faces);

          // ─── Baskın duygu (ilk yüz) ───
          const primary = data.faces[0];
          setDominantEmotion({
            emotion: primary.emotion,
            emotion_tr: primary.emotion_tr,
            emoji: primary.emoji,
            confidence: primary.confidence,
          });
          setProbabilities(primary.probabilities);

          // ─── Zaman çizelgesine ekle ───
          setHistory(prev => {
            const newPoint = {
              timestamp: Date.now(),
              probabilities: primary.probabilities,
            };
            const updated = [...prev, newPoint];
            // Son MAX_HISTORY_POINTS kaydı tut
            if (updated.length > MAX_HISTORY_POINTS) {
              return updated.slice(updated.length - MAX_HISTORY_POINTS);
            }
            return updated;
          });

          frameCountRef.current++;
        } else {
          setFaces([]);
        }

        // ─── Back-pressure serbest bırak ───
        waitingRef.current = false;
      } catch (err) {
        console.error('[WS] Parse hatası:', err);
        waitingRef.current = false;
      }
    };

    ws.onclose = () => {
      console.log('[WS] Bağlantı kesildi');
      setConnectionStatus('disconnected');
    };

    ws.onerror = (err) => {
      console.error('[WS] Hata:', err);
      setConnectionStatus('disconnected');
    };

    return ws;
  }, []);

  /**
   * Kameradan frame yakala ve WebSocket üzerinden gönder
   */
  const startFrameCapture = useCallback(() => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    intervalRef.current = setInterval(() => {
      const video = videoRef.current;
      const ws = wsRef.current;

      // Hazır değilse atla
      if (!video || !ws || ws.readyState !== WebSocket.OPEN) return;

      // Back-pressure: önceki yanıt gelmemişse atla
      if (waitingRef.current) return;

      // ─── Video frame'ini canvas'a çiz ───
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      // ─── JPEG olarak base64'e çevir (kalite: 0.7 — hız optimizasyonu) ───
      const base64 = canvas.toDataURL('image/jpeg', 0.7);

      // ─── JSON formatında WebSocket üzerinden gönder ───
      waitingRef.current = true;
      const msg = JSON.stringify({
        model: selectedModelRef.current,
        frame: base64,
      });
      ws.send(msg);
    }, FRAME_INTERVAL_MS);
  }, []);

  /**
   * Kamerayı başlat
   */
  const handleStart = useCallback(async () => {
    try {
      // ─── WebSocket'i hemen bağla (kamerayla paralel) ───
      connectWebSocket();

      // ─── Kamera erişimi iste ───
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      });

      streamRef.current = stream;

      // ─── Video elementine bağla ───
      if (videoRef.current) {
        videoRef.current.srcObject = stream;

        // ─── Video hazır olduğunda frame yakalamayı başlat ───
        videoRef.current.onloadedmetadata = () => {
          startFrameCapture();
          startFpsCounter();
        };
      }

      setIsActive(true);
      setHistory([]);
    } catch (err) {
      console.error('[Kamera] Erişim hatası:', err);
      alert('Kameraya erişilemedi. Lütfen tarayıcı izinlerini kontrol edin.');
    }
  }, [connectWebSocket, startFrameCapture, startFpsCounter]);

  /**
   * Kamerayı durdur
   */
  const handleStop = useCallback(() => {
    // ─── Frame yakalamayı durdur ───
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    // ─── WebSocket kapat ───
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // ─── Kamera stream'ini kapat ───
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }

    // ─── Videoyu temizle ───
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }

    stopFpsCounter();
    setIsActive(false);
    setFaces([]);
    setConnectionStatus('disconnected');
    waitingRef.current = false;
  }, [stopFpsCounter]);

  /**
   * Bileşen temizliği (unmount)
   */
  useEffect(() => {
    return () => {
      handleStop();
    };
  }, [handleStop]);

  // ─── Connection status text ───
  const statusText = {
    connected: 'Bağlı',
    connecting: 'Bağlanıyor...',
    disconnected: 'Bağlı Değil',
  };

  return (
    <div className="app-container">
      {/* ─── Header ─── */}
      <header className="app-header">
        <h1>🎭 Yüz Duygu Analizi</h1>
        <p className="subtitle">
          Gerçek Zamanlı Duygu Tanıma
        </p>
        <div className={`connection-status ${connectionStatus}`}>
          <span className="dot" />
          {statusText[connectionStatus]}
        </div>
      </header>

      {/* ─── Main Grid: Kamera + Sidebar ─── */}
      <div className="main-grid">
        {/* Sol: Webcam */}
        <WebcamView
          videoRef={videoRef}
          faces={faces}
          isActive={isActive}
          fps={fps}
          onStart={handleStart}
          onStop={handleStop}
        />

        {/* Sağ: Sidebar */}
        <div className="sidebar">
          <ModelSelector
            selectedModel={selectedModel}
            onModelChange={setSelectedModel}
            models={availableModels}
          />
          <EmotionPanel
            emotion={dominantEmotion?.emotion}
            confidence={dominantEmotion?.confidence}
            emoji={dominantEmotion?.emoji}
            emotionTr={dominantEmotion?.emotion_tr}
          />
          <ProbabilityBar probabilities={probabilities} />
        </div>
      </div>

      {/* ─── Alt: Timeline ─── */}
      <div className="bottom-section">
        <EmotionTimeline history={history} />
      </div>
    </div>
  );
}

export default App;
