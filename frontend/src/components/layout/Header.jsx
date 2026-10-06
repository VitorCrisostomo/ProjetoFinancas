import useFinancialVisibility from '../../hooks/useFinancialVisibility.js';

const Header = ({ userName }) => {
  const { valuesHidden, toggleValues } = useFinancialVisibility();
  const visibilityLabel = valuesHidden ? 'Mostrar valores financeiros' : 'Ocultar valores financeiros';
  return (
    <header className="header">
      <div className="header-content">
        <h2 className="header-title">Gerenciador Financeiro</h2>
        <div className="header-user">
          <div className="header-user-profile">
            <span className="user-avatar" aria-hidden="true">👤</span>
            <span className="user-name">{userName || 'Usuário'}</span>
          </div>
          <button className="values-visibility-button" type="button" onClick={toggleValues}
            aria-label={visibilityLabel} title={visibilityLabel} aria-pressed={valuesHidden}>
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor"
              strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z" />
              <circle cx="12" cy="12" r="3" />
              {valuesHidden && <line x1="3" y1="3" x2="21" y2="21" />}
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;
