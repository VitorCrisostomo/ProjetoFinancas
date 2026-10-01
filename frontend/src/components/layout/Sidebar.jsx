import { useState } from "react";
import { pages } from "../../app/navigation.js";

const Sidebar = ({ currentPage, onPageChange, onLogout }) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      <button aria-label="Abrir ou fechar menu" aria-expanded={isMobileOpen} className="mobile-menu-btn" onClick={() => setIsMobileOpen(!isMobileOpen)}>
        ☰
      </button>

      <aside className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">💰</div>
          <h1 className="sidebar-title">FinanceHub</h1>
        </div>

        <nav className="sidebar-nav" aria-label="Navegação principal">
          {pages.map((item) => (
            <button
              key={item.id}
              aria-current={currentPage === item.id ? "page" : undefined}
              className={`nav-item ${currentPage === item.id ? 'active' : ''}`}
              onClick={() => {
                onPageChange(item.id);
                setIsMobileOpen(false);
              }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="nav-item logout-btn" onClick={onLogout} style={{ width: '100%', color: 'var(--accent-danger)' }}>
            <span className="nav-icon">🚪</span>
            <span className="nav-label">Sair</span>
          </button>
        </div>
      </aside>

      {isMobileOpen && (
        <div className="mobile-overlay" onClick={() => setIsMobileOpen(false)} />
      )}
    </>
  );
};

export default Sidebar;