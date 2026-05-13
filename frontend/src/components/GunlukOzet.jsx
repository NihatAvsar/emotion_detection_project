/**
 * GunlukOzet Bileseni
 * =====================
 * Metriklere dayali Turkce gunluk ozet metni uretir.
 * Kural tabanli — LLM kullanmaz.
 *
 * Props:
 *   ozet      — analytics overview verisi
 *   saatlikVeri — hourly visits verisi
 */

const DUYGU_ETIKETLERI = {
  happy: 'mutlu',
  sad: 'üzgün',
  angry: 'kızgın',
  surprised: 'şaşkın',
  neutral: 'nötr',
};

export default function GunlukOzet({ ozet, saatlikVeri }) {
  if (!ozet) return null;

  // ─── Metrikler ───
  const toplam = ozet.total_customers || 0;
  const dagilim = ozet.emotion_distribution || {};
  const toplamDuygu = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1;

  const pozitifSayisi = (dagilim.happy || 0) + (dagilim.surprised || 0);
  const negatifSayisi = (dagilim.sad || 0) + (dagilim.angry || 0);
  const pozitifOran = Math.round((pozitifSayisi / toplamDuygu) * 100);
  const negatifOran = Math.round((negatifSayisi / toplamDuygu) * 100);

  // ─── Baskın duygu ───
  let baskinDuygu = 'neutral';
  let baskinSayi = 0;
  Object.entries(dagilim).forEach(([duygu, sayi]) => {
    if (duygu !== 'unknown' && sayi > baskinSayi) {
      baskinSayi = sayi;
      baskinDuygu = duygu;
    }
  });

  // ─── En yoğun saat ───
  let enYogunSaat = null;
  if (saatlikVeri?.hourly_visits) {
    let maxSayi = 0;
    Object.entries(saatlikVeri.hourly_visits).forEach(([saat, sayi]) => {
      if (sayi > maxSayi) {
        maxSayi = sayi;
        enYogunSaat = `${String(saat).padStart(2, '0')}:00`;
      }
    });
  }

  // ─── Memnuniyet ───
  const memnuniyet = pozitifOran >= 60 ? 'yüksek' :
                     pozitifOran >= 40 ? 'orta' : 'düşük';

  // ─── Metin üret ───
  const cumleler = [];

  if (toplam > 0) {
    cumleler.push(`Bugün toplam ${toplam} müşteri analiz edildi.`);
  } else {
    cumleler.push('Bugün henüz müşteri analizi yapılmadı.');
  }

  if (enYogunSaat) {
    cumleler.push(`En yoğun saat ${enYogunSaat} olarak belirlendi.`);
  }

  if (toplam > 0) {
    cumleler.push(
      `Genel müşteri memnuniyeti ${memnuniyet} seviyede (%${pozitifOran} pozitif).`
    );

    cumleler.push(
      `Baskın duygu "${DUYGU_ETIKETLERI[baskinDuygu] || baskinDuygu}" olarak gözlemlendi.`
    );

    if (negatifOran <= 15) {
      cumleler.push(
        'Negatif duygu oranı düşük olduğu için müşteri deneyimi genel olarak olumlu değerlendirilebilir.'
      );
    } else if (negatifOran <= 30) {
      cumleler.push(
        `Negatif duygu oranı %${negatifOran} ile izlenebilir seviyede. Dikkat edilmesi önerilir.`
      );
    } else {
      cumleler.push(
        `⚠️ Negatif duygu oranı %${negatifOran} ile yüksek seviyede! Acil müdahale önerilir.`
      );
    }

    const ortSure = ozet.average_session_duration || 0;
    if (ortSure > 0) {
      cumleler.push(
        `Ortalama oturum süresi ${Math.round(ortSure)} saniye olarak kaydedildi.`
      );
    }
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🤖</span>
        <h2>Günlük AI Özeti</h2>
      </div>
      <div className="card-body gunluk-ozet-icerik">
        <div className="gunluk-ozet-metin">
          {cumleler.map((cumle, i) => (
            <p key={i}>{cumle}</p>
          ))}
        </div>
        <div className="gunluk-ozet-footer">
          <span className="gunluk-ozet-bilgi">
            📅 {new Date().toLocaleDateString('tr-TR', {
              day: 'numeric', month: 'long', year: 'numeric'
            })} — otomatik oluşturuldu
          </span>
        </div>
      </div>
    </div>
  );
}
