#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# Simple smoke test covering basic functionality as described
# in the quickstart documentation
load helper

setup() {
    start_vault
    use_fixture generic
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "can seed as root and not as root" {
    aomi_seed
    test_user foo
    aomi_seed --tags bar
}

@test "can seed and extract a file" {
    aomi_seed
    aomi_run extract_file \
        foo/bar/baz2/secret \
        "${BATS_TMPDIR}/secret.txt" \
        --verbose
    diff "${BATS_TMPDIR}/secret.txt" "${FIXTURE_DIR}/.secrets/secret.txt"
    [ "$status" -eq 0 ]    
}

@test "can seed and render environment" {
    aomi_seed
    aomi_run environment foo/bar/bam foo/bar/bang-bang
    scan_lines "FOO_BAR_BAM_SECRET=\"${YAML_SECRET1}\"" "${lines[@]}"
    scan_lines "FOO_BAR_BANG-BANG_SECRET=\"${YAML_SECRET2}\"" "${lines[@]}"
    aomi_run environment foo/bar/bam --add-prefix aaa_ --no-merge-path
    scan_lines "AAA_SECRET=\"${YAML_SECRET1}\"" "${lines[@]}"
    aomi_run environment foo/bar/bam --export
    scan_lines "FOO_BAR_BAM_SECRET=\"${YAML_SECRET1}\"" "${lines[@]}"
    scan_lines "export FOO_BAR_BAM_SECRET" "${lines[@]}"
}

@test "can seed and render a template" {
    SECRET1=$(shyaml get-value secret < ${FIXTURE_DIR}/.secrets/secret.yml)
    SECRET2=$(shyaml get-value secret < ${FIXTURE_DIR}/.secrets/secret2.yml)
    aomi_seed
    echo -n '{{foo_bar_bam_secret}}{{foo_bar_bang_bang_secret}}' > "${BATS_TMPDIR}/tpl"
    aomi_run template "${BATS_TMPDIR}/tpl" "${BATS_TMPDIR}/render" "foo/bar/bam" "foo/bar/bang-bang"
    [ "$(cat ${BATS_TMPDIR}/render)" == "${SECRET1}${SECRET2}" ]
}

@test "can seed a policy" {
    aomi_seed
    clean_run vault policies foo
    [ "$status" -eq 0 ]
}

@test "respects tags when seeding" {
    aomi_seed
    clean_run vault read foo/bar/baz
    [ "$status" -eq 2 ]
    clean_run vault read foo/bar/baz2
    [ "$status" -eq 0 ]
    aomi_seed --tags bar
    clean_run vault read foo/bar/baz
    [ "$status" -eq 0 ]
}
