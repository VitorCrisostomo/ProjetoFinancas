import HomePage from '../pages/Home.jsx';
import OverviewPage from '../pages/Overview.jsx';
import TransactionsPage from '../pages/Transactions.jsx';
import AccountsPage from '../pages/Accounts.jsx';
import PersonalizationPage from '../pages/Personalization.jsx';

export const DEFAULT_PAGE = 'home';

export const pages = [
  { id: 'home', label: 'Início', icon: '🏠', component: HomePage },
  { id: 'overview', label: 'Visão geral', icon: '📊', component: OverviewPage },
  { id: 'transactions', label: 'Transações', icon: '📋', component: TransactionsPage },
  { id: 'accounts', label: 'Contas', icon: '🏦', component: AccountsPage },
  { id: 'personalization', label: 'Personalização', icon: '🎨', component: PersonalizationPage },
];

export const getPage = (id) => pages.find((page) => page.id === id) || pages[0];
