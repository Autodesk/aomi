#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

setup() {
    cd "$BATS_TMPDIR"
    nohup vault server -dev &
    VAULT_PID=$!
}

teardown() {
    kill $VAULT_PID
    rm -f nohup.out
}

@test "can seed generic" {
    FIXTURE_DIR="${BATS_TEST_DIRNAME}/fixtures/generic"
    cd "$FIXTURE_DIR"
    run aomi seed
    [ "$status" -eq 0 ]
    run vault read -field=secret foo/bar/baz
    [ "$output" = "$(cat ${FIXTURE_DIR}/.secrets/secret.txt)" ]
}
