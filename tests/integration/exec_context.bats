#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper

@test "can run aomi normally" {
      aomi_run help
}
@test "can run aomi as a dev py" {
    cd "$CIDIR" || exit 1
    run python aomi.py help
    [ "$status" -eq 0 ]
}
@test "can run aomi as a dev dir" {
    cd "$CIDIR" || exit 1
    run python aomi help
    [ "$status" -eq 0 ]
}
