import { useState } from "react";
import { categoryIcons } from "../../utils/category";
import Button from "./Button";

const TransactionModal = ({ isOpen, onClose, onSave, transactionToEdit }) => {
  const categories = [...new Set([transactionToEdit?.category, ...Object.keys(categoryIcons)].filter(Boolean))];
  const [formData, setFormData] = useState(() => transactionToEdit ? {
    name: transactionToEdit.name,
    category: transactionToEdit.category,
    date: typeof transactionToEdit.date === 'string'
      ? transactionToEdit.date.split('T')[0] : transactionToEdit.date,
  } : { name: '', category: '', date: '' });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (transactionToEdit && formData.name && formData.date && formData.category) {
      onSave(formData, transactionToEdit.id);
    }
  };

  if (!isOpen || !transactionToEdit) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Editar Transação</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleSubmit} className="transaction-form">
          <div className="form-group">
            <label>Nome *</label>
            <input
              type="text"
              maxLength={120}
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="Ex: Supermercado"
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Categoria *</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                {categories.map((cat) => (
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
              Atualizar
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransactionModal;
