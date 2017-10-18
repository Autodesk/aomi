# -*- mode: Shell-script;bash -*-

VAULT_LOG="${BATS_TMPDIR}/aomi-vault-log"
if [ -z "$AWS_TIMEOUT" ] ; then
    AWS_TIMEOUT=20
fi

function start_vault() {
    if [ -e "${HOME}/.vault-token" ] ; then
        mv "${HOME}/.vault-token" "${BATS_TMPDIR}/og-token"
    fi
    nohup vault server -dev &> "$VAULT_LOG" &
    if ! pgrep vault &> /dev/null ; then
        stop_vault
        start_vault
    else
        VAULT_PID=$(pgrep vault)
        export VAULT_PID
        export VAULT_ADDR='http://127.0.0.1:8200'
        VAULT_TOKEN=""
        START="$(date +%s)"
        while [ -z "$VAULT_TOKEN" ] ; do
            NOW="$(date +%s)"
            if [ $((NOW - START)) -gt 10 ] ; then
                echo "unable to start vault"
                return 1
            fi
            VAULT_TOKEN=$(grep -e 'Root Token' "$VAULT_LOG" | cut -f 3 -d ' ')
        done
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
        PID=$(pgrep vault || true)
        if [ ! -z "$PID" ] ; then
            kill "$(pgrep vault)"
        fi
    fi
    rm -f "$VAULT_LOG"
}

function gpg_fixture() {
    export GNUPGHOME="${FIXTURE_DIR}/.gnupg"
    mkdir -p "$GNUPGHOME"
    echo "use-agent
always-trust
verbose
" > "${GNUPGHOME}/gpg.conf"
    PINENTRY="${CIDIR}/scripts/pinentry-dummy.sh"
    echo "pinentry-program ${PINENTRY}" > "${GNUPGHOME}/gpg-agent.conf"
    chmod -R og-rwx "$GNUPGHOME"    
    # https://www.gnupg.org/documentation/manuals/gnupg/Unattended-GPG-key-generation.html
    PASS="somegpgpass${RANDOM}"
    export CRYPTORITO_PASSPHRASE_FILE="${FIXTURE_DIR}/pass"
    echo "$PASS" > "$CRYPTORITO_PASSPHRASE_FILE"
    gpg --gen-key --verbose --batch <<< "
Key-Type: RSA
Key-Length: 2048
Subkey-Type: RSA
Subkey-Length: 2048
Name-Real: aomi test
Expire-Date: 300
Passphrase: ${PASS}
%commit
"
    GPGID=$(gpg --list-keys 2>/dev/null | grep -A1 -e 'pub   rsa2048'  | tail -n 1 | sed -e 's! !!g')
    [ ! -z "$GPGID" ]
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
    echo -n "$RANDOM" > "${SECRET_DIR}/secret.txt"
    echo -n "$RANDOM" > "${SECRET_DIR}/secret2.txt"
    echo "secret: ${RANDOM}" > "${SECRET_DIR}/secret.yml"
    echo "secret: ${RANDOM}" > "${SECRET_DIR}/secret2.yml"
    echo -n "secret2: ${RANDOM}" >> "${SECRET_DIR}/secret.yml"
    echo -n "secret2: ${RANDOM}" >> "${SECRET_DIR}/secret2.yml"
    echo -n '{"secret": "'"${RANDOM}"'"}' > "${SECRET_DIR}/secret.json"
    echo -n '{"secret": "'"${RANDOM}"'"}' > "${SECRET_DIR}/secret2.json"
    echo ".secrets${ALT}" > "${FIXTURE_DIR}/.gitignore"
    chmod -R o-rwx "${SECRET_DIR}"
    chmod -R g-w "${SECRET_DIR}"
    export FILE_SECRET1="$(cat "${SECRET_DIR}/secret.txt")"
    export FILE_SECRET2="$(cat "${SECRET_DIR}/secret2.txt")"
    export YAML_SECRET1=$(shyaml get-value secret < "${SECRET_DIR}/secret.yml" 2> /dev/null)
    export YAML_SECRET2=$(shyaml get-value secret < "${SECRET_DIR}/secret2.yml" 2> /dev/null)
    export YAML_SECRET1_2=$(shyaml get-value secret2 < "${SECRET_DIR}/secret.yml" 2> /dev/null)
    export YAML_SECRET2_2=$(shyaml get-value secret2 < "${SECRET_DIR}/secret2.yml" 2> /dev/null)
    [ ! -z "$FILE_SECRET1" ] && \
        [ ! -z "$FILE_SECRET2" ] && \
        [ ! -z "$YAML_SECRET1" ] && \
        [ ! -z "$YAML_SECRET2" ] && \
        [ ! -z "$YAML_SECRET1_2" ] && \
        [ ! -z "$YAML_SECRET2_2" ]
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
    [ "$status" -eq "$rc" ]
    if [ "$rc" -eq "0" ] ; then
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

function aomi_run_rc() {
    RC="$1"
    OP="$2"    
    shift 2
    run coverage run -a --source "${CIDIR}/aomi/" "${CIDIR}/aomi.py" "$OP" --verbose "$@"
    echo "$output"
    [ "$status" -eq "$RC" ]
}

function aomi_run() {
    aomi_run_rc 0 "$@"
}

function aomi_seed() {
    aomi_run seed "$@" --verbose
}

function check_mount() {
    local rc=1
    if [ "$1" == "true" ] ; then
        rc=0
    fi
    run vault mounts
    [ "$status" == "0" ]
    if [ "$rc" == "0" ] ; then
        scan_lines "^${2}.+$" "${lines[@]}"
    fi
}

scan_lines() {
    local STRING="$1"
    shift
    while [ ! -z "$1" ] ; do
        if grep -qE "$STRING" <<< "$1" ; then
            return 0
        fi
        shift
    done
    return 1
}

function aws_creds() {
    [ -e "${CIDIR}/.aomi-test/vault-addr" ]
    [ -e "${CIDIR}/.aomi-test/vault-token" ]
    local TMP="/tmp/aomi-int-aws${RANDOM}"
    VAULT_TOKEN="$(cat "${CIDIR}/.aomi-test/vault-token")" \
               VAULT_ADDR=$(cat "${CIDIR}/.aomi-test/vault-addr") \
               aomi aws_environment \
               "$VAULT_AWS_PATH" \
               --export --lease 300s --verbose 1> "$TMP"
    RC="$?"
    if [ "$RC" != 0 ] || [ "$(cat $TMP)" == "" ] ; then
        return 1
    fi
    . "$TMP"
    rm "$TMP"
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] ; then
        return 1
    fi
    export AWS_DEFAULT_REGION="us-east-1"
    AWS_FILE="${FIXTURE_DIR}/.secrets/aws.yml"
    echo "access_key_id: ${AWS_ACCESS_KEY_ID}" > "$AWS_FILE"
    echo "secret_access_key: ${AWS_SECRET_ACCESS_KEY}" >> "$AWS_FILE"
    chmod og-rwx "$AWS_FILE"
}

function vault_cfg() {
    local key="$1"
    [ -e "${CIDIR}/.aomi-test/vault-addr" ]
    [ -e "${CIDIR}/.aomi-test/vault-token" ]
    VAULT_TOKEN=$(cat "${CIDIR}/.aomi-test/vault-token") VAULT_ADDR=$(cat "${CIDIR}/.aomi-test/vault-addr") vault read -field "$key" "$VAULT_SECRET_PATH"
}

function check_aws {
    TMP="/tmp/aomi-int${RANDOM}"
    ROLE="$1"
    START="$(date +%s)"
    # first bit of eventual consistency is on the aws creds created
    # by the upstream vault server
    while [ -z "$OK" ] ; do
        set +e
        aomi aws_environment "aws/creds/${ROLE}" --lease 60s --verbose 1> "$TMP"
        RC=$?
        set -e
        if [ "$RC" == "0" ] && [ ! -z "$(cat $TMP)" ] ; then
            OK="ok"
        else
            NOW="$(date +%s)"
            if [ $((NOW - START)) -gt "$AWS_TIMEOUT" ] ; then
                echo "Timed out waiting for initial AWS creds"
                return 1
            else
                sleep 5
            fi
        fi
    done
    . "$TMP"
    if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] ; then
        echo "AWS keys did not get set"
        return 1
    fi
    rm "$TMP"
    OK=""
    START="$(date +%s)"
    sleep 5
    # and now this eventual consistency is on the test vault
    # aws iam credentials
    while [ -z "$OK" ] ; do
        if ! aws ec2 describe-availability-zones &> /dev/null ; then
            NOW="$(date +%s)"
            if [ $((NOW - START)) -gt "$AWS_TIMEOUT" ] ; then
                echo "Timed out waiting for test AWS creds"                
                return 1
            else
                echo "AWS check failed! Time out in $((AWS_TIMEOUT - (NOW - START)))"
                sleep 5
            fi
        else
            OK="ok"
        fi
    done
    # and now this eventual consistency is on the test vault
    # aws iam credentials
    while [ -z "$OK" ] ; do
        if ! "${CIDIR}/.ci-env/bin/aws" ec2 describe-availability-zones &> /dev/null ; then
            NOW="$(date +%s)"
            if [ $((NOW - START)) -gt "$AWS_TIMEOUT" ] ; then
                echo "Timed out waiting for test AWS creds"                
                return 1
            else
                echo "AWS check failed! Time out in $((AWS_TIMEOUT - (NOW - START)))"
                sleep 5
            fi
        else
            OK="ok"
        fi
    done
}
