### TODO

Update all yaml files with comments explaining choices.

# Introduction

Each app has its yaml file(s) inside of its folder: all the apps have a `values.yaml` to customize the values of the helm charts, but only some apps have an `ingress.yaml` to handle traffic.

```
k8s
├── README.md
├── hello_world
│   ├── hello-deployment.yaml
│   └── hello-service.yaml
├── keycloak
│   ├── ingress.yaml
│   └── values.yaml
├── net_debug
│   └── values.yaml
├── open_webui
│   ├── ingress.yaml
│   └── values.yaml
└── qdrant
    └── values.yaml
```

> Remember that for a container to be deployed resource limits are to be set.

# Net Debug

For now, it is the only one that was not set using helm. To change the values, first modify its `values.yaml`, and then run 
```bash
kubectl apply -f k8s/net_debug/values.yaml
```

> This should work fine, otherwise simply run `kubectl delete -f ...` and then `kubectl apply -f ...`

# Keycloak

First, add the [Keycloakx repo](https://github.com/codecentric/helm-charts/tree/master/charts/keycloakx) (community-based implementation of keycloak) and then install it using the `values.yaml`:
```bash
helm repo add codecentric https://codecentric.github.io/helm-charts
helm repo update
helm upgrade --install keycloak codecentric/keycloakx -f k8s/keycloak/values.yaml
```

To uninstall the deployment:
```bash
helm uninstall keycloak
```

You then apply the ingress configuration in order to access it without port-forwarding:
```bash
kubectl apply -f k8s/keycloak/ingress.yaml
```

and add the following configuration to `/etc/hosts/` for ease-of-use:
```
10.128.18.132    auth.local
10.128.18.132    chat.local
```

Now, when you search auth.local you will be redirected to Keycloak.

### Open WebUI in Keycloak

> It is based on the following tutorial: [Integrate Open WebUI with Keycloak for OIDC SSO](https://docs.openwebui.com/features/authentication-access/auth/sso/keycloak/)

First, create a realm (e.g., orfeo). Then, create a new client:  
1. Client ID: 'open-webui'
2. Add client authentication
3. Set Valid redirect URIs: http://chat.local/oauth/oidc/callback
4. Set Web origins: http://chat.local
5. Save and go in the *Credentials* tab in order to get the *Client Secret* which will be later used
6. Finally, create a test user (e.g., admin) and go in the *Credentials* tab to set a new password (e.g., admin)(remember to uncheck temporary)

First, check whether there already is a secret called `open-webui-oidc`:
```bash
kubectl get secrets
```

If there is, delete it:
```bash
kubectl delete secret open-webui-oidc
```

Then, create a new one with the *Client Secret* found in the *Credentials* tab of the Client created in Keycloak:
```bash
kubectl create secret generic open-webui-oidc --from-literal=client-secret='XXX'
```

> Probably this is not the best practice, I know SOPS is used but this was the easiest way :)

You then need to either install Open WebUI or upgrade it with the helm command:
```bash
helm upgrade --install open-webui open-webui/open-webui -f k8s/open_webui/values.yaml
# kubectl apply -f k8s/open_webui/ingress.yaml # if not already done
# kubectl create secret generic vllm-api-key --from-literal=api-key='XXX' # if not already done
```

You can test it all works by searching *chat.local* and trying to sign-in via Keycloak.

# Open WebUI

First, add the [Open WebUI repo](https://github.com/open-webui/helm-charts/tree/main/charts/open-webui) and then install it using the `values.yaml`:
```bash
helm repo add open-webui https://helm.openwebui.com/
helm repo update
helm upgrade --install open-webui open-webui/open-webui -f k8s/open_webui/values.yaml
```

To uninstall the deployment:
```bash
helm uninstall open-webui
# kubectl delete pvc -l app.kubernetes.io/instance=open-webui # perhaps not necessary
```

You then apply the ingress configuration in order to access it without port-forwarding:
```bash
kubectl apply -f k8s/open_webui/ingress.yaml
```

Since Open WebUI runs using the models hosted on Orfeo, it is mandatory to create a secret containing the token to actually access the models (copy the output of `request_token.bash`):
```bash
kubectl create secret generic vllm-api-key --from-literal=api-key='XXX'
```

# Qdrant

