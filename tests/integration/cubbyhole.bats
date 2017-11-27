#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for vault seeding in various permutations
load helper

setup() {
    start_vault
    use_fixture cubbyhole
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "cubbyhole crud" {
      aomi_seed
      check_secret true cubbyhole/foo/txt "$FILE_SECRET1"
      aomi_seed --extra-vars a_secret=secret2
      check_secret true cubbyhole/foo/txt "$FILE_SECRET2"      
      aomi_seed --extra-vars a_state=absent --extra-vars a_secret=secret2
      check_secret false cubbyhole/foo/txt "$FILE_SECRET2"
}
