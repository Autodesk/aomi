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

@test "can remove things" {
    aomi_seed
    check_secret true "foo/file/bar/secret" "$FILE_SECRET1"
    check_secret true "foo/var/bar/secret" "$YAML_SECRET1"
    check_secret true "auth/userpass/users/foo/ttl" "0"
    check_mount true "bar"
    aomi_seed --secretfile Secretfile2
    check_secret false "foo/file/bar/secret" "$FILE_SECRET1"
    check_secret false "foo/var/bar/secret" "$YAML_SECRET1"
    check_secret false "auth/userpass/users/foo/ttl" "0"
    check_mount false "bar"    
}

@test "can set a policy variable in secretfile" {
    aomi_seed --tags bam-var
    check_policy true bam
    run vault policies bam
    scan_lines 'path.+variable.+' "${lines[@]}"
}

@test "can remove a policy" {
    aomi_seed --tags bam
    check_policy true bam
    aomi_seed --tags bam-remove
    check_policy false bam
}

@test "can seed a simple template" {
    use_fixture jinja2
    aomi_seed
    validate_defaults
}

@test "can seed a complex template" {
    use_fixture jinja2-complex
    aomi_seed --extra-vars-file vars.yml --extra-vars username=foo
    validate_defaults
}

@test "can seed with alt paths" {
    use_fixture seed alt
    aomi_seed --secretfile Secretfile-alt \
        --secrets .secrets-alt \
        --policies vault-alt
    validate_defaults
}
@test "can seed users" {
    aomi_seed
    check_secret true "auth/userpass/users/foo/ttl" "0" 
}

@test "can mount everything (non-tagged) on a blank vault" {
    aomi_seed --mount-only
    check_mount true bar
    check_mount true foo
}

@test "can seed everything (non-tagged) on a blank vault" {
    aomi_seed
    validate_defaults    
}
@test "can mount then seed everything (non-tagged) on a blank vault" {
    aomi_seed --mount-only
    check_mount true bar
    check_mount true foo
    aomi_seed
    validate_defaults
}
@test "can re-seed" {
    aomi_seed
    validate_defaults
    aomi_seed
    validate_defaults
}
@test "can seed with tags" {
    aomi_seed --tags baz
    validate_resources true baz
    validate_resources false bar
    validate_resources false bam
    check_policy true baz
    check_policy false foo
    check_policy false bam
}
@test "can seed multiple files to one path" {
    aomi_seed
    check_secret true "foo/file/bar/secret" "$FILE_SECRET1"
    check_secret true "foo/file/bar/secret2" "$FILE_SECRET2"
}
@test "can seed multiple vars to one path" {
    aomi_seed
    check_secret true "foo/var/bar/secret" "$YAML_SECRET1"
    check_secret true "foo/var/bar/secret2" "$YAML_SECRET1_2"
}
@test "can use a bunch of tags and can seed a bunch of policies" {
    aomi_seed
    aomi_seed --tags baz --tags bam
    run vault policies
    [ "$status" -eq 0 ]
    scan_lines "foo" "${lines[@]}"
    scan_lines "baz" "${lines[@]}"
    scan_lines "bam" "${lines[@]}"
}
