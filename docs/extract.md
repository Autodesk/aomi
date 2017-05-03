---
layout: default
---

# Overview

The aomi tool does provide a bunch of mechanisms for easily pulling stuff out of Vault. It is not meant to replace things such as [envconsul](https://github.com/hashicorp/envconsul), but complement it. Generally we have been using these operations in continuous delivery pipelines where rotation of long lived secrets is not necessary.

# key modification

The `environment` and `template` actions have several options which allow you to modify how the secret key will be presented. This is an evolution of the `--prefix` argument which is now deprecated. Previously, you could replace the first part of the Vault path with a static prefix.

```
aomi environment --prefix aaa foo/bar/baz
AAA_BAM=secret
```

The same behavior is still available through a combination of new modifying options.

```
aomi environment --add-prefix aaa_ --no-merge-path foo/bar/baz
AAA_BAM=secret
```

With `--add-prefix ` and `--add-suffix` you can add a string to the front or end of a key. The `--no-merge-path` and `--merge-path` options force whether or not to use the full Vault path. The `--key-map` option can be passed in multiple times and takes a `old=new` argument and will cause the key names to be mapped accordingly, prior to other modifications.

# extract_file

This action takes two arguments - the source path and the destination file. The destination file directory must already exist.

This example extracts a hypothetical SSH private into a users home directory.

`aomi extract_file foo/bar/baz/private /home/foo/.ssh/id_rsa`

# aws_environment

This action takes a single argument - an AWS credentials path in Vault.  In return, it will generate a shell snippet exporting the `AWS_SECRET_ACCESS_KEY` and `AWS_ACCESS_KEY_ID` environment variables. This output is sufficient to be eval'd (don't do this) or piped to a file and sourced in to a shell. Export snippets can be generated  with `--export`. If the AWS Vault path provides a STS token, this will also be used.

This example will render a shell environment snippet derived from dynamic IAM credentials.

`aomi aws_environment foo/bar/baz/aws/creds/default`

# environment

This action takes any number of Vault paths are it's arguments. In return, it will generate a small snipped exporting the contained secrets as environment variables. This output is sufficient to be eval'd (no really, don't do this) or piped to a file an sourced in to a shell. Export snippets can be generated  with `--export`.

```
aomi environment foo/bar/baz
FOO_BAR_BAZ_USER="foo"
FOO_BAR_BAZ_PASSWORD="bar"
```

The previously available `--prefix` functionality has been replaced with more generic [key modification]({{site.baseurl}}/extract#key-modification) functionality. The old functionality will still work for now, but will throw a warning about deprecation. Compare the following commands to see how the same effect would be accomplished now.

```
$ aomi environment foo/bar/baz --prefix foo/bar
$ aomi environment --no-merge-path foo/bar/baz --add-prefix baz_
BAZ_USER="foo"
BAZ_PASSWORD="bar"
```

# template

This action takes at least three arguments - the template source, a destination file, and a list of Vault paths. Secrets will be included as variables in the template as the full path with forward slashes replaced by underscores. As an example, `foo/bar/baz/user` would become `foo_bar_baz_user`. The template format used is Jinja2. Note that hyphens will be replaced with underscores in variable names. Take the following example for generating a simple inifile configuration snippet.

```
$ vault read foo/bar
Key                  Value
---                  -----
refresh_interval     720h0m0s
user                 test
password             1234
$ cat /tmp/template
[auth]
username: {{user}}
password: {{password}}
$ aomi template /tmp/template /tmp/render foo/bar
$ cat /tmp/render
[auth]
username: test
password: 1234
```

Additional variables may be passed in via the command line with the `--extra-vars` option. This may be specified more than once and takes a `key=value` argument. You may also pass in YAML variable files with the `--extra-vars-file` options.

If your template requires iteration across a bunch of secrets then you may use the `aomi_items` variable, which is Python dictionary accessible from the Jinja2 template. This is automatically added to every `aomi` template context.

`aomi` now includes some built in templates. They are specified them with a `builtin:` prefix. In combination with the key modification and extra variables this should allow easy support of non Vault native applications. When interacting with the builtin templates the `--extra-args` and `--key-map` can be used to help work with existing Vault schemas. 

You may list all included builtin templates by invoking `aomi template --builtin-list`. You may get information on the template itself by invoking `aomi template --builtin-info foo` where `foo` is the template name. The following is a list of all templates and their required variables.

* `bundle-config` provides a read only configuration for a Ruby gems host. This file is generally found in `~/.bundle/config`. It takes the `user` and `password` variables. It also expects a `bundle_url` variable which conforms to `bundlers` obtuse URL format. If you capitalize the URL of your Gem repository, and replace the `.` with `__`, then it should probably work. Otherwise the URL can be extracted from the output of `bundle config`.
* `gem-credentials` provides a write configuration for uploading gems. This file is generally found in `~/.gem/credentials`. It takes a `user` and a `password` variable, which are then base64'd for the HTTP Basic auth format that a Gem credentials file expects.
* `pip-conf` provides a read configuration for a Python PyPi repository. It is generally found at `~/.pip/pip.conf`. This template takes a `user`, `password`, `url_suffix`, and optional `schema` (defaults to `https`). The `url_suffix` is everything that would be _after_ a URL which includes inline HTTP basic auth.
* `pypirc` provides a read configuration for a Python PyPi repository. This file is generally found at `~/.pypirc`. It takes a `user`, `password`, `url`, and optional `repository` (defaults to `private`) variable. The URL is the full PyPi repository URL.
* `tfvars` will render a Terraform compatible variable file with every returned secret.
* `terraform-aws` will render a Terraform AWS `provider` section. Note you will need to pass in the `aws_region` variable as an extra.
* `json-kv` will render a JSON key-value file.
* `docker-auth` will render a Docker `config.json` auth snippet. It expects a `user`, `password`, and `url` variable.
* `shenv` will render a Shell snippet full of environment variables.
