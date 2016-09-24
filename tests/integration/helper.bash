# -*- mode: Shell-script;bash -*-

VAULT_LOG="${BATS_TMPDIR}/aomi-vault-log"

function start_vault() {
    if [ -e "${HOME}/.vault-token" ] ; then
        mv "${HOME}/.vault-token" "${BATS_TMPDIR}/og-token"
    fi
    nohup vault server -dev &> "$VAULT_LOG" &
    export VAULT_PID=$!
    if ! ps $VAULT_PID 2> /dev/null ; then
        stop_vault
        start_vault
    else
        export VAULT_ADDR='http://127.0.0.1:8200'
        VAULT_TOKEN=$(grep -e 'Root Token' "$VAULT_LOG" | cut -f 3 -d ' ')
        export VAULT_TOKEN="$VAULT_TOKEN"
        vault auth-enable app-id &> /dev/null
    fi
}

function stop_vault() {
    if [ -e "${BATS_TMPDIR}/og-token" ] ; then
        mv "${BATS_TMPDIR}/og-token" "${HOME}/.vault-token"
    fi
    kill $VAULT_PID
    rm -f "$VAULT_LOG"
}

function use_fixture() {
    FIXTURE="$1"
    FIXTURE_DIR="${BATS_TMPDIR}/fixtures"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    cp -r "${BATS_TEST_DIRNAME}/fixtures/${FIXTURE}/"* "$FIXTURE_DIR"
    cp -r "${BATS_TEST_DIRNAME}/fixtures/${FIXTURE}/.secrets/"* "${FIXTURE_DIR}/.secrets"
    cd "$FIXTURE_DIR" || exit 1
    echo -n "$RANDOM" > "${FIXTURE_DIR}/.secrets/secret.txt"
    echo -n "secret: ${RANDOM}" > "${FIXTURE_DIR}/.secrets/secret.yml"
    echo -n "secret: ${RANDOM}" > "${FIXTURE_DIR}/.secrets/secret2.yml"
    echo ".secrets" > "${FIXTURE_DIR}/.gitignore"    
}
