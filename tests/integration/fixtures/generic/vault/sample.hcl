path "foo/*" {
  capabilities = ["read", "update", "create", "delete"]
}
path "auth/token/lookup-self" {
  capabilities = ["read"]
}
path "auth/token/create" {
  capabilities = ["create", "update"]
}
path "sys/mounts" {
  capabilities = [ "read" ]
}
