# Sem ativar manualmente o ambiente virtual.
ifeq ($(OS),Windows_NT)
PYTHON ?= python
else
PYTHON ?= python3
endif
SETUP = $(PYTHON) deploy/setup.py
ARGS ?=
DOCKER_SETUP = bash deploy/docker/setup.sh
COMPOSE = docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml
EXTERNAL_BACKUPS ?= 0
ifeq ($(EXTERNAL_BACKUPS),1)
COMPOSE += -f deploy/docker/compose.external.yaml
BACKUP_ARGS = --external-directory /external-backups
endif

.PHONY: help install setup configure run run-backend run-frontend build check lint test \
        init-db create-user reset-password configure-pluggy admin production \
        docker-setup docker-config docker-up docker-down docker-logs docker-backup

help:
	@$(SETUP) --help
	@echo "Docker Linux: make docker-setup ARGS='--host servidor.tailnet.ts.net --state-root /srv/financehub --fresh --start'"

install setup:
	$(SETUP) install $(ARGS)

configure:
	$(SETUP) configure $(ARGS)

run:
	$(SETUP) run $(ARGS)

run-backend:
	$(SETUP) backend $(ARGS)

run-frontend:
	$(SETUP) frontend $(ARGS)

build:
	$(SETUP) build $(ARGS)

check lint test:
	$(SETUP) $@ $(ARGS)

init-db create-user reset-password configure-pluggy:
	$(SETUP) $@ $(ARGS)

admin:
	$(SETUP) admin $(ARGS)

production:
	$(SETUP) production $(ARGS)

docker-setup:
	$(DOCKER_SETUP) $(ARGS)

docker-config:
	$(COMPOSE) config --quiet

docker-up:
	$(COMPOSE) up -d --wait api web backup

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs --tail=100 $(ARGS)

docker-backup:
	$(COMPOSE) run --rm maintenance python -B /app/deploy/run_backup.py --state-dir /state $(BACKUP_ARGS)
