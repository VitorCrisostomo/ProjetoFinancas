import { PluggyConnect } from 'react-pluggy-connect';
import Button from "../components/common/Button.jsx";
import AccountCard from '../components/accounts/AccountCard.jsx';
import useAccountConnection from '../hooks/useAccountConnection.js';

const AccountsPage = ({ accounts, ...actions }) => {
  const { isWidgetOpen, isSyncing, connectToken, isFetchingToken,
    handlePluggySuccess, handleOpenWidget, handleDeleteAccount, closeWidget,
    handleWidgetError } = useAccountConnection(actions);

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Minhas Contas</h1>
        
        <Button variant="primary" size="lg" onClick={handleOpenWidget} disabled={isFetchingToken || isSyncing}>
          {isFetchingToken ? "⏳ Preparando ambiente seguro..." : "🔗 Conectar Nova Conta"}
        </Button>
      </div>

      <div className="section">
        <p className="text-muted" style={{ marginBottom: '20px' }}>
          Gerencie suas contas bancárias e cartões de crédito sincronizados via Open Finance.
        </p>

        {isSyncing && (
          <div style={{ padding: '20px', textAlign: 'center', background: '#f8f9fa', borderRadius: '8px', marginBottom: '20px' }}>
            ⏳ Sincronizando dados com a instituição financeira...
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
          {accounts.length === 0 && !isSyncing ? (
            <div className="empty-state" style={{ gridColumn: '1 / -1', padding: '40px' }}>
              Nenhuma conta conectada. Clique no botão acima para conectar.
            </div>
          ) : (
            accounts.map((account) => (
              <AccountCard key={account.id} account={account} onDelete={handleDeleteAccount} />
            ))
          )}
        </div>
      </div>

      {isWidgetOpen && connectToken && (
        <PluggyConnect
          connectToken={connectToken}
          includeSandbox={true} 
          onSuccess={handlePluggySuccess}
          onError={handleWidgetError}
          onClose={closeWidget}
        />
      )}
    </div>
  );
};

export default AccountsPage;
