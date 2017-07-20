---
layout: default
---

# Data Operations

There are three operations which are used as part of Operational Secret lifecycle management. These actions help provide what we believe are safe practices around managing these secrets in a delivery pipeline.

* The [`seed`]({{site.baseurl}}/data#seed) action will provision a Vault server with defined data. This may optionally use a encrypted icefile.
* The [`freeze`]({{site.baseurl}}/data#freeze) action will generate an encrypted file (icefile) suitable for cold storage of secrets
* The [`thaw`]({{site.baseurl}}/data#thaw) action will extract an icefile for modification
* The [`diff`]({{site.baseurl}}/data#diff) action shows what will change
* You can [`export`]({{site.baseurl}}/data#export) secrets into a local directory

# Common Arguments

These operations all have some shared constructs which allow the user a fair amount of flexibility. Much of the opinionless aspects of aomi are handled by these options.

## About File Paths

By default the [`Secretfile`]({{site.baseurl}}/secretfile) is searched for in the current directory. You can override this behavior with the `--secretfile` option.

Supplemental data is loaded from relative paths by default. If files are not found at the relative (but tunable) path, the data will be loaded as an absolute path.

All Vault and AWS policy files will be searched for first in a relative location. This relative "metadata directory" defaults to `vault` adjacent to the `Secretfile` however you may override it with `--policies`. 

All files containing secrets referenced from the `Secretfile` will be searched for in an adjacent "secret directory" named `.secrets`. You are able to override the directory used for static secrets with the `--secrets` option. 

## Tags

You may tag individual policies, appids, and secrets. When resources have tags, and the `seed` command is run with the `--tags` option, only matching items will be seeded. If the `--tags` option is not specified, then only things which do not have tags specified will be seeded.

## AdHoc Path Selection

You can include or exclude paths from execution on a one-off basis with the `--include` and `--exclude` options. This can be used to fine tune an aomi `seed` operation without having to permanently modify a `Secretfile` with tags. Note that exclude takes priority over include.

# diff

The diff command will go through the [`Secretfile`]({{site.baseurl}}/secretfile) and report on what would be changed by a `seed` operation. Note that you need to be logged in, and already have appropriate permissions. The `diff` command _can_ be executed with no arguments, and it will look for everything in the current working directory. The `diff` command takes the `--secretfile`, `--policies`, and `--secrets` options.

Differences will be reported in a human readable fashion according annotated depending on the action required.

* A green <span color="green">+</span> indicates a new Vault resource will be created
* A red <span color="red">-</span>indicates a Vault resource will be removed
* A yellow <span color="yellow">~</span> indicates a Vault resource will be changed
* A yellow <span color="yellow">+</span> indicates a write-only Vault resource will be overwritten
* Vault resources for which there is no change are not mentioned

# seed

The seed command will go through the [`Secretfile`]({{site.baseurl}}/secretfile) and appropriately provision Vault. Note that you need to be logged in, and already have appropriate permissions. The seed command _can_ be executed with no arguments, and it will look for everything in the current working directory. The `seed` command takes the `--secretfile`, `--policies`, and `--secrets` options. The `--mount-only` option ensures that backends are attached and does not actually writing anything to Vault.

It is possible to have aomi clean up unrecognzied Vault mount points. Note that by doing this, _any_ mount point that is not defined in the fully rendered `Secretfile` will be unmounted. This causes non-recoverable data from the perspective of Vault. Care should be taken to back up your data using [`freeze`]({{site.baseurl}}/data#freeze) and [`thaw`]({{site.baseurl}}/data#thaw) prior to using this option. It may be enabled by specifying `--remove-unknown`.

The `Secretfile` is interpreted as a Jinja2 template, and you can pass in `--extra-vars` and `--extra-vars-file` to `seed`. This opens up some possibilities for bulk-creating sets of credentials based on integrations with other systems, while still preserving various paths and structures.

The `seed` command will make some sanity checks as it goes. One of these is to check for the presence of the secrets directory within your `.gitignore`. As this directory can contain plaintext secrets, it should never be committed. A recommended alternative is to specify an icefile with the `--thaw-from` option. When doing this, plain text secrets are only accessible in the clear during the seed operation and are removed immediately after.

# freeze

The `freeze` action will go through the [`Secretfile`]({{site.baseurl}}/secretfile) and extract specified secrets from the local file system into an encrypted zip file. This file is known as an icefile, because it sounds cool. You can specify tags, or include/exclude paths. In order to make use of `freeze` you _must_ specify a list of either Keybase or GPG fingerprints in the `Secretfile` under the `pgp_keys` section. All the options supported by `seed` for selection of secrets and file paths are supported with this operation.

----

`Secretfile`

```
pgp_keys:
- 'keybase:otakup0pe'
- 'B1234ABC'
```

This example will generate an icefile in the `/tmp` directory.

```
$ aomi freeze /tmp
```

# thaw

The `thaw` action will take a generated icefile and thaw it into the configured "secrets" directory. This operation will take all of the options that `seed` accepts with regards to file paths and secret selection.

This example will thaw the named icefile into the default "secrets" directory.

```
$ aomi thaw /tmp/aomi-example-000000-01-01-2017.ice 
```

# export

The `export` action will go through a `Secretfile` and read out any readable secret from the Vault server. Note that some paths are _write only_ and thus the information is not retrievable. Examples of this are the root path for the [AWS backend](https://www.vaultproject.io/docs/secrets/aws/) or the password of a [userpass](https://www.vaultproject.io/docs/auth/userpass.html) user. This operation takes the `--secretfile`, `--policies`, and `--secrets` directory options along with `--extra-vars` and `--extra-vars-file` options.

```
$ aomi export /tmp/secrets
```

# Errata

Note that actions which rely on GPG (`freeze`/`thaw`/`seed` with `--thaw-from`) are not really working well in Docker yet.
