import React, { useState } from "react";
import { initialTransactions } from "../../App";
import { categoryIcons } from "../../utils/category";
import Button from "./Button";

const TransactionModal = ({ isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    name: '',
    category: 'Alimentação',
    amount: '',
    type: 'expense',
    date: new Date().toISOString().split('T')[0],
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.name && formData.amount) {
      onSave({
        ...formData,
        amount: parseFloat(formData.amount),
      });
      setFormData({
        name: '',
        category: 'Alimentação',
        amount: '',
        type: 'expense',
        date: new Date().toISOString().split('T')[0],
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Nova Transação</h2>
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
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
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
              Salvar Transação
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default TransactionModal;