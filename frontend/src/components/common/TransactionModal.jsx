import { useState, useEffect } from "react";
import { categoryIcons } from "../../utils/category";
import Button from "./Button";

const TransactionModal = ({ isOpen, onClose, onSave, transactionToEdit }) => {
  const defaultState = {
    name: '',
    category: 'Alimentação',
    value: '',
    type: 'expense',
    date: new Date().toISOString().split('T')[0],
  };

  const [formData, setFormData] = useState(defaultState);

  useEffect(() => {
    if (isOpen) {
      if (transactionToEdit) {
        setFormData({
          name: transactionToEdit.name,
          category: transactionToEdit.category,
          value: transactionToEdit.value,
          type: transactionToEdit.type,
          date: typeof transactionToEdit.date === 'string' ? transactionToEdit.date.split('T')[0] : transactionToEdit.date,
        });
      } else {
        setFormData(defaultState);
      }
    }
  }, [isOpen, transactionToEdit]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.name && formData.value) {
      onSave({
        ...formData,
        value: parseFloat(formData.value),
      }, transactionToEdit?.id); 
      
      setFormData(defaultState);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{transactionToEdit ? 'Editar Transação' : 'Nova Transação'}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="transaction-form">
          <div className="form-group">
            <label>Descrição *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ex: Supermercado"
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Tipo *</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              >
                <option value="expense">Despesa</option>
                <option value="income">Receita</option>
              </select>
            </div>

            <div className="form-group">
              <label>Valor *</label>
              <input
                type="number"
                step="0.01"
                value={formData.value}
                onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                placeholder="0.00"
                required
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Categoria *</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                {Object.keys(categoryIcons).map((cat) => (
                  <option key={cat} value={cat}>
                    {categoryIcons[cat]} {cat}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Data *</label>
              <input
                type="date"
                value={formData.date}
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="form-actions">
            <Button variant="secondary" onClick={onClose}>
              Cancelar
            </Button>
            <Button variant="primary" type="submit">
              {transactionToEdit ? 'Atualizar' : 'Salvar'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransactionModal;