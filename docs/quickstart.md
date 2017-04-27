---
layout: default
---
# Prelude

There is a underlying assumption here that you have access to a working Vault server. If not, you can easily use Vault in [dev mode](https://www.vaultproject.io/docs/concepts/dev-server.html).

## Dev Mode quickstart, start vault server in dev mode listening to all interfaces.
```
vault server -dev -dev-listen-address="0.0.0.0:8200"
...
Unseal Key (hex)   : 38058131e3e451fe0073f27ef2992e803fa2777f0075afffe3d21d90db75635c
Unseal Key (base64): OAWBMePkUf4Ac/J+8pkugD+id38Ada//49IdkNt1Y1w=
Root Token: fab4819e-9929-794d-1c5e-d3e036a25246
...
```


# First Steps

You can pull aomi from [Docker Hub](https://hub.docker.com/r/autodesk/aomi/) and run it either on a workstation or within a continuous delivery pipeline. You can pass authentication information in through a variety of hints, but the easiest is to just use your already established Vault credentials.

To start, we will authenticate to Vault and run the container once.

```
$ vault auth -method=userpass username=foo
Password (will be hidden):
Successfully authenticated! You are now logged in.
The token below is already saved in the session. You do not
need to "vault auth" again with the token.
token: 7e8a2be4-d1b8-4ca8-a8fd-b35ef2591250
token_duration: 86400
token_policies: [default]
$ docker run \
      -e VAULT_ADDR=$VAULT_ADDR \
      -v ${HOME}:/.vault-token \
      autodesk/aomi
aomi docker container
usage: aomi [-h]
            {extract_file,environment,aws_environment,seed,freeze,thaw,template,set_password,token,help}
                        ...
aomi: error: too few arguments
```

## If you are running vault in dev mode, the authentication will be slightly different. VAULT_ADDRESS needs to be set to the Docker IP address, NOT 127.0.0.1.

# Example

```

$ ifconfig -a | grep netmask | grep 172
	inet 172.28.128.1 netmask 0xffffff00 broadcast 172.28.128.255


#Above is output from my machine. Your machine will give different ips.
#Set the VAULT_ADDR to the docker ip address

$ export VAULT_ADDR="172.28.128.1"

$ vault auth # input *root token* given when starting vault in dev mode
    Token (will be hidden):
    Successfully authenticated! You are now logged in.
    token: fab4819e-9929-794d-1c5e-d3e036a25246
    token_duration: 0

```


We are now authenticated with a Vault instance and have `aomi` locally available for execution under Docker.

# Seeding

We are going to use a very simple [Secretfile]({{site.baseurl}}/secretfile) with a single [generic]({{site.baseurl}}/generic) secret. We will be creating a new directory and setting it up in a safe way.

```
$ cd /tmp
$ mkdir test
$ cd test
$ mkdir -p .secrets
$ echo "secret" > .secrets/a-secret
$ chmod -R og-rwx .secrets
```

Right now aomi [assumes](https://github.com/Autodesk/aomi/issues/88) you are always in a git repo. To that end we need to create a fake `.gitignore` to appease it.

```
$ echo ".secrets" > .gitignore
```

We are now ready to create our simple Secretfile. Using the editor of your choice, edit the `Secretfile` to contain the following.

```
---
secrets:
- files:
  - source: 'a-secret'
    name: 'a-secret'
  mount: 'secret'
  path: 'fresh'
```

You are now ready to write to your vault! To make it more exciting, we can invoke aomi in verbose mode. Note that when running in Docker, we need to be explicit about our file paths.

```
$ docker run \
    -e VAULT_ADDR=$VAULT_ADDR \
    -v "${HOME}/.vault-token:/.vault-token" \
    -v "$(pwd):$(pwd)" \
    autodesk/aomi \
    seed --verbose --secretfile "$(pwd)/Secretfile" --secrets "$(pwd)/.secrets"
Connecting to https://127.0.0.1:8200/
Token derived from /.vault-token
Token metadata operation seed
Token metadata via aomi
Token metadata hostname 1fde10ca1763
Using lease of 10s
writing file /tmp/test/.secrets/a-secret into secret/fresh/a-secret
```

You'll note that `aomi` associates a bunch of metadata with our operational token. You can specify extra metadata if you wish with the `--metadata` option.

# Extraction

We've now written out a simple secret to Vault using our data model. But now we want to do something with it. For this, we have a few options.

To start, we can extract it as a file locally.

```
$ docker run \
    -e VAULT_ADDR=$VAULT_ADDR \
    -v "${HOME}/.vault-token:/.vault-token" \
    -v "/tmp:/tmp" \
    autodesk/aomi \
    extract_file secret/fresh/a-secret /tmp/secret
$ cat /tmp/secret
secret
```

You could also easily render a template. Let's do this using the builtin JSON key/value template. Note that, by default, the "key" will include the _full_ Vault path. You can get fancy with how this is represented with the [key modification]({{site.baseurl}}/extract#key-modification) options.

```
$ docker run \
    -e VAULT_ADDR=$VAULT_ADDR \
    -v "${HOME}/.vault-token:/.vault-token" \
    -v "/tmp:/tmp" \
    autodesk/aomi \
    template builtin:json-kv /tmp/secret.json secret/fresh
$ cat /tmp/secret.json
{
"secret_fresh_a_secret": "asda"
}
```
