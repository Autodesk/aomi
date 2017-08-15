#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for vault seeding in various permutations
load helper

setup() {
    start_vault
    use_fixture auth
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

userpass_auth() {
    PASSFILE="secret.txt"
    if [ ! -z "$1" ] ; then
        PASSFILE="$1"
    fi
    local og_token="$VAULT_TOKEN"
    unset VAULT_TOKEN
    run vault auth -method=userpass "username=foo" "password=$(cat ${FIXTURE_DIR}/.secrets/${PASSFILE})" -format=json
    export VAULT_TOKEN="$(cat ~/.vault-token)"
    [ "$status" -eq "0" ]
    [ "$(vault token-lookup -format=json | jq -Mr ".data.display_name")" == "userpass-foo" ]
    export VAULT_TOKEN="$og_token"
}

# http://www.forumsys.com/tutorials/integration-how-to/ldap/online-ldap-test-server/
# hey if it works for vault
ldap_auth() {
    local L_USER="$1"
    local og_token="$VAULT_TOKEN"
    unset VAULT_TOKEN
    run vault auth -method=ldap "username=riemann" "password=password" -format=json
    export VAULT_TOKEN="$(cat ~/.vault-token)"
    echo "$output"
    [ "$status" -eq "0" ]
    [ "$(vault token-lookup -format=json | jq -Mr ".data.display_name")" == "ldap-${L_USER}" ]
    export VAULT_TOKEN="$og_token"
}

@test "basic ldap" {
    aomi_seed --tags ldap --extra-vars user=riemann --extra-vars group=mathematicians
    ldap_auth riemann
}

@test "can crud a userpass" {
    aomi_seed
    check_secret auth/userpass/users/foo/policies true "default,foo"
    userpass_auth
    aomi_seed --tags chpass
    userpass_auth secret2.txt
    aomi_seed --tags remove
    check_secret auth/userpass/users/foo/policies false "default,foo"   
}

@test "password updates" {
    aomi_seed
    aomi_run set_password user:foo <<< "blah"
    aomi_run set_password secret/user/pass <<< "blah"
    check_secret true "secret/user/pass" "blah"
    aomi_run_rc 1 set_password secret/user/pass <<< "blah" # because it is the same
}

@test "userpass export" {
    aomi_seed
    aomi_run export "$BATS_TMPDIR" # should be a noop    
}

@test "userpass diff" {
    aomi_run diff --monochrome
    scan_lines "\+ UserPass auth/userpass/users/foo" "${lines[@]}"    
    aomi_seed
    aomi_run diff --monochrome
    scan_lines "\+ UserPass auth/userpass/users/foo" "${lines[@]}"
    aomi_run diff --monochrome --tags remove    
    scan_lines "\- UserPass auth/userpass/users/foo" "${lines[@]}"    
}

@test "duo userpass" {
    aomi_seed
    echo "secret: foo" >> "${FIXTURE_DIR}/.secrets/duo.yml"
    echo "key: foo" >> "${FIXTURE_DIR}/.secrets/duo.yml"
    chmod og-rwx "${FIXTURE_DIR}/.secrets/duo.yml"
    aomi_run diff --monochrome --tags duo
    scan_lines "\+ DUO API auth/userpass/duo/access" "${lines[@]}"
    aomi_seed --tags duo
    aomi_run diff --monochrome --tags duo_remove
    scan_lines "\- DUO API auth/userpass/duo/access" "${lines[@]}"
    aomi_seed --tags duo_remove    
}
