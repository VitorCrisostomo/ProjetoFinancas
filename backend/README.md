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

Ao executar `python main.py`, a inicialização cria tabelas ausentes e executa as migrações incrementais existentes. Debug fica desativado por padrão. Em um servidor WSGI, execute `python -m flask --app main init-db` uma vez antes de iniciar o serviço; importar `main:app` não migra o banco.

## Configuração e execução

Instale as dependências e ative o ambiente virtual conforme o [README da raiz](../README.md). Copie `.env.example` para `.env` nesta pasta e configure:

| Variável | Finalidade |
|---|---|
| `JWT_SECRET_KEY` | Chave de assinatura dos tokens de autenticação. |
| `AUTH_COOKIE_SECURE` | `true` por padrão; exige HTTPS. Use `false` somente no desenvolvimento local com HTTP. |
| `AUTH_ALLOWED_ORIGINS` | Origens exatas separadas por vírgula. Em produção, somente o endereço HTTPS da aplicação. |
| `DATABASE_URI` | URI SQLAlchemy. Exemplo local: `sqlite:///financehub.db`. |
| `PLUGGY_CLIENT_ID` | Identificador da integração Pluggy. |
| `PLUGGY_CLIENT_SECRET` | Segredo da integração Pluggy. |

Gere uma chave local com `python -c "import secrets; print(secrets.token_hex(32))"` e copie o resultado para `JWT_SECRET_KEY`. A aplicação recusa chaves com menos de 32 caracteres. O `.env` local está ignorado pelo Git; o exemplo não contém credenciais reais. Se estiver reutilizando um `.env`, acrescente as novas variáveis a partir do exemplo.

Execute `python main.py` a partir de `backend/`. A API de desenvolvimento atende na porta 5000. Os imports atuais são resolvidos a partir dessa pasta.

## Contratos HTTP

Requisições JSON usam `Content-Type: application/json`. A sessão JWT fica exclusivamente em cookie `HttpOnly`, `SameSite=Lax` e, por padrão, `Secure`. O navegador envia `credentials: include`. Escritas autenticadas exigem `X-CSRF-TOKEN`, recebido no login ou em `GET /auth/session` e mantido somente em memória pelo frontend. Tokens Bearer antigos não são aceitos. Os dados serializados não incluem senha, código de verificação ou JWT.

| Método | Caminho | JWT | Entrada principal |
|---|---|---|---|
| POST | `/create_users` | — | Cadastro público fechado; retorna 403 |
| POST | `/login` | Não | `email`, `password` |
| POST | `/verify_email` | — | Verificação pública fechada; retorna 403 |
| GET | `/auth/session` | Sim | Próprio perfil e proteção CSRF |
| POST | `/logout` | Sim | Revoga a sessão atual e remove o cookie |
| GET | `/users` | Sim | Apenas o próprio perfil, em `users` |
| PATCH | `/update_users/<user_id>` | Sim | Próprio ID; `name` ou `firstName`, senha nova opcional, `current_password` obrigatório |
| DELETE | `/delete_users/<user_id>` | Sim | Próprio ID; `current_password` obrigatório; remove também os próprios dados financeiros |
| GET | `/accounts` | Sim | — |
| DELETE | `/accounts/<account_id>` | Sim | — |
| GET | `/transactions` | Sim | — |
| PATCH | `/update_transactions/<transaction_id>` | Sim | `name`, `date`, `category` e `subcategory` opcional; demais campos são rejeitados |
| GET | `/categories` | Sim | Catálogo do usuário com subcategorias |
| POST | `/categories` | Sim | `name` |
| POST | `/categories/<category_id>/subcategories` | Sim | `name`, dentro de uma categoria do usuário |
| POST | `/transactions/associate` | Sim | `transaction_ids` (dois ou mais IDs), `updated_data` opcional; aceita também o formato anterior com `keep_id` e `remove_id` |
| POST | `/pluggy/connect_token` | Sim | — |
| POST | `/pluggy/accounts/sync` | Sim | `itemId` |
| POST | `/pluggy/transactions/sync` | Sim | `mode: "month"`, `month`, `year` obrigatórios |

Criação de categorias e subcategorias retorna 201; demais operações habilitadas retornam 200. Erros de serviço e de autenticação usam `{"message": "..."}`. Sessões ausentes, expiradas, revogadas ou CSRF inválido retornam 401. Tentativas de acessar recursos alheios são rejeitadas no servidor. Respostas da API usam `Cache-Control: no-store`.

### Categorias e subcategorias

As tabelas `categories` e `subcategories` guardam o catálogo por usuário. Nomes têm até 50 caracteres; espaços excedentes são normalizados e nomes duplicados, independentemente de maiúsculas/minúsculas, são rejeitados. Categorias são únicas por usuário; subcategorias são únicas dentro de cada categoria. O mesmo nome de subcategoria pode existir em categorias diferentes. `Saldo anterior` é reservado aos ajustes automáticos.

Ao listar o catálogo pela primeira vez, o serviço acrescenta as categorias padrão e as categorias já presentes no histórico do usuário, sem reclassificar transações. A criação de uma subcategoria retorna a categoria com sua lista atualizada. Não há rotas para renomear ou excluir categorias nesta funcionalidade.

O catálogo inclui as subcategorias do BB fornecidas pelo usuário, somente nos grupos existentes: Moradia, Alimentação, Transporte, Saúde, Educação, Lazer, Compras, Investimentos e Taxas e Impostos. Despesas Pessoais / Vestuário corresponde a Compras; Faturas não é criada. A inclusão é idempotente, preserva subcategorias personalizadas e não atribui subcategorias automaticamente às transações. A lista fica em `DEFAULT_SUBCATEGORIES`, no serviço de categorias.

A inicialização executa `CategoryService().migrate_leisure_category()` após a criação das tabelas e da coluna de subcategoria. Esse procedimento renomeia Entretenimento para Lazer no catálogo e no histórico, preservando os demais campos e as proteções da sincronização. Se Lazer já existir, os filhos são reunidos sem duplicar nomes. A listagem do catálogo também aplica essa migração por usuário; inicializadores alternativos devem executá-la antes de atender requisições.

A transação mantém o campo `category` existente e acrescenta `subcategory`, uma classificação opcional. O backend valida que a subcategoria pertence à categoria do usuário antes de alterar qualquer campo. `null` remove a subcategoria; mudar a categoria sem informar subcategoria limpa a classificação filha anterior. Editar apenas nome ou data preserva a classificação. Associações mantêm a classificação da primeira transação, e edições de subcategoria também protegem o lançamento contra sobrescrita pela Pluggy.

Reinicie o backend com `python main.py` para aplicar a atualização do banco. A inicialização cria as tabelas do catálogo e acrescenta a coluna opcional `transactions.subcategory` quando ausente, sem modificar o histórico existente. O procedimento é idempotente; inicializadores alternativos devem executar `db.create_all()` e `TransactionRepository.initialize_subcategory_column()` no contexto da aplicação.

### Cadastro e autenticação

O cadastro público e a verificação por e-mail simulada foram desativados. Somente quem administra o servidor e tem acesso ao seu terminal pode criar acessos. Não há função administrativa acessível aos familiares pela API.

Na pasta `backend/`, com o ambiente Python ativo:

```sh
python -m flask --app main init-db
python -m flask --app main create-user
```

O comando solicita nome, e-mail e senha, com confirmação e entrada oculta. Senhas novas devem ter entre 12 e 128 caracteres e recebem hash no servidor. E-mails são normalizados; um cadastro existente, mesmo pendente, nunca é sobrescrito por uma tentativa de criação.

Para recuperar uma conta existente, inclusive uma conta antiga pendente de verificação ou com senha inválida:

```sh
python -m flask --app main reset-password
```

O administrador informa e-mail e nova senha. O comando confirma o acesso e revoga todas as sessões anteriores. Não envia e-mail nem imprime a senha.

O login retorna `user` e `csrf_token`; o JWT é entregue somente no cookie. A sessão expira em oito horas, sem renovação automática. O frontend restaura o perfil após recarregar a página e comunica login/logout às outras abas da mesma origem. Cada navegador compartilha sua sessão entre abas; dispositivos diferentes têm sessões independentes.

As tabelas adicionais `auth_sessions`, `login_attempts` e `user_security` preservam a revogação, as falhas recentes e uma identidade bancária opaca. Nenhuma coluna existente foi alterada. Reiniciar com `python main.py` cria essas tabelas automaticamente; para WSGI, use `init-db`. Faça backup antes de aplicar a atualização. Sessões antigas exigem novo login; senhas e histórico financeiro existentes são preservados.

Toda rota autenticada confere sessão persistida, proprietário, validade e usuário ainda verificado. Logout revoga apenas a sessão atual; troca de senha revoga todas as sessões daquele usuário. Mudanças de perfil e exclusão exigem senha atual e o próprio ID. A senha nova recebe um hash novo, mesmo se o texto enviado se parecer com um hash.

Falhas de login são limitadas a cinco por e-mail ou vinte por endereço de origem em quinze minutos, com registros persistentes e identificadores protegidos por HMAC. Limites continuam válidos após reiniciar o servidor. A API usa o endereço de conexão, sem confiar em `X-Forwarded-For` enviado pelo cliente. Ao implantar atrás de proxy, configure encaminhamento confiável na infraestrutura; até lá, o limite por IP pode ser compartilhado pelos usuários do proxy.

A configuração CORS admite somente as origens especificadas e permite cookies. Requisições que alteram dados com uma origem não autorizada também são recusadas antes de executar a rota. Para acesso remoto, mantenha frontend e API na mesma origem HTTPS e `AUTH_COOKIE_SECURE=true`; o uso local de HTTP não é configuração de produção.

### Contas e sincronização

O ID de conta é o UUID externo fornecido pela Pluggy. Novas contas exigem `type`, `subtype`, `itemId`, `number`, `name` e `balance`. Contas existentes atualizam saldo, nome e dados bancários/de crédito, mantendo o vínculo com o usuário.

O widget recebe `connectToken` vinculado ao usuário por `options.clientUserId`, usando a referência opaca persistida em `user_security`. O frontend envia apenas `itemId`; o servidor consulta `/items/<id>` e valida esse vínculo antes de buscar ou salvar contas. IDs numéricos de usuário eventualmente reutilizados não herdam conexões. A geração de token agora usa POST e exige CSRF. O antigo `/accounts/sync`, que aceitava dados bancários fornecidos pelo navegador, foi removido. A sincronização de transações percorre as contas do usuário e cria ou atualiza lançamentos por `external_id`. A busca segue todos os cursores `next` em `/v2/transactions`, conforme a [documentação da Pluggy](https://v2.docs.pluggy.ai/en/reference/transaction/transactions-list-by-cursor).

Itens antigos sem referência, ou com a referência numérica antiga, só são aceitos quando já possuem contas locais e todas pertencem ao usuário autenticado. Itens desconhecidos sem vínculo são recusados e exigem nova conexão. Não há atribuição automática de conexões de terceiros. Antes de sincronizar transações, o servidor repete a validação dos itens e verifica que as contas retornadas pertencem à conexão consultada. A lógica de lançamentos editados/associados e de saldo anterior permanece preservada.

A sincronização é solicitada manualmente com `{"mode": "month", "year": 2026, "month": 10}`. Mês e ano devem ser números inteiros. O backend valida os valores e envia `dateFrom` e `dateTo` inclusivos, do primeiro ao último dia do mês. Requisições sem período ou com `mode: "all"` são rejeitadas. Conectar uma conta salva seus dados e o ajuste local de saldo anterior, sem importar transações bancárias automaticamente. Essa busca consulta o histórico já disponibilizado pelo provedor; não força uma atualização da conexão bancária.

### Saldo anterior automático

`TransactionService.reconcile_opening_balance` calcula, por conta e usuário, `saldo informado pela instituição - (receitas salvas - despesas salvas)`. O cálculo inclui lançamentos manuais vinculados à conta e preserva seus valores; ignora lançamentos sem vínculo com essa conta e o próprio ajuste. Usa Decimal para calcular e arredondar o resultado em centavos.

Há um único ajuste com `external_id` reservado `opening-balance:<account_id>`, categoria `Saldo anterior` e `is_opening_balance: true` no JSON. Valores negativos são armazenados como despesa e positivos como receita, mantendo a convenção dos demais lançamentos. A data é o último dia do mês anterior ao lançamento mais antigo da conta. Sem lançamentos, usa o início do histórico do usuário; sem histórico algum, usa o mês atual. Importar transações mais antigas move a data do mesmo ajuste, sem criar outro.

Ao conectar ou reconectar, conta e ajuste são salvos juntos. Na sincronização manual mensal, os dados das contas são consultados uma vez por item para obter saldos atualizados; ao finalizar a importação de cada conta, o ajuste é recalculado. As transações bancárias editadas ou associadas continuam protegidas. O ajuste automático não pode ser editado, excluído ou associado, nem pela API. Não exige coluna adicional nem migração da tabela de transações.

O saldo anterior é uma reconciliação estimada: períodos ausentes no histórico também entram na diferença. Não representa comprovação do saldo histórico naquela data. O cálculo usa o último saldo disponibilizado pela instituição e não garante atualização bancária em tempo real.

Os cursores são utilizados sem reconstrução; respostas inválidas, cursores repetidos e falhas do provedor retornam erro. Todas as consultas Pluggy têm timeout de 30 segundos por requisição. A sincronização preserva lançamentos manuais e transações de outros períodos. Como a persistência continua individual, uma falha em uma conta posterior pode deixar dados de contas anteriores já gravados.

A sincronização ignora identificadores externos protegidos em `transaction_sync_protections`. Qualquer edição de campos do lançamento, inclusive apenas categoria, protege a transação inteira. Uma associação protege os identificadores de ambos os lançamentos e mantém a proteção do excluído, impedindo sua recriação. Edição, proteção e exclusão da associação são confirmadas na mesma transação do banco; falhas desfazem a operação. Lançamentos novos e ainda não editados continuam sendo criados ou atualizados normalmente.

Ao iniciar `python main.py`, o repositório cria a tabela de proteção se estiver ausente e protege todos os identificadores externos existentes. Essa inicialização é executada apenas uma vez e preserva edições antigas, já que o banco não mantinha uma marcação de alterações. Não modifica valores nem recria lançamentos. Identificadores excluídos em associações anteriores à implementação não podem ser recuperados automaticamente. Reinicie o backend para ativar a inicialização; inicializadores alternativos devem chamar `TransactionRepository.initialize_sync_protection()` no contexto da aplicação.

Para executar os testes, sem rede ou credenciais, use `python -B -m unittest discover -s tests -v` na pasta `backend/`. Os testes usam SQLite em memória e dependências da aplicação, sem acessar o banco configurado em `.env`. A suíte de autenticação utiliza Flask-JWT-Extended real e chaves estrangeiras habilitadas; testa cookies, CSRF, revogação, limitação de login, provisionamento administrativo, propriedade Pluggy e isolamento entre dois usuários.

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
