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
    aomi_run freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    aomi_run thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars "pgp_key=${GPGID}" --verbose
}

@test "can freeze a specific icefile" {
    aomi_run freeze "${BATS_TMPDIR}/cold" --icefile-prefix boogaloo --extra-vars pgp_key="$GPGID"
    ICEFILE=$(basename $(ls "${BATS_TMPDIR}/cold/boogaloo"*))
    aomi_run thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose
}

@test "can freeze and thaw and then seed" {
    aomi_run freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    rm -rf "${FIXTURE_DIR}/.secrets"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    aomi_run thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose
    aomi_seed --extra-vars pgp_key="$GPGID"
}

@test "can freeze and seed with thaw-from" {
    aomi_run freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose
    rm -rf "${FIXTURE_DIR}/.secrets"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    aomi_seed --extra-vars pgp_key="$GPGID" --thaw-from "${BATS_TMPDIR}/cold/${ICEFILE}"
}

@test "can freeze and thaw with subdirectories" {
    mkdir -p "${FIXTURE_DIR}/.secrets/sub"
    echo -n "$RANDOM" > "${FIXTURE_DIR}/.secrets/sub/secret.txt"
    aomi_run freeze "${BATS_TMPDIR}/cold" --extra-vars pgp_key="$GPGID" --verbose --tags sub --verbose
    rm -rf "${FIXTURE_DIR}/.secrets"
    mkdir -p "${FIXTURE_DIR}/.secrets"
    ICEFILE=$(ls "${BATS_TMPDIR}/cold")
    aomi_run thaw "${BATS_TMPDIR}/cold/${ICEFILE}" --extra-vars pgp_key="$GPGID" --verbose  --tags sub
    aomi_seed --extra-vars pgp_key="$GPGID"  --tags sub --verbose
}
