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
    run aomi freeze --extra-vars pgp_key="$GPGID" --verbose "${BATS_TMPDIR}/cold"
    echo "$output"
    [ "$status" -eq 0 ]
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    run aomi thaw --extra-vars pgp_key="$GPGID" --verbose "${BATS_TMPDIR}/cold/${ICEFILE}"
    echo "$output"
    [ "$status" -eq 0 ]
}
