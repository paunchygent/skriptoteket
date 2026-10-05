#!/bin/sh
# Preserve urllib GET semantics, including redirects and non-2xx failure.
set -eu
# urllib prefers lowercase HTTP_PROXY and ignores uppercase under CGI.
if [ -z "${http_proxy+x}" ] && [ -z "${REQUEST_METHOD+x}" ]; then
    http_proxy=${HTTP_PROXY-}
    export http_proxy
fi
# urllib does not use curl's catch-all proxy variables.
unset ALL_PROXY all_proxy
status=$(curl --silent --fail --location --max-redirs 10 --max-time 10 \
    --output /dev/null --write-out '%{http_code}' \
    "${1:-http://localhost:8000/healthz}") || exit 1
case "$status" in
    2??) exit 0 ;;
    *) exit 1 ;;
esac
