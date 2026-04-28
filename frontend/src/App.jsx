/**
 * App — Ana Uygulama Kabugu
 * ===========================
 * Routing ve navigation bar.
 * Sayfa icerikleri CanliTespit ve AnalizPaneli'nde.
 */

import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import CanliTespit from './pages/CanliTespit';
import AnalizPaneli from './pages/AnalizPaneli';
import './index.css';

function App() {
  return (
    <div className="app-container">
      {/* ─── Header + Navigation ─── */}
      <header className="app-header">
        <div className="header-marka">
          <h1>🎭 Duygu Analiz Platformu</h1>
          <p className="subtitle">Gerçek Zamanlı Müşteri Duygu Analizi</p>
        </div>

        <nav className="app-nav">
          <NavLink
            to="/"
            end
            className={({ isActive }) => `nav-link ${isActive ? 'aktif' : ''}`}
          >
            <span className="nav-ikon">📹</span>
            Canlı Tespit
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `nav-link ${isActive ? 'aktif' : ''}`}
          >
            <span className="nav-ikon">📊</span>
            Analiz Paneli
          </NavLink>
        </nav>
      </header>

      {/* ─── Sayfa icerigi ─── */}
      <main className="app-main">
        <Routes>
          <Route path="/" element={<CanliTespit />} />
          <Route path="/dashboard" element={<AnalizPaneli />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
