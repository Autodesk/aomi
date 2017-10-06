# for vault pre 0.7.x
path "secret/{{path|default("foo")}}" {
  capabilities = ["read", "create", "update"]
}
# for vault post 0.7.x
path "secret/{{path|default("foo")}}/*" {
  capabilities = ["read", "create", "update"]
}
