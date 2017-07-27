#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for vault seeding in various permutations
load helper

setup() {
    start_vault
    use_fixture jinja2
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "some basic external rendering" {
    DEST_DIR="${BATS_TMPDIR}/outpu"
    aomi_run render "$DEST_DIR" --verbose --verbose
    SECRETS="${DEST_DIR}/Secretfile"
    [ -e "$SECRETS" ]    
    grep 'file/baz' "$SECRETS"
}
