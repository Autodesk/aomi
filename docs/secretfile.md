---
layout: default
---

# Overview

The Secretfile (which does not actually need to be named `Secretfile`) contains your data definition of operational secrets. This information is comprised of an aomi data type combined with Vault mountpoint and path, along with associated metadata. It may contain references to complementary data, both secret and non-secret, which will also be written to vault. Examples of non-secret data include Vault policies and AWS credentials.

The default behavior is to look for Vault metadata and actual secrets in two different directories, both located relative to the `Secretfile`. You may customize the locations of these directories with runtime command line options. For more information check out the [file paths]({{site.baseurl}}/data#about-file-paths) data operations section.

This example `Secretfile` models two [userpass](https://www.vaultproject.io/docs/auth/userpass.html) style [users]({{site.baseurl}}/auth-resources#users) with different [policies]({{site.baseurl}}/policies), and a [file]({{site.baseurl}}/generic#files) with an SSH key. Note that this example would need both associated Vault metadata (for policies) and the SSH private key file.

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

The Secretfile is interpreted as a YAML file. Prior to parsing out Vault constructs, aomi will render it as a [Jinja2](http://jinja.pocoo.org/) template. This means you can have conditionals, includes, and external variables. There is a fair amount of flexibility in terms of how you may structure data. Once in YAML format, the data is interpreted based on a few broad categories.

* `secrets` is the most widely used section. It contains definitions for data that represents operational secrets. With the exception of the `generated` generic secret type, all of these entries must have companion files within the secrets directory as [interpreted](http://autodesk.github.io/aomi/data#about-file-paths) by aomi.
* Vault policies and audit logs are also configurable. These do not have any secrets associated with them.
* You can define some metadata which is limited to GPG/Keybase information, used for cold storage of secrets.
* The `userpass` authenticaiton backend is currently supported. The use of DUO with this backend is also supported.

It is possible to be explict about the presence of a Vault construct on the server. Every entry should support the `state` value, which can be set to either `present` (the default) or `absent`.

# Tagging

Every entry which will affect Vault may be "tagged". Any and all tags must be referenced in order for the resource to be processed. Untagged resources will only be processed if tags are not specified on the command line. The following example shows two sets of static files, each tied to a different tag. This is one way of having a single `Secretfile` which can be used to populate multiple environments.

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


# Mountpoints

You can specify generic secret store mountpoints to be created but not neccesarily provisioned with data. This is helpful when you have one group managing the base Vault instance but another group managing the data within certain mountpoints. The following example will ensure that the default generic backend (`secret)` is always present, along with a new mountpoint named `another_teams_secrets`.

----
`Secretfile`

```
mounts:
- 'secret'
- 'another_teams_secrets'
```

# Secrets

[Generic secrets]({{site.baseurl}}/generic) may be written to Vault based on one of three different formats. Static files map to objects at a given Vault path. Each key in the object may map to a different file. YAML files map also map directly to objects at a given Vault path. And finally you may have "generated" secrets which are random (or predefined) strings.

You can also setup [AWS secret]({{site.baseurl}}/aws) backends. Roles may be either externally specified or specified inline.

# Policies

Policies may be managed [separately]({{site.baseurl}}/policies) or in-line with supporting resources. It is recommended to manage each Vault policies separately as opposed to in-line with other resources.

# Authentication Resources

The aomi tool can [provision]({{site.baseurl}}/auth-resources) appid, user auto, duo, and approle resources into Vault.
