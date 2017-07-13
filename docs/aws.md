---
layout: default
---
# Overview

The aomi tool is able to write to the AWS backend of Vault.

# Format

By specifying an appropriately populated `aws_file` you can create [AWS secret backends](https://www.vaultproject.io/docs/secrets/aws/index.html) in Vault. The `aws_file` must point to a valid file, and the base of the AWS credentials will be set by the `mount`.

The AWS file contains the `access_key_id`, and `secret_access_key`. The `region`, and a list of AWS roles that will be loaded by Vault are in the `Secretfile`. Note that you may specify either an inline `policy` _or_ a native AWS `arn`. The `name` of each role will be used to compute the final path for accessing credentials. The policy files are simply JSON IAM Access representations. The following example would create an AWS Vault secret backend at `foo/bar/baz` based on the account and policy information defined in `.secrets/aws.yml`. While `lease` and `lease_max` are provided in this example, they are not strictly required. Note that you can specify the `state` as either `absent` or `present` for each individual role.

Note that a previous version had `lease`, `lease_max`, `region`, and the `roles` section located in the `aws_file` itself - this behavior is now considered deprecated. The _only_ thing which should be present in the AWS yaml is the actual secrets.

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
  - name: default
    policy: "policy.json"
  - name: "root"
    arn: "arn:aws:iam::aws:policy/AdministratorAccess"
```

----

`aws.yml`

```

access_key_id: "REDACTED"
secret_access_key: "REDACTED"
```
