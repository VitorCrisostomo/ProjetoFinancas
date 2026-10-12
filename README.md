# FinanceHub

Gerenciador financeiro com backend Flask, frontend React e integração bancária com Pluggy.

## Organização

- `backend/`: API, serviços, repositórios e modelos. Consulte [a documentação do backend](backend/README.md).
- `frontend/`: telas, componentes, hooks e serviços HTTP. Consulte [a arquitetura do frontend](frontend/ARCHITECTURE.md).
- `requirements.txt`: dependências Python da aplicação.

## Instalar e usar localmente

Instale Python 3.11 ou superior, com suporte a SQLite `serialize()`/`deserialize()`, e Node.js com npm compatível com o frontend; Node 22.12 ou superior atende ao build. Abra um terminal na raiz do projeto. No Windows:

```powershell
.\setup.bat
.\setup.bat create-user
.\setup.bat run
```

O primeiro comando cria `.venv`, instala as dependências Python e do frontend, prepara a configuração local, inicializa e verifica o banco e compila o frontend. Uma instalação nova recebe JWT e chave financeira aleatórios, sem precisar copiar chaves no terminal. Configurações e chaves existentes são preservadas; um banco existente é verificado antes da inicialização. Falhas de chave ou esquema não são corrigidas criando outro banco ou outra chave.

`create-user` cadastra o acesso administrativamente e pede senha e credenciais Pluggy com entrada oculta. Contas existentes continuam válidas; não é necessário recriá-las. O cadastro público permanece fechado.

`run` atende o frontend compilado e a API no mesmo endereço, **http://127.0.0.1:5173**, usando Waitress. Não exige dois terminais nem Node em execução. Mantenha o terminal aberto e use `Ctrl+C` para encerrar. Este é o modo local, com HTTP em loopback; o acesso remoto da família usa uma das opções de produção abaixo.

Em outro sistema, o mesmo instalador pode ser chamado com Python:

```sh
python3 deploy/setup.py install
python3 deploy/setup.py create-user
python3 deploy/setup.py run
```

Quem usa Make pode executar `make install`, `make create-user` e `make run`. Os alvos delegam ao mesmo instalador, sem repetir a lógica de configuração. Use `python deploy/setup.py --help` para consultar os comandos.

## Manutenção e desenvolvimento

No Windows, a partir da raiz:

| Comando | Uso |
|---|---|
| `setup.bat install` | Reinstalar/verificar dependências e configuração e recompilar o frontend, preservando dados. |
| `setup.bat configure` | Preparar ou validar somente a configuração local e suas chaves. |
| `setup.bat build` | Compilar o frontend depois de alterar seu código. |
| `setup.bat check` | Executar lint, testes e verificações de build. |
| `setup.bat create-user` | Criar um acesso, incluindo credenciais individuais da Pluggy. |
| `setup.bat reset-password` | Redefinir senha administrativamente. |
| `setup.bat configure-pluggy --email pessoa@exemplo.com` | Atualizar credenciais Pluggy de um usuário. |
| `setup.bat admin <argumentos Flask>` | Executar outro comando administrativo com o runtime e a configuração locais. |

Para desenvolver, use `setup.bat backend` e `setup.bat frontend` em terminais separados: API em `127.0.0.1:5000` e Vite em `127.0.0.1:5173`. O Vite recarrega o frontend ao editar; reinicie o backend depois de alterar Python. Encerre o modo `run` antes, pois o frontend usa a mesma porta. Depois de alterar o frontend, execute `build` para que o modo local com arquivos compilados mostre a versão nova.

Os comandos equivalentes são `python3 deploy/setup.py <comando>` e os alvos do Makefile. `install --runtime-only` exclui as ferramentas de desenvolvimento; `check` exige essas ferramentas. `install --skip-frontend` prepara somente o backend, sem instalar dependências nem gerar um build React.

`install` prepara o uso local e recusa um arquivo externo de produção. Para administrar uma instalação do servidor, selecione seu arquivo com `--env-file`; para atualizar o runtime do servidor, siga o guia de produção.

Para escolher uma configuração externa em um comando administrativo, informe `--env-file` antes do comando, como `setup.bat --env-file "C:\ProgramData\FinanceHub\state\config\app.env" create-user`. Use `setup.bat admin -- --help` para listar os comandos Flask disponíveis.

Os arquivos locais `.env`, o banco e as chaves são ignorados pelo Git. Consulte [a configuração do backend](backend/README.md#configuração-e-execução) e [a criptografia dos dados](backend/README.md#criptografia-dos-dados-financeiros) para operações manuais ou migração de bancos antigos.

## Produção em home server

Há duas opções de produção: [Windows com serviços nativos](deploy/README.md#instalação-windows) e [Linux com Docker Compose](deploy/docker/README.md). Ambas usam Waitress para a API, Caddy para o frontend, HTTPS privado pelo Tailscale Serve e backups periódicos criptografados. Banco, configuração, chaves e backups ficam fora do repositório e das imagens. Os guias incluem instalação nova, migração dos dados atuais, atualização e restauração.

Os scripts preparam a instalação; executar o projeto em desenvolvimento não registra serviços nem ativa HTTPS. A instalação no servidor exige o hostname real do Tailscale, as chaves financeiras preservadas quando houver dados e a configuração do destino externo dos backups. No Linux, a aplicação roda em contêineres; o Tailscale permanece no host. O deploy Windows continua disponível sem exigir Docker.
