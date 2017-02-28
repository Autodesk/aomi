---
layout: default
---
# Overview

The aomi tool may make use of different sources of data when writing to the generic secret backend of Vault. If the mountpoint does not exist it will be created as a [generic](https://www.vaultproject.io/docs/secrets/generic/) secret store.

# Format

The format will vary slightly depending on what your source data is.

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

## Generated Secrets

The aomi tool has the ability to populate a generic Vault path with random secrets. You still specify the mountpoint, path, and keys but not the contents. By default this is a write once operation but you can change this with the `overwrite` attribute. You can generate either random words or a uuid.

----

`Secretfile`

```
secrets:
- generated:
    mount: 'foo'
    path: 'bar'
    keys:
    - name: 'username'
      method: 'words'
    - name: 'password'
      method: 'uuid'
      overwrite: true
```
