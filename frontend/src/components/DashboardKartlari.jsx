/**
 * DashboardKartlari Bileseni
 * ============================
 * Ozet KPI kartlarini gosterir:
 * - Toplam Musteri
 * - Aktif Musteri
 * - Ortalama Oturum Suresi
 * - Pozitif / Notr / Negatif Orani
 */

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function DashboardKartlari({ ozet }) {
  if (!ozet) {
    return (
      <div className="dashboard-kartlari">
        {[1, 2, 3, 4].map(i => (
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

  // ─── Pozitif / Notr / Negatif hesapla ───
  const dagilim = ozet.emotion_distribution || {};
  const toplam = Object.values(dagilim).reduce((a, b) => a + b, 0) || 1;
  const pozitifSayisi = (dagilim.happy || 0);
  const notrSayisi = (dagilim.neutral || 0);
  const negatifSayisi = (dagilim.sad || 0) + (dagilim.angry || 0);

  const pozitifOrani = Math.round((pozitifSayisi / toplam) * 100);
  const notrOrani = Math.round((notrSayisi / toplam) * 100);
  const negatifOrani = Math.round((negatifSayisi / toplam) * 100);

  const kartlar = [
    {
      ikon: '👥',
      etiket: 'Toplam Müşteri',
      deger: ozet.total_customers ?? 0,
      renk: 'var(--accent-cyan)',
    },
    {
      ikon: '🟢',
      etiket: 'Aktif Müşteri',
      deger: ozet.active_customers ?? 0,
      renk: '#22c55e',
    },
    {
      ikon: '⏱️',
      etiket: 'Ort. Oturum Süresi',
      deger: `${ozet.average_session_duration ?? 0}s`,
      renk: 'var(--accent-purple)',
    },
    {
      ikon: '📊',
      etiket: 'Duygu Özeti',
      ozel: true,
      pozitif: pozitifOrani,
      notr: notrOrani,
      negatif: negatifOrani,
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
          {kart.ozel ? (
            <div className="kpi-duygu-ozet">
              <span className="duygu-ozet-parca pozitif">😊 %{kart.pozitif}</span>
              <span className="duygu-ozet-parca notr">😐 %{kart.notr}</span>
              <span className="duygu-ozet-parca negatif">😢 %{kart.negatif}</span>
            </div>
          ) : (
            <div className="kpi-deger" style={{ color: kart.renk }}>
              {kart.deger}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
