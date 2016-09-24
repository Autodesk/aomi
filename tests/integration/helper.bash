# -*- mode: Shell-script;bash -*-

VAULT_LOG="${BATS_TMPDIR}/aomi-vault-log"

function start_vault() {
    if [ -e "${HOME}/.vault-token" ] ; then
        mv "${HOME}/.vault-token" "${BATS_TMPDIR}/og-token"
    fi
    nohup vault server -dev &> "$VAULT_LOG" &
    if ! pgrep vault &> /dev/null ; then
        stop_vault
        start_vault
    else
        export VAULT_PID=$(pgrep vault)
        export VAULT_ADDR='http://127.0.0.1:8200'
        VAULT_TOKEN=$(grep -e 'Root Token' "$VAULT_LOG" | cut -f 3 -d ' ')
        export VAULT_TOKEN="$VAULT_TOKEN"
    fi
}

function stop_vault() {
    if [ -e "${BATS_TMPDIR}/og-token" ] ; then
        mv "${BATS_TMPDIR}/og-token" "${HOME}/.vault-token"
    fi
    if ps "$VAULT_PID" &> /dev/null ; then
        kill "$VAULT_PID"
    else
        echo "vault server went away"
        kill "$(pgrep vault)"
    fi
    rm -f "$VAULT_LOG"
}

function use_fixture() {
    FIXTURE="$1"
    if [ ! -z "$2" ] ; then
        ALT="-$2"
    fi
    FIXTURE_DIR="${BATS_TMPDIR}/fixtures"
    SECRET_DIR="${FIXTURE_DIR}/.secrets${ALT}"
    mkdir -p "$SECRET_DIR"
    cp -r "${BATS_TEST_DIRNAME}/fixtures/${FIXTURE}/"* "$FIXTURE_DIR"
    if [ ! -z "$ALT" ] ; then
        mv "${FIXTURE_DIR}/Secretfile" "${FIXTURE_DIR}/Secretfile${ALT}"
        mv "${FIXTURE_DIR}/vault" "${FIXTURE_DIR}/vault${ALT}"
    fi
    if [ -d "${BATS_TEST_DIRNAME}/fixtures/${FIXTURE}/.secrets/" ] ; then
        cp -r "${BATS_TEST_DIRNAME}/fixtures/${FIXTURE}/.secrets/"* "$SECRET_DIR"
    fi
    cd "$FIXTURE_DIR" || exit 1
    echo -n "$RANDOM" > "$SECRET_DIR/secret.txt"
    echo -n "$RANDOM" > "$SECRET_DIR/secret2.txt"
    echo "secret: ${RANDOM}" > "${SECRET_DIR}/secret.yml"
    echo "secret: ${RANDOM}" > "${SECRET_DIR}/secret2.yml"
    echo -n "secret2: ${RANDOM}" >> "${SECRET_DIR}/secret.yml"
    echo -n "secret2: ${RANDOM}" >> "${SECRET_DIR}/secret2.yml"
    echo ".secrets${ALT}" > "${FIXTURE_DIR}/.gitignore"
    export FILE_SECRET1="$(cat "${SECRET_DIR}/secret.txt")"
    export FILE_SECRET2="$(cat "${SECRET_DIR}/secret2.txt")"
    export YAML_SECRET1=$(shyaml get-value secret < "${SECRET_DIR}/secret.yml")
    export YAML_SECRET2=$(shyaml get-value secret < "${SECRET_DIR}/secret2.yml")
    export YAML_SECRET1_2=$(shyaml get-value secret2 < "${SECRET_DIR}/secret.yml")
    export YAML_SECRET2_2=$(shyaml get-value secret2 < "${SECRET_DIR}/secret2.yml")
}

function check_secret() {
    if [ $# != 3 ] ; then
        exit 1
    fi
    local rc=1
    if [ "$1" == "true" ] ; then
        rc=0
    fi
    #pathing is so convenient
    local path="$(dirname "$2")"
    local key="$(basename "$2")"
    local val="$3"
    run vault read "-field=$key" "$path"
    echo "$path/$key $status $output $rc $val"
    [ "$status" = "$rc" ]
    if [ "$rc" == "0" ] ; then
        [ "$output" = "$val" ]
    fi
}

function check_policy() {
    local rc=1
    if [ "$1" == "true" ] ; then
        rc=0
    fi
    run vault policies
    [ "$status" = "0" ]
    if [ "$rc" == "0" ] ; then
        scan_lines "$2" "${lines[@]}"
    fi
}

scan_lines() {
    local STRING="$1"
    shift
    while [ ! -z "$1" ] ; do
        if [ "$1" == "$STRING" ] ; then
            return 0
        fi
        shift
    done
    return 1
}
