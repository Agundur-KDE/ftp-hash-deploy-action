#!/usr/bin/env python3
"""
ftp-hash-deploy — deploy only changed files via FTP/FTPS using server-side Git-style hashing.
https://github.com/Agundur-KDE/ftp-hash-deploy-action
"""

import ftplib
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

# ── Config from environment ────────────────────────────────────────────────────

FTP_HOST     = os.environ["FTP_HOST"]
FTP_USER     = os.environ["FTP_USER"]
FTP_PASSWORD = os.environ["FTP_PASSWORD"]
FTP_PORT     = int(os.environ.get("FTP_PORT", "21"))
FTP_TLS      = os.environ.get("FTP_TLS", "true").lower() == "true"
LOCAL_DIR    = Path(os.environ.get("LOCAL_DIR", "./")).resolve()
SERVER_DIR   = os.environ.get("SERVER_DIR", "/").rstrip("/") + "/"
SITE_URL     = os.environ["SITE_URL"].rstrip("/")
DRY_RUN      = os.environ.get("DRY_RUN", "false").lower() == "true"
ACTION_PATH  = Path(os.environ["ACTION_PATH"])

HASHME_NAME  = "hashme_fhd.php"
HASHME_PATH  = ACTION_PATH / "hashme.php"

# ── Git-style blob hash ────────────────────────────────────────────────────────

def git_hash(content: bytes) -> str:
    """SHA1 of 'blob {len}\0{content}' — identical to Git's blob object hash."""
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()

# ── Local hashes ──────────────────────────────────────────────────────────────

def local_hashes() -> dict[str, str]:
    hashes = {}
    for path in LOCAL_DIR.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(LOCAL_DIR).as_posix()
        content = path.read_bytes().replace(b"\r\n", b"\n")
        hashes[rel] = git_hash(content)
    return hashes

# ── FTP connection ─────────────────────────────────────────────────────────────

def connect() -> ftplib.FTP:
    if FTP_TLS:
        ftp = ftplib.FTP_TLS()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
        ftp.login(FTP_USER, FTP_PASSWORD)
        ftp.prot_p()  # encrypted data channel
    else:
        ftp = ftplib.FTP()
        ftp.connect(FTP_HOST, FTP_PORT, timeout=30)
        ftp.login(FTP_USER, FTP_PASSWORD)
    return ftp

def ftp_upload(ftp: ftplib.FTP, remote_path: str, local_path: Path) -> None:
    parts = remote_path.strip("/").split("/")
    # ensure directories exist
    cur = SERVER_DIR.rstrip("/")
    for part in parts[:-1]:
        cur += "/" + part
        try:
            ftp.mkd(cur)
        except ftplib.error_perm:
            pass  # already exists
    with open(local_path, "rb") as f:
        ftp.storbinary(f"STOR {SERVER_DIR}{remote_path}", f)

def ftp_delete(ftp: ftplib.FTP, remote_path: str) -> None:
    try:
        ftp.delete(f"{SERVER_DIR}{remote_path}")
    except ftplib.error_perm:
        pass

# ── Server hashes via hashme.php ──────────────────────────────────────────────

def fetch_server_hashes(ftp: ftplib.FTP) -> dict[str, str]:
    # upload hashme.php
    with open(HASHME_PATH, "rb") as f:
        ftp.storbinary(f"STOR {SERVER_DIR}{HASHME_NAME}", f)

    # fetch hashes via HTTP
    url = f"{SITE_URL}/{HASHME_NAME}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        ftp.delete(f"{SERVER_DIR}{HASHME_NAME}")
        raise RuntimeError(f"Failed to fetch server hashes from {url}: {e}")

    # delete hashme.php
    try:
        ftp.delete(f"{SERVER_DIR}{HASHME_NAME}")
    except ftplib.error_perm:
        pass

    return data

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"{'🔍 DRY RUN — ' if DRY_RUN else ''}Connecting to {FTP_HOST}:{FTP_PORT} ({'FTPS' if FTP_TLS else 'FTP'})")

    ftp = connect()
    print("✓ Connected")

    print("⟳ Fetching server hashes via hashme.php ...")
    server = fetch_server_hashes(ftp)
    print(f"  {len(server)} files on server")

    print("⟳ Computing local hashes ...")
    local  = local_hashes()
    print(f"  {len(local)} local files")

    to_upload = [f for f, h in local.items()  if server.get(f) != h]
    to_delete = [f for f     in server         if f not in local]
    new_files  = [f for f in to_upload if f not in server]
    updated    = [f for f in to_upload if f in server]

    print()
    if new_files:
        print(f"🟡 New ({len(new_files)}):")
        for f in new_files: print(f"   + {f}")
    if updated:
        print(f"🟢 Update ({len(updated)}):")
        for f in updated: print(f"   ↑ {f}")
    if to_delete:
        print(f"🔴 Delete ({len(to_delete)}):")
        for f in to_delete: print(f"   - {f}")
    if not to_upload and not to_delete:
        print("✓ Server is up to date — nothing to deploy.")
        ftp.quit()
        return

    if DRY_RUN:
        print("\nDry run — nothing uploaded.")
        ftp.quit()
        return

    for f in to_upload:
        ftp_upload(ftp, f, LOCAL_DIR / f)
        print(f"  ✓ {f}")
    for f in to_delete:
        ftp_delete(ftp, f)
        print(f"  ✗ {f}")

    ftp.quit()
    print(f"\n✓ Deploy complete — {len(to_upload)} uploaded, {len(to_delete)} deleted.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"::error::{e}")
        sys.exit(1)
