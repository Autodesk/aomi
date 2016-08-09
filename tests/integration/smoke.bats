#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

VAULT_LOG="${BATS_TMPDIR}/aomi-vault-log"

setup() {
    if [ -e "${HOME}/.vault-token" ] ; then
        mv "${HOME}/.vault-token" "${BATS_TMPDIR}/og-token"
    fi
    nohup vault server -dev &> "$VAULT_LOG" &
    VAULT_PID=$!
    export VAULT_ADDR='http://127.0.0.1:8200'
    VAULT_TOKEN=$(grep -e 'Root Token' "$VAULT_LOG" | cut -f 3 -d ' ')
    export VAULT_TOKEN
    FIXTURE_DIR="${BATS_TMPDIR}/fixtures"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    cp -r "${BATS_TEST_DIRNAME}"/fixtures/generic/* "$FIXTURE_DIR"
    cd "$FIXTURE_DIR"
    echo -n "$RANDOM" > "${FIXTURE_DIR}/.secrets/secret.txt"
    echo -n "secret: ${RANDOM}" > "${FIXTURE_DIR}/.secrets/secret.yml"
    echo ".secrets" > "${FIXTURE_DIR}/.gitignore"
}

teardown() {
    if [ -e "${BATS_TMPDIR}/og-token" ] ; then
        mv "${BATS_TMPDIR}/og-token" "${HOME}/.vault-token"
    fi
    kill $VAULT_PID
    rm -f "$VAULT_LOG"
    rm -rf "$FIXTURE_DIR"
}

@test "can seed and extract a file" {
    run aomi seed
    [ "$status" -eq 0 ]
    run aomi extract_file foo/bar/baz/secret "${BATS_TMPDIR}/secret.txt"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/secret.txt)" = "$(cat ${FIXTURE_DIR}/.secrets/secret.txt)" ]
}

@test "can seed and render a var_file" {
    SECRET=$(shyaml get-value secret < ${FIXTURE_DIR}/.secrets/secret.yml)
    run aomi seed
    [ "$status" -eq 0 ]
    run aomi environment foo/bar/bam
    [ "$output" = "FOO_BAR_BAM_SECRET=\"${SECRET}\"" ]
}

@test "respects tags when seeding" {
    run aomi seed --tags bar
    [ "$status" -eq 0 ]
    run vault read foo/bar/bam
    [ "$status" -eq 1 ]
    run vault read foo/bar/baz
    [ "$status" -eq 0 ]
}
