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
| `models/` | Define usuários, catálogo e modelos financeiros com conteúdo criptografado. |
| `exceptions/` | Define APIError, NotFoundError e ValidationError. |
| `instance/` | Armazena o banco SQLite local, quando configurado. |

O fluxo usual é rota → serviço → repositório → modelo/banco. A sincronização de transações também consulta os modelos e utiliza a sessão diretamente no serviço; a rota Pluggy consulta as contas do usuário diretamente. Cada escrita dos repositórios confirma a sessão com `commit()`.

Ao executar `python main.py`, a inicialização verifica o esquema financeiro, cria tabelas ausentes e executa as migrações incrementais existentes. Um banco financeiro antigo precisa primeiro da migração offline descrita abaixo; a aplicação não a executa automaticamente. Debug fica desativado por padrão. Em um servidor WSGI, execute `python -m flask --app main init-db` uma vez antes de iniciar o serviço; importar `main:app` não migra o banco. Requisições também conferem o esquema e retornam 503 enquanto a migração necessária não tiver sido aplicada.

## Configuração e execução

Use Python 3.11 ou superior, com suporte a `sqlite3.Connection.serialize()` e `deserialize()`, e ative o ambiente virtual conforme o [README da raiz](../README.md). Instale as dependências a partir da raiz do repositório:

```sh
python -m pip install -r requirements.txt
```

Copie `.env.example` para `.env` nesta pasta e configure:

| Variável | Finalidade |
|---|---|
| `JWT_SECRET_KEY` | Chave de assinatura dos tokens de autenticação. |
| `AUTH_COOKIE_SECURE` | `true` por padrão; exige HTTPS. Use `false` somente no desenvolvimento local com HTTP. |
| `AUTH_ALLOWED_ORIGINS` | Origens exatas separadas por vírgula. Em produção, somente o endereço HTTPS da aplicação. |
| `DATABASE_URI` | URI SQLAlchemy. Exemplo local: `sqlite:///financehub.db`. |
| `DATA_ENCRYPTION_KEY_FILE` | Caminho do arquivo privado de chaves financeiras; padrão: `backend/.secrets/financial-data-keys.json`. Não contém a chave em si. |
| `PLUGGY_USER_<REFERENCIA>_CLIENT_ID` | Client ID individual; gravado no `.env` pelo administrador. |
| `PLUGGY_USER_<REFERENCIA>_CLIENT_SECRET` | Client Secret individual; gravado no `.env` pelo administrador. |

Gere uma chave local com `python -c "import secrets; print(secrets.token_hex(32))"` e copie o resultado para `JWT_SECRET_KEY`. A aplicação recusa chaves com menos de 32 caracteres. O `.env` local está ignorado pelo Git; o exemplo não contém credenciais reais. Se estiver reutilizando um `.env`, acrescente as novas variáveis a partir do exemplo.

Antes de importar a aplicação, gere o arquivo de chaves como descrito a seguir. Execute `python main.py` a partir de `backend/` depois da preparação do banco. A API de desenvolvimento atende na porta 5000. Os imports atuais são resolvidos a partir dessa pasta.

## Criptografia dos dados financeiros

Contas e transações armazenam seu conteúdo em `encrypted_data`, usando AES-256-GCM da biblioteca `cryptography`, com chave aleatória de 32 bytes, nonce aleatório de 12 bytes por escrita e envelope versionado que identifica a chave utilizada. A autenticação inclui a tabela, o ID, o contexto aleatório do registro e os vínculos de proprietário/conta/identificador externo; alterar conteúdo ou esses vínculos sem recriptografar causa falha de validação. Trocar manualmente o payload e seu contexto entre registros com IDs diferentes também é rejeitado. O payload JSON recebe preenchimento até um múltiplo de 256 bytes, reduzindo a exposição do comprimento exato dos textos; quantidade de registros e tamanho aproximado continuam observáveis. A API preserva seu contrato e decifra o conteúdo no servidor para o usuário autorizado. A documentação de [AEAD da cryptography](https://cryptography.io/en/latest/hazmat/primitives/aead/) descreve a proteção de confidencialidade e integridade desse mecanismo.

| Conteúdo | Persistência |
|---|---|
| Transação: valor, data, nome, categoria, subcategoria, descrição e tipo | Dentro do payload criptografado. |
| Conta: tipo/subtipo, número, nome, nome comercial, titular, CPF/CNPJ, saldo, moeda, dados bancários e de crédito | Dentro do payload criptografado. |
| IDs de registros, `user_id`, `account_id`, `external_id` (identificador externo), `itemId`, contexto de criptografia e identificador da chave | Visíveis no banco para vínculos, índices e sincronização. |
| Usuários, catálogo de categorias/subcategorias, sessões e proteções da sincronização | Fora da criptografia financeira; senhas continuam usando hash. Os nomes do catálogo permanecem visíveis. |

Essa é criptografia em repouso na aplicação. O administrador com acesso à chave, ou um processo comprometido que execute com os privilégios do backend, pode decifrar os dados. Não é criptografia de ponta a ponta e não impede leitura pela própria aplicação. HTTPS/TLS continua necessário no tráfego, assim como autorização, atualização do sistema e controle de acesso a arquivos.

### Geração e proteção da chave

Para preparar uma instalação nova, na pasta `backend/`, com as dependências instaladas, execute uma única vez para um arquivo novo:

```sh
python -m services.data_encryption generate-key --file .secrets/financial-data-keys.json
```

Esse comando funciona sem importar `main`/`config`, não imprime a chave e recusa sobrescrever um arquivo existente. A chave financeira é independente de `JWT_SECRET_KEY` e das senhas dos usuários. A aplicação recusa iniciar sem um arquivo de chaves válido; gerar outra chave não recupera dados cuja chave foi perdida.

Guarde o arquivo fora do banco e do Git. O caminho padrão fica no diretório privado `.secrets`; em produção, configure `DATA_ENCRYPTION_KEY_FILE` para um local protegido fora do checkout e das pastas publicadas. O gerador aplica permissão `0600` em POSIX e, no Windows, remove herança e concede acesso à identidade executora e ao sistema. Confira as ACLs de arquivo e diretório e conceda somente o acesso necessário à conta que executará o serviço. Proteja também o banco e os backups. Separar chave e dados com permissões restritas segue a orientação de [armazenamento criptográfico da OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html#key-storage).

Mantenha uma cópia segura e testada das chaves, separada dos backups do banco, com acesso restrito e proteção adicional no meio de armazenamento. Quem obtiver banco e chave pode ler o conteúdo. Preserve todas as chaves necessárias aos registros e backups antigos. O formato aceita uma chave ativa para escrita e chaves anteriores para leitura; trocar a chave ativa não recriptografa automaticamente todo o histórico, e esta versão não oferece comando de rotação completa.

### Migração offline e verificação

Este procedimento é uma instrução operacional para bancos antigos; o resultado da aplicação ao banco local está registrado abaixo. A migração automática atende SQLite em arquivo até 512 MiB; estruturas financeiras diferentes das versões suportadas, índices/gatilhos personalizados ou views dependentes exigem revisão antes de migrar.

Pare completamente a API e outros processos que possam escrever no banco. Com o mesmo arquivo de chaves preservado e `DATABASE_URI` configurado, execute na pasta `backend/`:

```sh
python -m flask --app main encrypt-data
python -m flask --app main verify-encrypted-data
python -m flask --app main init-db
```

Ao encontrar tabelas antigas, `encrypt-data` cria primeiro um snapshot consistente em memória, criptografa o banco inteiro e grava um arquivo novo em `backend/backups/before-encryption-<identificador>.fhbackup`. Não grava uma cópia pré-migração em claro. O comando mantém IDs e vínculos, converte o conteúdo das contas/transações e compara conteúdo e contagens antes da confirmação. As tabelas de usuários, catálogo, sessões e proteções de sincronização são preservadas. Em um banco já convertido, verifica os registros em vez de criar outro backup pré-migração. `verify-encrypted-data` valida o esquema e decifra/valida todos os registros financeiros, informando somente contagens.

O procedimento usa bloqueio exclusivo, checkpoint do WAL, `secure_delete` e `VACUUM`, seguido de verificação física do SQLite. Falhas antes da confirmação desfazem a conversão; se a limpeza/verificação final falhar depois da confirmação, preserve o backup e siga a mensagem do comando para repetir `encrypt-data` com a aplicação parada. Só inicie o serviço após os comandos terminarem com sucesso.

`secure_delete` e `VACUUM` ajudam a remover conteúdo descartado do arquivo SQLite, mas não garantem apagar versões em snapshots, backups antigos, caches do sistema ou blocos remanescentes de SSD. Consulte as limitações de [secure_delete](https://www.sqlite.org/pragma.html#pragma_secure_delete) e [VACUUM](https://www.sqlite.org/lang_vacuum.html). Revise cópias antigas em claro e mantenha criptografia de disco/volume, como BitLocker ou LUKS, além de uma política de retenção e descarte adequada.

### Restauração do backup criptografado

Com o serviço parado e as chaves originais disponíveis, restaure para um caminho novo na pasta `backend/`:

```sh
python -m flask --app main restore-encrypted-backup --backup backups/before-encryption-<identificador>.fhbackup --output instance/financehub-restored.db
```

Substitua `<identificador>` pelo nome real do backup. O comando decifra o snapshot em memória, converte ali o esquema antigo, valida a integridade e grava um SQLite novo com os dados financeiros já criptografados. Recusa sobrescrever o destino e não troca o arquivo de chaves nem o banco configurado. Esse SQLite contém os mesmos metadados e tabelas não financeiras em claro descritos acima. Para adotá-lo, aponte `DATABASE_URI` para o arquivo restaurado e execute `verify-encrypted-data` e `init-db` antes de reiniciar. Faça esse teste primeiro em ambiente separado e mantenha a origem e as chaves até conferir a recuperação.

### Registro local — 2026-10-05

A migração foi aplicada com sucesso ao banco configurado `backend/instance/mydatabase.db`. A verificação anterior encontrou **0 contas e 0 transações**; portanto, houve preparação do esquema financeiro, sem registros financeiros existentes para converter. `verify-encrypted-data` confirmou as mesmas contagens, e `init-db` terminou com sucesso.

O arquivo de chaves foi criado em `backend/.secrets/financial-data-keys.json`, com ACL sem herança e duas regras: identidade executora e `SYSTEM`. Foi preservado um backup pré-migração criptografado em `backend/backups/`. A recuperação desse backup para um arquivo temporário com esquema financeiro criptografado foi validada por igualdade de fingerprints e contagens e por `integrity_check`; o arquivo temporário foi removido após a conferência. Separadamente, 107 testes do backend passaram usando dados fictícios, e as verificações de lint e formatação do Ruff passaram em 35 arquivos.

Esse resultado se limita ao banco configurado e vazio na data indicada. Não atesta a configuração de produção, o disco/BitLocker, outras cópias de banco ou backups nem a existência de uma cópia externa segura das chaves.

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

A inicialização executa `CategoryService().migrate_leisure_category()` após verificar o esquema financeiro e criar as tabelas ausentes. Esse procedimento renomeia Entretenimento para Lazer no catálogo e no histórico, preservando os demais campos e as proteções da sincronização. Se Lazer já existir, os filhos são reunidos sem duplicar nomes. A listagem do catálogo também aplica essa migração por usuário; inicializadores alternativos devem executá-la antes de atender requisições.

A transação mantém `category` e `subcategory` como campos do contrato HTTP e do payload criptografado, sendo a subcategoria opcional. O backend valida que a subcategoria pertence à categoria do usuário antes de alterar qualquer campo. `null` remove a subcategoria; mudar a categoria sem informar subcategoria limpa a classificação filha anterior. Editar apenas nome ou data preserva a classificação. Associações mantêm a classificação da primeira transação, e edições de subcategoria também protegem o lançamento contra sobrescrita pela Pluggy.

A versão criptografada não possui a coluna física `transactions.subcategory`: a classificação fica dentro de `encrypted_data`. A migração offline preserva subcategorias antigas e aceita bancos anteriores que ainda não tinham essa coluna. Depois da migração, `init-db` cria as tabelas ausentes do catálogo; a rotina histórica `initialize_subcategory_column()` não acrescenta colunas financeiras ao esquema criptografado.

### Cadastro e autenticação

O cadastro público e a verificação por e-mail simulada foram desativados. Somente quem administra o servidor e tem acesso ao seu terminal pode criar acessos. Não há função administrativa acessível aos familiares pela API.

Na pasta `backend/`, com o ambiente Python ativo:

```sh
python -m flask --app main init-db
python -m flask --app main create-user
```

O comando solicita nome, e-mail, senha e o par Client ID/Client Secret da aplicação Pluggy daquela pessoa. Senha e credenciais têm entrada oculta; senha e Client Secret exigem confirmação. Senhas novas devem ter entre 12 e 128 caracteres e recebem hash no servidor. E-mails são normalizados; um cadastro existente, mesmo pendente, nunca é sobrescrito por uma tentativa de criação. O acesso e sua identidade bancária são confirmados depois de salvar o par individual no `.env`; falhas desfazem as alterações pendentes.

Para recuperar uma conta existente, inclusive uma conta antiga pendente de verificação ou com senha inválida:

```sh
python -m flask --app main reset-password
```

O administrador informa e-mail e nova senha. O comando pergunta se deseja alterar também as credenciais da Pluggy: responder não preserva o par atual; responder sim solicita os dois novos valores. A operação confirma o acesso e revoga todas as sessões anteriores. Não envia e-mail nem imprime senha ou chaves. A alteração de senha pelo próprio usuário na tela de perfil mantém as credenciais; administrar chaves permanece uma operação local do administrador.

### Credenciais Pluggy por usuário

Para configurar as chaves de um usuário existente sem trocar sua senha, execute em `backend/`:

```sh
python -m flask --app main configure-pluggy --email pessoa@exemplo.com
```

As entradas ocultas solicitam Client ID e Client Secret (com confirmação). Não passe chaves como argumentos do terminal ou pelo frontend. As credenciais identificam a aplicação Pluggy de cada pessoa e são usadas somente no servidor, conforme a [documentação de autenticação da Pluggy](https://docs.pluggy.ai/en/reference/authentication).

Os comandos mantêm no arquivo `backend/.env` as variáveis `PLUGGY_USER_<REFERENCIA>_CLIENT_ID` e `PLUGGY_USER_<REFERENCIA>_CLIENT_SECRET`. `<REFERENCIA>` corresponde ao UUID permanente de `user_security.pluggy_reference`, sem hífens e em maiúsculas. E-mail ou ID numérico não são a chave de armazenamento; trocar o e-mail não muda o vínculo, e recriar um usuário com o mesmo ID numérico não lhe dá acesso ao par anterior. Entradas de identidades excluídas ficam sem uso e podem ser removidas pelo administrador conforme a política de retenção.

O backend instancia o cliente Pluggy para o usuário autenticado a cada requisição. Token de conexão, consulta de itens, contas e transações usam exclusivamente seu par; `user_id` enviado pelo navegador não escolhe credenciais. O par permanece consistente durante a requisição, e a chave temporária da API é reutilizada dentro dela. Não há cliente global com credenciais compartilhadas. Novas requisições leem as alterações do arquivo sem reiniciar os workers. Um usuário sem configuração recebe 503 na operação bancária e nenhuma chamada é feita ao provedor. Não há fallback para `PLUGGY_CLIENT_ID`/`PLUGGY_CLIENT_SECRET` globais: configure explicitamente cada acesso existente com `configure-pluggy`, inclusive quando o par informado for o anteriormente usado no servidor.

As escritas preservam as demais variáveis e comentários, coordenam comandos/leitores por bloqueio de arquivo e substituem o `.env` de forma atômica. Se a confirmação no banco falhar, o contexto administrativo restaura o conteúdo anterior; não há backup persistente do `.env` em claro. Quedas de processo entre a gravação do arquivo e a confirmação no banco ainda exigem conferência administrativa, pois SQLite e `.env` não compõem uma única transação distribuída. Os arquivos temporários recebem acesso restrito antes de conter segredos e são removidos; `.env`, `.env.lock` e arquivos temporários são ignorados pelo Git.

O `.env` contém as chaves em claro, conforme a opção de armazenamento adotada. No Windows, a escrita concede acesso à identidade que executou o comando e a `SYSTEM`; em POSIX, usa `0600`. Execute os comandos com a identidade do serviço ou ajuste explicitamente as permissões para que o backend possa ler o arquivo e acessar seu bloqueio. Preserve também o acesso necessário à chave de criptografia financeira. Não publique o diretório do backend nem inclua o `.env` em imagens públicas; mantenha sua cópia de recuperação protegida.

Trocar o Client Secret de uma mesma aplicação preserva os itens que a Pluggy permite acessar. Trocar o Client ID para outra aplicação não transfere conexões bancárias existentes: conecte novamente as contas com as novas credenciais. Os comandos não removem contas, histórico local ou proteções de sincronização. A validação local verifica o formato e a presença do par; a autenticação efetiva é verificada pela Pluggy quando houver uma operação bancária.

### Sessões e isolamento

O login retorna `user` e `csrf_token`; o JWT é entregue somente no cookie. A sessão expira em oito horas, sem renovação automática. O frontend restaura o perfil após recarregar a página e comunica login/logout às outras abas da mesma origem. Cada navegador compartilha sua sessão entre abas; dispositivos diferentes têm sessões independentes.

As tabelas adicionais `auth_sessions`, `login_attempts` e `user_security` preservam a revogação, as falhas recentes e uma identidade bancária opaca. Na etapa anterior de autenticação, nenhuma coluna existente foi alterada; a etapa atual de criptografia substitui as colunas de conteúdo financeiro por payloads criptografados. Depois de preparar o esquema financeiro, reiniciar com `python main.py` cria tabelas ausentes; para WSGI, use `init-db`. Sessões antigas da etapa de autenticação exigem novo login; senhas e conteúdo do histórico financeiro são preservados.

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

Para executar os testes, sem rede ou credenciais, use `python -B -m unittest discover -s tests -v` na pasta `backend/`. Os testes usam dados fictícios em SQLite em memória ou em arquivos temporários e dependências da aplicação, sem acessar o banco configurado em `.env`. A suíte de autenticação utiliza Flask-JWT-Extended real e chaves estrangeiras habilitadas; testa cookies, CSRF, revogação, limitação de login, provisionamento administrativo, propriedade Pluggy e isolamento entre dois usuários.

### Edição e associação de transações

Atualizações permitem somente `name`, `date`, `category` e `subcategory`, com datas `YYYY-MM-DD`, e validam o usuário proprietário do lançamento. Alterações de valor, tipo, descrição e outros campos são rejeitadas antes de modificar o banco. Transações bancárias são criadas pela sincronização da Pluggy, com valor absoluto e tipo representando a direção. As rotas de criação manual, importação CSV e exclusão individual foram removidas; os registros históricos permanecem salvos.

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

A etapa de criptografia altera a persistência de contas e transações e acrescenta preparação/verificação offline, preservando os contratos HTTP e as regras de autorização, sincronização e associação. Esta documentação descreve a implementação, o procedimento de operação e a preparação verificada do banco local vazio em 2026-10-05; a proteção do disco, outras cópias de dados e a configuração do servidor que será usado pela família continuam fora desse resultado.
