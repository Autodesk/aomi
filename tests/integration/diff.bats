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

@test "crud some policy diffs" {
    aomi_run diff --verbose --monochrome
    scan_lines "\+ Vault Policy foo" "${lines[@]}"
    aomi_seed
    aomi_run diff --verbose --monochrome    
    scan_lines "!\+ Vault Policy foo" "${lines[@]}"
    aomi_run diff --verbose --monochrome --tags mod
    scan_lines "\~ Vault Policy foo" "${lines[@]}"
    scan_lines "\-\- #test1" "${lines[@]}"
    scan_lines "\+\+ #test2" "${lines[@]}"
    aomi_run diff --verbose --monochrome --tags remove
    scan_lines "\- Vault Policy foo" "${lines[@]}"
    aomi_seed --tags remove    
    aomi_run diff --verbose --monochrome --tags remove
    scan_lines "!\- Vault Policy foo" "${lines[@]}"
}

@test "crud some secret diffs" {
    aomi_run diff --verbose --monochrome
    scan_lines "\+ Generic File secret/foo" "${lines[@]}"
    scan_lines "\+ Generic VarFile secret/bar" "${lines[@]}"
    scan_lines "\+ generic also_secret" "${lines[@]}"
    aomi_seed
    aomi_run diff --verbose --monochrome
    scan_lines "!\+ Generic File secret/foo" "${lines[@]}"
    scan_lines "!\+ Generic VarFile secret/bar" "${lines[@]}"
    scan_lines "!\+ generic also_secret" "${lines[@]}"    
    aomi_run diff --verbose --monochrome --tags mod
    scan_lines "\~ Generic File secret/foo" "${lines[@]}"
    scan_lines "\-\- txt2: ${FILE_SECRET2}" "${lines[@]}"
    scan_lines "\+\+ txt2: ${FILE_SECRET1}" "${lines[@]}"
    scan_lines "\-\- secret: ${YAML_SECRET1}" "${lines[@]}"
    scan_lines "\-\- secret2: ${YAML_SECRET1_2}" "${lines[@]}"
    scan_lines "\+\+ secret: ${YAML_SECRET2}" "${lines[@]}"
    scan_lines "\+\+ secret2: ${YAML_SECRET2_2}" "${lines[@]}"
    aomi_run diff --verbose --monochrome --tags remove
    scan_lines "\- Generic File secret/foo" "${lines[@]}"
    scan_lines "\- Generic VarFile secret/bar" "${lines[@]}"    
    scan_lines "\- generic also_secret" "${lines[@]}"
    aomi_seed --tags remove
    aomi_run diff --verbose --monochrome --tags remove
    scan_lines "!\- Generic File secret/foo" "${lines[@]}"
    scan_lines "!\- Generic VarFile secret/bar" "${lines[@]}"    
    scan_lines "!\- generic also_secret" "${lines[@]}"
}
