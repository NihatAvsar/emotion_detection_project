/**
 * ProbabilityBar Bileseni
 * ========================
 * Tum duygu siniflari icin yatay olasilik cubuk grafigi.
 * Her duygunun kendi rengi ve emojisi var.
 *
 * Props:
 *   probabilities — { happy: 0.8, sad: 0.1, ... }
 */

// ─── Duygu yapilandirmasi ───
const DUYGULAR = [
  { key: 'happy',     label: 'Mutlu',  emoji: '😊' },
  { key: 'sad',       label: 'Üzgün',  emoji: '😢' },
  { key: 'angry',     label: 'Kızgın', emoji: '😠' },
  { key: 'surprised', label: 'Şaşkın', emoji: '😲' },
  { key: 'neutral',   label: 'Nötr',   emoji: '😐' },
];

export default function ProbabilityBar({ probabilities }) {
  const olasiliklar = probabilities || {};

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📊</span>
        <h2>Olasılık Dağılımı</h2>
      </div>
      <div className="card-body">
        <div className="prob-bars">
          {DUYGULAR.map(({ key, label, emoji }) => {
            const deger = olasiliklar[key] || 0;
            const yuzde = Math.round(deger * 100);

            return (
              <div className="prob-row" key={key}>
                <span className="prob-emoji">{emoji}</span>
                <span className="prob-label">{label}</span>
                <div className="prob-track">
                  <div
                    className={`prob-fill ${key}`}
                    style={{ width: `${yuzde}%` }}
                  />
                </div>
                <span className="prob-value">%{yuzde}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
