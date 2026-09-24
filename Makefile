.PHONY: install run-backend run-frontend

install:
	@echo "==> Configurando o Backend (Python)..."
	python -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "==> Configurando o Frontend (React)..."
	npm install # Se o front estiver em uma pasta, mude para: cd nome_da_pasta && npm install
	@echo "==> Instalação concluída! Tudo pronto."


run-backend:
	@echo "==> Iniciando o servidor Flask..."
	./venv/bin/python app.py # Mude 'app.py' para o nome do seu arquivo principal


run-frontend:
	@echo "==> Iniciando o React..."
	npm run dev # Se estiver numa pasta: cd nome_da_pasta && npm run dev