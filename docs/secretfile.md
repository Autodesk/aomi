---
layout: default
---

# Overview

The Secretfile (which does not actually need to be called Secretfile) contains the data definition for operational secrets. This information is comprised of an aomi data type combined with Vault mountpoint and path, along with associated metadata. It may contain references to complementary data, both secret and non-secret, which will also be written to vault. Examples include Vault policies and AWS credentials.

The default behavior is to look for Vault metadata and actual secrets in two different directories, both located relative to the `Secretfile`. For more information check out the [File Paths]({{site.baseurl}}/data#about-file-paths) data operations section.

This example `Secretfile` models two "userpass" [users]({{site.baseurl}}/auth-resources#users) with different [policies]({{site.baseurl}}/policies), and a static secret [file]({{site.baseurl}}/generic#files). Note that this example would need both associated Vault metadata (for policies) and a SSH private key file.

```
policies:
- name: 'developer'
  file: 'developer.hcl'
- name: 'root'
  file: 'root.hcl'
users:
- username: 'root'
  password_file: 'root-user.txt'
  policies:
  - 'root'
- username: 'test'
  password_file: 'test-user.txt'
  policies:
  - 'developer'
mounts:
- 'secret'
secrets:
- files:
  - source: 'id_rsa'
    name: 'private'
  mount: 'secret'
  path: 'key'
```

# General Structure

The Secretfile is interpreted as a YAML file. Prior to parsing, aomi will handle it as a [Jinja2](http://jinja.pocoo.org/) template. This means you can have conditionals, includes, and external variables. There is a fair amount of flexibility in terms of how the data is structured. Once in YAML format, the data is interpreted based on a few broad categories.

* `secrets` is the most widely used section. It contains definitions for data that represents operational secrets. With the exception of the `generated` generic secret type, all of these entries will have companion files within the `.secrets` directory as used by aomi
* You can configure a few authentication types via aomi. Right now this is limited to general [userpass](https://www.vaultproject.io/docs/auth/userpass.html) and [DUO](https://www.vaultproject.io/docs/auth/mfa.html) support. Both of these constructs rely on files within `.secrets` as well.
* Vault policies and audit logs are also configurable. These do not have any secrets associated with them. Vault mountpoints are also manually definable.
* You can also define some metadata. This is limited to GPG/Keybase information, which is used for cold storage of secrets.

# Tagging

Every entry which will affect Vault can be "tagged". Any and all tags must be referenced in order for the entry to be processed. Untagged events will only be processed if tags are not specified on the command line. The following example shows two sets of static files, each tied to a different tag. This is one way of having a single `Secretfile` which can be used to populate multiple environments.

----
`Secretfile`

```
secrets:
- files: 
  - source: id_rsa_dev
    name: private
  path: 'ssh'
  mount: 'secret'
  tags:
  - dev
- files: 
  - source: id_rsa_stage
    name: private
  path: 'ssh'
  mount: 'secret'
  tags:
  - stage
```

With this model, you can then have a single file which may be applied in different contexts. For example, note the difference between running `aomi seed` against two different hosts.

```
$ VAULT_ADDR=https://dev.example.com:8200/ aomi seed --tags dev
$ VAULT_ADDR=https://stage.example.com:8200/ aomi seed --tags stage
```

Tagging is supported on every type of Vault resource. The `--tags` command line option is available on all [data]({{site.baseurl}}/data) operations.

# Templating

The `Secretfile` itself is a Jinja2 template. When rendering, it will take into account variables provided via either the `--extra-vars` or `--extra-vars-file` options as documented under the [`seed`]({{site.baseurl}}/data#seed) operation. This is another means with which you can have a single file being used in multiple logical Vault contexts. The following example shows how we could have a single file be used to provision different SSH keys to different Vault paths.

----
`Secretfile`

```
secrets:
- files:
    source: 'id_rsa_{{env}}'
    name: 'private'
  mount: 'secret'
  path: 'ssh/{{env}}'
```

When running the [data]({{site.baseurl}}/data) operations, you can then specify the environment on a command line.

```
$ aomi seed --extra-vars env=dev
$ aomi seed --extra-vars env=stage
```

# Secrets

[Generic secrets]({{site.baseurl}}/generic) may be written to Vault based on one of three different formats. Static files can map to objects at a given Vault path. Each key in the object may map to a different file. YAML files map also map directly to objects at a given Vault path. And finally you may have "generated" secrets which can be random (or predefined) strings.

You can also setup [AWS secret]({{site.baseurl}}/aws) backends. Roles may be either externally specified or specified inline.

# Policies

Policies may be managed [separately]({{site.baseurl}}/policies) or in-line with supporting resources. It is recommended to manage each Vault policies separately as opposed to in-line with other resources.

# Authentication Resources

The aomi tool can [provision]({{site.baseurl}}/auth-resources) appid, user auto, duo, and approle resources into Vault.
