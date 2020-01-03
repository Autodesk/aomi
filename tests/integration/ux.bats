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

@test "error states are real" {
    # token / env validation
    aomi_seed
    VAULT_TOKEN="no" aomi_run_rc 1 seed
    scan_lines "^.+permission denied$" "${lines[@]}"
    VAULT_ADDR="" aomi_run_rc 1 seed
    scan_lines "VAULT_ADDR is undefined or empty" "${lines[@]}"
    VAULT_ADDR="no" aomi_run_rc 1 seed
    scan_lines "VAULT_ADDR must be a URL" "${lines[@]}"    
    a_token=$(vault token-create -format=json -policy=foo -no-default-policy 2> /dev/null | jq -Mr ".auth.client_token")
    [ ! -z "$a_token" ] && [ "$a_token" != "null" ]
    VAULT_TOKEN="$a_token" aomi_run_rc 1 seed
    scan_lines "^.*permission denied.*$" "${lines[@]}"
    unset VAULT_TOKEN
    # missing file is the same as the var not being set
    VAULT_TOKEN_FILE="/tmp/nope${RANDOM}" aomi_run_rc 1 seed
    scan_lines "^.+credentials.+unknown method$" "${lines[@]}"
}

@test "skip ssl validation" {
    # note, this should actually test against a fake ssl server tho
    export VAULT_SKIP_VERIFY=1
    aomi_seed
}

@test "custom vault token file" {
    echo "$VAULT_TOKEN" > "${BATS_TMPDIR}/token"
    VAULT_TOKEN="" VAULT_TOKEN_FILE="${BATS_TMPDIR}/token" aomi_seed
}

@test "do not use insecure files" {
    chmod -R og+rw ".secrets"
    aomi_run_rc 1 seed
    scan_lines "^.+loose permissions$" "${lines[@]}"
}

@test "builtin template help" {
    aomi_run template --builtin-list
    scan_lines "shenv" "${lines[@]}"
    aomi_run template --builtin-info shenv
    scan_lines "snippet" "${lines[@]}"
}

@test "help if asked" {
      run aomi --help
      scan_lines "usage: aomi" "${lines[@]}"
      scan_lines "positional arguments" "${lines[@]}"
      run aomi help
      scan_lines "usage: aomi" "${lines[@]}"
      scan_lines "positional arguments" "${lines[@]}"      
}

@test "some help if not asked" {
      run aomi --help
      scan_lines "usage: aomi" "${lines[@]}"
      run aomi
      [ "$status" == 2 ]
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
