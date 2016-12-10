#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-

load helper

setup() {
    start_vault
    use_fixture minimal
    run aomi seed
    [ "$status" -eq 0 ]
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can render a base secret" {
    run aomi environment foo/bar --no-merge-path
    scan_lines "SECRET=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a base secret with prefix" {
    run aomi environment foo/bar --no-merge-path --add-prefix aaa
    scan_lines "AAASECRET=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a base secret with suffix" {
    run aomi environment foo/bar --no-merge-path --add-suffix bbb
    scan_lines "SECRETBBB=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a base secret with prefix ~and~ suffix" {
    run aomi environment foo/bar --no-merge-path \
        --add-prefix aaa \
        --add-suffix bbb
    scan_lines "AAASECRETBBB=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a secret with prefix" {
    run aomi environment foo/bar \
        --add-prefix aaa_
    scan_lines "AAA_FOO_BAR_SECRET=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a secret with suffix" {
    run aomi environment foo/bar \
        --add-suffix _bbb
    scan_lines "FOO_BAR_SECRET_BBB=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can render a secret with prefix and suffix" {
    run aomi environment foo/bar \
        --add-prefix aaa_ \
        --add-suffix _bbb
    scan_lines "AAA_FOO_BAR_SECRET_BBB=\"${FILE_SECRET1}\"" "${lines[@]}"
}

@test "can remap base keys" {
    run aomi environment foo/bar \
        --no-merge-path \
        --key-map secret=user \
        --key-map secret2=password
    scan_lines "USER=\"${FILE_SECRET1}\"" "${lines[@]}"
    scan_lines "PASSWORD=\"${FILE_SECRET2}\"" "${lines[@]}"
}

@test "can remap keys" {
    run aomi environment foo/bar \
         --key-map secret=user \
         --key-map secret2=password
    scan_lines "FOO_BAR_USER=\"${FILE_SECRET1}\"" "${lines[@]}"
    scan_lines "FOO_BAR_PASSWORD=\"${FILE_SECRET2}\"" "${lines[@]}"
}
@test "can remap (base) keys with a prefix and suffix" {
    run aomi environment foo/bar \
        --no-merge-path \
        --add-prefix aaa_ \
        --add-suffix _bbb \
        --key-map secret=user \
        --key-map secret2=password
    scan_lines "AAA_USER_BBB=\"${FILE_SECRET1}\"" "${lines[@]}"
    scan_lines "AAA_PASSWORD_BBB=\"${FILE_SECRET2}\"" "${lines[@]}"
}
