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
    aomi_run diff --verbose --verbose --monochrome
    scan_lines "\+ Generic File secret/foo" "${lines[@]}"
    scan_lines "\+ Vault Generic Backend also_secret" "${lines[@]}"
    aomi_seed
    aomi_run diff --verbose --verbose --monochrome --tags remove
    scan_lines "\- Generic File secret/foo" "${lines[@]}"
    scan_lines "\- Vault Generic Backend also_secret" "${lines[@]}"
    aomi_run diff --verbose --verbose --monochrome --tags mod
    scan_lines "\~ Generic File secret/foo" "${lines[@]}"
}
