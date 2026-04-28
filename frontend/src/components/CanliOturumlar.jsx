/**
 * CanliOturumlar Bileseni
 * ========================
 * Aktif oturumlari canli olarak gosterir.
 * Her aktif kisinin tracked_face_id, baskin duygu ve suresi listelenir.
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

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function CanliOturumlar({ oturumlar }) {
  const aktifVar = oturumlar && oturumlar.length > 0;

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🔴</span>
        <h2>Canlı Aktif Oturumlar</h2>
        {aktifVar && (
          <span className="face-count-badge">{oturumlar.length}</span>
        )}
      </div>
      <div className="card-body" style={{ padding: '12px' }}>
        {aktifVar ? (
          <div className="canli-oturum-listesi">
            {oturumlar.map((oturum, idx) => {
              const renk = DUYGU_RENKLERI[oturum.dominant_emotion] || '#94a3b8';
              const etiket = DUYGU_ETIKETLERI[oturum.dominant_emotion] || '—';
              const emoji = DUYGU_EMOJILERI[oturum.dominant_emotion] || '❓';
              const guven = oturum.average_confidence != null
                ? `%${Math.round(oturum.average_confidence * 100)}`
                : '—';

              return (
                <div
                  className="canli-oturum-kart"
                  key={oturum.tracked_face_id || idx}
                  style={{ '--canli-renk': renk }}
                >
                  <div className="canli-oturum-ust">
                    <span className="canli-canli-dot" />
                    <span className="canli-takip-id">{oturum.tracked_face_id}</span>
                    <span className="canli-kamera">Kamera #{oturum.camera_id}</span>
                  </div>
                  <div className="canli-oturum-alt">
                    <span className="canli-duygu" style={{ color: renk }}>
                      {emoji} {etiket}
                    </span>
                    <span className="canli-guven">{guven}</span>
                    <span className="canli-tespit">{oturum.total_detections} tespit</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grafik-bos">
            <span className="bos-ikon">👤</span>
            <span>Aktif oturum yok</span>
          </div>
        )}
      </div>
    </div>
  );
}
