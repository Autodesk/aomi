#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper
setup() {
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
    [ -e "${CIDIR}/.aomi-test/aws-account" ]
    run aomi seed --verbose --extra-vars aws_account=$(cat "${CIDIR}/.aomi-test/aws-account")
    [ "$status" -eq 0 ]
    run vault mounts
    scan_lines "aws/.+aws.+" "${lines[@]}"
    check_aws "inline"
}
