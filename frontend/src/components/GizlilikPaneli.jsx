/**
 * GizlilikPaneli Bileseni
 * ========================
 * KVKK uyumluluk bilgilerini gosteren statik panel.
 * Isletmelere gizlilik garantisi sunar.
 */

export default function GizlilikPaneli() {
  const maddeler = [
    { ikon: '🚫', metin: 'Ham kamera görüntüleri saklanmaz' },
    { ikon: '🔒', metin: 'Yüz fotoğrafları veritabanına kaydedilmez' },
    { ikon: '📊', metin: 'Sadece anonim duygu ve oturum verileri tutulur' },
    { ikon: '🆔', metin: 'Müşteri kimliği yerine anonim takip kimliği kullanılır' },
    { ikon: '🛡️', metin: 'Veriler yalnızca istatistiksel analiz amacıyla işlenir' },
  ];

  return (
    <div className="glass-card gizlilik-kart">
      <div className="card-header">
        <span className="icon">🔒</span>
        <h2>Gizlilik ve KVKK Uyumu</h2>
      </div>
      <div className="card-body gizlilik-icerik">
        {maddeler.map((madde, i) => (
          <div className="gizlilik-madde" key={i}>
            <span className="gizlilik-ikon">{madde.ikon}</span>
            <span className="gizlilik-metin">{madde.metin}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
