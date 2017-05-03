---
layout: default
---

# Overview

The aomi tool has two themes behind it's operations. The primary mode features a Vault server and handling the cold storage of [data]({{site.baseurl}}/data). There are also a variety of other actions which may be used to [extract]({{site.baseurl}}/extract) information from a Vault server in an easy to consume fashion.

There are also some [miscelaneous]({{site.baseurl}}/misc) operations which you may find helpful.

# Common Constructs

Every aomi operation can take a `--verbose` flag. By default, the tool is quite silent, using return codes to communicate status. The verbose mode is good for troubleshooting and should not display any sensitive information.

You should be able to trust that meaningful output will be written to stdout. All errors (and verbose information) will be written to stderr.

Help for operations should be available with the `--help` argument.

# Authentication

The `aomi` tool will make several attempts at determining appropriate credentials to use with Vault. Upon receiving an initial token, it will request a short lived token for to use for itself. When requesting this token (which has a default TTL of ten seconds) an assortment of metadata is provided. The `USER` environment variable, the system hostname, and the current operation will always be included as token metadata. You may optionally add additional fields with the `--metadata` option in the format of `key1=value1,key2=value2`.

When sourcing a initial token first the `VAULT_TOKEN` environment variable will be searched, followed by the file `~/.vault-token`. This is in-line with the default behavior of the Vault client itself.  Next `aomi` will check the `VAULT_APP_ID` and `VAULT_USER_ID` environment variables followed by the file `~/.aomi-app-token`. This file is YAML encoded with only the `app_id` and `user_id` attributes. You may override both the Vault token and App/User ID files with the `VAULT_TOKEN_FILE` and `VAULT_APP_FILE` environment variables.

The default behaviour for aomi is to create an _operational_ token prior to interacting with Vault resources. This allows us to specify a TTL and metadata on the specific request. You can disable this behaviour with the `--reuse-token` argument, usable on all operations.
