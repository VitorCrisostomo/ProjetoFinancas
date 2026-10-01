# Organização do frontend

O fluxo de dados segue: página → hook → serviço → API. Componentes recebem dados e callbacks; não fazem requisições HTTP.

## Pastas

- `src/App.jsx`: escolhe entre login e aplicação autenticada.
- `src/app/`: composição da sessão autenticada e registro das páginas.
- `src/components/layout/`: menu, cabeçalho e estrutura comum da aplicação.
- `src/pages/`: composição das telas.
- `src/components/transactions/`: barra de ações, filtros e tabela de transações.
- `src/components/accounts/`: apresentação de contas.
- `src/components/common/`: componentes reutilizáveis, incluindo formulário de transação.
- `src/hooks/`: autenticação, dados remotos e controles de interface.
- `src/services/`: requisições HTTP, endpoints e configuração da API.
- `src/utils/`: funções sem efeitos colaterais para formatação, categorias e resumos.
- `src/styles/`: estilos da aplicação.

## Navegação e sessão

`app/navigation.js` reúne IDs, rótulos, ícones e componentes das páginas. O menu e o conteúdo usam esse mesmo registro. A navegação continua baseada em estado local, sem mudança de URLs.

`AuthenticatedDashboard` instancia os hooks de dados uma vez por sessão e passa dados e ações para as páginas. Trocar de página mantém os dados; sair desmonta a aplicação autenticada e descarta seu estado.

Para adicionar uma página, registre-a em `navigation.js` e forneça suas propriedades no mapa `pageProps` de `AuthenticatedDashboard.jsx`.

## Hooks

- `useAuth`: usuário e ações de autenticação.
- `useAccounts` e `useTransactions`: carregamento e alterações persistidas no backend.
- `useCollection`: carregamento, erros e proteção contra respostas após o encerramento da sessão.
- `useTransactionControls`: filtros, seleção, formulário e feedback das ações de transação.
- `useAccountConnection`: abertura do widget, conexão e feedback das ações de conta.

Os hooks de dados retornam resultados ou lançam erros. Os controles de interface cuidam de confirmações e mensagens. O formulário de transação é montado ao abrir, inicializado com os dados da edição e descartado ao fechar.

## Serviços

Os serviços retornam `Response`. `readResponse`, em `services/api.js`, interpreta respostas nos hooks de dados e converte falhas HTTP em erros. O cliente comum adiciona o JWT e serializa JSON; arquivos CSV usam `FormData`.

`VITE_API_URL` configura o endereço do backend; consulte `.env.example`.

## Verificação

Na pasta `frontend`, execute `npm run build`, `npm run lint` e `npm test`. Ao alterar fluxos, valide também login, navegação, importação, sincronização e edição no navegador com o backend disponível.

## Períodos em Transações e Visão geral

Cada página mantém seus próprios filtros de mês e ano em `useTransactionPeriod`. A lógica comum fica em `utils/transactionPeriod.js`; a interface dos seletores fica em `TransactionPeriodFilter`.

O padrão mostra todo o histórico. É possível selecionar um ano inteiro, um mês em todos os anos ou a combinação de mês e ano. Os anos disponíveis são extraídos do histórico completo. As datas exibidas e os filtros usam a data de calendário recebida da API, sem conversão de fuso.

Em Transações, o período combina com categoria e tipo; ao selecionar um mês, todas as linhas correspondentes são exibidas. Sem mês selecionado, permanece o limite visual de 50 linhas. Mudar um filtro limpa a seleção para associação. Transações e Visão geral incluem o saldo anterior quando há um ano definido: o histórico anterior ao início do mês (ou do ano inteiro) é somado às movimentações filtradas. Mês sem ano não possui saldo anterior único. Receitas, despesas, gráficos e taxa de economia do Overview consideram somente o período. Períodos sem lançamentos mantêm o saldo anterior quando aplicável. Os filtros não alteram os dados persistidos.

## Modal de sincronização

O botão Sincronizar em Transações abre `SyncTransactionsModal`, um diálogo nativo com navegação por teclado, foco contido e fechamento por Escape. A sincronização é apenas manual, para um mês específico escolhido com o controle de mês e ano do navegador. O campo usa o período dos filtros quando definido; os valores ausentes vêm do período atual de São Paulo. Conectar uma conta salva os dados da conta e orienta o usuário a buscar as transações nesta tela, sem disparar a importação automaticamente. A API exige o período e rejeita a busca de todo o histórico.

`utils/transactionSync.js` monta as opções enviadas ao backend. `useTransactionControls` controla abertura, carregamento e erros. Durante a sincronização, os campos e o fechamento são bloqueados; uma falha mantém o modal aberto. Ao concluir, `useTransactions` recarrega a lista completa, preservando também os lançamentos manuais. A seleção de sincronização não modifica os filtros de visualização.
