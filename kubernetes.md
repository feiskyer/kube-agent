# Run in Kubernetes

## Use default service account

If the default service account is already configured with RBAC bindings, you can use this simpler method to run:

```sh
kubectl run -it --rm copilot \
  --env="OPENAI_API_KEY=$OPENAI_API_KEY" \
  --restart=Never \
  --image=ghcr.io/feiskyer/kube-agent \
  -- execute --verbose 'What Pods are using max memory in the cluster'
```

## Use a dedicated service account

Create RBAC rule and binding:

```sh
kubectl apply -f - <<EOF
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kube-agent-reader
rules:
- apiGroups:
  - '*'
  resources:
  - '*'
  verbs:
  - 'get'
  - 'list'
- nonResourceURLs:
  - '*'
  verbs:
  - 'get'
  - 'list'
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kube-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: kube-agent-reader
subjects:
- kind: ServiceAccount
  name: kube-agent
  namespace: default
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kube-agent
  namespace: default
automountServiceAccountToken: true
EOF
```

Create secret:

```sh
kubectl create secret generic kube-agent-auth \
    --from-literal=OPENAI_API_KEY=${OPENAI_API_KEY}
```

Run:

```sh
kubectl run -it --rm copilot \
  --restart=Never \
  --image=ghcr.io/feiskyer/kube-agent \
  --overrides='
{
  "spec": {
    "serviceAccountName": "kube-agent",
    "containers": [
      {
        "name": "copilot",
        "image": "ghcr.io/feiskyer/kube-agent",
        "env": [
          {
            "name": "OPENAI_API_KEY",
            "valueFrom": {
              "secretKeyRef": {
                "name": "kube-agent-auth",
                "key": "OPENAI_API_KEY"
              }
            }
          }
        ]
      }
    ]
  }
}' \
  -- execute --verbose 'What Pods are using max memory in the cluster'
```
