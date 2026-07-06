"""Fetch City of Toronto Open Data needed for corridor reconnaissance.

Downloads into ``/data/open/`` (gitignored):

- ``traffic_signals.csv``          — all ~2,550 signals with SIGNALSYSTEM and
  CONTROL_MODE per intersection (datastore dump)
- ``traffic_signal_readme.xlsx``   — data dictionary (decodes CONTROL_MODE)
- ``tmc_most_recent_summary.csv``  — most recent turning movement count per
  intersection (datastore dump)
- ``bluetooth_routes_wgs84.zip``   — Bluetooth travel-time route geometries
  (2014-2017 program), to check corridor coverage

Sources are recorded with licenses in ``docs/data-sources.md``.

Usage (venv with the ``data`` extra installed):
    python python/scripts/fetch_toronto_open_data.py [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
OPEN_DIR = REPO_ROOT / "data" / "open"

CKAN_BASE = "https://ckan0.cf.opendata.inter.prod-toronto.ca"

# (destination filename, CKAN resource id, fetch mode)
# "dump" uses the datastore CSV dump endpoint; "file" downloads the resource's
# url field (resolved at runtime via resource_show, so filenames can change
# portal-side without breaking us).
RESOURCES = [
    ("traffic_signals.csv", "139e5357-0caf-4c9a-a6be-ce94d38bcfeb", "dump"),
    ("traffic_signal_readme.xlsx", "8098ddfa-ec61-4c23-afd7-76830be73e4e", "file"),
    ("tmc_most_recent_summary.csv", "6afa3b1f-f6a5-4235-8bd6-7568411c19f4", "dump"),
    ("bluetooth_routes_wgs84.zip", "f24bd6d6-5333-47ad-b20c-93167489550a", "file"),
]


def resource_url(resource_id: str, mode: str) -> str:
    if mode == "dump":
        return f"{CKAN_BASE}/datastore/dump/{resource_id}"
    response = requests.get(
        f"{CKAN_BASE}/api/3/action/resource_show",
        params={"id": resource_id},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["result"]["url"]


def fetch(dest_name: str, resource_id: str, mode: str, force: bool) -> None:
    dest = OPEN_DIR / dest_name
    if dest.exists() and not force:
        print(f"exists, skipping (use --force to refetch): {dest}")
        return
    url = resource_url(resource_id, mode)
    print(f"fetching {url} ...")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    dest.write_bytes(response.content)
    print(f"wrote {dest} ({len(response.content):,} bytes)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="refetch even if cached")
    args = parser.parse_args()

    OPEN_DIR.mkdir(parents=True, exist_ok=True)
    for dest_name, resource_id, mode in RESOURCES:
        fetch(dest_name, resource_id, mode, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
