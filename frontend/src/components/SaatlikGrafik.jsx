/**
 * SaatlikGrafik Bileseni
 * =======================
 * Recharts BarChart ile saatlik musteri yogunlugunu gosterir.
 */

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

function OzelTooltip({ active, payload, label }) {
  if (active && payload && payload.length) {
    return (
      <div className="grafik-tooltip">
        <span>{label}:00</span>
        <strong>{payload[0].value} müşteri</strong>
      </div>
    );
  }
  return null;
}

export default function SaatlikGrafik({ saatlikVeri }) {
  if (!saatlikVeri || !saatlikVeri.hourly_visits) {
    return (
      <div className="glass-card">
        <div className="card-header">
          <span className="icon">📊</span>
          <h2>Saatlik Müşteri Yoğunluğu</h2>
        </div>
        <div className="card-body grafik-bos">
          <span className="bos-ikon">📈</span>
          <span>Henüz veri yok</span>
        </div>
      </div>
    );
  }

  const grafikVerisi = Object.entries(saatlikVeri.hourly_visits).map(([saat, sayi]) => ({
    saat: `${saat}`,
    sayi: sayi,
  }));

  return (
    <div className="glass-card">
      <div className="card-header">
        <span className="icon">📊</span>
        <h2>Saatlik Müşteri Yoğunluğu</h2>
      </div>
      <div className="card-body">
        <div className="grafik-alani" style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={grafikVerisi} barCategoryGap="20%">
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
              <Bar
                dataKey="sayi"
                fill="url(#barGradient)"
                radius={[4, 4, 0, 0]}
                maxBarSize={32}
              />
              <defs>
                <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.6} />
                </linearGradient>
              </defs>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
