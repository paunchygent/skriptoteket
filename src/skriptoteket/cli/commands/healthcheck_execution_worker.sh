#!/bin/sh
# Authenticated SQL, daemon response and actual artifact-write readiness.
set -eu

fail() {
    printf '%s\n' "$1" >&2
    exit 1
}

database_url=${DATABASE_URL-}
[ -n "$database_url" ] || fail "DATABASE_URL is not configured"
case "$database_url" in
    postgresql+asyncpg://*) database_url="postgresql://${database_url#postgresql+asyncpg://}" ;;
esac
# psql expands connection URIs through --dbname; suppress credential diagnostics.
case "$database_url" in
    *\?*) database_url="$database_url&connect_timeout=2" ;;
    *) database_url="$database_url?connect_timeout=2" ;;
esac
PGDATABASE="$database_url" PGCONNECT_TIMEOUT=2 \
    timeout 4 psql --dbname "$database_url" --no-psqlrc --no-password --set ON_ERROR_STOP=1 \
    --tuples-only --no-align --command 'SELECT 1' >/dev/null 2>&1 \
    || fail "Database healthcheck failed"

docker_host=${DOCKER_HOST:-unix:///var/run/docker.sock}
case "$docker_host" in
    unix://*) docker_socket=${docker_host#unix://} ;;
    *) fail "Docker healthcheck requires the configured Unix socket" ;;
esac
docker_response=$(curl --silent --fail --noproxy '*' --max-time 3 \
    --unix-socket "$docker_socket" http://localhost/_ping 2>/dev/null) \
    || fail "Docker healthcheck failed"
[ "$docker_response" = "OK" ] || fail "Docker healthcheck response failed"

artifacts_root=${ARTIFACTS_ROOT-/tmp/skriptoteket/artifacts}
probe_path=
cleanup() {
    if [ -n "$probe_path" ]; then
        rm -f -- "$probe_path" >/dev/null 2>&1 || :
    fi
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
mkdir -p -- "$artifacts_root" 2>/dev/null || fail "Artifacts healthcheck failed"
probe_path=$(mktemp "$artifacts_root/.healthcheck-worker-XXXXXXXXXX" 2>/dev/null) \
    || fail "Artifacts healthcheck failed"
(printf 'ok' >"$probe_path") 2>/dev/null || fail "Artifacts healthcheck write failed"
rm -- "$probe_path" 2>/dev/null || fail "Artifacts healthcheck cleanup failed"
probe_path=
