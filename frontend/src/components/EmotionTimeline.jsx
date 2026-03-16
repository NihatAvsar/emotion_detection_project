/**
 * EmotionTimeline Bileşeni
 * =========================
 * Son 30 saniyenin duygu geçmişini çizgi grafiği olarak gösterir.
 * Canvas API kullanılarak her duygu için ayrı renkli çizgi çizilir.
 *
 * Props:
 *   history — Array of { timestamp, probabilities: { happy, sad, ... } }
 */

import { useRef, useEffect } from 'react';

// ─── Duygu renkleri ve etiketleri ───
const EMOTIONS = [
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

    // ─── HiDPI canvas ayarı ───
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width;
    const H = rect.height;
    const padTop = 8;
    const padBottom = 8;
    const padLeft = 4;
    const padRight = 4;

    const graphW = W - padLeft - padRight;
    const graphH = H - padTop - padBottom;

    // ─── Arka plan (saydam) ───
    ctx.clearRect(0, 0, W, H);

    // ─── Grid çizgileri ───
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const y = padTop + (graphH / 4) * i;
      ctx.beginPath();
      ctx.moveTo(padLeft, y);
      ctx.lineTo(padLeft + graphW, y);
      ctx.stroke();
    }

    if (!history || history.length < 2) {
      // ─── Veri yok mesajı ───
      ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
      ctx.font = '13px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('Veri bekleniyor...', W / 2, H / 2);
      return;
    }

    // ─── Her duygu için çizgi çiz ───
    const dataLen = history.length;

    EMOTIONS.forEach(({ key, color }) => {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.globalAlpha = 0.8;

      ctx.beginPath();

      for (let i = 0; i < dataLen; i++) {
        const x = padLeft + (i / (dataLen - 1)) * graphW;
        const val = history[i].probabilities?.[key] || 0;
        const y = padTop + graphH - val * graphH;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }

      ctx.stroke();

      // ─── Son noktaya küçük daire ───
      const lastVal = history[dataLen - 1].probabilities?.[key] || 0;
      const lastX = padLeft + graphW;
      const lastY = padTop + graphH - lastVal * graphH;

      ctx.globalAlpha = 1;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
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
          {EMOTIONS.map(({ key, color, label }) => (
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
