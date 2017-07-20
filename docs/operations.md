---
layout: default
---

The aomi tool has several themes behind it's available operations.

* Interacting with a Vault server and handling cold storage of [data]({{site.baseurl}}/data)
  * [`diff`]({{site.baseurl}}/data#diff) will display the steps required to have the Vault server reflect what is defined in the [`Secretfile`]({{site.baseurl}}/secretfile).
  * [`seed`]({{site.baseurl}}/data#seed) will write what is defined in the [`Secretfile`]({{site.baseurl}}/secretfile) to the Vault server.
  * [`freeze`]({{site.baseurl}}/data#freeze) will save the secrets defined in the [`Secretfile`]({{site.baseurl}}/secretfile) to an "icefile".
  * [`thaw`]({{site.baseurl}}/data#thaw) will extract secrets defined in the [`Secretfile`]({{site.baseurl}}/secretfile) from a previously frozen "icefile".
  * [`export`]({{site.baseurl}}/data#thaw) readable secrets from a Vault server as defined in the [`Secretfile`]({{site.baseurl}}/secretfile).
* There are also a variety of other actions which may be used to [extract]({{site.baseurl}}/extract) information from a Vault server in an easy to consume fashion.
  * [`extract_file`]({[site.baseurl}}/extract#extract_file) is used to extract the contents of a key withing a Vault path to a local file.
  * [`template`]({{site.baseurl}}/extract#template) can be used to render secrets into templates, many of which ship with `aomi`
* [Some]({{site.baseurl}}/misc) operations do not really fit into any category.
  * [`auth`]({{site.baseurl}}/misc#auth) will attempt to determine a Vault token based on various environmental and file based hints.
  * [`set_password`]({{site.baseurl}}/misc#set_password) can be used to set a userpass password, or update a single key in a Generic backend
  * [`render`]({{site.baseurl}}/misc#render) can be used to _only_ render the Secretfile and assocaited files.

# Authentication

The `aomi` tool will make several attempts at determining appropriate credentials to use with Vault. Upon receiving an initial token, it will request a short lived token for to use for itself. When requesting this token (which has a default TTL of ten seconds) an assortment of metadata is provided. The `USER` environment variable, the system hostname, and the current operation will always be included as token metadata. You may optionally add additional fields with the `--metadata` option in the format of `key1=value1,key2=value2`.

When sourcing a initial token first the `VAULT_TOKEN` environment variable will be searched, followed by the file `~/.vault-token`. This is in-line with the default behavior of the Vault client itself.  Next `aomi` will check the `VAULT_APP_ID` and `VAULT_USER_ID` environment variables followed by the file `~/.aomi-app-token`. This file is YAML encoded with only the `app_id` and `user_id` attributes. You may override both the Vault token and App/User ID files with the `VAULT_TOKEN_FILE` and `VAULT_APP_FILE` environment variables.

The default behaviour for aomi is to create an _operational_ token prior to interacting with Vault resources. This allows us to specify a TTL and metadata on the specific request. You can disable this behaviour with the `--reuse-token` argument, usable on all operations. Note that this will effecively disable the `--lease` and `--metadata` arguments.

# Run Time Help

Every aomi operation can take a `--verbose` flag. By default, the tool is quite silent, using return codes to communicate status. The verbose mode is good for troubleshooting and should not display any sensitive information. This option may be specified twice at most.

When submitting [issues](https://github.com/Autodesk/aomi/issues) please include the output of the command that has failed with `--verbose` specified twice. This will help up us troubleshoot and reproduce the submitted issues.

You should be able to trust that meaningful output will be written to stdout. All errors (and verbose information) will be written to stderr.

Help for operations should be available with the `--help` argument.

