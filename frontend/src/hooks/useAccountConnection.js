import { useState } from 'react';

export default function useAccountConnection({ onGetConnectToken, onSyncAccounts,
  onSyncTransactions, onDeleteAccount }) {
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [connectToken, setConnectToken] = useState("");
  const [isFetchingToken, setIsFetchingToken] = useState(false);

  const handlePluggySuccess = async (data) => {
    setIsWidgetOpen(false);
    setIsSyncing(true);
    try {
      const result = await onSyncAccounts(data.item.id);
      if (!result) return;
      await onSyncTransactions();
      alert(`Sucesso! ${result.accounts.length} conta(s) sincronizada(s).`);
    } catch (error) {
      alert(`Erro na sincronização: ${error.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleOpenWidget = async () => {
    setIsFetchingToken(true);
    try {
      const token = await onGetConnectToken();
      if (!token) return;
      setConnectToken(token);
      setIsWidgetOpen(true);
    } catch (error) {
      alert(`Erro ao preparar conexão com o banco: ${error.message}`);
    } finally {
      setIsFetchingToken(false);
    }
  };

  const handleDeleteAccount = async (id) => {
    if (!window.confirm('Tem certeza que deseja desconectar esta conta?')) return;
    try {
      await onDeleteAccount(id);
    } catch (error) {
      alert(`Erro ao desconectar conta: ${error.message}`);
    }
  };

  const closeWidget = () => setIsWidgetOpen(false);
  const handleWidgetError = (error) => {
    console.error('Erro no widget da Pluggy:', error);
    closeWidget();
  };

  return { isWidgetOpen, isSyncing, connectToken, isFetchingToken,
    handlePluggySuccess, handleOpenWidget, handleDeleteAccount, closeWidget, handleWidgetError };
}
