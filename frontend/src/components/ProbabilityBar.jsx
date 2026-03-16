/**
 * ProbabilityBar Bileşeni
 * ========================
 * Tüm duygu sınıfları için yatay olasılık çubuk grafiği.
 * Her duygunun kendi rengi ve emojisi var.
 *
 * Props:
 *   probabilities — { happy: 0.8, sad: 0.1, ... }
 */

// ─── Duygu yapılandırması ───
const EMOTIONS = [
  { key: 'happy',     label: 'Mutlu',  emoji: '😊' },
  { key: 'sad',       label: 'Üzgün',  emoji: '😢' },
  { key: 'angry',     label: 'Kızgın', emoji: '😠' },
  { key: 'surprised', label: 'Şaşkın', emoji: '😲' },
  { key: 'neutral',   label: 'Nötr',   emoji: '😐' },
];

export default function ProbabilityBar({ probabilities }) {
  const probs = probabilities || {};

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📊</span>
        <h2>Olasılık Dağılımı</h2>
      </div>
      <div className="card-body">
        <div className="prob-bars">
          {EMOTIONS.map(({ key, label, emoji }) => {
            const value = probs[key] || 0;
            const percent = Math.round(value * 100);

            return (
              <div className="prob-row" key={key}>
                <span className="prob-emoji">{emoji}</span>
                <span className="prob-label">{label}</span>
                <div className="prob-track">
                  <div
                    className={`prob-fill ${key}`}
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <span className="prob-value">%{percent}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
