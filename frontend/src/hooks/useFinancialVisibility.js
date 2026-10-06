import { useContext } from 'react';
import FinancialVisibilityContext from '../app/FinancialVisibilityContext.js';

export default function useFinancialVisibility() {
  return useContext(FinancialVisibilityContext);
}
