import Button from '../common/Button.jsx';

export default function TransactionToolbar({ selectedIds, handleExecuteAssociation,
  isSyncing, isAssociating, openSyncModal }) {
  return (
    <div className="page-header">
      <div>
        <h1>Transações</h1>
        <p>Gerencie e filtre suas receitas e despesas</p>
      </div>
      
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        {selectedIds.length >= 2 && (
          <Button variant="secondary" size="lg" onClick={handleExecuteAssociation}
            disabled={isAssociating || isSyncing}>
            {isAssociating ? 'Associando...' : `🔗 Associar (${selectedIds.length})`}
          </Button>
        )}

        <Button variant="secondary" size="lg" onClick={openSyncModal} disabled={isSyncing || isAssociating}>
          {isSyncing ? '⏳ Sincronizando...' : '🔄 Sincronizar'}
        </Button>

      </div>
    </div>
  );
}
