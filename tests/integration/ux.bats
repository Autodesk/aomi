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

@test "vault token file" {
    echo "$VAULT_TOKEN" > "${BATS_TMPDIR}/token"
    VAULT_TOKEN_FILE="${BATS_TMPDIR}/token" aomi_seed
    [ "$status" -eq 0 ]
}

@test "builtin template help" {
    run aomi template --builtin-list
    [ "$status" -eq 0 ]
    scan_lines "shenv" "${lines[@]}"
    run aomi template --builtin-info shenv
    [ "$status" -eq 0 ]
    scan_lines "snippet" "${lines[@]}"
}

@test "help if asked" {
      run aomi --help
      [ "$status" -eq 0 ]      
      scan_lines "usage: aomi" "${lines[@]}"
      scan_lines "positional arguments" "${lines[@]}"
}
@test "some help if not asked" {
      run aomi --help
      [ "$status" -eq 0 ]      
      scan_lines "usage: aomi" "${lines[@]}"
      run aomi
      [ "$status" -eq 2 ]
      scan_lines "usage: aomi" "${lines[@]}"      
}

@test "a single op, help if asked" {
    run aomi extract_file --help
    [ "$status" -eq 0 ]
    scan_lines "usage: aomi extract_file" "${lines[@]}"
    scan_lines "positional arguments" "${lines[@]}"
}

@test "a single op, some if not asked" {
    run aomi extract_file
    [ "$status" -eq 2 ] # because it's bad syntax
    scan_lines "usage: aomi extract_file" "${lines[@]}"
}

@test "verbosity" {
    run aomi help --verbose --verbose
    [ "$status" -eq 0 ]
    scan_lines "Auth Hints Present" "${lines[@]}"
}
