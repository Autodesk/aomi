#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# AWS backend related tests

load helper
setup() {
    start_vault
    use_fixture aws
}

teardown() {
    vault token-revoke "$VAULT_TOKEN"
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can add and remove a role" {
    aomi_seed --tags double
    vault list aws/roles | grep bar
    aomi_seed --tags remove
    ! vault list aws/roles | grep bar
    vault list aws/roles | grep foo
}

@test "aws happy path" {
    aws_creds    
    aomi_seed
    check_aws "inline"
    run vault mounts
    scan_lines "aws/.+aws.+" "${lines[@]}"
}
@test "aws templated role" {
    aomi_seed \
        --extra-vars "effect=Allow" \
        --tags template
    run vault mounts
    scan_lines "aws/.+aws.+" "${lines[@]}"
}
