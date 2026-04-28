/**
 * FaceListPanel Bileseni
 * =======================
 * Kamerada tespit edilen tum yuzleri listeler.
 * Her kisi icin emoji, Turkce duygu etiketi, guven yuzdesi
 * ve tracked_face_id gosterilir.
 *
 * Props:
 *   faces             — Backend'den gelen yuz verileri dizisi
 *   selectedFaceIndex — Su an secili yuzun index'i
 *   onSelectFace      — Yuz secildiginde cagrilacak callback
 */

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function FaceListPanel({ faces, selectedFaceIndex, onSelectFace }) {
  const yuzlerVar = faces && faces.length > 0;

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">👥</span>
        <h2>Tespit Edilen Kişiler</h2>
        {yuzlerVar && (
          <span className="face-count-badge">{faces.length}</span>
        )}
      </div>
      <div className="card-body face-list-body">
        {yuzlerVar ? (
          <div className="face-list">
            {faces.map((yuz, indeks) => {
              const renk = DUYGU_RENKLERI[yuz.emotion] || '#94a3b8';
              const guven = Math.round((yuz.confidence || 0) * 100);
              const seciliMi = indeks === selectedFaceIndex;
              const takipId = yuz.tracked_face_id || null;

              return (
                <button
                  key={yuz.face_id || indeks}
                  className={`face-list-item ${seciliMi ? 'selected' : ''}`}
                  onClick={() => onSelectFace(indeks)}
                  style={{ '--face-color': renk }}
                >
                  <span className="face-list-id">#{yuz.face_id || indeks + 1}</span>
                  <span className="face-list-emoji">{yuz.emoji || '😐'}</span>
                  <div className="face-list-info">
                    <span className="face-list-emotion" style={{ color: renk }}>
                      {yuz.emotion_tr || yuz.emotion}
                    </span>
                    <div className="face-list-alt-bilgi">
                      <span className="face-list-conf">%{guven} güven</span>
                      {takipId && (
                        <span className="face-list-takip" title={takipId}>
                          🔗 {takipId}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="face-list-bar-track">
                    <div
                      className="face-list-bar-fill"
                      style={{ width: `${guven}%`, background: renk }}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="face-list-empty">
            <span className="face-list-empty-icon">👤</span>
            <span>Yüz tespit edilmedi</span>
          </div>
        )}
      </div>
    </div>
  );
}
