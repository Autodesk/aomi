Aomi: A Vault Wrapper
---------------

This wrapper provide a relatively strongly opinionated interface to Hashicorp Vault. It fulfills two core functions : seeding secrets on behalf of an application or service, and retrieving secrets as pre-formatted consumables. Many operations for the wrapper are defined in a `Secretfile` which will generally live at the top level of a repository.

Secretfile
==========
The important piece of the `Secretfile` is `secrets` as that is where seeds are defined. There are different types o seeds which may be created in vault.

**Files**

You may specify a list of files and their destination Vault secret item. Each `files` section has a list of source files, and the key name they should use in Vault. Each instance of a `files` section must also include a Vault mount point and path. 

----
`Secretfile`

```
secrets:
- files:
  - source: 'dev-secrets'
    name: 'secret'
  - source: 'dev-validator.pem'
    name: 'validator'
  mount: 'paas/abus/dev/secrets'
  path: 'chef'
```

**AWS**

By specifying an appropriately populated `aws_file` you can seed AWS credentials into Vault. The `aws_file` must point to a valid file, and the base of the AWS credentials will be set by the `path`.

The AWS file contains the `region`, `access_key_id`, `secret_access_key`, and a list of AWS roles that will be loaded by Vault. The `name` of each role will be used to compute the final path for accessing credentials. The policy files are simply JSON IAM Access representations.

----

`Secretfile`

```
secrets:
- aws_file: 'dev-aws.yml'
  mount: 'paas/abus/dev/aws'
```

----

`dev-aws.yml`

```

access_key_id: "REDACTED"
secret_access_key: "REDACTED"
region: "us-east-1"
roles:
- policy: "deploy-policy.json"
  name: 'deploy'
- roles:
  policy: "build-policy.json"
  name: 'build'
```

Commands
========

Other than the `seed` command, everything else is used to extract secrets from the vault. All actions will take the `--secretfile` option, to specify where to find the `Secretfile`. The default is the current working directory.

**seed**

The `seed` command also takes the `--policies` and '--secrets` options, which can override the default locations to find Vault policies and roles and actually secrets. These default to `vault` and `.secrets` in the current working directory. The seed command will go through the `Secretfile` and appropriately provision Vault. Note that you need to be logged in, and already have appropriate permissions. The seed command _can_ be executed with no arguments, and it will look for everything in the current working directory..

**extract_file**

This action takes two arguments - the source path and the destination file. The destination file directory must already exist.

`aomi extract_file paas/abus/dev/secrets/chef/secret /etc/chef/secret`

**aws_environment**

This action takes a single argument - an AWS credentials path in Vault.  In return, it will generate a shell snippet exporting the `AWS_SECRET_ACCESS_KEY` and `AWS_ACCESS_KEY_ID` environment variables. This output is sufficient to be eval'd (don't do this) or piped to a file and sourced in to a shell.

`aomi aws_environment paas/abus/dev/aws/creds/build`

**template**

This action takes three arguments - the template source, a destination file, and the Vault path. Secrets will be included as variables in the template as the full path with forward slashes replaced by underscores. As an example, `paas/abus/dev/secrets/chef/secret` would become `paas_abus_dev_secrets_chef_secret`. The template format used is Jinja2.

Contribution Guidelines
-----------------

* Changes are welcome via pull request!
* Please use informative commit messages and pull request descriptions.
* Please remember to update the README if needed
* Please keep style consistent. This means PEP8 at a minimum.

If you have any questions, please feel free to contact Jonathan Freedman <jonathan.freedman@autodesk.com>.
