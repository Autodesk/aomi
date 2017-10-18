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
    aomi_run diff --verbose --monochrome
    scan_lines "\+ generic also_secret" "${lines[@]}"
    aomi_seed
    aomi_run diff --verbose --monochrome --tags remove
    scan_lines "\- generic also_secret" "${lines[@]}"
    aomi_run diff --monochrome --tags mod
    scan_lines "\~ generic also_secret" "${lines[@]}"
    scan_lines "\-\- default_lease_ttl: 2764800" "${lines[@]}"
    scan_lines "\-\- max_lease_ttl: 2764800" "${lines[@]}"  
    scan_lines "\+\+ default_lease_ttl: 3600" "${lines[@]}"
    scan_lines "\+\+ max_lease_ttl: 86400" "${lines[@]}"
    aomi_seed --tags mod
    aomi_seed --tags remove
}

@test "warning on assumed generic mount" {
    aomi_run seed --tags file_warn
    scan_lines "^Ad-Hoc mount with Generic File also_secret/bar.+$" "${lines[@]}"
    aomi_run seed --tags var_file_warn
    scan_lines "^Ad-Hoc mount with Generic VarFile also_secret/bar.+" "${lines[@]}"    
}
