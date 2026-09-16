"""Ensure a portable Blender 4.5 binary is available for craft runs.

Prefer an existing ``BLENDER_PATH`` / ``BLENDER_EXE`` / ``find_blender()`` hit.
Otherwise download the official linux-x64 (or windows-x64) portable build into
``tools/`` and return the binary path.

Usage:
  python -m mvm.blender.ensure
  python -m mvm.blender.ensure --print-only
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from mvm.blender.runner import find_blender

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"

BLENDER_VERSION = "4.5.10"
BLENDER_SERIES = "4.5"
USER_AGENT = "Mozilla/5.0 (compatible; MVM-craft/1.0; +https://github.com/levizigza/Animation-MV-)"

# Official release archives from download.blender.org
_ARCHIVES = {
    "linux-x64": {
        "name": f"blender-{BLENDER_VERSION}-linux-x64",
        "url": (
            f"https://download.blender.org/release/Blender{BLENDER_SERIES}/"
            f"blender-{BLENDER_VERSION}-linux-x64.tar.xz"
        ),
        "binary_rel": "blender",
        "archive_kind": "tar.xz",
    },
    "windows-x64": {
        "name": f"blender-{BLENDER_VERSION}-windows-x64",
        "url": (
            f"https://download.blender.org/release/Blender{BLENDER_SERIES}/"
            f"blender-{BLENDER_VERSION}-windows-x64.zip"
        ),
        "binary_rel": "blender.exe",
        "archive_kind": "zip",
    },
}


def _platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "linux" and machine in ("x86_64", "amd64"):
        return "linux-x64"
    if system == "windows" and machine in ("x86_64", "amd64", "amd64"):
        return "windows-x64"
    raise RuntimeError(
        f"Unsupported platform for portable Blender ensure: {system}/{machine}"
    )


def _existing() -> Path | None:
    env = os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_EXE")
    if env and Path(env).is_file():
        return Path(env).resolve()
    found = find_blender()
    if found and found.is_file():
        return found.resolve()
    return None


def _extract(archive: Path, dest_parent: Path, kind: str) -> Path:
    dest_parent.mkdir(parents=True, exist_ok=True)
    if kind == "tar.xz":
        with tarfile.open(archive, "r:xz") as tf:
            tf.extractall(dest_parent)
            names = tf.getnames()
        top = names[0].split("/")[0] if names else ""
        return dest_parent / top
    if kind == "zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest_parent)
            names = zf.namelist()
        top = names[0].split("/")[0] if names else ""
        return dest_parent / top
    raise ValueError(f"Unknown archive kind: {kind}")


def _download(url: str, dest: Path) -> None:
    """Download with a browser-like User-Agent (Cloudflare blocks bare urllib)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=600) as resp, dest.open("wb") as out:
            shutil.copyfileobj(resp, out)
        return
    except urllib.error.HTTPError as exc:
        # Fall back to curl if present — more reliable on restricted egress.
        curl = shutil.which("curl")
        if curl is None:
            raise
        print(f"[ensure] urllib failed ({exc}); retrying with curl", flush=True)
    proc = subprocess.run(
        [
            "curl",
            "-fL",
            "--retry",
            "3",
            "--retry-delay",
            "2",
            "-A",
            USER_AGENT,
            "-o",
            str(dest),
            url,
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not dest.is_file():
        raise RuntimeError(
            f"Download failed for {url}: {(proc.stderr or proc.stdout or '')[-500:]}"
        )


def ensure_blender(*, force_download: bool = False) -> Path:
    """Return a usable Blender binary, downloading into tools/ if needed."""
    if not force_download:
        hit = _existing()
        if hit is not None:
            return hit

    key = _platform_key()
    spec = _ARCHIVES[key]
    install_dir = TOOLS / spec["name"]
    binary = install_dir / spec["binary_rel"]
    if binary.is_file() and not force_download:
        return binary.resolve()

    TOOLS.mkdir(parents=True, exist_ok=True)
    print(f"[ensure] downloading {spec['url']}", flush=True)
    with tempfile.TemporaryDirectory(prefix="mvm-blender-") as tmp:
        tmp_path = Path(tmp)
        archive_name = Path(spec["url"]).name
        archive_path = tmp_path / archive_name
        _download(spec["url"], archive_path)
        size = archive_path.stat().st_size
        if size < 10_000_000:
            raise RuntimeError(f"Download too small ({size} bytes): {archive_path}")
        print(f"[ensure] archive size={size}", flush=True)
        if install_dir.exists():
            shutil.rmtree(install_dir)
        extracted = _extract(archive_path, TOOLS, spec["archive_kind"])
        if extracted.resolve() != install_dir.resolve():
            if install_dir.exists():
                shutil.rmtree(install_dir)
            extracted.rename(install_dir)

    if not binary.is_file():
        raise FileNotFoundError(f"Blender binary missing after extract: {binary}")
    binary.chmod(binary.stat().st_mode | 0o111)
    print(f"[ensure] blender={binary}", flush=True)
    return binary.resolve()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ensure portable Blender 4.5 is available")
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download even if a Blender binary is already discoverable",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the resolved path only (no extra notes)",
    )
    args = parser.parse_args(argv)
    try:
        path = ensure_blender(force_download=args.force_download)
    except Exception as exc:  # noqa: BLE001 — CLI surface
        print(f"[ensure] FAILED: {exc}", file=sys.stderr)
        return 1
    os.environ["BLENDER_PATH"] = str(path)
    if args.print_only:
        print(path)
    else:
        print(f"BLENDER_PATH={path}")
        print("ENSURE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
