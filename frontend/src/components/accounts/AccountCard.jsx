import formatCurrency from '../../utils/currency.jsx';

export default function AccountCard({ account, onDelete }) {
  return (
    <div style={{
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
          onClick={() => onDelete(account.id)}
          style={{ background: 'transparent', border: 'none', color: '#d32f2f', cursor: 'pointer', fontSize: '0.9em', padding: '5px' }}
        >
          Desconectar
        </button>
      </div>
    </div>
  );
}
