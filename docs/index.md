---
layout: default
---

# Overview

The primary purpose behind aomi is to provide a data model, suitable for use in a continuous delivery pipeline, for operational secrets as stored in Hashicorp [Vault](https://www.vaultproject.io/). This data model is expressed as [YAML](http://www.yaml.org/) in a file generally called [`Secretfile`](/secretfile).

aomi itself is quite flexible, but can be used to enforce rigorous opinions upon how an organization chooses to leverage Vault. It currently supports a variety of means of representing [Generic](https://www.terraform.io/docs/providers/vault/r/generic_secret.html) and [AWS](https://www.vaultproject.io/docs/secrets/aws/index.html) secrets. There is also limited support for other constructs such as audit logs and policies.

# Quickstart

You can pull aomi from [Docker Hub](https://hub.docker.com/r/autodesk/aomi/) and run it either on a workstation or within a continuous delivery pipeline. You can pass authentication information in through a variety of hints, but the easiest is to just use your already established Vault credentials.

This simple operation will display the aomi operations which are available. You need to have succesfully completed a `vault auth` operation for this to work.

```
$ docker run \
      -e VAULT_ADDR=$VAULT_ADDR \
      -v ${HOME}:/.vault-token \
      autodesk/aomi
```
