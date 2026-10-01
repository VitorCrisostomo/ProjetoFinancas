const Header = ({ userName }) => {
  return (
    <header className="header">
      <div className="header-content">
        <h2 className="header-title">Gerenciador Financeiro</h2>
        <div className="header-user">
          <span className="user-avatar">👤</span>
          <span className="user-name">{userName || 'Usuário'}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;