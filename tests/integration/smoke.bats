#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper

setup() {
    start_vault
    use_fixture generic
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can seed and extract a file" {
    run aomi seed
    [ "$status" -eq 0 ]
    run aomi extract_file foo/bar/baz/secret "${BATS_TMPDIR}/secret.txt"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/secret.txt)" = "$(cat ${FIXTURE_DIR}/.secrets/secret.txt)" ]
}

@test "can seed and render environment" {
    SECRET=$(shyaml get-value secret < ${FIXTURE_DIR}/.secrets/secret.yml)
    run aomi seed
    [ "$status" -eq 0 ]
    run aomi environment foo/bar/bam
    [ "$output" = "FOO_BAR_BAM_SECRET=\"${SECRET}\"" ]
    run aomi environment foo/bar/bam --prefix aaa
    [ "$output" = "AAA_SECRET=\"${SECRET}\"" ]
    run aomi environment foo/bar/bam --export
    [ "${lines[0]}" = "FOO_BAR_BAM_SECRET=\"${SECRET}\"" ]
    [ "${lines[1]}" = "export FOO_BAR_BAM_SECRET" ]
}

@test "can seed a policy" {
    run aomi seed
    [ "$status" -eq 0 ]
    run vault policies foo
    [ "$status" -eq 0 ]
}

@test "can seed an app and user with builtin policy" {
    run aomi seed
    [ "$status" -eq 0 ]
    run vault read -field=key auth/app-id/map/app-id/test
    [ "$status" -eq 0 ]
}

@test "respects tags when seeding" {
    run aomi seed --tags bar
    [ "$status" -eq 0 ]
    run vault read foo/bar/bam
    [ "$status" -eq 1 ]
    run vault read foo/bar/baz
    [ "$status" -eq 0 ]
}
