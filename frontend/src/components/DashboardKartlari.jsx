/**
 * DashboardKartlari Bileseni
 * ============================
 * 6 KPI karti: Toplam Musteri, Aktif Musteri, Memnuniyet Skoru,
 * Ort. Oturum Suresi, Negatif Duygu Orani, Veri Kalitesi.
 *
 * Dune gore degisim gostergeleri icerir.
 *
 * Props:
 *   ozet     — bugunun analytics overview verisi
 *   dunOzet  — dunku analytics overview verisi (karsilastirma)
 */

export default function DashboardKartlari({ ozet, dunOzet }) {
  if (!ozet) {
    return (
      <div className="dashboard-kartlari">
        {[1, 2, 3, 4, 5, 6].map(i => (
          <div className="kpi-kart skeleton" key={i}>
            <div className="kpi-ust">
              <span className="kpi-ikon">⏳</span>
              <span className="kpi-etiket">Yükleniyor...</span>
            </div>
            <div className="kpi-deger">—</div>
          </div>
        ))}
      </div>
    );
  }

  // ─── Hesaplamalar ───
  const dagilim = ozet.emotion_distribution || {};
  const toplam = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1;
  const pozitifSayisi = (dagilim.happy || 0) + (dagilim.surprised || 0);
  const notrSayisi = dagilim.neutral || 0;
  const negatifSayisi = (dagilim.sad || 0) + (dagilim.angry || 0);

  const memnuniyetSkor = Math.round(((pozitifSayisi * 1.0 + notrSayisi * 0.5) / toplam) * 100);
  const negatifOran = Math.round((negatifSayisi / toplam) * 100);

  // ─── Oturum guven ortalamasini hesapla ───
  const oturumlar = ozet.recent_sessions || [];
  const guvenDegerleri = oturumlar.filter(o => o.average_confidence != null).map(o => o.average_confidence);
  const ortGuven = guvenDegerleri.length > 0
    ? guvenDegerleri.reduce((a, b) => a + b, 0) / guvenDegerleri.length
    : 0;
  let kaliteSeviye = 'İyi';
  if (ortGuven < 0.5 && oturumlar.length > 0) kaliteSeviye = 'Düşük';
  else if (ortGuven < 0.7 && oturumlar.length > 0) kaliteSeviye = 'Orta';

  // ─── Dünkü karşılaştırma hesaplamaları ───
  function degisimHesapla(bugun, dun) {
    if (dun == null || dun === 0) return null;
    const fark = ((bugun - dun) / dun) * 100;
    return Math.round(fark);
  }

  let dunToplamMusteri = null;
  let dunOrtSure = null;
  let dunMemnuniyet = null;
  let dunNegatif = null;

  if (dunOzet) {
    dunToplamMusteri = dunOzet.total_customers || 0;
    dunOrtSure = dunOzet.average_session_duration || 0;

    const dunDagilim = dunOzet.emotion_distribution || {};
    const dunToplam = Object.values(dunDagilim).reduce((a, b) => a + b, 0) || 1;
    const dunPozitif = (dunDagilim.happy || 0) + (dunDagilim.surprised || 0);
    const dunNotr = dunDagilim.neutral || 0;
    const dunNegatifS = (dunDagilim.sad || 0) + (dunDagilim.angry || 0);

    dunMemnuniyet = Math.round(((dunPozitif * 1.0 + dunNotr * 0.5) / dunToplam) * 100);
    dunNegatif = Math.round((dunNegatifS / dunToplam) * 100);
  }

  const kartlar = [
    {
      ikon: '👥',
      etiket: 'Toplam Müşteri',
      deger: ozet.total_customers ?? 0,
      renk: 'var(--accent-cyan)',
      degisim: degisimHesapla(ozet.total_customers || 0, dunToplamMusteri),
    },
    {
      ikon: '🟢',
      etiket: 'Aktif Müşteri',
      deger: ozet.active_customers ?? 0,
      renk: '#22c55e',
      degisim: null,
    },
    {
      ikon: '😊',
      etiket: 'Memnuniyet Skoru',
      deger: `%${memnuniyetSkor}`,
      renk: memnuniyetSkor >= 65 ? '#22c55e' : memnuniyetSkor >= 40 ? '#eab308' : '#ef4444',
      degisim: dunMemnuniyet != null ? memnuniyetSkor - dunMemnuniyet : null,
      degisimTip: 'puan',
    },
    {
      ikon: '⏱️',
      etiket: 'Ort. Oturum Süresi',
      deger: `${Math.round(ozet.average_session_duration ?? 0)}s`,
      renk: 'var(--accent-purple)',
      degisim: degisimHesapla(ozet.average_session_duration || 0, dunOrtSure),
    },
    {
      ikon: '😞',
      etiket: 'Negatif Duygu Oranı',
      deger: `%${negatifOran}`,
      renk: negatifOran >= 30 ? '#ef4444' : negatifOran >= 15 ? '#eab308' : '#22c55e',
      degisim: dunNegatif != null ? negatifOran - dunNegatif : null,
      degisimTip: 'puan',
      tersDegisim: true,
    },
    {
      ikon: '🔬',
      etiket: 'Veri Kalitesi',
      deger: kaliteSeviye,
      renk: kaliteSeviye === 'İyi' ? '#22c55e' : kaliteSeviye === 'Orta' ? '#eab308' : '#ef4444',
      degisim: null,
    },
  ];

  return (
    <div className="dashboard-kartlari">
      {kartlar.map((kart, i) => (
        <div className="kpi-kart" key={i}>
          <div className="kpi-ust">
            <span className="kpi-ikon">{kart.ikon}</span>
            <span className="kpi-etiket">{kart.etiket}</span>
          </div>
          <div className="kpi-deger" style={{ color: kart.renk }}>
            {kart.deger}
          </div>
          {kart.degisim != null && (
            <div className={`kpi-degisim ${kart.tersDegisim ? (kart.degisim > 0 ? 'negatif' : 'pozitif') : (kart.degisim >= 0 ? 'pozitif' : 'negatif')}`}>
              <span className="kpi-degisim-ok">
                {kart.degisim >= 0 ? '↑' : '↓'}
              </span>
              <span className="kpi-degisim-deger">
                {kart.degisimTip === 'puan'
                  ? `${Math.abs(kart.degisim)} puan`
                  : `%${Math.abs(kart.degisim)}`
                }
              </span>
              <span className="kpi-degisim-etiket">düne göre</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
