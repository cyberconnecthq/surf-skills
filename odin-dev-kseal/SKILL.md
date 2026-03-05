---
name: odin-dev-kseal
description: >
  Manage Kubernetes sealed secrets on EKS — decrypt from cluster, edit plaintext secrets file,
  seal with kubeseal, validate, and commit to gitops. Use when user says /odin-dev-kseal
  or asks about sealed secrets, adding env vars, updating secrets, kubeseal, or secret management.
---

# Sealed Secrets Management

Manage Bitnami SealedSecrets on EKS (us-west-2). Secrets are encrypted locally, committed to gitops, and decrypted in-cluster by the sealed-secrets controller.

## Cluster Info

- **Clusters**: `stg-app` (staging) and `prd-app` (production), both us-west-2
- **ALL kubectl commands must include `--context stg-app` or `--context prd-app`**
- **Controller**: `sealed-secrets-controller` in `kube-system` (same on both clusters)
- **Gitops repo**: `/Users/peng/Workspace/k8s/gitops/`

## File Structure

Each service folder contains:
- `secrets` — plaintext secrets file (gitignored via `**/secrets`)
- `sealed-secret.yaml` — encrypted sealed secret committed to git

## Workflow: Add or Update Secrets

### 1. Pull latest gitops code

```bash
cd /Users/peng/Workspace/k8s/gitops && git pull
```

### 2. Decrypt current secrets from cluster

Use the `kseal-decrypt.py` script. It reads `sealed-secret.yaml` to auto-detect secret name and namespace.

```bash
# Decrypt from stg (default context)
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-decrypt.py apps/<path>/

# Decrypt from prd
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-decrypt.py apps/<path>/ --context prd-app

# Preview keys without writing (dry-run)
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-decrypt.py apps/<path>/ --dry-run
```

The script writes a properly formatted YAML `secrets` file with `stringData` to the app path. It handles YAML quoting for values that could be misinterpreted (booleans, special chars).

### 3. Edit the secrets file

Add, remove, or update keys in `stringData`.

### 4. Seal and validate

Use the `kseal-seal.py` script. It seals the `secrets` file with kubeseal, validates the output, and shows a key diff against the existing `sealed-secret.yaml`.

```bash
# Seal against stg (default context)
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-seal.py apps/<path>/

# Seal against prd
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-seal.py apps/<path>/ --context prd-app

# Dry-run: seal + validate without writing
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-seal.py apps/<path>/ --dry-run
```

The script: reads `secrets` → validates YAML structure → seals with kubeseal → validates sealed output → shows added/removed keys → writes `sealed-secret.yaml`.

### 6. Commit & push

```bash
cd /Users/peng/Workspace/k8s/gitops
git add apps/<path>/sealed-secret.yaml
git commit -m "chore: update <service> secrets"
git push
```

### 7. ArgoCD sync + restart

```bash
kubectl patch application <app-name> -n argocd --context prd-app --type merge \
  -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"normal"}}}'
kubectl rollout restart deployment/<deployment-name> -n <namespace> --context <stg-app|prd-app>
kubectl rollout status deployment/<deployment-name> -n <namespace> --context <stg-app|prd-app> --timeout=120s
```

### 8. Verify

```bash
kubectl get secret <secret-name> -n <namespace> --context <stg-app|prd-app> -o jsonpath='{.data.<KEY>}' | base64 -d
```

## Decrypt: Read Live Secret from Cluster

```bash
# Quick preview of key names only
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-decrypt.py apps/<path>/ --dry-run

# Full decrypt to file
python3 ~/.claude/skills/surf-skills/odin-dev-kseal/scripts/kseal-decrypt.py apps/<path>/ --context <stg-app|prd-app>
```

## Alternative: Seal a single raw value

Only use when patching one key without re-sealing everything. Prefer the full re-seal workflow above.

```bash
echo -n "the-secret-value" | kubeseal --raw \
  --name <secret-name> \
  --namespace <namespace> \
  --controller-name sealed-secrets-controller \
  --controller-namespace kube-system \
  --context <stg-app|prd-app>
```

Outputs the encrypted value. Manually paste it into `encryptedData` in `sealed-secret.yaml`.

## Important Notes

- **ALWAYS decrypt before sealing**: The `secrets` file is a local cache that can become stale. Before any seal operation, ALWAYS run `kseal-decrypt.py` first to get fresh secrets from the cluster. The seal script will warn if the file is older than 5 minutes, but do not rely on this alone — make it a habit.
  - **Why this matters**: If someone updated `sealed-secret.yaml` directly (e.g., unifying JWT keys across services), the local `secrets` file won't reflect that change. Re-sealing from a stale `secrets` file will silently revert those updates.
- **Always use `--context`**: Every kubectl command must specify `--context stg-app` or `--context prd-app` for the correct cluster.
- **Scope binding**: SealedSecrets are bound to a specific `name` + `namespace` pair. You cannot copy a sealed-secret.yaml to a different namespace without re-sealing.
- **Re-seal everything**: When changing any key, it's safest to re-seal the entire `secrets` file rather than patching individual values with `--raw`.
- **Certificate rotation**: The controller rotates its key every 30 days. Old sealed secrets remain valid (the controller keeps old keys). But if you saved a cert file, refresh it periodically.
- **Output format**: Some sealed-secret.yaml files in the gitops repo use JSON format (older), others use YAML. Always use `--format yaml` for consistency going forward.
- **Plaintext `secrets` file**: Keep it around for human readability. It is gitignored (`**/secrets`) so it won't be committed accidentally.
- **NEVER** print secret values in tool output or logs. When showing the user, mask values or only show key names.

## Known Services and Paths

| Service | Namespace | Secret Name | Path |
|---------|-----------|-------------|------|
| swell (dagster) | dagster | swell-secrets | `apps/dagster/common/swell/` |
| dagster-core | dagster | dagster-core-secrets | `apps/dagster/common/dagster-core/` |
| odin (dagster) | dagster | odin-secrets | `apps/dagster/common/odin/` |
| odin-flow (dagster) | dagster | odin-flow-secrets | `apps/dagster/common/odin-flow/` |
| helios (dagster) | dagster | helios-secrets | `apps/dagster/common/helios/` |
| diver (dagster) | dagster | diver-secrets | `apps/dagster/common/diver/` |
| urania-agent | app | urania-agent-sec | `apps/urania-agent/` |
| surfwiki-api | app | surfwiki-api-sec | `apps/surfwiki-api/` |

For the full list, check: `find /Users/peng/Workspace/k8s/gitops -name 'sealed-secret.yaml'`
