import useFinancialVisibility from '../../hooks/useFinancialVisibility.js';

export default function FinancialValue({ children }) {
  const { valuesHidden } = useFinancialVisibility();

  // O modo oculto também evita copiar ou anunciar o valor real em leitores de tela.
  return (
    <span className={`financial-value${valuesHidden ? ' is-hidden' : ''}`}>
      <span className={valuesHidden ? 'financial-value-mask' : undefined} aria-hidden={valuesHidden || undefined}>
        {valuesHidden ? '••••••' : children}
      </span>
      {valuesHidden && <span className="sr-only">Valor oculto</span>}
    </span>
  );
}
