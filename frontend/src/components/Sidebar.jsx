import React, { useState } from "react";
import { initialTransactions } from "../App";

const Sidebar = ({ currentPage, onPageChange, onLogout }) => {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  const navItems = [
    { id: 'home', label: 'Início', icon: '🏠' },
    { id: 'overview', label: 'Visão geral', icon: '📊' },
    { id: 'transactions', label: 'Transações', icon: '📋' },
  ];

  return (
    <>
      <button className="mobile-menu-btn" onClick={() => setIsMobileOpen(!isMobileOpen)}>
        ☰
      </button>

      <aside className={`sidebar ${isMobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">💰</div>
          <h1 className="sidebar-title">FinanceHub</h1>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.id}
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