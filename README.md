# FinanceHub

Gerenciador financeiro com backend Flask, frontend React e integração bancária com Pluggy.

## Organização

- `backend/`: API, serviços, repositórios e modelos. Consulte [a documentação do backend](backend/README.md).
- `frontend/`: telas, componentes, hooks e serviços HTTP. Consulte [a arquitetura do frontend](frontend/ARCHITECTURE.md).
- `requirements.txt`: dependências Python da aplicação.

## Instalação manual

Use Python 3.11 ou superior e Node.js com npm. Na raiz do projeto, crie um ambiente virtual:

```sh
python -m venv venv
```

Ative o ambiente no Windows PowerShell com `.\venv\Scripts\Activate.ps1`; no macOS/Linux, com `source venv/bin/activate`.

Instale as dependências Python:

```sh
python -m pip install -r requirements.txt
```

Instale o frontend:

```sh
cd frontend
npm install
```

Copie `backend/.env.example` para `backend/.env` e preencha as variáveis conforme a [documentação do backend](backend/README.md). Em uma instalação nova, crie a chave dos dados financeiros; ao reutilizar um banco, preserve suas chaves e siga a migração descrita em [criptografia do banco](backend/README.md#criptografia-dos-dados-financeiros). Para mudar o endereço da API no frontend, use `frontend/.env.example` como referência para `frontend/.env`.

## Executar em desenvolvimento

Com o ambiente Python ativo, abra um terminal na raiz:

```sh
cd backend
python main.py
```

Em outro terminal na raiz:

```sh
cd frontend
npm run dev
```

A API usa `http://localhost:5000`; o frontend usa `http://localhost:5173` e encaminha `/api` para a API. O cadastro público está fechado. Contas existentes continuam válidas; novos acessos e recuperação de senha são feitos pelo administrador, conforme [a documentação de autenticação](backend/README.md#cadastro-e-autenticação).

## Verificação de código

Na raiz, instale as ferramentas de desenvolvimento e confira o backend:

```sh
python -m pip install -r backend/requirements-dev.txt
python -m ruff check backend
python -m ruff format backend --check
```

Na pasta `frontend`, execute `npm run build` e `npm run lint`.

`setup.bat` e `Makefile` ainda contêm caminhos do template inicial. A instalação manual acima corresponde à organização atual; os scripts não foram alterados nesta revisão de documentação e lint.
