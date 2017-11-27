#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for vault ssh
load helper

setup() {
    start_vault
    use_fixture ssh
}
teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "ssh crud" {
      aomi_seed --verbose
      check_secret "ssh/roles/foo/default_user" true "nobody"
      check_secret "ssh/roles/bar/default_user" true "also_nobody"
      aomi_seed --verbose --extra-vars a_state=absent
      check_secret "ssh/roles/foo/default_user" false "nobody"
      check_secret "ssh/roles/bar/default_user" false "also_nobody"
}
