#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests around template extraction
# also covers the internal template mappings
load helper

setup() {
    start_vault
    use_fixture minimal
    aomi_seed
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

@test "jinja include" {
    echo "{% include 'real' -%}" > "${BATS_TMPDIR}/tpl"
    echo "{{secret}}" > "${BATS_TMPDIR}/real"
    run aomi template \
        --no-merge-path \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat "${BATS_TMPDIR}/render")" == "$FILE_SECRET1" ]
}

@test "can use b64encode/b64decode filters" {
    echo -n '{{b64|b64decode}}{{secret|b64encode}}' > "${BATS_TMPDIR}/tpl"
    B64_SECRET="$(echo -n ${FILE_SECRET1} | base64)"
    run aomi template \
        --no-merge-path \
        --extra-vars "b64=${B64_SECRET}" \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    echo "$(cat ${BATS_TMPDIR}/render) ${B64_SECRET}"
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}${B64_SECRET}" ]
}

@test "can render a template" {
    echo -n '{{foo_bar_secret}}{{foo_bar_secret2}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" == "${FILE_SECRET1}${FILE_SECRET2}" ]
}
@test "can render a template with base key" {
    echo -n '{{secret}}{{secret2}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --no-merge-path \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" == "${FILE_SECRET1}${FILE_SECRET2}" ]
}
@test "can render a template with base key and prefix" {
    echo -n '{{aaa_secret}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --no-merge-path \
        --add-prefix aaa_ \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" == "${FILE_SECRET1}" ]
}

@test "can render a template with base key and suffix" {
    echo -n '{{secret_bbb}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --no-merge-path \
        --add-suffix _bbb \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}" ]
}

@test "can render a template with base key, prefix, and suffix" {
    echo -n '{{aaa_secret_bbb}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --no-merge-path \
        --add-prefix aaa_ \
        --add-suffix _bbb \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}" ]
}

@test "can render a template with prefix" {
    echo -n '{{aaa_foo_bar_secret}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --add-prefix aaa_ \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}" ]
}

@test "can render a template with suffix" {
    echo -n '{{foo_bar_secret_bbb}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --add-suffix _bbb \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}" ]
}

@test "can render a template with prefix and suffix" {
    echo -n '{{aaa_foo_bar_secret_bbb}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --add-prefix aaa_ \
        --add-suffix _bbb \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}" ]
}

@test "can render a template with key mapping, prefix, and suffix" {
    echo -n '{{aaa_foo_bar_user_bbb}}:{{aaa_foo_bar_password_bbb}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --key-map secret=user --key-map secret2=password \
        --add-prefix aaa_ \
        --add-suffix _bbb \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "${FILE_SECRET1}:${FILE_SECRET2}" ]
}

@test "can use extra vars" {
    echo -n '{{extra}}:{{secret}}' > "${BATS_TMPDIR}/tpl"
    run aomi template \
        --no-merge-path \
        --extra-vars extra=yolo \
        "${BATS_TMPDIR}/tpl" \
        "${BATS_TMPDIR}/render" \
        "foo/bar"
    [ "$status" -eq 0 ]
    [ "$(cat ${BATS_TMPDIR}/render)" = "yolo:${FILE_SECRET1}" ]
}
