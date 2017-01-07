#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

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
    gpg --list-keys
    aomi_seed --extra-vars pgp_key="$GPGID"
    run aomi freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    echo "$output"
    [ "$status" -eq 0 ]
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    run aomi thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose
    echo "$output"
    [ "$status" -eq 0 ]
}
