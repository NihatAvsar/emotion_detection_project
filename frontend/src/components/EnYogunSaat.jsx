/**
 * EnYogunSaat Bileseni
 * =====================
 * Saatlik yogunluk verisinden en yogun saati otomatik cikarir.
 * Insight karti olarak gosterir: saat, musteri sayisi, baskin duygu.
 *
 * Props:
 *   saatlikVeri — { hourly_visits: { 0: 3, 1: 0, ... } }
 *   dagilim — emotion_distribution { happy: 5, sad: 2, ... }
 */

const DUYGU_ETIKETLERI = {
  happy: 'Mutlu',
  sad: 'Üzgün',
  angry: 'Kızgın',
  surprised: 'Şaşkın',
  neutral: 'Nötr',
};

const DUYGU_EMOJILERI = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😲',
  neutral: '😐',
};

export default function EnYogunSaat({ saatlikVeri, dagilim }) {
  if (!saatlikVeri?.hourly_visits) return null;

  const visits = saatlikVeri.hourly_visits;

  // ─── En yoğun saati bul ───
  let maxSaat = 0;
  let maxSayi = 0;

  Object.entries(visits).forEach(([saat, sayi]) => {
    if (sayi > maxSayi) {
      maxSayi = sayi;
      maxSaat = parseInt(saat);
    }
  });

  if (maxSayi === 0) return null;

  // ─── Baskın duygu ───
  let baskinDuygu = 'neutral';
  if (dagilim) {
    let maxDuyguSayi = 0;
    Object.entries(dagilim).forEach(([duygu, sayi]) => {
      if (duygu !== 'unknown' && sayi > maxDuyguSayi) {
        maxDuyguSayi = sayi;
        baskinDuygu = duygu;
      }
    });
  }

  const saatStr = `${String(maxSaat).padStart(2, '0')}:00`;

  return (
    <div className="glass-card insight-kart">
      <div className="card-header">
        <span className="icon">🏆</span>
        <h2>En Yoğun Saat</h2>
      </div>
      <div className="card-body insight-icerik">
        <div className="insight-saat">{saatStr}</div>
        <div className="insight-detaylar">
          <div className="insight-detay">
            <span className="insight-detay-etiket">Müşteri</span>
            <span className="insight-detay-deger">{maxSayi}</span>
          </div>
          <div className="insight-ayirici" />
          <div className="insight-detay">
            <span className="insight-detay-etiket">Baskın Duygu</span>
            <span className="insight-detay-deger">
              {DUYGU_EMOJILERI[baskinDuygu] || '❓'} {DUYGU_ETIKETLERI[baskinDuygu] || baskinDuygu}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
