/**
 * SaatlikDuyguTrendi Bileseni
 * ============================
 * Recharts StackedBarChart ile saatlik duygu dagilimini gosterir.
 *
 * Props:
 *   trendVeri — { hourly_emotions: { "0": { happy: 1, sad: 0, ... }, ... } }
 */

import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend
} from 'recharts';

const DUYGU_RENKLERI = {
  happy: '#fbbf24',
  neutral: '#94a3b8',
  surprised: '#a78bfa',
  sad: '#60a5fa',
  angry: '#ef4444',
};

const DUYGU_ETIKETLERI = {
  happy: 'Mutlu',
  neutral: 'Nötr',
  surprised: 'Şaşkın',
  sad: 'Üzgün',
  angry: 'Kızgın',
};

function OzelTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    const toplam = payload.reduce((t, p) => t + (p.value || 0), 0);
    if (toplam === 0) return null;

    return (
      <div className="grafik-tooltip">
        <span style={{ fontWeight: 600 }}>{label}:00</span>
        {payload.filter(p => p.value > 0).map(p => (
          <div key={p.dataKey} style={{ color: p.fill, fontSize: '0.78rem' }}>
            {DUYGU_ETIKETLERI[p.dataKey] || p.dataKey}: {p.value}
          </div>
        ))}
        <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', marginTop: 4, paddingTop: 4, fontSize: '0.75rem' }}>
          Toplam: {toplam}
        </div>
      </div>
    );
  }
  return null;
}

export default function SaatlikDuyguTrendi({ trendVeri }) {
  if (!trendVeri?.hourly_emotions) {
    return (
      <div className="glass-card">
        <div className="card-header">
          <span className="icon">📈</span>
          <h2>Saatlik Duygu Trendi</h2>
        </div>
        <div className="card-body grafik-bos">
          <span className="bos-ikon">📊</span>
          <span>Henüz veri yok</span>
        </div>
      </div>
    );
  }

  const grafikVerisi = Object.entries(trendVeri.hourly_emotions).map(([saat, duygular]) => ({
    saat,
    ...duygular,
  }));

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📈</span>
        <h2>Saatlik Duygu Trendi</h2>
      </div>
      <div className="card-body">
        <div className="grafik-alani" style={{ height: 280 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={grafikVerisi} barCategoryGap="15%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="saat"
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                allowDecimals={false}
              />
              <Tooltip content={<OzelTooltip />} />
              <Legend
                formatter={(value) => (
                  <span style={{ color: '#94a3b8', fontSize: '0.72rem' }}>
                    {DUYGU_ETIKETLERI[value] || value}
                  </span>
                )}
              />
              {Object.entries(DUYGU_RENKLERI).map(([key, color]) => (
                <Bar
                  key={key}
                  dataKey={key}
                  stackId="duygu"
                  fill={color}
                  radius={key === 'angry' ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                  maxBarSize={28}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
