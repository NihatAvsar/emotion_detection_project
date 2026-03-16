/**
 * EmotionPanel Bileşeni
 * ======================
 * Anlık baskın duyguyu büyük emoji, Türkçe etiket
 * ve güven yüzdesi ile gösterir.
 *
 * Props:
 *   emotion    — Duygu adı (İngilizce, ör. "happy")
 *   confidence — Güven skoru (0-1)
 *   emoji      — Duygu emojisi
 *   emotionTr  — Türkçe etiket
 */

const EMOTION_COLORS = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function EmotionPanel({ emotion, confidence, emoji, emotionTr }) {
  const color = EMOTION_COLORS[emotion] || '#94a3b8';
  const confPercent = Math.round((confidence || 0) * 100);

  // ─── Güven seviyesi sınıfı ───
  let confClass = 'low';
  if (confPercent >= 70) confClass = 'high';
  else if (confPercent >= 40) confClass = 'medium';

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
            <div className="emotion-label" style={{ color }}>
              {emotionTr || emotion}
            </div>
            <div className="emotion-sublabel">
              {emotion}
            </div>
            <span className={`confidence-badge ${confClass}`}>
              🎯 %{confPercent} güven
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
