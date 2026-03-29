"""
inventory_manager.py
--------------------
Loads and manages manufacturer's raw material inventory.
Reads from a CSV file (can be swapped for Google Sheets later).

CSV Format expected:
    material, current_stock_days, minimum_safe_days,
    supplier_state, unit, monthly_usage
"""

import os
import csv
from dotenv import load_dotenv

load_dotenv()

INVENTORY_FILE = os.getenv("INVENTORY_FILE", "inventory/sample_inventory.csv")


# ─────────────────────────────────────────────
# LOADER
# ─────────────────────────────────────────────

def load_inventory() -> list[dict]:
    """
    Loads inventory from CSV file.
    Returns list of material dicts with typed values.
    """
    if not os.path.exists(INVENTORY_FILE):
        raise FileNotFoundError(
            f"Inventory file not found at '{INVENTORY_FILE}'.\n"
            f"Make sure sample_inventory.csv exists in the inventory/ folder."
        )

    inventory = []
    try:
        with open(INVENTORY_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                inventory.append({
                    "material":            row["material"].strip().lower(),
                    "current_stock_days":  int(row["current_stock_days"]),
                    "minimum_safe_days":   int(row["minimum_safe_days"]),
                    "supplier_state":      row["supplier_state"].strip(),
                    "unit":                row["unit"].strip(),
                    "monthly_usage":       float(row["monthly_usage"]),
                })
    except (KeyError, ValueError) as e:
        raise ValueError(f"Inventory CSV format error: {e}")

    print(f"  [INVENTORY] Loaded {len(inventory)} materials from {INVENTORY_FILE}")
    return inventory


def get_material(inventory: list[dict], material_name: str) -> dict | None:
    """Finds a specific material by name. Returns None if not found."""
    material_name = material_name.strip().lower()
    for item in inventory:
        if item["material"] == material_name:
            return item
    return None


def get_low_stock_materials(inventory: list[dict]) -> list[dict]:
    """
    Returns all materials currently below their minimum safe days.
    These are already at risk even before a disruption.
    """
    return [
        item for item in inventory
        if item["current_stock_days"] < item["minimum_safe_days"]
    ]


def print_inventory_summary(inventory: list[dict]):
    """Pretty prints the full inventory status."""
    print(f"\n{'─'*60}")
    print(f"  INVENTORY STATUS")
    print(f"{'─'*60}")
    print(f"  {'Material':<15} {'Stock Days':>10} {'Safe Days':>10} {'Status':>10}")
    print(f"  {'─'*50}")

    for item in sorted(inventory, key=lambda x: x["current_stock_days"]):
        status = "⚠️  LOW" if item["current_stock_days"] < item["minimum_safe_days"] else "✅ OK"
        print(
            f"  {item['material'].capitalize():<15} "
            f"{item['current_stock_days']:>10} "
            f"{item['minimum_safe_days']:>10} "
            f"{status:>10}"
        )


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    inventory = load_inventory()
    print_inventory_summary(inventory)

    low = get_low_stock_materials(inventory)
    if low:
        print(f"\n⚠️  {len(low)} materials already below safe levels:")
        for item in low:
            print(f"   - {item['material']} ({item['current_stock_days']} days vs {item['minimum_safe_days']} days safe)")
    else:
        print("\n✅ All materials above minimum safe levels.")