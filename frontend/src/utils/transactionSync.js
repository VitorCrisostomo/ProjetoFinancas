export const getDefaultSyncMonth = (period, now = new Date()) => {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit',
  }).formatToParts(now);
  const currentYear = parts.find((part) => part.type === 'year').value;
  const currentMonth = parts.find((part) => part.type === 'month').value;
  const year = period?.year && period.year !== 'all' ? period.year : currentYear;
  const month = period?.month && period.month !== 'all' ? period.month : currentMonth;
  return `${year}-${String(month).padStart(2, '0')}`;
};

export const getSyncOptions = (selectedMonth) => {
  const match = /^(\d{4})-(\d{2})$/.exec(selectedMonth || '');
  if (!match || Number(match[1]) < 1900
    || Number(match[2]) < 1 || Number(match[2]) > 12) {
    throw new Error('Escolha um mês e ano válidos.');
  }
  return { mode: 'month', year: Number(match[1]), month: Number(match[2]) };
};
