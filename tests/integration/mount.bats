#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for mount/backend crud
load helper

setup() {
    start_vault
    use_fixture mount
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "crud a kv/generic mount" {
    aomi_run diff
    scan_lines "\+ kv also_secret" "${lines[@]}"
    scan_lines "\+\+ description: some kinda" "${lines[@]}"
    aomi_seed
    aomi_run diff --tags remove
    scan_lines "\- kv also_secret" "${lines[@]}"
    aomi_run diff --tags mod
    scan_lines "\~ kv also_secret" "${lines[@]}"
    scan_lines "\-\- default_lease_ttl: 0" "${lines[@]}"
    scan_lines "\-\- max_lease_ttl: 0" "${lines[@]}"  
    scan_lines "\+\+ default_lease_ttl: 3600" "${lines[@]}"
    scan_lines "\+\+ max_lease_ttl: 86400" "${lines[@]}"
    aomi_seed --tags mod
    aomi_seed --tags remove
}

@test "warning on assumed generic mount" {
    # adhoc no longer support
    aomi_run_rc 1 seed --tags adhoc
    scan_lines '.*Ad\-Hoc backend not supported.*' "${lines[@]}"
}
