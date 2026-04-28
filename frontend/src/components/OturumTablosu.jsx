/**
 * OturumTablosu Bileseni
 * =======================
 * Son oturumlari tablo formatinda gosterir.
 */

const DUYGU_EMOJILERI = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😲',
  neutral: '😐',
};

const DUYGU_ETIKETLERI = {
  happy: 'Mutlu',
  sad: 'Üzgün',
  angry: 'Kızgın',
  surprised: 'Şaşkın',
  neutral: 'Nötr',
};

function zamanFormat(isoStr) {
  if (!isoStr) return '—';
  try {
    const tarih = new Date(isoStr);
    return tarih.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '—';
  }
}

function durumRozeti(durum) {
  if (durum === 'active') {
    return <span className="durum-rozeti aktif">● Aktif</span>;
  }
  return <span className="durum-rozeti kapali">● Kapalı</span>;
}

export default function OturumTablosu({ oturumlar }) {
  if (!oturumlar || oturumlar.length === 0) {
    return (
      <div className="glass-card">
        <div className="card-header">
          <span className="icon">📋</span>
          <h2>Son Oturumlar</h2>
        </div>
        <div className="card-body grafik-bos">
          <span className="bos-ikon">📝</span>
          <span>Henüz oturum kaydı yok</span>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📋</span>
        <h2>Son Oturumlar</h2>
        <span className="face-count-badge">{oturumlar.length}</span>
      </div>
      <div className="card-body" style={{ padding: '8px' }}>
        <div className="tablo-kapsayici">
          <table className="oturum-tablosu">
            <thead>
              <tr>
                <th>ID</th>
                <th>Takip Kimliği</th>
                <th>Başlangıç</th>
                <th>Bitiş</th>
                <th>Süre</th>
                <th>Baskın Duygu</th>
                <th>Güven</th>
                <th>Tespit</th>
                <th>Durum</th>
              </tr>
            </thead>
            <tbody>
              {oturumlar.map((oturum) => (
                <tr key={oturum.id}>
                  <td className="tablo-id">#{oturum.id}</td>
                  <td className="tablo-takip">
                    <span className="takip-kimlik">{oturum.tracked_face_id || '—'}</span>
                  </td>
                  <td>{zamanFormat(oturum.start_time)}</td>
                  <td>{zamanFormat(oturum.end_time)}</td>
                  <td className="tablo-sure">
                    {oturum.duration_seconds != null ? `${oturum.duration_seconds}s` : '—'}
                  </td>
                  <td>
                    <span className="duygu-hucre">
                      {DUYGU_EMOJILERI[oturum.dominant_emotion] || '❓'}
                      {' '}
                      {DUYGU_ETIKETLERI[oturum.dominant_emotion] || oturum.dominant_emotion || '—'}
                    </span>
                  </td>
                  <td className="tablo-guven">
                    {oturum.average_confidence != null
                      ? `%${Math.round(oturum.average_confidence * 100)}`
                      : '—'}
                  </td>
                  <td className="tablo-tespit">{oturum.total_detections ?? '—'}</td>
                  <td>{durumRozeti(oturum.session_status)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
