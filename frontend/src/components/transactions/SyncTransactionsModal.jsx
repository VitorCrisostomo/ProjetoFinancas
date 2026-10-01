import { useEffect, useId, useRef, useState } from 'react';
import Button from '../common/Button.jsx';
import { getDefaultSyncMonth, getSyncOptions } from '../../utils/transactionSync.js';

export default function SyncTransactionsModal({ period, isSyncing, error, onClose, onSync }) {
  const dialogRef = useRef(null);
  const submitting = useRef(false);
  const id = useId();
  const [selectedMonth, setSelectedMonth] = useState(() => getDefaultSyncMonth(period));
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog.showModal();
    return () => { if (dialog.open) dialog.close(); };
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (isSyncing || submitting.current) return;
    setValidationError('');
    try {
      const options = getSyncOptions(selectedMonth);
      submitting.current = true;
      await onSync(options);
    } catch (cause) {
      setValidationError(cause.message);
    } finally {
      submitting.current = false;
    }
  };

  return (
    <dialog ref={dialogRef} className="modal-content sync-modal"
      aria-labelledby={`${id}-title`} aria-describedby={`${id}-description`}
      onCancel={(event) => { event.preventDefault(); if (!isSyncing) onClose(); }}>
      <div className="modal-header">
        <h2 id={`${id}-title`}>Sincronizar transações</h2>
        <button className="modal-close" type="button" aria-label="Fechar"
          disabled={isSyncing} onClick={onClose}>×</button>
      </div>
      <p id={`${id}-description`} className="sync-description">
        Escolha o mês e ano das transações que deseja buscar nas contas conectadas.
      </p>
      <form onSubmit={handleSubmit}>
        <fieldset className="sync-options" disabled={isSyncing}>
          <legend className="sr-only">Período da sincronização</legend>
          <div className="form-group">
            <label htmlFor={`${id}-month`}>Mês e ano</label>
            <input id={`${id}-month`} type="month" value={selectedMonth} min="1900-01"
              required onChange={(event) => { setSelectedMonth(event.target.value); setValidationError(''); }} />
          </div>
        </fieldset>
        {(validationError || error) && <p role="alert">{validationError || error}</p>}
        {isSyncing && <p role="status" className="sync-description">Sincronizando… Aguarde a conclusão.</p>}
        <div className="form-actions">
          <Button variant="secondary" onClick={onClose} disabled={isSyncing}>Cancelar</Button>
          <Button type="submit" disabled={isSyncing}>
            {isSyncing ? 'Sincronizando...' : 'Sincronizar'}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
