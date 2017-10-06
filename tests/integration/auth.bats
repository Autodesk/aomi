#!/usr/bin/env bats
# -*- mode: Shell-script;bash -*-
# tests for vault seeding in various permutations
load helper

setup() {
    start_vault
    use_fixture auth
    export SOME_SECRET="blahblahblah${RANDOM}"
    echo "$SOME_SECRET" > "${FIXTURE_DIR}/.secrets/foo-test"
    chmod og-rwx "${FIXTURE_DIR}/.secrets/foo-test"    
}

teardown() {
    stop_vault
    rm -rf "$FIXTURE_DIR"
}

approle_auth() {
    FAIL=""
    if [ ! -z "$1" ] ; then
        FAIL="$1"
    fi
    ROLE_ID_FILE="${BATS_TMPDIR}/roleid${RANDOM}"
    LOGIN_FILE="${BATS_TMPDIR}/login${RANDOM}"
    vault read -format=json auth/approle/role/foo/role-id 2> /dev/null > "$ROLE_ID_FILE"
    ROLE_ID=$(jq -Mr ".data.role_id" < "$ROLE_ID_FILE" 2> /dev/null)
    [ ! -z "$ROLE_ID" ]
    unset VAULT_TOKEN
    vault write -format=json auth/approle/login "role_id=${ROLE_ID}" "secret_id=${SOME_SECRET}" 2> /dev/null > "$LOGIN_FILE" || true
    VAULT_TOKEN=$(jq -Mr ".auth.client_token" < "$LOGIN_FILE" 2> /dev/null)
    if [ "$FAIL" == "no" ] ; then
        [ -z "$VAULT_TOKEN" ]
    else
        [ ! -z "$VAULT_TOKEN" ]
        export VAULT_TOKEN
        [ "$(vault token-lookup -format=json | jq -Mr ".data.display_name")" == "approle" ]
    fi
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
    local L_USER
    local L_MOUNT
    if [ $# == 2 ] ; then
        L_MOUNT="$1"
        L_USER="$2"
    elif [ $# == 1 ] ; then
        L_MOUNT="ldap"
        L_USER="$1"
    else
        return 1
    fi
    local og_token="$VAULT_TOKEN"
    unset VAULT_TOKEN
    run vault auth -method=ldap "username=riemann" "password=password" -format=json
    export VAULT_TOKEN="$(cat ~/.vault-token)"
    echo "$output"
    [ "$status" -eq "0" ]
    [ "$(vault token-lookup -format=json | jq -Mr ".data.display_name")" == "ldap-${L_USER}" ]
    export VAULT_TOKEN="$og_token"
}

@test "audit file log" {
    aomi_seed --tags logs --extra-vars "log_path=${FIXTURE_DIR}/a.log"
    aomi_seed --tags logs --extra-vars "log_path=${FIXTURE_DIR}/a.log" --extra-vars "state=absent"
}

@test "basic approle" {
    OG_VAULT="$VAULT_TOKEN"
    aomi_seed --verbose
    vault write auth/approle/role/foo/secret-id/lookup "secret_id=${SOME_SECRET}"
    approle_auth
    run vault write secret/foo test=things
    [ "$status" -eq 0 ]
    run vault read secret/foo
    [ "$status" -eq 0 ]
    if [ "$VAULT_VERSION" != "0.6.2" ] ; then
        # tokens only good for three uses
        run vault read secret/foo
        echo "$output"
        [ "$status" -eq 1 ]
    fi
    # secrets only good for one use
    export VAULT_TOKEN="$OG_VAULT"    
    approle_auth no
}

@test "basic ldap" {
    echo 'bindpass: "password"' >> "${FIXTURE_DIR}/.secrets/ldap"
    chmod og-rwx "${FIXTURE_DIR}/.secrets/ldap"
    aomi_seed --tags ldap --extra-vars user=riemann --extra-vars group=mathematicians
    ldap_auth riemann
}

@test "dual wield ldap" {
    echo 'bindpass: "password"' >> "${FIXTURE_DIR}/.secrets/ldap"
    chmod og-rwx "${FIXTURE_DIR}/.secrets/ldap"
    aomi_seed --tags dual_ldap --extra-vars user=riemann --extra-vars group=mathematicians
    ldap_auth riemann
    ldap_auth also_ldap riemann    
}

@test "ldap crud" {
    echo 'bindpass: "password"' >> "${FIXTURE_DIR}/.secrets/ldap"
    chmod og-rwx "${FIXTURE_DIR}/.secrets/ldap"
    aomi_seed --tags ldap --extra-vars user=riemann --extra-vars group=mathematicians
    check_secret "auth/ldap/users/riemann/policies" true "default,foo"
    check_secret "auth/ldap/groups/mathematicians/policies" true "default,foogroup"    
    aomi_seed --tags ldap --extra-vars user=riemann --extra-vars group=mathematicians --extra-vars state=absent
    check_secret "auth/ldap/users/riemann/policies" false "default,foo"
    check_secret "auth/ldap/groups/mathematicians/policies" false "default,foogroup"
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
