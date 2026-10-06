import formatCurrency from '../../utils/currency.jsx';
import FinancialValue from '../common/FinancialValue.jsx';

export default function AccountCard({ account, onDelete }) {
  return (
    <div className="card account-card">
      <div className="account-card-header">
        <div>
          <h3 className="account-card-name">{account.name}</h3>
          <span className="account-card-subtype">
            {account.subtype?.replaceAll('_', ' ')}
          </span>
        </div>
        <span className="account-card-icon" aria-hidden="true">
          {account.type === 'BANK' ? '🏦' : '💳'}
        </span>
      </div>

      <div>
        <p className="account-card-label">Agência/Conta</p>
        <p className="account-card-number">{account.number}</p>
      </div>

      <div>
        <p className="account-card-label">Saldo Atual</p>
        <p className={`account-card-balance ${account.balance >= 0 ? 'positive' : 'negative'}`}>
          <FinancialValue>{formatCurrency(account.balance)}</FinancialValue>
        </p>
      </div>

      <div className="account-card-footer">
        <button 
          onClick={() => onDelete(account.id)}
          type="button" className="account-disconnect"
        >
          Desconectar
        </button>
      </div>
    </div>
  );
}
