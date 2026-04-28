/**
 * WebcamView Bileseni
 * ====================
 * Kamera goruntusunu gosterir ve tespit edilen yuzlerin
 * etrafina bounding box + duygu etiketi cizer.
 *
 * Props:
 *   videoRef  — <video> elementi referansi
 *   faces     — Backend'den gelen yuz verileri dizisi
 *   isActive  — Kamera acik mi?
 *   fps       — Anlik FPS degeri
 *   onStart   — Kamerayi baslat callback
 *   onStop    — Kamerayi durdur callback
 *
 * ONEMLI: <video> elementi her zaman DOM'da kalir (display:none ile gizlenir).
 * Bu sayede videoRef.current her zaman gecerlidir ve stream baglama
 * islemi asla null ref sorunu yasamaz.
 */

import { useRef, useEffect } from 'react';

// ─── Duygu renkleri (bounding box) ───
const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

// ─── Duygu Turkce etiketleri ───
const DUYGU_ETIKETLERI = {
  happy: 'Mutlu',
  sad: 'Üzgün',
  angry: 'Kızgın',
  surprised: 'Şaşkın',
  neutral: 'Nötr',
};

export default function WebcamView({ videoRef, faces, isActive, fps, onStart, onStop }) {
  const canvasRef = useRef(null);

  // ─── Canvas uzerine bounding box ciz ───
  useEffect(() => {
    const canvas = canvasRef.current;
    const video = videoRef?.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    // Canvas boyutunu video boyutuna esitle
    canvas.width = video.videoWidth || canvas.clientWidth;
    canvas.height = video.videoHeight || canvas.clientHeight;

    // Temizle
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!faces || faces.length === 0) return;

    faces.forEach((yuz) => {
      const { face_bbox, emotion, confidence, face_id } = yuz;
      if (!face_bbox) return;

      // ─── Normalize koordinatlari piksele cevir (X aynalaniyor — video mirror) ───
      const x = (1 - face_bbox.x - face_bbox.w) * canvas.width;
      const y = face_bbox.y * canvas.height;
      const g = face_bbox.w * canvas.width;
      const yukseklik = face_bbox.h * canvas.height;

      const renk = DUYGU_RENKLERI[emotion] || '#ffffff';
      const etiket = DUYGU_ETIKETLERI[emotion] || emotion;
      const guven = Math.round(confidence * 100);
      const kimlikEtiketi = face_id ? `#${face_id} ` : '';

      // ─── Glow efekti ───
      ctx.shadowColor = renk;
      ctx.shadowBlur = 12;

      // ─── Bounding box (kose susleri) ───
      const koseUzunlugu = Math.min(g, yukseklik) * 0.2;
      const cizgiKalinligi = 3;
      ctx.strokeStyle = renk;
      ctx.lineWidth = cizgiKalinligi;
      ctx.lineCap = 'round';

      // Sol ust kose
      ctx.beginPath();
      ctx.moveTo(x, y + koseUzunlugu);
      ctx.lineTo(x, y);
      ctx.lineTo(x + koseUzunlugu, y);
      ctx.stroke();

      // Sag ust kose
      ctx.beginPath();
      ctx.moveTo(x + g - koseUzunlugu, y);
      ctx.lineTo(x + g, y);
      ctx.lineTo(x + g, y + koseUzunlugu);
      ctx.stroke();

      // Sol alt kose
      ctx.beginPath();
      ctx.moveTo(x, y + yukseklik - koseUzunlugu);
      ctx.lineTo(x, y + yukseklik);
      ctx.lineTo(x + koseUzunlugu, y + yukseklik);
      ctx.stroke();

      // Sag alt kose
      ctx.beginPath();
      ctx.moveTo(x + g - koseUzunlugu, y + yukseklik);
      ctx.lineTo(x + g, y + yukseklik);
      ctx.lineTo(x + g, y + yukseklik - koseUzunlugu);
      ctx.stroke();

      // ─── Ince kenar cizgileri ───
      ctx.shadowBlur = 0;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.3;
      ctx.strokeRect(x, y, g, yukseklik);
      ctx.globalAlpha = 1;

      // ─── Etiket arka plani ───
      const etiketMetni = `${kimlikEtiketi}${etiket}  ${guven}%`;
      ctx.font = 'bold 14px Inter, sans-serif';
      const metinOlculeri = ctx.measureText(etiketMetni);
      const metinG = metinOlculeri.width + 16;
      const metinY = 28;
      const metinX = x;
      const metinUst = y - metinY - 4;

      // Yari saydam arka plan
      ctx.fillStyle = renk;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.roundRect(metinX, metinUst, metinG, metinY, 6);
      ctx.fill();
      ctx.globalAlpha = 1;

      // Metin
      ctx.fillStyle = '#000000';
      ctx.font = 'bold 13px Inter, sans-serif';
      ctx.fillText(etiketMetni, metinX + 8, metinUst + 19);
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
            ONEMLI: <video> her zaman DOM'da kalir.
            aktifMi false iken display:none ile gizlenir.
            Bu sayede videoRef.current asla null olmaz ve
            stream baglama islemi sorunsuz calisir.
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
