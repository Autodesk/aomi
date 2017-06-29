---
layout: default
---

If you want to just jump in, check out the [quickstart]({{site.baseurl}}/quickstart).

# Overview

The purpose of aomi is to provide a data model, suitable for use in a continuous delivery pipeline, to facilitate the storing of operational secrets within Hashicorp [Vault](https://www.vaultproject.io/). This data model is expressed as [YAML](http://www.yaml.org/) in a file (generally) named [`Secretfile`]({{site.baseurl}}/secretfile). You can then leverage this data model to provide consistent deployment of secrets in isolated environments with distinct Hashicorp Vault servers.

The aomi tool itself is quite flexible, but can be used to enforce rigorous opinions upon how an organization chooses to leverage Vault. The `aomi` tool may write to a variety of Vault backends.

* [Generic]({{site.baseurl}}/generic) secrets
* [AWS]({{site.baseurl}}/aws) credentials
* Vault [Policies]({{site.baseurl}}/policies)
* [Authentication]({{site.baseurl}}/auth-resources) resources

# Docker

The ability to use aomi to interact with Vault via a Docker container is key towards easily integrating with most modern continuous delivery pipelines. You can pass configuration into the `aomi` Docker container using either environment variables or files passed in during `docker run`.

* The `VAULT_TOKEN` environment variable.
* The `VAULT_APP_ID` and `VAULT_USER_ID` variables.
* The `/.vault-token` file.
* The `/.aomi-app-token` file.
* If the `/app` directory is present, the working directory will be switched. Use this during `seed` operations

To view perform an `aomi seed` using an existing Vault login on a workstation you could use something like the following.

```
docker run \
    -e VAULT_ADDR=$VAULT_ADDR \
    -v ${HOME}/.vault-token:/.vault-token \
    -v ${HOME}/src/example \
    autodesk/aomi \
    seed
```

# Requirements

The `aomi` tool has several requirements which can (generally) all be sourced from [PyPI](https://pypi.python.org/pypi).

The [PyYAML](http://pyyaml.org/) package, by default, will make use of libyaml. This can be a problem on some systems as you may need to manually install libyaml.

You should be using a recent enough version of Python to have good TLS support. Vault can make use of SNI and that requires Python 3.0 or a fresh Python 2.7.

Tests run (both locally and on Travis) in isolation using [virtualenv](https://virtualenv.pypa.io/en/stable/) so you must have this installed if you wish to do active development on `aomi`.
