---
name: odin-dev-kube
description: Kubernetes operations on EKS — manual rollouts, ArgoCD refresh, sealed secrets, pod debugging, and Dagster pipeline inspection. Use when user says /odin-dev-kube or asks about k8s rollout, restart deployment, argocd sync, sealed secrets, dagster pods, k8s logs, or pipeline failures.
---

# Kubernetes Operations & Debugging

Manage deployments, rollouts, sealed secrets, and debug pods on EKS.

## Cluster Access

Two EKS clusters in `us-west-2` (account `996435522985`), configured as kubectl contexts:

| Environment | Context Name | EKS Cluster |
|-------------|-------------|-------------|
| **Staging** | `stg` | `stg-app` |
| **Production** | `prd` | `prd-app` |

### IMPORTANT: Environment Selection

**Before running ANY kubectl command, you MUST determine the target environment.**

1. If the user explicitly says "stg", "staging", "prd", "prod", or "production" → use that environment.
2. If the context of the conversation implies an environment (e.g., debugging a prod incident, testing in staging) → use that environment.
3. **If the environment is ambiguous or not specified → ASK the user which environment they mean. Do NOT assume.**

### Using --context (REQUIRED)

**Always use `--context` flag** instead of switching the global kubeconfig context. This avoids side effects on other terminal sessions.

```bash
# Staging
kubectl --context stg get pods -n dagster | head -5

# Production
kubectl --context prd get pods -n dagster | head -5
```

### Kubeconfig Setup (one-time)

```bash
aws eks update-kubeconfig --region us-west-2 --name stg-app --alias stg
aws eks update-kubeconfig --region us-west-2 --name prd-app --alias prd
```

**IP whitelisting required**: EKS public access CIDRs are managed in `cybertino/gitops` Terraform. If `kubectl` times out, your IP needs whitelisting.

## Manual Rollout & ArgoCD Refresh

When you update secrets, configmaps, or need to force a new deployment rollout:

### 1. Trigger ArgoCD Refresh (pick up gitops changes)

```bash
# Annotate the ArgoCD application to trigger a refresh
kubectl patch application <app-name> -n argocd --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"normal"}}}'

# Check sync status
kubectl get application <app-name> -n argocd -o jsonpath='{.status.sync.status} {.status.health.status}'
```

### 2. Restart Deployment (rolling restart)

```bash
# Trigger a rolling restart — pods pick up new secrets/configmaps
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# Watch rollout progress
kubectl rollout status deployment/<deployment-name> -n <namespace> --timeout=120s
```

### 3. Verify

```bash
# Check pods are running with new revision
kubectl get pods -n <namespace> -l app=<app-label> -o wide

# Check a specific env var is set
kubectl exec -n <namespace> deployment/<deployment-name> -- env | grep <VAR_NAME>
```

### Known Apps

| App | Namespace | ArgoCD Application |
|-----|-----------|-------------------|
| surfwiki-api | app | surfwiki-api |
| dagster | dagster | dagster |

## Sealed Secrets

Secrets are managed via Bitnami Sealed Secrets. The sealed-secrets-controller runs in `kube-system`.

### Seal a new secret value

```bash
kubectl create secret generic <secret-name> \
  --namespace <namespace> \
  --from-literal=<KEY>='<value>' \
  --dry-run=client -o yaml | \
  kubeseal --format yaml \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system
```

Copy the `encryptedData.<KEY>` value into the `sealed-secret.yaml` in the gitops repo, commit, push, then trigger ArgoCD refresh + rollout restart (steps above).

### Verify a secret was unsealed

```bash
# List all keys in the secret
kubectl get secret <secret-name> -n <namespace> -o jsonpath='{.data}' | python3 -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in sorted(d.keys())]"

# Decode a specific value
kubectl get secret <secret-name> -n <namespace> -o jsonpath='{.data.<KEY>}' | base64 -d
```

## Dagster Pod Layout

| Pod Pattern | Role |
|-------------|------|
| `dagster-core-daemon-*` | Dagster daemon (schedules, sensors, run queue) |
| `dagster-core-dagster-webserver-*` | Dagster UI |
| `swell-dagster-user-deployments-swell-*` | User code server (our pipeline code) |
| `dagster-run-{uuid}-*` | One pod per run (Completed or Running) |

## Common Debugging Commands

### List Active Pods (skip completed runs)

```bash
kubectl get pods -n dagster | grep -v Completed
```

### Check for OOMKilled Pods

```bash
kubectl get pods -n dagster -o json | jq '.items[] | select(.status.containerStatuses[]?.lastState.terminated.reason == "OOMKilled") | .metadata.name'
```

### User Code Server Logs

Asset-level errors (dbt failures, script errors) surface in the user code server:

```bash
# Find the pod name
kubectl get pods -n dagster | grep swell-dagster-user-deployments

# Read recent logs
kubectl logs -n dagster swell-dagster-user-deployments-swell-<suffix> --tail=200
```

### Run Pod Logs

Each Dagster run creates its own pod. Find it by run ID or by recency:

```bash
# List recent run pods (newest last)
kubectl get pods -n dagster --sort-by='.metadata.creationTimestamp' | grep dagster-run | tail -10

# Logs from a specific run
kubectl logs -n dagster dagster-run-<uuid>-<suffix> --tail=200

# Follow logs from a running pod
kubectl logs -n dagster dagster-run-<uuid>-<suffix> --tail=50 -f
```

### Find Failed Runs

```bash
# Pods in Error state
kubectl get pods -n dagster | grep Error

# Recently terminated pods with non-zero exit
kubectl get pods -n dagster -o json | jq -r '.items[] | select(.status.phase == "Failed" or (.status.containerStatuses[]?.state.terminated.exitCode // 0) != 0) | "\(.metadata.name) \(.status.phase) \(.status.containerStatuses[0].state.terminated.reason // "unknown")"'
```

### Pod Resource Usage

```bash
# Memory/CPU usage of running pods
kubectl top pods -n dagster | grep -v Completed | sort -k3 -h
```

### Describe Pod (events, restart reasons)

```bash
kubectl describe pod -n dagster <pod-name> | tail -30
```

## Deployment

- **GitOps**: `cybertino/gitops` repo → `apps/dagster/dagster-user-deployments/swell-prod-values.yaml`
- **CI**: `.github/workflows/dagster-prod.yml` builds Docker image → pushes to ECR → updates gitops values
- **Docker image**: `996435522985.dkr.ecr.us-west-2.amazonaws.com/swell-dagster`
- **Dockerfile**: `Dockerfile-Dagster` at repo root
- **Sync**: Flux/ArgoCD picks up values change and rolls out new pods

## Troubleshooting

### kubectl times out
Your IP is not whitelisted on EKS public access CIDRs. Check your IP (`curl ifconfig.me`) and add it in `cybertino/gitops` Terraform.

### Pod stuck in Running for hours
Check if it's a long-running backfill or stuck. Read logs:
```bash
kubectl logs -n dagster <pod-name> --tail=20
```

### OOM on ClickHouse (not k8s)
Dagster pods may succeed but the ClickHouse query they trigger OOMs server-side. Check ClickHouse `system.query_log`:
```sql
SELECT query_start_time, round(query_duration_ms/1000,1) as sec,
    round(memory_usage/1024/1024/1024,2) as gib, exception
FROM system.query_log
WHERE type != 'QueryStart' AND exception != ''
ORDER BY query_start_time DESC LIMIT 10
```
