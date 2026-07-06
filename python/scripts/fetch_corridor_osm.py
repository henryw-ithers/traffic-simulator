"""Fetch the v0.1 corridor OSM extract into ``/data/osm/`` (gitignored).

Corridor (README v0.1 scope): Dufferin & Bloor -> Bathurst & Bloor -> St Clair
corridor -> Eglinton Ave W -> Allen Rd (north to Hwy 401). Fetched as a
bounding box covering that route, drive network only.

Downloads:
- ``corridor.graphml``     — osmnx drive graph with lane/turn/speed way tags
- ``corridor_edges.gpkg``  — edge geodataframe for inspection in GIS tools
- ``turn_restrictions.json`` — raw ``type=restriction`` relations from
  Overpass (osmnx graphs do not retain restriction relations)

Usage (venv with the ``data`` extra installed):
    python python/scripts/fetch_corridor_osm.py [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import osmnx as ox
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
OSM_DIR = REPO_ROOT / "data" / "osm"

# (west, south, east, north) — covers Bloor (south) to Hwy 401 (north),
# west of Dufferin/Allen to east of Bathurst.
BBOX = (-79.475, 43.650, -79.395, 43.745)

# Way tags the lane-level network model (ADR-0002) will depend on.
USEFUL_TAGS_WAY = [
    "highway",
    "name",
    "ref",
    "oneway",
    "lanes",
    "lanes:forward",
    "lanes:backward",
    "turn:lanes",
    "turn:lanes:forward",
    "turn:lanes:backward",
    "maxspeed",
    "junction",
    "access",
    "bus:lanes",
    "railway",
]

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def fetch_graph(force: bool) -> None:
    graphml_path = OSM_DIR / "corridor.graphml"
    edges_path = OSM_DIR / "corridor_edges.gpkg"
    if graphml_path.exists() and not force:
        print(f"exists, skipping (use --force to refetch): {graphml_path}")
        return

    ox.settings.useful_tags_way = USEFUL_TAGS_WAY
    # Keep osmnx's HTTP cache inside gitignored /data, not the CWD.
    ox.settings.cache_folder = OSM_DIR / "cache"
    print(f"fetching drive network for bbox {BBOX} ...")
    graph = ox.graph_from_bbox(BBOX, network_type="drive", simplify=True)
    ox.save_graphml(graph, graphml_path)
    print(f"wrote {graphml_path}")

    _, edges = ox.convert.graph_to_gdfs(graph)
    edges.to_file(edges_path, driver="GPKG")
    print(f"wrote {edges_path}")


def fetch_turn_restrictions(force: bool) -> None:
    out_path = OSM_DIR / "turn_restrictions.json"
    if out_path.exists() and not force:
        print(f"exists, skipping (use --force to refetch): {out_path}")
        return

    west, south, east, north = BBOX
    query = (
        f"[out:json][timeout:120];"
        f'relation["type"="restriction"]({south},{west},{north},{east});'
        f"out body;"
    )
    print("fetching turn-restriction relations from Overpass ...")
    # Overpass rejects requests without an identifying User-Agent (HTTP 406).
    headers = {"User-Agent": "toronto-traffic-simulator-recon/0.1"}
    response = requests.post(
        OVERPASS_URL, data={"data": query}, headers=headers, timeout=180
    )
    response.raise_for_status()
    out_path.write_text(json.dumps(response.json(), indent=1), encoding="utf-8")
    print(f"wrote {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="refetch even if cached")
    args = parser.parse_args()

    OSM_DIR.mkdir(parents=True, exist_ok=True)
    fetch_graph(args.force)
    fetch_turn_restrictions(args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
