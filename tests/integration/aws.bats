#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# AWS backend related tests

load helper
setup() {
    start_vault
    use_fixture aws
    aws_creds
}

teardown() {
    vault token-revoke "$VAULT_TOKEN"
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can add and remove an aws" {
    aomi_seed
    vault mounts ; vault list aws/roles
    echo $output
    vault list aws/roles | grep inline
    aomi_seed --tags remove_mount
    ! vault list aws/roles | grep inline
}

@test "can add and remove a role" {
    aomi_seed --tags double
    vault list aws/roles | grep bar
    aomi_seed --tags remove
    ! vault list aws/roles | grep bar
    vault list aws/roles | grep foo
}

@test "aws happy path" {
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
