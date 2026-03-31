/**
 * WebcamView Bileşeni
 * ====================
 * Kamera görüntüsünü gösterir ve tespit edilen yüzlerin
 * etrafına bounding box + duygu etiketi çizer.
 *
 * Props:
 *   videoRef  — <video> elementi referansı
 *   faces     — Backend'den gelen yüz verileri dizisi
 *   isActive  — Kamera açık mı?
 *   fps       — Anlık FPS değeri
 *   onStart   — Kamerayı başlat callback
 *   onStop    — Kamerayı durdur callback
 *
 * ÖNEMLİ: <video> elementi her zaman DOM'da kalır (display:none ile gizlenir).
 * Bu sayede videoRef.current her zaman geçerlidir ve stream bağlama
 * işlemi asla null ref sorunu yaşamaz.
 */

import { useRef, useEffect } from 'react';

// ─── Duygu renkleri (bounding box) ───
const EMOTION_COLORS = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

// ─── Duygu Türkçe etiketleri ───
const EMOTION_LABELS = {
  happy: 'Mutlu',
  sad: 'Üzgün',
  angry: 'Kızgın',
  surprised: 'Şaşkın',
  neutral: 'Nötr',
};

export default function WebcamView({ videoRef, faces, isActive, fps, onStart, onStop }) {
  const canvasRef = useRef(null);

  // ─── Canvas üzerine bounding box çiz ───
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef?.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    // Canvas boyutunu video boyutuna eşitle
    canvas.width = video.videoWidth || canvas.clientWidth;
    canvas.height = video.videoHeight || canvas.clientHeight;

    // Temizle
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!faces || faces.length === 0) return;

    faces.forEach((face) => {
      const { face_bbox, emotion, confidence } = face;
      if (!face_bbox) return;

      // ─── Normalize koordinatları piksele çevir ───
      const x = face_bbox.x * canvas.width;
      const y = face_bbox.y * canvas.height;
      const w = face_bbox.w * canvas.width;
      const h = face_bbox.h * canvas.height;

      const color = EMOTION_COLORS[emotion] || '#ffffff';
      const label = EMOTION_LABELS[emotion] || emotion;
      const conf = Math.round(confidence * 100);

      // ─── Glow efekti ───
      ctx.shadowColor = color;
      ctx.shadowBlur = 12;

      // ─── Bounding box (köşe süsleri) ───
      const cornerLen = Math.min(w, h) * 0.2;
      const lineWidth = 3;
      ctx.strokeStyle = color;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = 'round';

      // Sol üst köşe
      ctx.beginPath();
      ctx.moveTo(x, y + cornerLen);
      ctx.lineTo(x, y);
      ctx.lineTo(x + cornerLen, y);
      ctx.stroke();

      // Sağ üst köşe
      ctx.beginPath();
      ctx.moveTo(x + w - cornerLen, y);
      ctx.lineTo(x + w, y);
      ctx.lineTo(x + w, y + cornerLen);
      ctx.stroke();

      // Sol alt köşe
      ctx.beginPath();
      ctx.moveTo(x, y + h - cornerLen);
      ctx.lineTo(x, y + h);
      ctx.lineTo(x + cornerLen, y + h);
      ctx.stroke();

      // Sağ alt köşe
      ctx.beginPath();
      ctx.moveTo(x + w - cornerLen, y + h);
      ctx.lineTo(x + w, y + h);
      ctx.lineTo(x + w, y + h - cornerLen);
      ctx.stroke();

      // ─── İnce kenar çizgileri ───
      ctx.shadowBlur = 0;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.3;
      ctx.strokeRect(x, y, w, h);
      ctx.globalAlpha = 1;

      // ─── Etiket arka planı ───
      const text = `${label}  ${conf}%`;
      ctx.font = 'bold 14px Inter, sans-serif';
      const textMetrics = ctx.measureText(text);
      const textW = textMetrics.width + 16;
      const textH = 28;
      const textX = x;
      const textY = y - textH - 4;

      // Yarı saydam arka plan
      ctx.fillStyle = color;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.roundRect(textX, textY, textW, textH, 6);
      ctx.fill();
      ctx.globalAlpha = 1;

      // Metin
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 13px Inter, sans-serif';
      ctx.fillText(text, textX + 8, textY + 19);
    });
  }, [faces, videoRef]);

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📹</span>
        <h2>Canlı Kamera</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        <div className="webcam-container">
          {/*
            ÖNEMLİ: <video> her zaman DOM'da kalır.
            isActive false iken display:none ile gizlenir.
            Bu sayede videoRef.current asla null olmaz ve
            stream bağlama işlemi sorunsuz çalışır.
          */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              transform: 'scaleX(-1)',
              display: isActive ? 'block' : 'none',
            }}
          />
          <canvas
            ref={canvasRef}
            style={{
              transform: 'scaleX(-1)',
              display: isActive ? 'block' : 'none',
            }}
          />
          {isActive && fps > 0 && (
            <div className="fps-counter">{fps} FPS</div>
          )}
          {isActive && faces && faces.length === 0 && (
            <div className="no-face-overlay">
              😶 Yüz tespit edilemiyor...
            </div>
          )}
          {!isActive && (
            <div className="webcam-placeholder">
              <div className="camera-icon">📷</div>
              <p>Kameraya erişim için başlatın</p>
            </div>
          )}
        </div>
        <div style={{ padding: '16px', textAlign: 'center' }}>
          {isActive ? (
            <button className="btn-camera stop" onClick={onStop} id="stop-camera-btn">
              ⏹ Kamerayı Durdur
            </button>
          ) : (
            <button className="btn-camera" onClick={onStart} id="start-camera-btn">
              🎥 Kamerayı Başlat
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
