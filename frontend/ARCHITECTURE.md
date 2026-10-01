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

Na pasta `frontend`, execute `npm run build` e `npm run lint`. Ao alterar fluxos, valide também login, navegação, importação, sincronização e edição no navegador com o backend disponível.
