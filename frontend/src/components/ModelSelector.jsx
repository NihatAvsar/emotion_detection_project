/**
 * ModelSelector Bileseni
 * =======================
 * Backend'deki /models endpointinden model listesini ceker
 * ve kullaniciya dropdown ile model secimi sunar.
 *
 * Props:
 *   selectedModel — Secili model adi
 *   onModelChange — Model degistiginde callback (name) => void
 *   models        — Model listesi [ { name, timm_name, input_size, loaded } ]
 */

const SUNUCU_ADRESI = 'http://localhost:8000';

export default function ModelSelector({ selectedModel, onModelChange, models }) {
  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🧠</span>
        <h2>Model Seçimi</h2>
      </div>
      <div className="card-body">
        <div className="model-selector">
          <select
            id="model-select"
            value={selectedModel || ''}
            onChange={(e) => onModelChange(e.target.value)}
            className="model-dropdown"
          >
            {models.length === 0 ? (
              <option value="">Modeller yükleniyor...</option>
            ) : (
              models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name} {m.loaded ? '✅' : ''} — {m.input_size}px
                </option>
              ))
            )}
          </select>
          <div className="model-info">
            {selectedModel && models.length > 0 && (
              (() => {
                const model = models.find(m => m.name === selectedModel);
                if (!model) return null;
                return (
                  <>
                    <span className="model-detail">
                      <span className="model-detail-label">timm:</span>
                      {model.timm_name}
                    </span>
                    <span className="model-detail">
                      <span className="model-detail-label">Boyut:</span>
                      {model.input_size}×{model.input_size}
                    </span>
                    <span className={`model-status ${model.loaded ? 'loaded' : 'idle'}`}>
                      {model.loaded ? '🟢 Yüklü' : '⚪ Henüz yüklenmedi'}
                    </span>
                  </>
                );
              })()
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
