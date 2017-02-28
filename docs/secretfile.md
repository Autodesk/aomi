---
layout: default
---

# Overview

The Secretfile (which does not actually need to be called Secretfile) contains the data definition for operational secrets. This information is comprised of an aomi data type combiened with Vault mountpoint and path, along with associated metadata. It may contain references to complementary data, both secret and non-secret, which will also be written to vault. Examples include Vault policies and AWS credentials.

# General Structure

The Secretfile is interpreted as a YAML file. Prior to parsing, aomi will handle it as a [Jinja2](http://jinja.pocoo.org/) template. This means you can have conditionals, includes, and external variables. There is a fair amount of flexibility in terms of how the data is structured. Once in YAML format, the data is interpreted based on a few broad categories.

* `secrets` is the most widely used section. It contains definitions for data that represents operational secrets. With the exception of the `generated` generic secret type, all of these entries will have companion files within the `.secrets` directory as used by aomi
* You can configure a few authentication types via aomi. Right now this is limited to general [userpass](https://www.vaultproject.io/docs/auth/userpass.html) and [DUO](https://www.vaultproject.io/docs/auth/mfa.html) support. Both of these constructs rely on files within `.secrets` as well.
* Vault policies and audit logs are also configurable. These do not have any secrets associated with them. Vault mountpoints are also manually definable.
* You can also define some metadata. This is limited to GPG/Keybase information, which is used for cold storage of secrets.

Every entry which will affect Vault can be "tagged". Any and all tags must be referenced in order for the entry to be processed.

# Secrets

[Generic secrets]({{site.baseurl}}/generics) may be written to Vault based on one of three different formats. Static files can map to objects at a given Vault path. Each key in the object may map to a different file. YAML files map also map directly to objects at a given Vault path. And finally you may have "generated" secrets which can be random (or predefined) strings.

You can also setup [AWS secret]({{site.baseurl}}/aws) backends. Roles may be either externally specified or specified inline. 

# Policies

Policies may be manged [separately]({{site.baseurl}}/policies) or in-line with supporting resources. It is recommended to manage each Vault resource separately.

# Authentication Resources

The aomi tool can [provision]({{site.baseurl}}/auth-resources) appid, user auto, duo, and approle resources into Vault.
