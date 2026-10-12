#!/usr/bin/env bash
# Teste Linux com estado fictício e isolado; não importa .env ou bancos do host.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
TEMP_ROOT="$(mktemp -d /tmp/financehub-docker-smoke.XXXXXXXX)"
PROJECT_NAME="fh-smoke-$(basename -- "$TEMP_ROOT" | tr '[:upper:].' '[:lower:]-')"
API_IMAGE="financehub-smoke-api:$PROJECT_NAME"
WEB_IMAGE="financehub-smoke-web:$PROJECT_NAME"
ENV_FILE="$TEMP_ROOT/compose.env"
OVERRIDE="$TEMP_ROOT/compose.smoke.yaml"
HELPER="$PROJECT_ROOT/backend/tests/docker_http_scenario.py"
BUILT=0

compose() {
  docker compose --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" \
    -f "$SCRIPT_DIR/compose.yaml" -f "$SCRIPT_DIR/compose.external.yaml" \
    -f "$OVERRIDE" "$@"
}

cleanup() {
  local result=$?
  trap - EXIT
  if [ "$result" -ne 0 ] && [ -f "$OVERRIDE" ]; then
    compose logs --tail 100 api web backup || true
  fi
  if [ -f "$OVERRIDE" ]; then
    timeout 30s docker compose --project-name "$PROJECT_NAME" --env-file "$ENV_FILE" \
      -f "$SCRIPT_DIR/compose.yaml" -f "$SCRIPT_DIR/compose.external.yaml" \
      -f "$OVERRIDE" down --remove-orphans --timeout 10 || true
  fi
  # Confere o destino antes de remover: nenhum caminho externo ao diretório
  # exclusivo desta execução é montado ou enviado à rotina de limpeza.
  case "$TEMP_ROOT" in
    /tmp/financehub-docker-smoke.*)
      if [ -d "$TEMP_ROOT" ] && [ ! -L "$TEMP_ROOT" ] \
        && [ "$(realpath -- "$TEMP_ROOT")" = "$TEMP_ROOT" ]; then
        if [ "$BUILT" -eq 1 ]; then
          timeout 30s docker run --rm --network none --user 0:0 \
            --mount "type=bind,source=$TEMP_ROOT,target=/cleanup" \
            "$API_IMAGE" python -B -c '
import shutil
from pathlib import Path
root = Path("/cleanup").resolve()
for name in ("runtime", "external", "recovery"):
    target = root / name
    if target.is_symlink():
        target.unlink()
    elif target.exists():
        if target.resolve().parent != root:
            raise RuntimeError("Destino de limpeza inválido")
        shutil.rmtree(target)
' || true
        fi
        rm -f -- "$ENV_FILE" "$OVERRIDE"
        rmdir -- "$TEMP_ROOT" 2>/dev/null || true
      fi
      ;;
    *) printf '%s\n' 'Limpeza recusada: diretório temporário inesperado.' >&2 ;;
  esac
  docker image rm "$API_IMAGE" "$WEB_IMAGE" >/dev/null 2>&1 || true
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

mkdir -- "$TEMP_ROOT/runtime" "$TEMP_ROOT/external" "$TEMP_ROOT/recovery"
cat > "$ENV_FILE" <<EOF
APP_HOST=docker-smoke.fixture.ts.net
FINANCEHUB_STATE_ROOT=$TEMP_ROOT/runtime
FINANCEHUB_EXTERNAL_BACKUP_DIR=$TEMP_ROOT/external
FINANCEHUB_SUBNET=172.30.85.0/29
FINANCEHUB_GATEWAY=172.30.85.1
FINANCEHUB_API_IP=172.30.85.2
FINANCEHUB_WEB_IP=172.30.85.3
EOF
cat > "$OVERRIDE" <<EOF
services:
  api:
    image: $API_IMAGE
    healthcheck:
      interval: 2s
      start_period: 10s
  web:
    image: $WEB_IMAGE
    ports: !override []
    healthcheck:
      interval: 2s
      start_period: 5s
  backup:
    image: $API_IMAGE
    healthcheck:
      interval: 2s
      start_period: 10s
  bootstrap:
    image: $API_IMAGE
  maintenance:
    image: $API_IMAGE
EOF

# O override usa !override, disponível no Compose 2.24.4 ou superior. Os IDs
# de projeto e imagens são exclusivos; não substitui tags da instalação real.
compose config --quiet
compose build api web
BUILT=1
docker run --rm --network none --user 0:0 \
  --mount "type=bind,source=$TEMP_ROOT,target=/fixture-root" \
  "$API_IMAGE" python -B -c '
import os
from pathlib import Path
root = Path("/fixture-root").resolve()
for name in ("runtime", "external", "recovery"):
    path = root / name
    if path.is_symlink() or path.resolve().parent != root:
        raise RuntimeError("Diretório de teste inválido")
    os.chown(path, 10001, 10001)
    path.chmod(0o700)
'
compose run --rm bootstrap --fresh
compose run --rm --no-deps maintenance python -B -m flask --app main init-db
compose run --rm --no-deps \
  --volume "$HELPER:/fixture.py:ro" maintenance python -B /fixture.py --seed
compose run --rm --no-deps maintenance python -B -m flask --app main verify-encrypted-data
compose up -d --wait --wait-timeout 200

# Este cliente monta somente o helper; não possui banco, configuração ou chave.
docker run --rm --network "${PROJECT_NAME}_application" --user 10001:10001 \
  --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  --mount "type=bind,source=$HELPER,target=/fixture.py,readonly" \
  "$API_IMAGE" python -B /fixture.py --check

compose run --rm --no-deps maintenance python -B /app/deploy/run_backup.py \
  --state-dir /state --external-directory /external-backups
compose run --rm --no-deps maintenance python -B -m flask --app main verify-backup
compose exec -T backup python -B /app/deploy/docker/backup_scheduler.py \
  --state-dir /state --healthcheck

# Para restaurar usa apenas chave e cópia externa, sem app.env ou DB ativos.
compose run --rm --no-deps --entrypoint python \
  --volume "$TEMP_ROOT/external:/recovery-source:ro" \
  --volume "$TEMP_ROOT/runtime/state/keys:/recovery-keys:ro" \
  --volume "$TEMP_ROOT/recovery:/recovery" bootstrap -B -c '
from pathlib import Path
from subprocess import run
import sys
backups = sorted(Path("/recovery-source").glob("scheduled-*.fhbackup"))
if not backups:
    raise RuntimeError("Nenhuma cópia externa para recuperar")
run([sys.executable, "-B", "/app/deploy/docker/restore_backup.py",
     "--backup", str(backups[-1]),
     "--key", "/recovery-keys/financial-data-keys.json",
     "--output-dir", "/recovery/restored"], check=True)
'
compose run --rm --no-deps --entrypoint python \
  --volume "$TEMP_ROOT/recovery:/recovery:ro" \
  --volume "$HELPER:/fixture.py:ro" bootstrap \
  -B /fixture.py --verify-recovery --directory /recovery/restored
printf '%s\n' 'Docker smoke concluído: imagens, HTTP, isolamento, backup externo e restauração.'
