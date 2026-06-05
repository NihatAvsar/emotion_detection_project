/**
 * OturumDetayModal Bileseni
 * ===========================
 * Bir oturumun detaylarini gosteren modal overlay.
 * Session ID, takip kimligi, baslangic/bitis, baskin duygu vb.
 *
 * Props:
 *   oturum   — secilen oturum verisi (null ise modal kapali)
 *   onKapat  — modal kapatma callback'i
 */

const DUYGU_EMOJILERI = {
  happy: '😊', sad: '😢', angry: '😠',
  surprised: '😲', neutral: '😐',
};

const DUYGU_ETIKETLERI = {
  happy: 'Mutlu', sad: 'Üzgün', angry: 'Kızgın',
  surprised: 'Şaşkın', neutral: 'Nötr',
};

const DUYGU_RENKLERI = {
  happy: '#fbbf24', sad: '#60a5fa', angry: '#ef4444',
  surprised: '#a78bfa', neutral: '#94a3b8',
};

function zamanFormat(isoStr) {
  if (!isoStr) return '—';
  try {
    const tarih = new Date(isoStr);
    return tarih.toLocaleString('tr-TR', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      timeZone: 'Europe/Istanbul',
    });
  } catch {
    return '—';
  }
}

export default function OturumDetayModal({ oturum, onKapat }) {
  if (!oturum) return null;

  const guvenYuzde = oturum.average_confidence != null
    ? Math.round(oturum.average_confidence * 100)
    : null;

  // ─── Duygu dağılımı bar chart verisi ───
  const dagilim = oturum.emotion_distribution;
  let dagilimBarlari = null;

  if (dagilim) {
    const counts = dagilim.counts || dagilim;
    const ratios = dagilim.ratios || {};
    const hasCounts = counts && typeof counts === 'object' && !counts.counts;

    if (Object.keys(ratios).length > 0 || (hasCounts && Object.keys(counts).length > 0)) {
      const veri = Object.keys(ratios).length > 0 ? ratios : counts;
      const toplamForBar = Object.values(counts).reduce((a, b) => a + b, 0) || 1;

      dagilimBarlari = Object.entries(veri).map(([duygu, deger]) => {
        const oran = Object.keys(ratios).length > 0
          ? Math.round(deger * 100)
          : Math.round((deger / toplamForBar) * 100);

        return (
          <div className="modal-bar-satir" key={duygu}>
            <span className="modal-bar-emoji">
              {DUYGU_EMOJILERI[duygu] || '❓'}
            </span>
            <span className="modal-bar-etiket">
              {DUYGU_ETIKETLERI[duygu] || duygu}
            </span>
            <div className="modal-bar-track">
              <div
                className="modal-bar-fill"
                style={{
                  width: `${oran}%`,
                  background: DUYGU_RENKLERI[duygu] || '#64748b',
                }}
              />
            </div>
            <span className="modal-bar-deger">%{oran}</span>
          </div>
        );
      });
    }
  }

  return (
    <div className="modal-overlay" onClick={onKapat}>
      <div className="modal-icerik" onClick={e => e.stopPropagation()}>
        <div className="modal-baslik">
          <h3>📋 Oturum Detayı</h3>
          <button className="modal-kapat" onClick={onKapat}>✕</button>
        </div>

        <div className="modal-govde">
          <div className="modal-bilgi-grid">
            <div className="modal-bilgi">
              <span className="modal-etiket">Session ID</span>
              <span className="modal-deger">#{oturum.id}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Takip Kimliği</span>
              <span className="modal-deger mono">{oturum.tracked_face_id || '—'}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Kamera ID</span>
              <span className="modal-deger">#{oturum.camera_id}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Başlangıç</span>
              <span className="modal-deger">{zamanFormat(oturum.start_time)}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Bitiş</span>
              <span className="modal-deger">{zamanFormat(oturum.end_time)}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Oturum Süresi</span>
              <span className="modal-deger vurgulu">
                {oturum.duration_seconds != null ? `${oturum.duration_seconds}s` : '—'}
              </span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Baskın Duygu</span>
              <span className="modal-deger">
                {DUYGU_EMOJILERI[oturum.dominant_emotion] || '❓'}{' '}
                {DUYGU_ETIKETLERI[oturum.dominant_emotion] || oturum.dominant_emotion || '—'}
              </span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Ortalama Güven</span>
              <span className="modal-deger">
                {guvenYuzde != null ? `%${guvenYuzde}` : '—'}
              </span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Toplam Tespit</span>
              <span className="modal-deger">{oturum.total_detections ?? '—'}</span>
            </div>
            <div className="modal-bilgi">
              <span className="modal-etiket">Durum</span>
              <span className={`durum-rozeti ${oturum.session_status === 'active' ? 'aktif' : 'kapali'}`}>
                ● {oturum.session_status === 'active' ? 'Aktif' : 'Kapalı'}
              </span>
            </div>
          </div>

          {dagilimBarlari && (
            <div className="modal-dagilim-bolumu">
              <h4>Duygu Dağılımı</h4>
              <div className="modal-bar-listesi">
                {dagilimBarlari}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
