---
layout: default
---

# Overview

The Secretfile (which does not actually need to be called Secretfile) contains the data definition for operational secrets. This information is comprised of an aomi data type combiened with Vault mountpoint and path, along with associated metadata. It may contain references to complementary data, both secret and non-secret, which will also be written to vault. Examples include Vault policies and AWS credentials.

# Types of Secrets

Generic secrets may be written to Vault based on one of three different formats. Static files can map to objects at a given Vault path. Each key in the object may map to a different file. YAML files map also map directly to objects at a given Vault path. And finally you may have "generated" secrets which can be random (or predefined) strings.

You can also setup AWS secret backends. Roles may be either externally specified or specified inline. 
