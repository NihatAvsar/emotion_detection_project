/**
 * AkilliUyarilar Bileseni
 * ========================
 * Metriklere dayali kural tabanli uyari sistemi.
 * Negatif duygu orani, kizgin musteri orani, yogunluk ve veri kalitesi kontrol eder.
 *
 * Props:
 *   ozet      — analytics overview verisi
 *   oturumlar — son oturumlar listesi
 */

export default function AkilliUyarilar({ ozet, oturumlar }) {
  if (!ozet) return null;

  const dagilim = ozet.emotion_distribution || {};
  const toplam = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1;
  const oturumListesi = oturumlar || ozet?.recent_sessions || [];

  const negatifSayisi = (dagilim.sad || 0) + (dagilim.angry || 0);
  const kizginSayisi = dagilim.angry || 0;
  const negatifOran = Math.round((negatifSayisi / toplam) * 100);
  const kizginOran = Math.round((kizginSayisi / toplam) * 100);

  // ─── Ortalama güven ───
  const guvenDegerleri = oturumListesi
    .filter(o => o.average_confidence != null)
    .map(o => o.average_confidence);
  const ortGuven = guvenDegerleri.length > 0
    ? guvenDegerleri.reduce((a, b) => a + b, 0) / guvenDegerleri.length
    : 1;

  const aktifMusteri = ozet.active_customers || 0;

  // ─── Uyarıları oluştur ───
  const uyarilar = [];

  if (negatifOran >= 30) {
    uyarilar.push({
      tip: 'kritik',
      ikon: '🔴',
      baslik: 'Yüksek Negatif Duygu',
      mesaj: `Negatif duygu oranı %${negatifOran} ile kritik seviyede. Müşteri memnuniyeti tehlikede.`,
    });
  } else if (negatifOran >= 20) {
    uyarilar.push({
      tip: 'uyari',
      ikon: '🟡',
      baslik: 'Artan Negatif Duygu',
      mesaj: `Negatif duygu oranı %${negatifOran}. İzlenmesi önerilir.`,
    });
  }

  if (kizginOran >= 20) {
    uyarilar.push({
      tip: 'kritik',
      ikon: '😠',
      baslik: 'Kızgın Müşteri Uyarısı',
      mesaj: `Kızgın müşteri oranı %${kizginOran} ile yüksek. Acil müdahale gerekebilir.`,
    });
  }

  if (aktifMusteri >= 10) {
    uyarilar.push({
      tip: 'bilgi',
      ikon: '👥',
      baslik: 'Yoğunluk Uyarısı',
      mesaj: `Şu an ${aktifMusteri} aktif müşteri var. Yoğun dönem.`,
    });
  }

  if (ortGuven < 0.5 && oturumListesi.length > 0) {
    uyarilar.push({
      tip: 'uyari',
      ikon: '🔬',
      baslik: 'Düşük Veri Kalitesi',
      mesaj: `Ortalama güven skoru %${Math.round(ortGuven * 100)}. Kamera konumu veya ışık kontrol edilmeli.`,
    });
  }

  if (uyarilar.length === 0) {
    uyarilar.push({
      tip: 'basarili',
      ikon: '✅',
      baslik: 'Her Şey Yolunda',
      mesaj: 'Tüm metrikler normal aralıkta. Müşteri deneyimi olumlu seyrediyor.',
    });
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">⚠️</span>
        <h2>Akıllı Uyarılar</h2>
        {uyarilar.some(u => u.tip === 'kritik') && (
          <span className="uyari-sayac kritik">{uyarilar.filter(u => u.tip === 'kritik').length}</span>
        )}
      </div>
      <div className="card-body uyari-icerik">
        {uyarilar.map((uyari, i) => (
          <div className={`uyari-kart ${uyari.tip}`} key={i}>
            <span className="uyari-ikon">{uyari.ikon}</span>
            <div className="uyari-bilgi">
              <span className="uyari-baslik">{uyari.baslik}</span>
              <span className="uyari-mesaj">{uyari.mesaj}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
