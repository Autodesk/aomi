#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# Tests related to cold storage data operations

load helper

setup() {
    start_vault
    use_fixture cold
    gpg_fixture
    export GNUPGHOME="${FIXTURE_DIR}/.gnupg"
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
    rm -rf "${BATS_TMPDIR}/cold"
}

@test "can freeze and thaw" {
    run aomi freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    echo $output
    [ "$status" -eq 0 ]
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    run aomi thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose
    echo $output
    [ "$status" -eq 0 ]
}

@test "can freeze and thaw and then seed" {
    run aomi freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    [ "$status" -eq 0 ]
    rm -rf "${FIXTURE_DIR}/.secrets"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    run aomi thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose
    [ "$status" -eq 0 ]
    aomi_seed --extra-vars pgp_key="$GPGID"
    [ "$status" -eq 0 ]
}

@test "can freeze and thaw with subdirectories" {
    mkdir -p "${FIXTURE_DIR}/.secrets/sub"
    echo -n "$RANDOM" > "${FIXTURE_DIR}/.secrets/sub/secret.txt"
    run aomi freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose --tags sub --verbose
    echo $output    
    [ "$status" -eq 0 ]
    rm -rf "${FIXTURE_DIR}/.secrets"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    run aomi thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose  --tags sub
    echo $output    
    [ "$status" -eq 0 ]
    aomi_seed --extra-vars pgp_key="$GPGID"  --tags sub --verbose
    echo $output
    [ "$status" -eq 0 ]    
}
