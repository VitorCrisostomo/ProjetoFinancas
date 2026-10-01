import Sidebar from './Sidebar.jsx';
import Header from './Header.jsx';

export default function AppLayout({ user, currentPage, onPageChange, onLogout, children }) {
  return (
    <div className="app-container">
      <Sidebar currentPage={currentPage} onPageChange={onPageChange} onLogout={onLogout} />
      <div className="main-content">
        <Header userName={user.name} />
        <main className="content-area">{children}</main>
      </div>
    </div>
  );
}
