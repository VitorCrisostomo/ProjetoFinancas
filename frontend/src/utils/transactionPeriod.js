export const months = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

export const getCurrentPeriod = (now = new Date()) => {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: 'numeric',
  }).formatToParts(now);
  return {
    month: parts.find((part) => part.type === 'month').value,
    year: parts.find((part) => part.type === 'year').value,
  };
};

export const getCurrentYear = (now = new Date()) => getCurrentPeriod(now).year;

export const normalizeTransactionPeriod = (month, year, now = new Date()) => ({
  month,
  year: month !== 'all' && year === 'all' ? getCurrentYear(now) : year,
});

// Preserva a data do lançamento, sem deslocar dias por conversão de fuso horário.
export const getTransactionDateParts = (date) => {
  if (typeof date !== 'string') return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:$|[T ])/.exec(date);
  if (!match) return null;
  const [, yearText, monthText, dayText] = match;
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  const leapYear = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]) return null;
  return { year, month, day };
};

export const getTransactionYears = (transactions) => [...new Set(
  transactions.map((transaction) => getTransactionDateParts(transaction.date)?.year)
    .filter((year) => year !== undefined),
)].sort((a, b) => b - a);

export const filterTransactionsByPeriod = (transactions, month = 'all', year = 'all', now = new Date()) => {
  ({ month, year } = normalizeTransactionPeriod(month, year, now));
  if (month === 'all' && year === 'all') return transactions;
  return transactions.filter((transaction) => {
    const date = getTransactionDateParts(transaction.date);
    return date !== null
      && (month === 'all' || date.month === Number(month))
      && (year === 'all' || date.year === Number(year));
  });
};
