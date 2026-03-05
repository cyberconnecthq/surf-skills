#!/usr/bin/env python3
"""Seal a plaintext secrets file into sealed-secret.yaml using kubeseal, then validate.

Usage:
    kseal-seal.py <gitops-app-path> [--context stg-app|prd-app]
    kseal-seal.py <gitops-app-path> --context prd-app --dry-run

Examples:
    kseal-seal.py apps/dagster/common/swell/
    kseal-seal.py apps/urania-agent/ --context prd-app
    kseal-seal.py apps/dagster/common/odin/ --dry-run
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

import yaml

GITOPS_ROOT = "/Users/peng/Workspace/k8s/gitops"
DEFAULT_CONTEXT = "stg-app"
CONTROLLER_NAME = "sealed-secrets-controller"
CONTROLLER_NS = "kube-system"
STALE_THRESHOLD_SECONDS = 300  # 5 minutes


def resolve_app_path(path_arg):
    """Resolve the app path to an absolute path under gitops root."""
    if os.path.isabs(path_arg):
        return path_arg.rstrip("/")
    full = os.path.join(GITOPS_ROOT, path_arg)
    if os.path.isdir(full):
        return full.rstrip("/")
    print(f"ERROR: Path not found: {full}", file=sys.stderr)
    sys.exit(1)


def check_secrets_freshness(secrets_path):
    """Warn if the secrets file is stale (not recently decrypted from cluster)."""
    mtime = os.path.getmtime(secrets_path)
    age_seconds = time.time() - mtime
    if age_seconds > STALE_THRESHOLD_SECONDS:
        age_min = int(age_seconds / 60)
        if age_min >= 60:
            age_str = f"{age_min // 60}h {age_min % 60}m"
        else:
            age_str = f"{age_min}m"
        print(f"WARNING: secrets file is {age_str} old (last modified: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))})", file=sys.stderr)
        print("The file may be stale. Run kseal-decrypt.py first to get fresh secrets from the cluster.", file=sys.stderr)
        print("Sealing a stale file can overwrite values that were updated directly in sealed-secret.yaml.", file=sys.stderr)
        try:
            answer = input("Continue anyway? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "y":
            print("Aborted. Run kseal-decrypt.py first.", file=sys.stderr)
            sys.exit(1)


def read_secrets_file(app_path):
    """Read and validate the plaintext secrets file."""
    secrets_path = os.path.join(app_path, "secrets")
    if not os.path.isfile(secrets_path):
        print(f"ERROR: No secrets file found at {secrets_path}", file=sys.stderr)
        print("Run kseal-decrypt.py first to fetch current secrets from cluster.", file=sys.stderr)
        sys.exit(1)

    check_secrets_freshness(secrets_path)

    with open(secrets_path) as f:
        content = f.read()

    # Basic validation
    try:
        doc = yaml.safe_load(content)
    except yaml.YAMLError as e:
        print(f"ERROR: secrets file is not valid YAML:\n{e}", file=sys.stderr)
        sys.exit(1)

    if not doc or doc.get("kind") != "Secret":
        print("ERROR: secrets file must be a Kubernetes Secret manifest (kind: Secret)", file=sys.stderr)
        sys.exit(1)

    string_data = doc.get("stringData", {})
    if not string_data:
        print("ERROR: secrets file has no stringData entries", file=sys.stderr)
        sys.exit(1)

    name = doc.get("metadata", {}).get("name", "unknown")
    namespace = doc.get("metadata", {}).get("namespace", "unknown")
    return content, name, namespace, sorted(string_data.keys())


def seal(secrets_content, context):
    """Run kubeseal to seal the secrets."""
    cmd = [
        "kubeseal",
        "--controller-name", CONTROLLER_NAME,
        "--controller-namespace", CONTROLLER_NS,
        "--context", context,
        "--format", "yaml",
    ]
    result = subprocess.run(cmd, input=secrets_content, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: kubeseal failed:\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def validate(sealed_content, context):
    """Validate the sealed secret."""
    cmd = [
        "kubeseal", "--validate",
        "--controller-name", CONTROLLER_NAME,
        "--controller-namespace", CONTROLLER_NS,
        "--context", context,
    ]
    result = subprocess.run(cmd, input=sealed_content, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: validation failed:\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def diff_keys(app_path, new_keys):
    """Compare new keys against existing sealed-secret.yaml keys."""
    sealed_path = os.path.join(app_path, "sealed-secret.yaml")
    if not os.path.isfile(sealed_path):
        return None, None, None

    with open(sealed_path) as f:
        doc = yaml.safe_load(f)

    old_keys = set(doc.get("spec", {}).get("encryptedData", {}).keys())
    new_set = set(new_keys)
    added = sorted(new_set - old_keys)
    removed = sorted(old_keys - new_set)
    return old_keys, added, removed


def main():
    parser = argparse.ArgumentParser(description="Seal plaintext secrets into sealed-secret.yaml")
    parser.add_argument("path", help="Gitops app path (absolute or relative to gitops root)")
    parser.add_argument("--context", default=DEFAULT_CONTEXT, choices=["stg-app", "prd-app"],
                        help=f"Kubernetes context (default: {DEFAULT_CONTEXT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Seal and validate but don't write the file")
    args = parser.parse_args()

    app_path = resolve_app_path(args.path)

    # Read and validate secrets
    secrets_content, name, namespace, keys = read_secrets_file(app_path)
    print(f"Secret: {name} (namespace: {namespace}, context: {args.context})")
    print(f"Keys ({len(keys)}): {', '.join(keys)}")

    # Show key diff
    old_keys, added, removed = diff_keys(app_path, keys)
    if old_keys is not None:
        if added:
            print(f"  + Added: {', '.join(added)}")
        if removed:
            print(f"  - Removed: {', '.join(removed)}")
        if not added and not removed:
            print("  (same keys, values updated)")

    # Seal
    print("Sealing...", end=" ", flush=True)
    sealed_content = seal(secrets_content, args.context)
    print("OK")

    # Validate
    print("Validating...", end=" ", flush=True)
    validate(sealed_content, args.context)
    print("OK")

    if args.dry_run:
        print(f"\nDry run — would write to: {os.path.join(app_path, 'sealed-secret.yaml')}")
    else:
        output_path = os.path.join(app_path, "sealed-secret.yaml")
        with open(output_path, "w") as f:
            f.write(sealed_content)
        print(f"Wrote sealed-secret.yaml to {output_path}")



if __name__ == "__main__":
    main()
