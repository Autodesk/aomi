#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper
setup() {
    [ -e "${CIDIR}/.vault-token" ]
    start_vault
    use_fixture aws
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can seed some aws stuff" {
    aws_creds
    [ -e "${FIXTURE_DIR}/.secrets/aws.yml" ]
    run aomi seed --verbose --extra-vars aws_account=565773857241
    [ "$status" -eq 0 ]
    run vault mounts
    scan_lines "aws/.+aws.+" "${lines[@]}"
    check_aws "inline"
}
