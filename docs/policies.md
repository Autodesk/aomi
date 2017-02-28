---
layout: default
---

# Data Format

Each policy has a `name` and a source `file` specified. This is recommended over using inline policies. You can specify a state of either `present` (the defaut) or `absent` but this is not required. The following example will provision a simple policy.

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

Compare this to the following example which would remove the previously created policy.

----
`Secretfile`

```
policies:
- name: 'foo'
  state: 'absent'
```
