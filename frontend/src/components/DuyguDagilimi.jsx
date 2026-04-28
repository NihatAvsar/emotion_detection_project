/**
 * DuyguDagilimi Bileseni
 * =======================
 * Recharts PieChart ile duygu dagilimini pasta grafik olarak gosterir.
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  sad: '#60a5fa',
  angry: '#ef4444',
  surprised: '#a78bfa',
  neutral: '#94a3b8',
  unknown: '#64748b',
};

const DUYGU_ETIKETLERI = {
  happy: 'Mutlu',
  sad: 'Üzgün',
  angry: 'Kızgın',
  surprised: 'Şaşkın',
  neutral: 'Nötr',
  unknown: 'Bilinmiyor',
};

const DUYGU_EMOJILERI = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😲',
  neutral: '😐',
  unknown: '❓',
};

function OzelTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const veri = payload[0].payload;
    return (
      <div className="grafik-tooltip">
        <span>{DUYGU_EMOJILERI[veri.name] || '❓'} {DUYGU_ETIKETLERI[veri.name] || veri.name}</span>
        <strong>{veri.value} kişi</strong>
      </div>
    );
  }
  return null;
}

export default function DuyguDagilimi({ dagilim }) {
  if (!dagilim || Object.keys(dagilim).length === 0) {
    return (
      <div className="glass-card">
        <div className="card-header">
          <span className="icon">🥧</span>
          <h2>Duygu Dağılımı</h2>
        </div>
        <div className="card-body grafik-bos">
          <span className="bos-ikon">📊</span>
          <span>Henüz veri yok</span>
        </div>
      </div>
    );
  }

  const grafikVerisi = Object.entries(dagilim).map(([key, value]) => ({
    name: key,
    value: value,
    label: DUYGU_ETIKETLERI[key] || key,
  }));

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">🥧</span>
        <h2>Duygu Dağılımı</h2>
      </div>
      <div className="card-body">
        <div className="grafik-alani" style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={grafikVerisi}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {grafikVerisi.map((girdi) => (
                  <Cell
                    key={girdi.name}
                    fill={DUYGU_RENKLERI[girdi.name] || '#64748b'}
                  />
                ))}
              </Pie>
              <Tooltip content={<OzelTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grafik-aciklama">
          {grafikVerisi.map(({ name, value, label }) => (
            <div className="aciklama-satiri" key={name}>
              <span
                className="aciklama-renk"
                style={{ background: DUYGU_RENKLERI[name] || '#64748b' }}
              />
              <span className="aciklama-etiket">
                {DUYGU_EMOJILERI[name] || '❓'} {label}
              </span>
              <span className="aciklama-deger">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
