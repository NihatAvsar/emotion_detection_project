/**
 * VeriKalitesi Bileseni
 * ======================
 * Analiz verilerinin kalite metriklerini gosteren panel.
 * Ortalama guven skoru, toplam tespit ve dusuk guvenli tahmin sayisi.
 *
 * Props:
 *   ozet — analytics overview verisi
 *   oturumlar — son oturumlar listesi
 */

export default function VeriKalitesi({ ozet, oturumlar }) {
  if (!ozet) return null;

  const oturumListesi = oturumlar || ozet?.recent_sessions || [];

  // ─── Metrikleri hesapla ───
  const toplamTespit = oturumListesi.reduce(
    (t, o) => t + (o.total_detections || 0), 0
  );

  const guvenDegerleri = oturumListesi
    .filter(o => o.average_confidence != null)
    .map(o => o.average_confidence);

  const ortGuven = guvenDegerleri.length > 0
    ? guvenDegerleri.reduce((a, b) => a + b, 0) / guvenDegerleri.length
    : 0;

  const dusukGuvenSayisi = guvenDegerleri.filter(g => g < 0.5).length;

  // ─── Kalite seviyesi ───
  let kaliteSeviye = 'İyi';
  let kaliteRenk = '#22c55e';
  let kaliteEmoji = '✅';

  if (ortGuven < 0.5 || dusukGuvenSayisi > guvenDegerleri.length * 0.3) {
    kaliteSeviye = 'Düşük';
    kaliteRenk = '#ef4444';
    kaliteEmoji = '⚠️';
  } else if (ortGuven < 0.7 || dusukGuvenSayisi > guvenDegerleri.length * 0.15) {
    kaliteSeviye = 'Orta';
    kaliteRenk = '#eab308';
    kaliteEmoji = '🔶';
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🔬</span>
        <h2>Veri Kalitesi</h2>
        <span className="veri-kalite-rozet" style={{ color: kaliteRenk }}>
          {kaliteEmoji} {kaliteSeviye}
        </span>
      </div>
      <div className="card-body veri-kalite-icerik">
        <div className="vk-satir">
          <span className="vk-etiket">Toplam Tespit</span>
          <span className="vk-deger">{toplamTespit.toLocaleString('tr-TR')}</span>
        </div>
        <div className="vk-satir">
          <span className="vk-etiket">Ortalama Güven</span>
          <span className="vk-deger" style={{ color: kaliteRenk }}>
            %{Math.round(ortGuven * 100)}
          </span>
        </div>
        <div className="vk-satir">
          <span className="vk-etiket">Düşük Güvenli Tahmin</span>
          <span className="vk-deger">
            {dusukGuvenSayisi}
            {dusukGuvenSayisi > 0 && (
              <span className="vk-uyari"> ⚠️</span>
            )}
          </span>
        </div>
        <div className="vk-satir">
          <span className="vk-etiket">Analiz Edilen Oturum</span>
          <span className="vk-deger">{oturumListesi.length}</span>
        </div>
      </div>
    </div>
  );
}
