// Preserva classificações antigas e nomes ainda ausentes no catálogo carregado.
export const getCategoryCatalog = (categories = [], transactions = []) => {
  const catalog = new Map(categories.map((category) => [category.name, {
    ...category, subcategories: [...(category.subcategories || [])],
  }]));
  for (const transaction of transactions) {
    if (!transaction.category || transaction.is_opening_balance) continue;
    if (!catalog.has(transaction.category)) {
      catalog.set(transaction.category, { name: transaction.category, subcategories: [] });
    }
    const children = catalog.get(transaction.category).subcategories;
    if (transaction.subcategory && !children.some((child) => child.name === transaction.subcategory)) {
      children.push({ name: transaction.subcategory });
    }
  }
  return [...catalog.values()].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
};

export const getExpenseBreakdown = (transactions, category = null) => {
  const totals = new Map();
  for (const transaction of transactions) {
    if (transaction.type !== 'expense' || transaction.is_opening_balance) continue;
    if (category !== null && transaction.category !== category) continue;
    const name = category === null ? transaction.category || 'Sem categoria'
      : transaction.subcategory || 'Sem subcategoria';
    totals.set(name, (totals.get(name) || 0) + Math.round(Number(transaction.value) * 100));
  }
  return [...totals].map(([name, cents]) => ({ name, value: cents / 100 }))
    .sort((a, b) => b.value - a.value || a.name.localeCompare(b.name, 'pt-BR'));
};
