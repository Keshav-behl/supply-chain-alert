"""
vendor_registry.py
------------------
Manages the database of backup vendors per material.
Loads from sample_vendors.json and provides lookup functions.
"""

import os
import json

VENDORS_FILE = os.getenv("VENDORS_FILE", "vendor_network/sample_vendors.json")


def load_vendor_registry() -> dict:
    """Loads vendor registry from JSON file."""
    if not os.path.exists(VENDORS_FILE):
        raise FileNotFoundError(
            f"Vendor registry not found at '{VENDORS_FILE}'.\n"
            f"Make sure sample_vendors.json exists in vendor_network/ folder."
        )
    with open(VENDORS_FILE, "r") as f:
        return json.load(f)


def get_vendors_for_material(registry: dict, material: str) -> list[dict]:
    """
    Returns list of vendors for a given material.
    Sorted by reliability score descending.
    """
    material = material.strip().lower()
    vendors = registry.get(material, [])
    return sorted(vendors, key=lambda x: x["reliability_score"], reverse=True)


def get_top_vendors(registry: dict, material: str, top_n: int = 3) -> list[dict]:
    """Returns top N vendors for a material by reliability score."""
    return get_vendors_for_material(registry, material)[:top_n]


def print_vendors(vendors: list[dict], material: str):
    """Pretty prints vendor list for a material."""
    print(f"\n  Vendors for {material.capitalize()}:")
    for i, v in enumerate(vendors, 1):
        print(f"    [{i}] {v['name']} — ⭐ {v['reliability_score']} | {v['typical_lead_days']}d lead | {v['location']}")


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    registry = load_vendor_registry()
    print(f"Loaded vendors for {len(registry)} materials\n")
    for material in registry:
        vendors = get_top_vendors(registry, material)
        print_vendors(vendors, material)