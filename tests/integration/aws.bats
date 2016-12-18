#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

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

@test "can seed some aws stuff" {
    aws_creds
    [ -e "${FIXTURE_DIR}/.secrets/aws.yml" ]
    ACCOUNT=$(vault_cfg aws_account)
    [ ! -z "$ACCOUNT" ]
    aomi_seed --extra-vars "aws_account=${ACCOUNT}"
    run vault mounts
    scan_lines "aws/.+aws.+" "${lines[@]}"
    check_aws "inline"
}
