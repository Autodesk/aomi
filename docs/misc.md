---
layout: default
---

There are some operations which don't really fit in either the context of the [data]({{site.baseurl}}/data) model or [extraction]({{site.baseurl}}/extract) of data.

# auth

This operation will derive an operational Vault token based on any environmental hints that aomi supports. The various mechanisms which aomi will use for authentication are described under [operations]({{site.baseurl}}/operations#Authentication). Both the `--metadata` and `--lease` options are supported.

# set_password

This action can be used to easily change passwords. It can operate on both userpass users and generic secrets paths. It will ask for the password (and a confirmation). Optionally, you may pass in a password via stdin.

To modify a users password you would invoke the following

```
aomi set_password user:foo
Enter Password:
Again, Please:
```

You can also modify passwords stored in arbitary Vault paths (in this example using stdin).

```
aomi set_password foo/pass <<< "1234"
```

# render

This action is used to render the [`Secretfile`]({{site.baseurl}}/secretfile). It respects the `--policies`, `--secrets`, `--secretfile`, `--extra-vars`, and `--extra-vars-file` options in the same way as the [`seed`]({{site.baseurl}}/data#seed) operation. This operation takes a minimum of one argument, the directory to write the rendered `Secretfile` (and accoutrement) to.

```
$ aomi render /tmp/rendered
```

The output will be written to the specified directory, with the following structure.

* The `Secretfile` will be at the directory root
* Policies will be found in a directory named `policies`
* AWS inline roles will be found in a directory named `aws`
