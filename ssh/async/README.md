# Key Generation.

> Private-Key files
```shell
ssh-keygen -t ed25519 -f client_host_key
```

```shell
ssh-keygen -t ed25519 -f server_key
```
> for the __trusted_server_keys__ file
> Just copy the content of __server_key.pub__ inside it.

> for the __trusted_client_host_keys__ file 
> Just copy the content of __client_host_key.pub__ inside it prefixed with the client IP-Address
