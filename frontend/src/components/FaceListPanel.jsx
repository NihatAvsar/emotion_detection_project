/**
 * FaceListPanel Bileşeni
 * =======================
 * Kamerada tespit edilen tüm yüzleri listeler.
 * Her kişi için emoji, Türkçe duygu etiketi ve güven yüzdesi gösterilir.
 * Tıklanan kişi seçili olarak işaretlenir ve sağ paneldeki
 * detay bilgileri o kişiye göre güncellenir.
 *
 * Props:
 *   faces             — Backend'den gelen yüz verileri dizisi
 *   selectedFaceIndex — Şu an seçili yüzün index'i
 *   onSelectFace      — Yüz seçildiğinde çağrılacak callback
 */

const EMOTION_COLORS = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
};

export default function FaceListPanel({ faces, selectedFaceIndex, onSelectFace }) {
  const hasFaces = faces && faces.length > 0;

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">👥</span>
        <h2>Tespit Edilen Kişiler</h2>
        {hasFaces && (
          <span className="face-count-badge">{faces.length}</span>
        )}
      </div>
      <div className="card-body face-list-body">
        {hasFaces ? (
          <div className="face-list">
            {faces.map((face, index) => {
              const color = EMOTION_COLORS[face.emotion] || '#94a3b8';
              const conf = Math.round((face.confidence || 0) * 100);
              const isSelected = index === selectedFaceIndex;

              return (
                <button
                  key={face.face_id || index}
                  className={`face-list-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectFace(index)}
                  style={{ '--face-color': color }}
                >
                  <span className="face-list-id">#{face.face_id || index + 1}</span>
                  <span className="face-list-emoji">{face.emoji || '😐'}</span>
                  <div className="face-list-info">
                    <span className="face-list-emotion" style={{ color }}>
                      {face.emotion_tr || face.emotion}
                    </span>
                    <span className="face-list-conf">%{conf} güven</span>
                  </div>
                  <div className="face-list-bar-track">
                    <div
                      className="face-list-bar-fill"
                      style={{ width: `${conf}%`, background: color }}
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
