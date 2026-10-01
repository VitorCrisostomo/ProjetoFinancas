# Backend FinanceHub

API Flask com Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS e integração HTTP com Pluggy.

## Estrutura atual

| Arquivo ou pasta | Responsabilidade |
|---|---|
| `main.py` | Registra blueprints e executa o servidor de desenvolvimento. |
| `config.py` | Configura Flask, banco, JWT, CORS e erros. |
| `routes/` | Recebe requisições e monta respostas HTTP. |
| `services/` | Implementa validações, regras e integração bancária. |
| `repositories/` | Consulta e persiste os dados com SQLAlchemy. |
| `models/` | Define User, Account e Transaction. |
| `exceptions/` | Define APIError, NotFoundError e ValidationError. |
| `instance/` | Armazena o banco SQLite local, quando configurado. |

O fluxo usual é rota → serviço → repositório → modelo/banco. A sincronização de transações também consulta os modelos e utiliza a sessão diretamente no serviço; a rota Pluggy consulta as contas do usuário diretamente. Cada escrita dos repositórios confirma a sessão com `commit()`.

Ao executar `python main.py`, os modelos são importados e `db.create_all()` é chamado antes de iniciar o servidor com debug. Essa chamada cria tabelas ausentes; não migra tabelas existentes.

## Configuração e execução

Instale as dependências e ative o ambiente virtual conforme o [README da raiz](../README.md). Copie `.env.example` para `.env` nesta pasta e configure:

| Variável | Finalidade |
|---|---|
| `JWT_SECRET_KEY` | Chave de assinatura dos tokens de autenticação. |
| `DATABASE_URI` | URI SQLAlchemy. Exemplo local: `sqlite:///financehub.db`. |
| `PLUGGY_CLIENT_ID` | Identificador da integração Pluggy. |
| `PLUGGY_CLIENT_SECRET` | Segredo da integração Pluggy. |

Gere uma chave local com `python -c "import secrets; print(secrets.token_hex(32))"` e copie o resultado para `JWT_SECRET_KEY`. O `.env` local está ignorado pelo Git; o exemplo não contém credenciais reais.

Execute `python main.py` a partir de `backend/`. A API de desenvolvimento atende na porta 5000. Os imports atuais são resolvidos a partir dessa pasta.

## Contratos HTTP

Requisições JSON usam `Content-Type: application/json`. As rotas com JWT exigem `Authorization: Bearer <token>`. Os dados serializados de usuários não incluem senha nem código de verificação.

| Método | Caminho | JWT | Entrada principal |
|---|---|---|---|
| POST | `/create_users` | Não | `name`, `email`, `password` |
| POST | `/login` | Não | `email`, `password` |
| POST | `/verify_email` | Não | `email`, `code` |
| GET | `/users` | Não | — |
| PATCH | `/update_users/<user_id>` | Não | `firstName`, `password` |
| DELETE | `/delete_users/<user_id>` | Não | — |
| GET | `/accounts` | Sim | — |
| POST | `/accounts/sync` | Sim | Dados da conta externa, incluindo `id` |
| DELETE | `/accounts/<account_id>` | Sim | — |
| GET | `/transactions` | Sim | — |
| POST | `/create_transactions` | Sim | `name`, `value`, `date`, `category`; `type` e `description` opcionais |
| PATCH | `/update_transactions/<transaction_id>` | Sim | Campos da transação a atualizar |
| DELETE | `/transactions/<transaction_id>` | Sim | — |
| POST | `/transactions/associate` | Sim | `keep_id`, `remove_id`, `updated_data` |
| POST | `/transactions/import` | Sim | Arquivo no campo multipart `file` |
| GET | `/pluggy/connect_token` | Sim | — |
| POST | `/pluggy/accounts/sync` | Sim | `itemId` |
| POST | `/pluggy/transactions/sync` | Sim | — |

Criação de usuários, criação de transações e importação CSV retornam 201 no sucesso; as demais rotas retornam 200. Erros derivados de `APIError` retornam `{"message": "..."}` com o status associado. Erros do Flask e do JWT seguem os handlers das respectivas bibliotecas.

### Cadastro e autenticação

O cadastro gera um código de seis dígitos e o imprime no terminal, simulando o envio de e-mail. Repetir o cadastro para um e-mail ainda não verificado renova seus dados e o código. O login exige senha válida e cadastro verificado; retorna `access_token` e `user`.

### Contas e sincronização

O ID de conta é o UUID externo fornecido pela Pluggy. Novas contas exigem `type`, `subtype`, `itemId`, `number`, `name` e `balance`. Contas existentes atualizam saldo, nome e dados bancários/de crédito, mantendo o vínculo com o usuário.

O widget recebe `connectToken`; após a conexão, o frontend envia `itemId` para sincronizar as contas. A sincronização de transações percorre as contas do usuário e cria ou atualiza lançamentos por `external_id`. As consultas externas atuais utilizam `results` da resposta, sem percorrer páginas adicionais.

### Transações e CSV

Lançamentos manuais e atualizações usam datas `YYYY-MM-DD`. O tipo padrão na criação é `expense`; receitas usam `income`. Na sincronização bancária, o valor é armazenado como absoluto e o tipo representa sua direção.

A importação aceita UTF-8 com ou sem BOM e Latin-1 e detecta vírgula ou ponto e vírgula como separador. O formato implementado usa as seguintes colunas:

| Coluna | Uso |
|---|---|
| `Lançamento` | Nome; linhas sem nome e linhas de saldo são ignoradas. |
| `Data` | Data `DD/MM/YYYY`; `00/00/0000` é ignorado. |
| `Valor` | Formato brasileiro, como `-1.234,56`. |
| `Tipo Lançamento` | Opcional; texto contendo `entrada` indica receita, os demais indicam despesa. Na ausência, utiliza o sinal do valor. |
| `Detalhes` | Descrição opcional. |
| `N° documento` | Identificador opcional acrescentado à descrição. |

Os lançamentos importados recebem a categoria `Importado`. Cada linha é persistida separadamente; se uma linha posterior falhar, as anteriores permanecem gravadas. Valores zero são rejeitados pela validação de criação existente.

## Lint, formatação e comentários

O Ruff está fixado em `requirements-dev.txt`, com configuração em `pyproject.toml`. É uma ferramenta de desenvolvimento, não uma dependência de execução da API.

Na raiz do repositório:

```sh
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format backend --check
```

Para aplicar correções automáticas seguras e formatação, revise o diff resultante:

```sh
python -m ruff check backend --fix
python -m ruff format backend
```

O lint verifica imports, nomes indefinidos, variáveis sem uso e erros básicos de sintaxe. O formatador usa aspas duplas, quatro espaços e largura preferida de 100 caracteres. A análise considera sintaxe Python 3.10; dependências, ambientes virtuais e banco local são excluídos.

Comentários explicam regras, decisões ou limitações relevantes, sem instruções de edição nem repetição de linhas simples. Docstrings descrevem módulos, classes e operações principais. Os imports dos modelos em `main.py` possuem `noqa: F401` porque registram as tabelas antes de `create_all()`.

## Escopo desta revisão

Endpoints, validações, modelos, esquema de banco e organização das camadas foram mantidos. A documentação descreve o comportamento atual, inclusive o contrato legado de atualização de usuários e as permissões existentes. Mudanças funcionais ou estruturais devem ser tratadas em uma etapa própria.
