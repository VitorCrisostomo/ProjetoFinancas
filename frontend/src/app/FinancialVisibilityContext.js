import { createContext } from 'react';

const FinancialVisibilityContext = createContext({ valuesHidden: false, toggleValues: () => {} });

export default FinancialVisibilityContext;
