#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper

@test "can run aomi normally" {
      run aomi help
      [ "$status" -eq 0 ]
}
@test "can run aomi as a dev py" {
    cd "$CIDIR"
    run python aomi.py help
    [ "$status" -eq 0 ]
}
@test "can run aomi as a dev dir" {
    cd "$CIDIR"
    run python aomi help
    [ "$status" -eq 0 ]
}
