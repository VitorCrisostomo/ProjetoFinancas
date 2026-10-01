import React, { useState } from 'react';
import { PluggyConnect } from 'react-pluggy-connect';
import formatCurrency from "../utils/currency.jsx";
import Button from "../components/common/Button.jsx";

const AccountsPage = ({ accounts, onSyncAccount, onDeleteAccount }) => {
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [connectToken, setConnectToken] = useState("");
  const [isFetchingToken, setIsFetchingToken] = useState(false);

  const handlePluggySuccess = async (data) => {
    setIsWidgetOpen(false);
    setIsSyncing(true);

    const itemId = data.item.id;
    console.log("Conectado na Pluggy! Sincronizando Item ID:", itemId);

    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch('http://localhost:5000/pluggy/accounts/sync', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ itemId: itemId })
      });

      if (response.ok) {
        const result = await response.json();
        
        result.accounts.forEach(acc => {
          onSyncAccount(acc);
        });

        console.log("Contas sincronizadas! Buscando transações...");
        await fetch('http://localhost:5000/pluggy/transactions/sync', {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
          }
        });
        
        alert(`Sucesso! ${result.accounts.length} conta(s) sincronizada(s).`);
      } else {
        const errorData = await response.json();
        alert(`Erro na sincronização: ${errorData.message}`);
      }
    } catch (error) {
      console.error("Erro ao sincronizar contas:", error);
      alert("Falha de conexão com o servidor ao sincronizar.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleOpenWidget = async () => {
    setIsFetchingToken(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5000/pluggy/connect_token', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        const data = await response.json();
        setConnectToken(data.connectToken); // Salva o token gerado pelo backend
        setIsWidgetOpen(true);              // Abre o widget
      } else {
        alert("Erro ao preparar conexão com o banco.");
      }
    } catch (error) {
      console.error("Erro ao buscar connect token:", error);
      alert("Falha de conexão com o servidor.");
    } finally {
      setIsFetchingToken(false);
    }
  };

  return (
    <div className="page-content">
      <div className="page-header">
        <h1>Minhas Contas</h1>
        
        <Button variant="primary" size="lg" onClick={handleOpenWidget} disabled={isFetchingToken}>
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
              <div key={account.id} style={{
                border: '1px solid #eee',
                borderRadius: '12px',
                padding: '20px',
                boxShadow: '0 4px 6px rgba(0,0,0,0.05)',
                backgroundColor: 'white',
                display: 'flex',
                flexDirection: 'column',
                gap: '15px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <h3 style={{ margin: '0 0 5px 0', fontSize: '1.1em' }}>{account.name}</h3>
                    <span style={{ fontSize: '0.85em', color: '#666', background: '#f0f0f0', padding: '2px 8px', borderRadius: '12px' }}>
                      {account.subtype.replace('_', ' ')}
                    </span>
                  </div>
                  <span style={{ fontSize: '1.5em' }}>
                    {account.type === 'BANK' ? '🏦' : '💳'}
                  </span>
                </div>

                <div>
                  <p style={{ margin: '0', fontSize: '0.9em', color: '#888' }}>Agência/Conta</p>
                  <p style={{ margin: '0', fontWeight: '500' }}>{account.number}</p>
                </div>

                <div>
                  <p style={{ margin: '0', fontSize: '0.9em', color: '#888' }}>Saldo Atual</p>
                  <p style={{ margin: '0', fontSize: '1.4em', fontWeight: 'bold', color: account.balance >= 0 ? '#2e7d32' : '#d32f2f' }}>
                    {formatCurrency(account.balance)}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '10px', marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid #eee' }}>
                  <button 
                    onClick={() => onDeleteAccount(account.id)}
                    style={{ background: 'transparent', border: 'none', color: '#d32f2f', cursor: 'pointer', fontSize: '0.9em', padding: '5px' }}
                  >
                    Desconectar
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {isWidgetOpen && connectToken && (
        <PluggyConnect
          connectToken={connectToken}
          includeSandbox={true} 
          onSuccess={handlePluggySuccess}
          onError={(error) => {
            console.error("Erro no widget da Pluggy:", error);
            setIsWidgetOpen(false);
          }}
          onClose={() => setIsWidgetOpen(false)} 
        />
      )}
    </div>
  );
};

export default AccountsPage;