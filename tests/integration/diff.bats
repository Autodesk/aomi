#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for diff functionality
load helper

setup() {
    start_vault
    use_fixture diff
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "crud some diffs" {
    run aomi diff --verbose --verbose --monochrome
    [ "$status" -eq 0 ]
    scan_lines "\+ Generic File secret/foo" "${lines[@]}"
    scan_lines "\+ Vault Generic Backend also_secret" "${lines[@]}"
    aomi_seed
    run aomi diff --verbose --verbose --monochrome --tags remove
    [ "$status" -eq 0 ]
    scan_lines "\- Generic File secret/foo" "${lines[@]}"
    scan_lines "\- Vault Generic Backend also_secret" "${lines[@]}"
    run aomi diff --verbose --verbose --monochrome --tags mod
    [ "$status" -eq 0 ]
    scan_lines "\~ Generic File secret/foo" "${lines[@]}"
}
