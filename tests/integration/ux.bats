#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for user experience constructs

load helper

setup() {
    start_vault
    use_fixture generic
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "custom vault token file" {
    echo "$VAULT_TOKEN" > "${BATS_TMPDIR}/token"
    VAULT_TOKEN="" VAULT_TOKEN_FILE="${BATS_TMPDIR}/token" aomi_seed
}

@test "builtin template help" {
    aomi_run template --builtin-list
    scan_lines "shenv" "${lines[@]}"
    aomi_run template --builtin-info shenv
    scan_lines "snippet" "${lines[@]}"
}

@test "help if asked" {
      aomi_run --help
      scan_lines "usage: aomi" "${lines[@]}"
      scan_lines "positional arguments" "${lines[@]}"
      aomi_run help
      scan_lines "usage: aomi" "${lines[@]}"
      scan_lines "positional arguments" "${lines[@]}"      
}

@test "some help if not asked" {
      aomi_run --help
      scan_lines "usage: aomi" "${lines[@]}"
      aomi_run_rc 2 aomi
      scan_lines "usage: aomi" "${lines[@]}"      
}

@test "a single op, help if asked" {
    aomi_run extract_file --help
    scan_lines "usage: aomi.py extract_file" "${lines[@]}"
    scan_lines "positional arguments" "${lines[@]}"
}

@test "a single op, some if not asked" {
    aomi_run_rc 2 extract_file
    scan_lines "usage: aomi.py extract_file" "${lines[@]}"
}

@test "verbosity" {
    aomi_run help --verbose
    scan_lines "INFO:aomi.cli:Auth Hints Present" "${lines[@]}"
}

@test "can specify token metadata" {
    aomi_seed --metadata test=good
}

@test "can specify operational token" {
    aomi_seed --reuse-token
}
