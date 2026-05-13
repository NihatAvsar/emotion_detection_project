/**
 * MemnuniyetSkoru Bileseni
 * =========================
 * Duygu dagiliminden tek bir isletme metrigi uretir.
 * SVG progress ring ile gosterir.
 *
 * Formul: (pozitif * 1.0 + notr * 0.5) / toplam * 100
 *
 * Props:
 *   dagilim — { happy: 5, sad: 2, angry: 1, neutral: 3, surprised: 1 }
 */

export default function MemnuniyetSkoru({ dagilim }) {
  if (!dagilim || Object.keys(dagilim).length === 0) return null;

  const toplam = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1;
  const pozitif = (dagilim.happy || 0) + (dagilim.surprised || 0);
  const notr = dagilim.neutral || 0;
  const negatif = (dagilim.sad || 0) + (dagilim.angry || 0);

  const skor = Math.round(((pozitif * 1.0 + notr * 0.5) / toplam) * 100);

  const pozitifOran = Math.round((pozitif / toplam) * 100);
  const notrOran = Math.round((notr / toplam) * 100);
  const negatifOran = Math.round((negatif / toplam) * 100);

  // ─── SVG ring ───
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (skor / 100) * circumference;

  // ─── Renk ───
  let renk = '#22c55e';
  let seviye = 'İyi';
  if (skor < 40) {
    renk = '#ef4444';
    seviye = 'Düşük';
  } else if (skor < 65) {
    renk = '#eab308';
    seviye = 'Orta';
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">😊</span>
        <h2>Müşteri Memnuniyet Skoru</h2>
      </div>
      <div className="card-body memnuniyet-icerik">
        <div className="memnuniyet-ring-alani">
          <svg width="130" height="130" viewBox="0 0 130 130" className="memnuniyet-svg">
            {/* Arka plan halkası */}
            <circle
              cx="65" cy="65" r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="10"
            />
            {/* İlerleme halkası */}
            <circle
              cx="65" cy="65" r={radius}
              fill="none"
              stroke={renk}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              transform="rotate(-90 65 65)"
              style={{ transition: 'stroke-dashoffset 0.8s ease, stroke 0.3s ease' }}
            />
          </svg>
          <div className="memnuniyet-ring-metin">
            <span className="memnuniyet-skor" style={{ color: renk }}>%{skor}</span>
            <span className="memnuniyet-seviye">{seviye}</span>
          </div>
        </div>
        <div className="memnuniyet-breakdown">
          <div className="memnuniyet-parca">
            <span className="mb-emoji">😊</span>
            <span className="mb-etiket">Pozitif</span>
            <span className="mb-deger pozitif">%{pozitifOran}</span>
          </div>
          <div className="memnuniyet-parca">
            <span className="mb-emoji">😐</span>
            <span className="mb-etiket">Nötr</span>
            <span className="mb-deger notr">%{notrOran}</span>
          </div>
          <div className="memnuniyet-parca">
            <span className="mb-emoji">😞</span>
            <span className="mb-etiket">Negatif</span>
            <span className="mb-deger negatif">%{negatifOran}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
