/**
 * EmotionPanel Bileseni
 * ======================
 * Anlik baskin duyguyu buyuk emoji, Turkce etiket
 * ve guven yuzdesi ile gosterir.
 *
 * Props:
 *   emotion    — Duygu adi (Ingilizce, or. "happy")
 *   confidence — Guven skoru (0-1)
 *   emoji      — Duygu emojisi
 *   emotionTr  — Turkce etiket
 */

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function EmotionPanel({ emotion, confidence, emoji, emotionTr }) {
  const renk = DUYGU_RENKLERI[emotion] || '#94a3b8';
  const guvenYuzdesi = Math.round((confidence || 0) * 100);

  // ─── Guven seviyesi sinifi ───
  let guvenSinifi = 'low';
  if (guvenYuzdesi >= 70) guvenSinifi = 'high';
  else if (guvenYuzdesi >= 40) guvenSinifi = 'medium';

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🎯</span>
        <h2>Baskın Duygu</h2>
      </div>
      <div className="card-body emotion-panel">
        {emotion ? (
          <>
            <div className="emotion-emoji" key={emotion}>
              {emoji || '😐'}
            </div>
            <div className="emotion-label" style={{ color: renk }}>
              {emotionTr || emotion}
            </div>
            <div className="emotion-sublabel">
              {emotion}
            </div>
            <span className={`confidence-badge ${guvenSinifi}`}>
              🎯 %{guvenYuzdesi} güven
            </span>
          </>
        ) : (
          <>
            <div className="emotion-emoji" style={{ opacity: 0.3 }}>🔍</div>
            <div className="emotion-label" style={{ color: 'var(--text-muted)' }}>
              Bekleniyor...
            </div>
            <div className="emotion-sublabel">
              Kamerayı başlatın
            </div>
          </>
        )}
      </div>
    </div>
  );
}
