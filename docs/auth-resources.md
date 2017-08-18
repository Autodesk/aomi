---
layout: default
---

# Overview

Vault offers a variety of means for users and systems to authenticate and receive a token. Aomi supports a handful of these.

# App Role

The succesor to the AppID authentication type is [AppRole](https://www.vaultproject.io/docs/auth/approle.html). This is a mechanism which is meant for system usage. The aomi tool only supports provisioning of roles, it does not currently support manual creation of associated secret ids. If you wish to have that style of authentication it is best to stick with App ID for now.

You can currently associate policies, associated IP addresses, the number of uses for a created secret id, and how long the resulting tokens will last.

----

`Secretfile`

```
approles:
- name: 'foo'
  policies:
  - 'default'
  - 'not_default'
  secret_uses: 1
  secret_ttl: 1
```

# Users

Vault supports basic user/password [combinations](https://www.vaultproject.io/docs/auth/userpass.html). You can provision this with aomi as well. The `Secretfile` contains the user and policy associations. The password is stored as a plain text file in the secrets directory.

----

`Secretfile`

```
users:
- username: 'foo'
  password_file: 'foo-user.txt'
  policies:
  - 'default'
```

`.secrets/foo-user.txt`

```
password
```

# DUO

The aomi tool supports the Vault [MFA](https://www.vaultproject.io/docs/auth/mfa.html) intgration for user/password combinations.

----

`Secretfile`

```
duo:
- backend: "userpass"
  creds: "duo.yml"
  host: "api-foo.duosecurity.com"
```

`.secrets/duo.yml`

```
key: "foo"
secret: "bar"
```

# LDAP

The aomi tool supports [LDAP authentication](https://www.vaultproject.io/docs/auth/ldap.html), along with mapping users to policies/groups, and groups to policies. It should work with all the ways that Vault supports LDAP.

The basic configuration will setup an auth endpoint. You can specify all the config variables listed in the Vault documentation itself. Note that the `bindpass` and `certificate` options _must_ be specified in a "secret" file indicated by the `secrets` option.

----

`Secretfile`

```
ldap_auth:
  - url: "ldap://example.com"
    binddn: "cn=vault,dc=example,dc=com"
    userattr: "uid"
    userdn: "dc=example,dc=com"
    groupdn: "dc=example,dc=com"
    secrets: "ldap.yml"
```

`.secrets/ldap.yml`

```
bindpass: "password"
```

## LDAP Users

Vault provides the ability to map users to policies and LDAP groups. Note that depending on your particular Vault/LDAP configuration, you may not be able to set overrides for users.

----

`Secretfile`

```
ldap_users:
  - user: "test"
    groups:
      - "some-group"
      - "another-group"
    policies:
      - "another-policy"
```

## LDAP Groups

Vault provides the ability to map LDAP groups to policies.

----

`Secretfile`

```
ldap_groups:
   - name: "some-group"
     policies:
       - "some-policy"
```

