import { useEffect, useState } from 'react';
import FinancialVisibilityContext from './FinancialVisibilityContext.js';

function readPreference(key) {
  try {
    return window.localStorage.getItem(key) === 'true';
  } catch {
    return false;
  }
}

export default function FinancialVisibilityProvider({ userId, children }) {
  const storageKey = `financehub:values-hidden:${userId}`;
  const [valuesHidden, setValuesHidden] = useState(() => readPreference(storageKey));

  useEffect(() => {
    try {
      window.localStorage.setItem(storageKey, String(valuesHidden));
    } catch {
      // A preferência continua funcionando quando o navegador bloqueia o armazenamento.
    }
  }, [storageKey, valuesHidden]);

  return (
    <FinancialVisibilityContext.Provider value={{
      valuesHidden,
      toggleValues: () => setValuesHidden((previous) => !previous),
    }}>
      {children}
    </FinancialVisibilityContext.Provider>
  );
}
