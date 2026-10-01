import { useRef } from 'react';
import Button from '../common/Button.jsx';

export default function TransactionToolbar({ selectedIds, handleExecuteAssociation,
  handleFileUpload, isUploading, isSyncing, handleSyncTransactions, handleOpenNewModal }) {
  const fileInput = useRef(null);
  return (
    <div className="page-header">
      <div>
        <h1>Transações</h1>
        <p>Gerencie e filtre suas receitas e despesas</p>
      </div>
      
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        {selectedIds.length === 2 && (
          <Button variant="secondary" size="lg" onClick={handleExecuteAssociation}>
            🔗 Associar (2)
          </Button>
        )}

        <input
          type="file"
          accept=".csv"
          ref={fileInput}
          style={{ display: 'none' }}
          onChange={async (event) => {
            const input = event.target;
            const file = input.files[0];
            try { await handleFileUpload(file); }
            finally { input.value = ''; }
          }}
        />
        
        <Button 
          variant="secondary" 
          size="lg" 
          onClick={() => fileInput.current?.click()}
          disabled={isUploading || isSyncing}
        >
          {isUploading ? '⏳ Importando...' : '📄 Importar CSV'}
        </Button>

        <Button variant="secondary" size="lg" onClick={handleSyncTransactions} disabled={isSyncing || isUploading}>
          {isSyncing ? '⏳ Sincronizando...' : '🔄 Sincronizar'}
        </Button>

        <Button variant="primary" size="lg" onClick={handleOpenNewModal}>
          ➕ Nova Transação
        </Button>
      </div>
    </div>
  );
}
