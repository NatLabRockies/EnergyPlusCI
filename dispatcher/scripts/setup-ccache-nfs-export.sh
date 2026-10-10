#!/usr/bin/env bash
set -euo pipefail

CACHE_ROOT="${CACHE_ROOT:-/srv/energyplus-ccache}"
NFS_CLIENTS="${NFS_CLIENTS:-192.168.0.0/16}"
EXPORT_OPTIONS="${EXPORT_OPTIONS:-rw,sync,no_subtree_check,no_root_squash}"
EXPORTS_FILE="${EXPORTS_FILE:-/etc/exports.d/energyplus-ccache.exports}"

sudo apt-get update
sudo apt-get install -y nfs-kernel-server

sudo install -d -m 0777 "$CACHE_ROOT"
sudo install -d -m 0755 "$(dirname "$EXPORTS_FILE")"

export_line="${CACHE_ROOT} ${NFS_CLIENTS}(${EXPORT_OPTIONS})"
printf '%s\n' "$export_line" | sudo tee "$EXPORTS_FILE" >/dev/null

sudo exportfs -ra
sudo systemctl enable --now nfs-server
sudo exportfs -v
