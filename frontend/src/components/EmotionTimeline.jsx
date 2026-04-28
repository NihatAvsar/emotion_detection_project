/**
 * EmotionTimeline Bileseni
 * =========================
 * Son 30 saniyenin duygu gecmisini cizgi grafigi olarak gosterir.
 * Canvas API kullanilarak her duygu icin ayri renkli cizgi cizilir.
 *
 * Props:
 *   history — Array of { timestamp, probabilities: { happy, sad, ... } }
 */

import { useRef, useEffect } from 'react';

// ─── Duygu renkleri ve etiketleri ───
const DUYGULAR = [
  { key: 'happy',     color: '#fbbf24', label: 'Mutlu' },
  { key: 'sad',       color: '#60a5fa', label: 'Üzgün' },
  { key: 'angry',     color: '#ef4444', label: 'Kızgın' },
  { key: 'surprised', color: '#a78bfa', label: 'Şaşkın' },
  { key: 'neutral',   color: '#94a3b8', label: 'Nötr' },
];

export default function EmotionTimeline({ history }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    // ─── HiDPI canvas ayari ───
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const G = rect.width;
    const Y = rect.height;
    const ustBosluk = 8;
    const altBosluk = 8;
    const solBosluk = 4;
    const sagBosluk = 4;

    const grafikG = G - solBosluk - sagBosluk;
    const grafikY = Y - ustBosluk - altBosluk;

    // ─── Arka plan (saydam) ───
    ctx.clearRect(0, 0, G, Y);

    // ─── Grid cizgileri ───
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = ustBosluk + (grafikY / 4) * i;
      ctx.beginPath();
      ctx.moveTo(solBosluk, y);
      ctx.lineTo(solBosluk + grafikG, y);
      ctx.stroke();
    }

    if (!history || history.length < 2) {
      // ─── Veri yok mesaji ───
      ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
      ctx.font = '13px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Veri bekleniyor...', G / 2, Y / 2);
      return;
    }

    // ─── Her duygu icin cizgi ciz ───
    const veriUzunlugu = history.length;

    DUYGULAR.forEach(({ key, color }) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.8;

      ctx.beginPath();

      for (let i = 0; i < veriUzunlugu; i++) {
        const x = solBosluk + (i / (veriUzunlugu - 1)) * grafikG;
        const deger = history[i].probabilities?.[key] || 0;
        const y = ustBosluk + grafikY - deger * grafikY;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      // ─── Son noktaya kucuk daire ───
      const sonDeger = history[veriUzunlugu - 1].probabilities?.[key] || 0;
      const sonX = solBosluk + grafikG;
      const sonY = ustBosluk + grafikY - sonDeger * grafikY;

      ctx.globalAlpha = 1;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(sonX, sonY, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.globalAlpha = 1;
  }, [history]);

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📈</span>
        <h2>Duygu Zaman Çizelgesi (30s)</h2>
      </div>
      <div className="card-body">
        <div className="timeline-container">
          <canvas
            ref={canvasRef}
            className="timeline-canvas"
          />
        </div>
        <div className="timeline-legend">
          {DUYGULAR.map(({ key, color, label }) => (
            <div className="legend-item" key={key}>
              <span className="legend-dot" style={{ background: color }} />
              {label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
