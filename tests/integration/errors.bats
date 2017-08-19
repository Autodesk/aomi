#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for error handling

load helper

setup() {
    start_vault
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"    
}

@test "bad model" {
    use_fixture "error/missing_model"
    aomi_seed
    [ "$status" -eq 0 ]
    scan_lines "missing model for ayyyyy" "${lines[@]}"
}
