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

@test "works as expected with cubbyhole paths" {
      aomi_seed
      check_secret true cubbyhole/foo/txt "$FILE_SECRET1"
}