#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper

setup() {
    start_vault
    use_fixture seed
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

validate_resources() {
    local test="$1"
    local key="$2"
    check_secret "$test" "foo/file/${key}/secret" "$FILE_SECRET1"
    check_secret "$test" "foo/var/${key}/secret" "$YAML_SECRET1"
}

validate_defaults() {
    validate_resources true bar
    check_policy true "foo"
    for f in baz bam ; do
        validate_resources false "$f"
        check_policy false "$f"
    done
}

@test "can seed with alt paths" {
    use_fixture seed alt
    run aomi seed --secretfile Secretfile-alt \
        --secrets .secrets-alt \
        --policies vault-alt
    echo "$output"
    [ "$status" -eq 0 ]
    validate_defaults
}
@test "can seed users" {
    run aomi seed
    [ "$status" -eq 0 ]
    check_secret true "auth/userpass/users/foo/ttl" "0" 
}

@test "can mount everything (non-tagged) on a blank vault" {
    run aomi seed --mount-only
    [ "$status" -eq 0 ]
}

@test "can seed everything (non-tagged) on a blank vault" {
    run aomi seed
    [ "$status" -eq 0 ]
    validate_defaults    
}
@test "can mount then seed everything (non-tagged) on a blank vault" {
    run aomi seed --mount-only
    [ "$status" -eq 0 ]
    run aomi seed
    [ "$status" -eq 0 ]
    validate_defaults
}
@test "can re-seed" {
    run aomi seed
    [ "$status" -eq 0 ]
    validate_defaults
    run aomi seed
    [ "$status" -eq 0 ]
    validate_defaults
}
@test "can seed with tags" {
    run aomi seed --tags baz
    [ "$status" -eq 0 ]
    validate_resources true baz
    validate_resources false bar
    validate_resources false bam
    check_policy true baz
    check_policy false foo
    check_policy false bam
}
@test "can seed multiple files to one path" {
    run aomi seed
    [ "$status" -eq 0 ]
    check_secret true "foo/file/bar/secret" "$FILE_SECRET1"
    check_secret true "foo/file/bar/secret2" "$FILE_SECRET2"
}
@test "can seed multiple vars to one path" {
    run aomi seed
    [ "$status" -eq 0 ]
    check_secret true "foo/var/bar/secret" "$YAML_SECRET1"
    check_secret true "foo/var/bar/secret2" "$YAML_SECRET1_2"
}
@test "can use a bunch of tags and can seed a bunch of policies" {
    run aomi seed
    [ "$status" -eq 0 ]
    run aomi seed --tags baz --tags bam
    [ "$status" -eq 0 ]
    run vault policies
    [ "$status" -eq 0 ]
    scan_lines "foo" "${lines[@]}"
    scan_lines "baz" "${lines[@]}"
    scan_lines "bam" "${lines[@]}"
}
