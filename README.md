![Build Status](https://travis-ci.org/Autodesk/aomi.svg?branch=master)[![PyPI](https://img.shields.io/pypi/v/aomi.svg)](https://pypi.python.org/pypi/aomi)[![Maintenance](https://img.shields.io/maintenance/yes/2016.svg)]()

# Aomi: A Vault Wrapper

This wrapper around vault provides [lightly opinionated](http://cloudengineering.autodesk.com/blog/2016/08/introducing-aomi-a-light-dusting-of-opinions-on-using-vault.html) interface to Hashicorp Vault that provides the ability to enforce strong opinions across organizations. It fulfills two core functions : seeding secrets on behalf of an application or service, and retrieving secrets as pre-formatted consumables. Many operations for the wrapper are defined in a `Secretfile` which will generally live at the top level of a repository.

# Requirements

The `aomi` tool has several requirements which can (generally) all be sourced from [PyPI](https://pypi.python.org/pypi).

The [PyYAML](http://pyyaml.org/) package, by default, will make use of libyaml. This can be a problem on some systems as you may need to manually install libyaml.

You should be using a recent enough version of Python to have good TLS support. Vault can make use of SNI and thaht requires fresh Python 2.7.

Tests run (both locally and on Travis) in isolation using [virtualenv](https://virtualenv.pypa.io/en/stable/) so you must have this installed if you wish to do active development on `aomi`.

# Authentication

The `aomi` tool will make several attempts at determining appropriate credentials to use with Vault. Upon receiving an initial token, it will request a short lived token for to use for itself. When requesting this token (which has a default TTL of ten seconds) an assortment of metadata is provided. The `USER` environment variable, the system hostname, and the current operation will always be included as token metadata. You may optionally add additional fields with the `--metadata` option in the format of `key1=value1,key2=value2`.

When sourcing a initial token first the `VAULT_TOKEN` environment variable will be searched, followed by the file `~/.vault-token`. This is in-line with the default behavior of the Vault client itself.  Next `aomi` will check the `VAULT_APP_ID` and `VAULT_USER_ID` environment variables followed by the file `~/.aomi-app-token`. This file is YAML encoded with only the `app_id` and `user_id` attributes. You may override both the Vault token and App/User ID files with the `VAULT_TOKEN_FILE` and `VAULT_APP_FILE` environment variables.

# Secretfile

The important piece of the `Secretfile` is `secrets` as that is where seeds are defined. There are different types of secrets which may be seeded into vault.

## About File Paths

By default the `Secretfile` is searched for in the current directory. You can override this behaviour with the `--secretfile` option.

Supplemental data is loaded from relative paths by default. If files are not found at the relative (but tunable) path, the data will be loaded as an absolute path.

All Vault and AWS policy files will be searched for first in a relative location. This relative directory defaults to `vault` adjacent to the `Secretfile` however you may override it with `--policies`. 

All files containing secrets referenced from the `Secretfile` will be searched for in an adjacent directory named `.secrets`. You are able to override the directory used for static secretswith the `--secrets` option. 

## Tags

You may tag individual policies, appids, and secrets. When resources have tags, and the `seed` command is run with the `--tags` option, only matching items will be seeded. If the `--tags` option is not specified, then everything will be seeded.

# Vault Constructs

These are the different things which `aomi` may interact with in a Vault instance.

## Files

You may specify a list of files and their destination Vault secret item. Each `files` section has a list of source files, and the key name they should use in Vault. Each instance of a `files` section must also include a Vault mount point and path.  The following example would create two secrets (`private` and `public`) based on the two files under the `.secrets` directory and place them in the Vault path `foo/bar/baz`.

----
`Secretfile`

```
secrets:
- files:
  - source: id_rsa
    name: private
  - source: id_rsa.pub
    name: public
  mount: foo/bar
  path: 'baz'
```

## AWS

By specifying an appropriately populated `aws_file` you can create [AWS secret backends](https://www.vaultproject.io/docs/secrets/aws/index.html) in Vault. The `aws_file` must point to a valid file, and the base of the AWS credentials will be set by the `path`.

The AWS file contains the `access_key_id`, and `secret_access_key`. The `region`, and a list of AWS roles that will be loaded by Vault are in the `Secretfile`. Note that you may specify either an inline `policy` _or_ a native AWS `arn`. The `name` of each role will be used to compute the final path for accessing credentials. The policy files are simply JSON IAM Access representations. The following example would create an AWS Vault secret backend at `foo/bar/baz` based on the account and policy information defined in `.secrets/aws.yml`. While `lease` and `lease_max` are provided in this example, they are not strictly required. Note that a previous version had `lease`, `lease_max`, `region`, and the `roles` section located in the `aws_file` itself - this behavior is now considered deprecated. The _only_ thing which should be present in the AWS yaml is the actual secrets.

----

`Secretfile`

```
secrets:
- aws_file: 'aws.yml'
  mount: 'foo/bar/baz'
  lease: "1800s"
  lease_max: "86400s"
  region: "us-east-1"
  roles:
  - policy: "policy.json"
    name: default
```

----

`aws.yml`

```

access_key_id: "REDACTED"
secret_access_key: "REDACTED"
```

## Variable Files

You may define a preset list of secrets and associate them with a mountpoint and path. The `var_file` contains a list of YAML key value pairs. The following example would create two secrets (`user` and `password`) at the Vault path `foo/bar/baz`.

----

`Secretfile`

```
secrets:
- var_file: 'foo.yml'
  mount: 'foo/bar'
  path: 'baz'
```

`.secrets/foo.yml`

```
user: 'foo'
password: 'bar'
```

## Vault Applications

One of the authentication types supported by Vault is that of an Application/UserID combination. You may provision these with `aomi` as well. You may specify an Application ID, a series of User ID's, and a [Vault policy](https://www.vaultproject.io/docs/concepts/policies.html) to apply to resulting tokens. The following example would create an application named `foo` with two users (`bar` and `baz`) who read anything under the `foo/bar` Vault path. In this example the policy will be created _inline_. You may also re-use an existing policy by _only_ specifying a `policy_name`. When creating inline policies, you can _not_ modify the existing policy. This is a safeguard designed to prevent overwriting shared policies. It is recommended that you do not use inline policies for real world deployments.

----

`Secretfile`

```
secrets:
apps:
- app_file: 'foo.yml'
```

`.secrets/foo.yml`

```
app_id: 'foo'
users:
- 'bar'
- 'baz'
policy: 'foo.hcl'
policy_name: 'foo'
```

`vault/foo.hcl`

```
path "foo/bar/*" {
  policy = "read"
}
```

## Policies

You can seed policies separately now. Each policy has a `name` and a source `file` specified. This is recommended over using inline policies. The following example will provision a simple policy.

----
`Secretfile`

```
policies:
- name: 'foo'
  file: 'foo.hcl'
```

`vault/foo.hcl`

```
path "foo/bar/*" {
  policy = "read"
}
```

# Commands

Other than the `seed` command, everything else is used to extract secrets from the vault. Every command take a `--verbose` option. You should be able to trust that stdout only contains output, with all logs/errors going to stderr.

## seed

The seed command will go through the `Secretfile` and appropriately provision Vault. Note that you need to be logged in, and already have appropriate permissions. The seed command _can_ be executed with no arguments, and it will look for everything in the current working directory. The `seed` command takes the `--secretfile`, `--policies`, and `--secrets` options. The `--mount-only` option ensures that backends are attached and does not actually writing anything to Vault.

This command will make some sanity checks as it goes. One of these is to check for the presence of the secrets directory within your `.gitignore`. As this directory can contain plaintext secrets, it should never be comitted.

## extract_file

This action takes two arguments - the source path and the destination file. The destination file directory must already exist.

`aomi extract_file foo/bar/baz/private /home/foo/.ssh/id_rsa`

## aws_environment

This action takes a single argument - an AWS credentials path in Vault.  In return, it will generate a shell snippet exporting the `AWS_SECRET_ACCESS_KEY` and `AWS_ACCESS_KEY_ID` environment variables. This output is sufficient to be eval'd (don't do this) or piped to a file and sourced in to a shell. Export snippets can be generated  with `--export`. If the AWS Vault path provides a STS token, this will also be used.

`aomi aws_environment foo/bar/baz/aws/creds/default`

## key modification

The `environment` and `template` actions have several options which allow you to modify how the secret key will be presented. This is an evolution of the `--prefix` argument which is now deprecated. Previously, you could replace the first part of the Vault path with a static prefix.

```
aomi environment --prefix aaa foo/bar/baz
AAA_BAM=secret
```

The same behaviour is still available through a combination of new modifying options.

```
aomi environment --add-prefix aaa_ --no-merge-path foo/bar/baz
AAA_BAM=secret
```

With `--add-prefix ` and `--add-suffix` you can add a string to the front or end of a key. The `--no-merge-path` and `--merge-path` options force whether or not to use the full Vault path. The `--key-map` option can be passed in multiple times and takes a `old=new` argument and will cause the key names to be mapped accordingly, prior to other modifications.

## environment

This action takes any number of Vault paths are it's arguments. In return, it will generate a small snipped exporting the contained secrets as environment variables. This output is sufficient to be eval'd (no really, don't do this) or piped to a file an sourced in to a shell. Export snippets can be generated  with `--export`.

```
aomi environment foo/bar/baz
FOO_BAR_BAZ_USER="foo"
FOO_BAR_BAZ_PASSWORD="bar"
```

## template

This action takes at least three arguments - the template source, a destination file, and a list of Vault paths. Secrets will be included as variables in the template as the full path with forward slashes replaced by underscores. As an example, `foo/bar/baz/user` would become `foo_bar_baz_user`. The template format used is Jinja2. Note that hyphens will be replaced with underscores in variable names.

Additional variables may be passed in via the command line with the `--extra-vars` option. This may be specified more than once and takes a `key=value` argument.

`aomi` now includes some built in templates. They are specified them with a `builtin:` prefix. In combination with the key modification and extra variables this should allow easy support of non Vault native applications. Current templates are lited

* `bundle-config` provides a read only configuration for a Ruby gems host.
* `gem-credentials` provides a write configuration for uploading gems.
* `pip-conf` provides a read configuration for a Python PyPi repository.
* `pypirc` provides a read configuration for a Python PyPi repository.

# Test

Run with: `make test`

Unit testing is performed with nosetests, simply add new python modules to the tests directory prefixed with `test_`. Integration testing is done with BATS and involves a standalone Vault server. These tests are located under `tests/integration`.

# Contribution Guidelines

* Changes are welcome via pull request!
* Please use informative commit messages and pull request descriptions.
* Please remember to update the README if needed.
* Please keep style consistent. This means PEP8 and pylint compliance at a minimum.
* Please add tests.

If you have any questions, please feel free to contact <jonathan.freedman@autodesk.com>.
