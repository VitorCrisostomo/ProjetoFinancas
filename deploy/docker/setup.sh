#!/usr/bin/env bash
# Prepara uma instalação Linux com Docker sem sobrescrever configuração ou chaves.
set -Eeuo pipefail
umask 077

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
PROJECT_DIR=$(cd -- "$SCRIPT_DIR/../.." && pwd -P)
ENV_FILE="$SCRIPT_DIR/.env"
TEMPLATE="$SCRIPT_DIR/.env.example"
HOST_ARGUMENT=""
ROOT_ARGUMENT=""
SOURCE_DIR=""
EXTERNAL_ARGUMENT=""
FRESH=false
CREATE_USER=false
START=false

fail() { printf 'Erro: %s\n' "$*" >&2; exit 1; }
notice() { printf '%s\n' "$*"; }
trap 'printf "Preparação interrompida. Os arquivos existentes e as fontes foram preservados; confira a etapa indicada acima antes de repetir.\n" >&2' ERR

usage() {
  cat <<'USAGE'
Uso: sudo bash deploy/docker/setup.sh --host servidor.tailnet.ts.net \
       [--state-root /srv/financehub] [--fresh | --source-dir /srv/import] \
       [--external-backups /mnt/financehub-backups] [--create-user] [--start]

Sem --host: cria somente o modelo .env operacional, caso esteja ausente.
Na primeira instalação, escolha --fresh ou --source-dir. Para uma instalação
existente, omita ambos: nenhuma chave ou configuração privada será recriada.
--source-dir precisa conter app.env, financial-data-keys.json e financehub.db.
--create-user abre o cadastro administrativo interativo; --start inicia a stack.
USAGE
}

while (($#)); do
  case "$1" in
    --host|--state-root|--source-dir|--external-backups)
      (($# >= 2)) || fail "Falta o valor de $1."
      [[ -n "$2" && "$2" != --* ]] || fail "Falta o valor de $1."
      case "$1" in
        --host) [[ -z "$HOST_ARGUMENT" ]] || fail '--host repetido.'; HOST_ARGUMENT=$2 ;;
        --state-root) [[ -z "$ROOT_ARGUMENT" ]] || fail '--state-root repetido.'; ROOT_ARGUMENT=$2 ;;
        --source-dir) [[ -z "$SOURCE_DIR" ]] || fail '--source-dir repetido.'; SOURCE_DIR=$2 ;;
        --external-backups) [[ -z "$EXTERNAL_ARGUMENT" ]] || fail '--external-backups repetido.'; EXTERNAL_ARGUMENT=$2 ;;
      esac
      shift 2 ;;
    --fresh) $FRESH && fail '--fresh repetido.'; FRESH=true; shift ;;
    --create-user) CREATE_USER=true; shift ;;
    --start) START=true; shift ;;
    --help|-h) usage; exit 0 ;;
    *) fail 'Opção desconhecida. Consulte --help.' ;;
  esac
done
$FRESH && [[ -n "$SOURCE_DIR" ]] && fail 'Escolha --fresh ou --source-dir, nunca ambos.'
[[ -f "$TEMPLATE" && ! -L "$TEMPLATE" ]] || fail 'Modelo operacional não encontrado.'
[[ ! -L "$ENV_FILE" ]] || fail 'O arquivo operacional não pode ser um link simbólico.'

if [[ -z "$HOST_ARGUMENT" ]]; then
  if [[ ! -e "$ENV_FILE" ]]; then
    (set -o noclobber; cat -- "$TEMPLATE" > "$ENV_FILE")
    notice 'Modelo operacional criado em deploy/docker/.env. Nenhum segredo foi gerado.'
  else
    notice 'deploy/docker/.env já existe e foi preservado.'
  fi
  notice 'Informe o hostname real do Tailscale com --host e escolha --fresh ou --source-dir para a primeira instalação.'
  notice 'Nenhuma imagem foi construída e nenhum serviço foi iniciado.'
  exit 0
fi

[[ $(uname -s) == Linux ]] || fail 'Execute este procedimento no servidor Linux.'
((EUID == 0)) || fail 'Execute com sudo para conferir as permissões e criar a raiz privada.'
for command in docker realpath stat install find; do
  command -v "$command" >/dev/null || fail "Comando necessário não encontrado: $command."
done

# Este arquivo contém somente parâmetros operacionais. Não use source/eval nem
# exponha seus valores: o Compose pode interpretar expansão e executar outro alvo.
declare -A OPERATIONAL=()
OPERATIONAL_KEYS=(APP_HOST FINANCEHUB_STATE_ROOT FINANCEHUB_SUBNET FINANCEHUB_GATEWAY FINANCEHUB_API_IP FINANCEHUB_WEB_IP FINANCEHUB_EXTERNAL_BACKUP_DIR)
trim() {
  REPLY=$1
  REPLY="${REPLY#"${REPLY%%[![:space:]]*}"}"
  REPLY="${REPLY%"${REPLY##*[![:space:]]}"}"
}
read_operational() {
  local line key value candidate allowed single_re double_re
  single_re="^'([^']*)'([[:space:]]*(#.*)?)$"
  double_re='^"([^"\\$`]*)"([[:space:]]*(#.*)?)$'
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=${line%$'\r'}
    trim "$line"; line=$REPLY
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" == export[[:space:]]* ]]; then
      trim "${line#export}"; line=$REPLY
    fi
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*)$ ]] || fail 'Sintaxe inválida no .env operacional.'
    key=${BASH_REMATCH[1]}; trim "${BASH_REMATCH[2]}"; value=$REPLY
    allowed=false
    for candidate in "${OPERATIONAL_KEYS[@]}"; do
      if [[ "$key" == "$candidate" ]]; then allowed=true; fi
    done
    $allowed || fail 'O .env operacional contém uma variável não permitida; mantenha segredos apenas no app.env privado.'
    [[ ! -v "OPERATIONAL[$key]" ]] || fail "Variável operacional repetida: $key."
    case "$value" in
      \') fail 'Valor operacional incompleto.' ;;
      \'*) [[ "$value" =~ $single_re ]] || fail 'Use valores literais no .env operacional.'; value=${BASH_REMATCH[1]} ;;
      \"*) [[ "$value" =~ $double_re ]] || fail 'Use valores literais no .env operacional.'; value=${BASH_REMATCH[1]} ;;
      *)
        value=${value%%[[:space:]]\#*}; trim "$value"; value=$REPLY
        case "$value" in *'$'*|*'`'*|*'\'*|*'"'*|*"'"*) fail 'Use valores literais no .env operacional.' ;; esac
        [[ ! "$value" =~ [[:space:]] ]] || fail 'Coloque valores com espaços entre aspas.' ;;
    esac
    [[ "$value" != *$'\n'* && "$value" != *$'\r'* ]] || fail 'Valor operacional inválido.'
    OPERATIONAL[$key]=$value
  done < "$1"
}

NEW_ENV=false
if [[ -e "$ENV_FILE" ]]; then
  [[ -f "$ENV_FILE" ]] || fail '.env operacional precisa ser um arquivo regular.'
  read_operational "$ENV_FILE"
  [[ -n ${OPERATIONAL[APP_HOST]:-} && -n ${OPERATIONAL[FINANCEHUB_STATE_ROOT]:-} ]] || fail 'Defina APP_HOST e FINANCEHUB_STATE_ROOT no .env operacional existente.'
  [[ "$HOST_ARGUMENT" == "${OPERATIONAL[APP_HOST]}" ]] || fail '--host diverge do .env existente; nenhuma configuração foi alterada.'
  if [[ -n "$ROOT_ARGUMENT" ]]; then
    [[ "$ROOT_ARGUMENT" == /* ]] || fail '--state-root precisa ser absoluto.'
    [[ $(realpath -m -- "$ROOT_ARGUMENT") == $(realpath -m -- "${OPERATIONAL[FINANCEHUB_STATE_ROOT]}") ]] || fail '--state-root diverge do .env existente; nenhuma configuração foi alterada.'
  fi
  if [[ -n "$EXTERNAL_ARGUMENT" ]]; then
    [[ "$EXTERNAL_ARGUMENT" == "${OPERATIONAL[FINANCEHUB_EXTERNAL_BACKUP_DIR]:-}" ]] || fail '--external-backups diverge do .env existente; confira a configuração antes de repetir.'
  fi
else
  read_operational "$TEMPLATE"
  OPERATIONAL[APP_HOST]=$HOST_ARGUMENT
  OPERATIONAL[FINANCEHUB_STATE_ROOT]=${ROOT_ARGUMENT:-/srv/financehub}
  if [[ -n "$EXTERNAL_ARGUMENT" ]]; then
    OPERATIONAL[FINANCEHUB_EXTERNAL_BACKUP_DIR]=$EXTERNAL_ARGUMENT
  fi
  NEW_ENV=true
fi
HOST=${OPERATIONAL[APP_HOST]}
ROOT=${OPERATIONAL[FINANCEHUB_STATE_ROOT]}
[[ "$HOST" =~ ^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+ts\.net$ && ${#HOST} -le 253 && "$HOST" != servidor.sua-tailnet.ts.net ]] || fail 'Informe um hostname concreto do Tailscale terminado em .ts.net, sem protocolo ou caminho.'
[[ "$ROOT" == /* ]] || fail 'FINANCEHUB_STATE_ROOT precisa ser um caminho absoluto.'
case "$ROOT" in *':'*|*'$'*|*'`'*|*'\'*|*'"'*|*"'"*|*$'\n'*|*$'\r'*) fail 'Caminho de estado contém caracteres não suportados.' ;; esac
ROOT=$(realpath -m -- "$ROOT")
[[ "$ROOT" != / && "$ROOT" != "$PROJECT_DIR" && "$ROOT" != "$PROJECT_DIR/"* && "$PROJECT_DIR" != "$ROOT/"* ]] || fail 'A raiz privada precisa ficar fora do checkout, sem ser sua ancestral ou a raiz do sistema.'
[[ ! -L "${OPERATIONAL[FINANCEHUB_STATE_ROOT]}" ]] || fail 'A raiz de estado não pode ser um link simbólico.'
STATE="$ROOT/state"
$FRESH && [[ -e "$STATE" || -L "$STATE" ]] && fail '--fresh recusado: o estado já existe. Nenhum arquivo foi alterado.'
[[ ! -L "$STATE" ]] || fail 'O estado não pode ser um link simbólico.'

OPERATIONAL[FINANCEHUB_SUBNET]=${OPERATIONAL[FINANCEHUB_SUBNET]:-172.30.84.0/29}
OPERATIONAL[FINANCEHUB_GATEWAY]=${OPERATIONAL[FINANCEHUB_GATEWAY]:-172.30.84.1}
OPERATIONAL[FINANCEHUB_API_IP]=${OPERATIONAL[FINANCEHUB_API_IP]:-172.30.84.2}
OPERATIONAL[FINANCEHUB_WEB_IP]=${OPERATIONAL[FINANCEHUB_WEB_IP]:-172.30.84.3}
for key in "${OPERATIONAL_KEYS[@]}"; do
  if [[ -v "$key" && "${!key}" != "${OPERATIONAL[$key]:-}" ]]; then
    fail "Variável exportada $key diverge do arquivo operacional. Remova o export antes de repetir."
  fi
done
for key in COMPOSE_PROJECT_NAME COMPOSE_FILE COMPOSE_PROFILES COMPOSE_ENV_FILES; do
  [[ -z ${!key:-} ]] || fail "Remova o controle exportado $key antes de executar o setup."
done

version_at_least() {
  local version=$1 required_major=$2 required_minor=$3 required_patch=$4 major minor patch
  [[ "$version" =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+) ]] || return 1
  major=$((10#${BASH_REMATCH[1]})); minor=$((10#${BASH_REMATCH[2]})); patch=$((10#${BASH_REMATCH[3]}))
  ((major > required_major || (major == required_major && minor > required_minor) || (major == required_major && minor == required_minor && patch >= required_patch)))
}
ENGINE_VERSION=$(docker version --format '{{.Server.Version}}') || fail 'Docker Engine indisponível.'
version_at_least "$ENGINE_VERSION" 28 0 0 || fail 'Este deploy exige Docker Engine 28 ou superior.'
COMPOSE_VERSION=$(docker compose version --short) || fail 'Instale o plugin Docker Compose.'
version_at_least "$COMPOSE_VERSION" 2 24 4 || fail 'Este deploy exige Docker Compose 2.24.4 ou superior.'
[[ $(docker info --format '{{.OSType}}') == linux ]] || fail 'Docker precisa executar contêineres Linux.'
SECURITY_OPTIONS=$(docker info --format '{{json .SecurityOptions}}')
[[ "$SECURITY_OPTIONS" != *rootless* && "$SECURITY_OPTIONS" != *userns* ]] || fail 'O setup automático exige Docker rootful sem remapeamento de UIDs.'
DAEMON_ENDPOINT=${DOCKER_HOST:-$(docker context inspect --format '{{.Endpoints.docker.Host}}')}
[[ "$DAEMON_ENDPOINT" == unix://* ]] || fail 'Execute o setup no servidor do Docker, usando o socket Unix local.'

NEW_ROOT=false
if [[ -e "$ROOT" ]]; then
  [[ -d "$ROOT" && $(stat -c '%u:%g:%a' -- "$ROOT") == 10001:10001:700 ]] || fail 'Raiz existente precisa ter UID/GID 10001 e modo 0700; nenhuma permissão foi alterada.'
else
  [[ -d $(dirname -- "$ROOT") ]] || fail 'Crie primeiro o diretório pai da nova raiz privada.'
  NEW_ROOT=true
fi
if [[ -e "$STATE" ]]; then
  [[ -z "$SOURCE_DIR" ]] || fail 'Estado existente: não importe novas fontes. Use o procedimento de recuperação em outra raiz.'
  for directory in "$STATE" "$STATE/config" "$STATE/keys" "$STATE/data" "$STATE/backups" "$STATE/logs"; do
    [[ -d "$directory" && ! -L "$directory" && $(stat -c '%u:%g:%a' -- "$directory") == 10001:10001:700 ]] || fail 'Estado existente possui diretório ausente ou permissões incompatíveis; nada foi corrigido automaticamente.'
  done
  for file in "$STATE/config/app.env" "$STATE/keys/financial-data-keys.json"; do
    [[ -f "$file" && ! -L "$file" && $(stat -c '%u:%g:%a' -- "$file") == 10001:10001:600 ]] || fail 'Estado existente está incompleto ou possui arquivos privados com permissões incompatíveis.'
  done
else
  if ! $FRESH && [[ -z "$SOURCE_DIR" ]]; then
    fail 'Na primeira instalação escolha --fresh ou --source-dir.'
  fi
  if ! $NEW_ROOT; then
    [[ -z $(find "$ROOT" -mindepth 1 -maxdepth 1 -print -quit) ]] || fail 'A raiz de uma nova instalação precisa estar vazia e ser dedicada à aplicação.'
  fi
fi
if [[ -n "$SOURCE_DIR" ]]; then
  [[ "$SOURCE_DIR" == /* && -d "$SOURCE_DIR" && ! -L "$SOURCE_DIR" ]] || fail 'Informe uma pasta de fontes absoluta, existente e sem link simbólico.'
  SOURCE_DIR=$(realpath -e -- "$SOURCE_DIR")
  case "$SOURCE_DIR" in *':'*|*$'\n'*|*$'\r'*) fail 'Caminho das fontes contém caracteres não suportados para o mount Docker.' ;; esac
  [[ "$SOURCE_DIR" != "$ROOT" && "$SOURCE_DIR" != "$ROOT/"* && "$ROOT" != "$SOURCE_DIR/"* && "$SOURCE_DIR" != "$PROJECT_DIR" && "$SOURCE_DIR" != "$PROJECT_DIR/"* ]] || fail 'Use uma pasta de fontes separada do checkout e do estado de destino.'
  [[ $(stat -c '%u:%g:%a' -- "$SOURCE_DIR") == 10001:10001:700 ]] || fail 'A pasta de transferência precisa ter UID/GID 10001 e modo 0700; as fontes não serão alteradas.'
  for name in app.env financial-data-keys.json financehub.db; do
    file="$SOURCE_DIR/$name"
    [[ -f "$file" && ! -L "$file" && $(stat -c '%u:%g:%a' -- "$file") == 10001:10001:600 ]] || fail 'As três fontes precisam ser arquivos regulares privados, UID/GID 10001 e modo 0600.'
  done
fi

COMPOSE_FILES=(-f "$SCRIPT_DIR/compose.yaml")
EXTERNAL=${OPERATIONAL[FINANCEHUB_EXTERNAL_BACKUP_DIR]:-}
if [[ -n "$EXTERNAL" ]]; then
  case "$EXTERNAL" in *':'*|*'$'*|*'`'*|*'\'*|*'"'*|*"'"*|*$'\n'*|*$'\r'*) fail 'Caminho externo contém caracteres não suportados.' ;; esac
  [[ "$EXTERNAL" == /* && -d "$EXTERNAL" && ! -L "$EXTERNAL" ]] || fail 'Destino externo configurado precisa existir e estar montado antes do setup.'
  EXTERNAL_REAL=$(realpath -e -- "$EXTERNAL")
  [[ "$EXTERNAL_REAL" != / && "$EXTERNAL_REAL" != "$ROOT" && "$EXTERNAL_REAL" != "$ROOT/"* && "$ROOT" != "$EXTERNAL_REAL/"* && "$EXTERNAL_REAL" != "$PROJECT_DIR" && "$EXTERNAL_REAL" != "$PROJECT_DIR/"* && "$PROJECT_DIR" != "$EXTERNAL_REAL/"* ]] || fail 'O backup externo precisa ficar separado do checkout e do estado persistente.'
  COMPOSE_FILES+=(-f "$SCRIPT_DIR/compose.external.yaml")
fi

# Todas as validações de preservação terminam antes da primeira escrita.
if $NEW_ENV; then
  (set -o noclobber
    {
      printf '# Parâmetros operacionais; segredos são gerados no app.env privado.\n'
      for key in "${OPERATIONAL_KEYS[@]}"; do
        if [[ -v "OPERATIONAL[$key]" ]]; then
          printf "%s='%s'\n" "$key" "${OPERATIONAL[$key]}"
        fi
      done
    } > "$ENV_FILE")
  notice 'Arquivo operacional criado. Configurações existentes nunca são substituídas.'
fi
if $NEW_ROOT; then
  install -d -o 10001 -g 10001 -m 0700 -- "$ROOT"
fi
compose() {
  local key
  local clean_environment=(env)
  for key in "${OPERATIONAL_KEYS[@]}" COMPOSE_PROJECT_NAME COMPOSE_FILE COMPOSE_PROFILES COMPOSE_ENV_FILES; do
    clean_environment+=(-u "$key")
  done
  "${clean_environment[@]}" docker compose --env-file "$ENV_FILE" "${COMPOSE_FILES[@]}" "$@"
}
compose config --quiet
RUNNING_SERVICES=$(compose ps --status running --services)
[[ -z "$RUNNING_SERVICES" ]] || fail 'A stack está em execução. Pare backup, web e api durante a janela de manutenção antes de repetir o setup.'
notice 'Construindo as imagens de produção da API e do frontend.'
compose build api web
if [[ ! -e "$STATE" ]]; then
  if $FRESH; then
    notice 'Gerando automaticamente JWT, chave financeira e configuração privada.'
    compose run --rm --no-deps bootstrap --fresh
  else
    notice 'Importando snapshot e chaves preservadas, com fontes somente para leitura.'
    compose run --rm --no-deps --volume "$SOURCE_DIR:/source:ro" bootstrap \
      --source-env /source/app.env --source-key /source/financial-data-keys.json \
      --source-database /source/financehub.db
  fi
else
  notice 'Estado existente preservado; bootstrap e geração de chaves foram ignorados.'
fi
notice 'Inicializando e verificando o banco criptografado.'
compose run --rm --no-deps maintenance python -B -m flask --app main verify-encrypted-data
compose run --rm --no-deps maintenance python -B -m flask --app main init-db
compose run --rm --no-deps maintenance python -B -m flask --app main verify-encrypted-data
if $CREATE_USER; then
  notice 'Criando acesso pelo comando administrativo interativo.'
  compose run --rm --no-deps maintenance python -B -m flask --app main create-user
fi
notice 'Criando e verificando o primeiro backup criptografado.'
BACKUP_ARGUMENTS=(--state-dir /state)
[[ -n "$EXTERNAL" ]] && BACKUP_ARGUMENTS+=(--external-directory /external-backups)
compose run --rm --no-deps maintenance python -B /app/deploy/run_backup.py "${BACKUP_ARGUMENTS[@]}"
compose run --rm --no-deps maintenance python -B -m flask --app main verify-backup
if $START; then
  notice 'Iniciando os serviços e aguardando os healthchecks.'
  compose up -d --wait api web backup
  compose ps
else
  notice 'Preparação concluída. Os serviços não foram iniciados; use --start para iniciá-los.'
fi
notice "Ative o HTTPS no servidor: sudo tailscale serve --bg http://127.0.0.1:8080"
notice "Endereço privado configurado: https://$HOST"
notice 'Preserve uma cópia protegida das chaves financeiras fora do disco do servidor.'
