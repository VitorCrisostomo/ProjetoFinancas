import { useCallback, useEffect, useRef, useState } from 'react';

// Compartilha carregamento e impede que respostas de uma sessão encerrada alterem a lista.
export default function useCollection(fetchItems) {
  const [items, setItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const latestLoad = useRef(0);

  const execute = useCallback(async (request, update) => {
    const current = generation.current;
    setError('');
    try {
      const result = await request();
      if (current !== generation.current) return null;
      if (update) setItems((previous) => update(previous, result));
      return result;
    } catch (cause) {
      if (current === generation.current) setError(cause.message);
      throw cause;
    }
  }, []);

  const refresh = useCallback(async () => {
    const current = generation.current;
    const load = ++latestLoad.current;
    setIsLoading(true);
    setError('');
    try {
      const result = await fetchItems();
      if (current === generation.current && load === latestLoad.current) setItems(result);
      return result;
    } catch (cause) {
      if (current === generation.current && load === latestLoad.current) setError(cause.message);
      throw cause;
    } finally {
      if (current === generation.current && load === latestLoad.current) setIsLoading(false);
    }
  }, [fetchItems]);

  useEffect(() => {
    const current = generation.current;
    // Agenda o carregamento após a montagem e cancela o início se a sessão encerrar.
    Promise.resolve().then(() => {
      if (current === generation.current) return refresh();
    }).catch(() => {});
    return () => { generation.current += 1; };
  }, [refresh]);

  return { items, isLoading, error, execute, refresh };
}
