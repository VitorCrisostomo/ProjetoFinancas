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
| PATCH | `/update_transactions/<transaction_id>` | Sim | `name`, `date`, `category` e `subcategory` opcional; demais campos são rejeitados |
| GET | `/categories` | Sim | Catálogo do usuário com subcategorias |
| POST | `/categories` | Sim | `name` |
| POST | `/categories/<category_id>/subcategories` | Sim | `name`, dentro de uma categoria do usuário |
| POST | `/transactions/associate` | Sim | `transaction_ids` (dois ou mais IDs), `updated_data` opcional; aceita também o formato anterior com `keep_id` e `remove_id` |
| GET | `/pluggy/connect_token` | Sim | — |
| POST | `/pluggy/accounts/sync` | Sim | `itemId` |
| POST | `/pluggy/transactions/sync` | Sim | `mode: "month"`, `month`, `year` obrigatórios |

Criação de usuários, categorias e subcategorias retorna 201 no sucesso; as demais rotas retornam 200. Erros derivados de `APIError` retornam `{"message": "..."}` com o status associado. Erros do Flask e do JWT seguem os handlers das respectivas bibliotecas.

### Categorias e subcategorias

As tabelas `categories` e `subcategories` guardam o catálogo por usuário. Nomes têm até 50 caracteres; espaços excedentes são normalizados e nomes duplicados, independentemente de maiúsculas/minúsculas, são rejeitados. Categorias são únicas por usuário; subcategorias são únicas dentro de cada categoria. O mesmo nome de subcategoria pode existir em categorias diferentes. `Saldo anterior` é reservado aos ajustes automáticos.

Ao listar o catálogo pela primeira vez, o serviço acrescenta as categorias padrão e as categorias já presentes no histórico do usuário, sem reclassificar transações. A criação de uma subcategoria retorna a categoria com sua lista atualizada. Não há rotas para renomear ou excluir categorias nesta funcionalidade.

O catálogo inclui as subcategorias do BB fornecidas pelo usuário, somente nos grupos existentes: Moradia, Alimentação, Transporte, Saúde, Educação, Lazer, Compras, Investimentos e Taxas e Impostos. Despesas Pessoais / Vestuário corresponde a Compras; Faturas não é criada. A inclusão é idempotente, preserva subcategorias personalizadas e não atribui subcategorias automaticamente às transações. A lista fica em `DEFAULT_SUBCATEGORIES`, no serviço de categorias.

A inicialização executa `CategoryService().migrate_leisure_category()` após a criação das tabelas e da coluna de subcategoria. Esse procedimento renomeia Entretenimento para Lazer no catálogo e no histórico, preservando os demais campos e as proteções da sincronização. Se Lazer já existir, os filhos são reunidos sem duplicar nomes. A listagem do catálogo também aplica essa migração por usuário; inicializadores alternativos devem executá-la antes de atender requisições.

A transação mantém o campo `category` existente e acrescenta `subcategory`, uma classificação opcional. O backend valida que a subcategoria pertence à categoria do usuário antes de alterar qualquer campo. `null` remove a subcategoria; mudar a categoria sem informar subcategoria limpa a classificação filha anterior. Editar apenas nome ou data preserva a classificação. Associações mantêm a classificação da primeira transação, e edições de subcategoria também protegem o lançamento contra sobrescrita pela Pluggy.

Reinicie o backend com `python main.py` para aplicar a atualização do banco. A inicialização cria as tabelas do catálogo e acrescenta a coluna opcional `transactions.subcategory` quando ausente, sem modificar o histórico existente. O procedimento é idempotente; inicializadores alternativos devem executar `db.create_all()` e `TransactionRepository.initialize_subcategory_column()` no contexto da aplicação.

### Cadastro e autenticação

O cadastro gera um código de seis dígitos e o imprime no terminal, simulando o envio de e-mail. Repetir o cadastro para um e-mail ainda não verificado renova seus dados e o código. O login exige senha válida e cadastro verificado; retorna `access_token` e `user`.

### Contas e sincronização

O ID de conta é o UUID externo fornecido pela Pluggy. Novas contas exigem `type`, `subtype`, `itemId`, `number`, `name` e `balance`. Contas existentes atualizam saldo, nome e dados bancários/de crédito, mantendo o vínculo com o usuário.

O widget recebe `connectToken`; após a conexão, o frontend envia `itemId` para sincronizar as contas. A sincronização de transações percorre as contas do usuário e cria ou atualiza lançamentos por `external_id`. A busca segue todos os cursores `next` em `/v2/transactions`, conforme a [documentação da Pluggy](https://v2.docs.pluggy.ai/en/reference/transaction/transactions-list-by-cursor).

A sincronização é solicitada manualmente com `{"mode": "month", "year": 2026, "month": 10}`. Mês e ano devem ser números inteiros. O backend valida os valores e envia `dateFrom` e `dateTo` inclusivos, do primeiro ao último dia do mês. Requisições sem período ou com `mode: "all"` são rejeitadas. Conectar uma conta salva seus dados e o ajuste local de saldo anterior, sem importar transações bancárias automaticamente. Essa busca consulta o histórico já disponibilizado pelo provedor; não força uma atualização da conexão bancária.

### Saldo anterior automático

`TransactionService.reconcile_opening_balance` calcula, por conta e usuário, `saldo informado pela instituição - (receitas salvas - despesas salvas)`. O cálculo inclui lançamentos manuais vinculados à conta e preserva seus valores; ignora lançamentos sem vínculo com essa conta e o próprio ajuste. Usa Decimal para calcular e arredondar o resultado em centavos.

Há um único ajuste com `external_id` reservado `opening-balance:<account_id>`, categoria `Saldo anterior` e `is_opening_balance: true` no JSON. Valores negativos são armazenados como despesa e positivos como receita, mantendo a convenção dos demais lançamentos. A data é o último dia do mês anterior ao lançamento mais antigo da conta. Sem lançamentos, usa o início do histórico do usuário; sem histórico algum, usa o mês atual. Importar transações mais antigas move a data do mesmo ajuste, sem criar outro.

Ao conectar ou reconectar, conta e ajuste são salvos juntos. Na sincronização manual mensal, os dados das contas são consultados uma vez por item para obter saldos atualizados; ao finalizar a importação de cada conta, o ajuste é recalculado. As transações bancárias editadas ou associadas continuam protegidas. O ajuste automático não pode ser editado, excluído ou associado, nem pela API. Não exige coluna adicional nem migração da tabela de transações.

O saldo anterior é uma reconciliação estimada: períodos ausentes no histórico também entram na diferença. Não representa comprovação do saldo histórico naquela data. O cálculo usa o último saldo disponibilizado pela instituição e não garante atualização bancária em tempo real.

Os cursores são utilizados sem reconstrução; respostas inválidas, cursores repetidos e falhas do provedor retornam erro. Autenticação e consulta de transações têm timeout de 30 segundos por requisição. A sincronização preserva lançamentos manuais e transações de outros períodos. Como a persistência continua individual, uma falha em uma conta posterior pode deixar dados de contas anteriores já gravados.

A sincronização ignora identificadores externos protegidos em `transaction_sync_protections`. Qualquer edição de campos do lançamento, inclusive apenas categoria, protege a transação inteira. Uma associação protege os identificadores de ambos os lançamentos e mantém a proteção do excluído, impedindo sua recriação. Edição, proteção e exclusão da associação são confirmadas na mesma transação do banco; falhas desfazem a operação. Lançamentos novos e ainda não editados continuam sendo criados ou atualizados normalmente.

Ao iniciar `python main.py`, o repositório cria a tabela de proteção se estiver ausente e protege todos os identificadores externos existentes. Essa inicialização é executada apenas uma vez e preserva edições antigas, já que o banco não mantinha uma marcação de alterações. Não modifica valores nem recria lançamentos. Identificadores excluídos em associações anteriores à implementação não podem ser recuperados automaticamente. Reinicie o backend para ativar a inicialização; inicializadores alternativos devem chamar `TransactionRepository.initialize_sync_protection()` no contexto da aplicação.

Para executar os testes, sem rede ou credenciais, use `python -B -m unittest discover -s tests -v` na pasta `backend/`. Os testes de proteção usam SQLite em memória e exigem Flask e Flask-SQLAlchemy; não acessam o banco configurado em `.env`.

### Edição e associação de transações

Atualizações permitem somente `name`, `date` e `category`, com datas `YYYY-MM-DD`, e validam o usuário proprietário do lançamento. Alterações de valor, tipo, descrição e outros campos são rejeitadas antes de modificar o banco. Transações bancárias são criadas pela sincronização da Pluggy, com valor absoluto e tipo representando a direção. As rotas de criação manual, importação CSV e exclusão individual foram removidas; os registros históricos permanecem salvos.

Na sincronização, a referência `RF RESERVA COFR` em qualquer campo textual do lançamento, inclusive descrições e dados aninhados, define a categoria `Investimentos`. A comparação ignora maiúsculas/minúsculas e espaços repetidos. A regra tem prioridade sobre o mapeamento da categoria bancária, mas não modifica a direção ou o valor da movimentação e não se aplica a lançamentos protegidos por edição ou associação.

Associações podem resultar em valor zero quando receita e despesa se anulam. A edição mantém esse valor sem enviá-lo novamente ao backend. Os identificadores externos protegidos permanecem registrados após associações sucessivas, inclusive quando o resultado de uma associação anterior é excluído ao ser incorporado em outra.

A associação múltipla recebe `transaction_ids` em ordem de seleção, mantém o primeiro lançamento e exclui os demais em uma única confirmação no banco. O backend calcula receitas menos despesas em centavos; ignora valor e tipo enviados pelo cliente. Por padrão, a descrição combina os nomes (até 120 caracteres) e mantém data e categoria do primeiro lançamento. Todos os IDs devem ser distintos e pertencer ao usuário; ajustes automáticos não podem ser associados. Falhas desfazem todas as alterações e proteções da operação.

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
