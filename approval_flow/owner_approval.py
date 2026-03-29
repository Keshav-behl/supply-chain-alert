"""
owner_approval.py
-----------------
Formats parsed vendor responses into a ranked comparison
and sends the owner a one-tap WhatsApp approval message.

The owner sees:
    "3 vendors responded for Diesel:
     1. Punjab Petroleum — ₹175/L, 10000L, 2 days ✅ BEST
     2. Sharma Fuels — ₹180/L, 8000L, 1 day
     3. Gupta Energy — ₹185/L, 7500L, 3 days

     Reply 1, 2, or 3 to confirm order.
     Reply SKIP to take no action."
"""

import os
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from whatsapp_agent.outbound_rfq import send_whatsapp_message
from dotenv import load_dotenv

load_dotenv()

OWNER_NUMBER = os.getenv("ALERT_PHONE_NUMBER")


def rank_vendor_responses(parsed_responses: list[dict]) -> list[dict]:
    """
    Ranks vendor responses using a composite score:
    - Price (lower is better) — 50% weight
    - Lead time (faster is better) — 30% weight
    - Confidence (higher is better) — 20% weight

    Returns responses sorted best to worst.
    """
    confidence_scores = {"high": 3, "medium": 2, "low": 1}

    def composite_score(r: dict) -> float:
        """Lower score = better vendor."""
        price_score = r["price_per_unit"] or 999
        lead_score  = (r["lead_time_days"] or 7) * 10
        conf_score  = (3 - confidence_scores.get(r["confidence"], 1)) * 5
        return (price_score * 0.5) + (lead_score * 0.3) + (conf_score * 0.2)

    # Only rank vendors who can fulfill
    fulfillable = [r for r in parsed_responses if r.get("can_fulfill", True)]
    fulfillable.sort(key=composite_score)
    return fulfillable


def format_approval_message(
    material: str,
    unit: str,
    ranked_responses: list[dict],
) -> str:
    """
    Formats a clean WhatsApp approval message for the owner.
    Designed to be readable on a phone screen.
    """
    if not ranked_responses:
        return (
            f"🚨 Supply Chain Alert\n\n"
            f"RFQs sent for {material.capitalize()} but no vendor responses yet.\n"
            f"Will update when replies come in."
        )

    lines = [f"📦 {material.capitalize()} — Vendor Quotes\n"]

    for i, r in enumerate(ranked_responses[:3], 1):
        best_tag = " ✅ BEST" if i == 1 else ""

        price = f"₹{r['price_per_unit']}/{unit}" if r["price_per_unit"] else "Price TBD"
        qty   = f"{r['available_qty']:,.0f}{unit[0]}" if r["available_qty"] else "Qty TBD"
        lead  = f"{r['lead_time_days']}d" if r["lead_time_days"] else "Lead TBD"

        lines.append(f"{i}. {r['vendor_name'][:25]}{best_tag}")
        lines.append(f"   {price} | {qty} | {lead}")

        if r.get("notes") and r["notes"] != "Parsed with fallback — LLM unavailable":
            lines.append(f"   📝 {r['notes'][:50]}")

        lines.append("")

    lines.append("Reply 1, 2, or 3 to confirm order.")
    lines.append("Reply SKIP to take no action.")

    return "\n".join(lines)


def send_approval_request(
    material: str,
    unit: str,
    parsed_responses: list[dict],
    dry_run: bool = True,
) -> dict:
    """
    Main function. Ranks vendor responses and sends owner
    a formatted approval request on WhatsApp.

    Args:
        material:         Material name
        unit:             Unit of measurement
        parsed_responses: From response_parser
        dry_run:          True = print only

    Returns:
        Dict with ranked responses and message sent
    """
    print(f"\n[APPROVAL FLOW] Preparing owner approval for {material.capitalize()}...")

    ranked    = rank_vendor_responses(parsed_responses)
    message   = format_approval_message(material, unit, ranked)

    print(f"\n  Ranked {len(ranked)} vendor responses")
    if ranked:
        best = ranked[0]
        price = f"₹{best['price_per_unit']}/{unit}" if best["price_per_unit"] else "TBD"
        print(f"  Best option: {best['vendor_name']} at {price}")

    # Send to owner
    if OWNER_NUMBER:
        send_whatsapp_message(
            to=OWNER_NUMBER,
            message=message,
            dry_run=dry_run,
        )
    else:
        print("  [WARN] ALERT_PHONE_NUMBER not set — printing message only")
        print(f"\n{'─'*50}")
        print(message)
        print(f"{'─'*50}")

    return {
        "ranked_responses": ranked,
        "message":          message,
        "best_vendor":      ranked[0] if ranked else None,
    }


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Mock parsed responses (as if response_parser already ran)
    mock_parsed = [
        {
            "vendor_name":    "Sharma Fuels Pvt Ltd",
            "price_per_unit": 180.0,
            "available_qty":  8000,
            "lead_time_days": 1,
            "confidence":     "high",
            "can_fulfill":    True,
            "notes":          "Cash payment preferred",
            "material":       "diesel",
        },
        {
            "vendor_name":    "Punjab Petroleum Suppliers",
            "price_per_unit": 175.0,
            "available_qty":  10000,
            "lead_time_days": 2,
            "confidence":     "high",
            "can_fulfill":    True,
            "notes":          None,
            "material":       "diesel",
        },
        {
            "vendor_name":    "Gupta Energy Solutions",
            "price_per_unit": 185.0,
            "available_qty":  7500,
            "lead_time_days": 3,
            "confidence":     "medium",
            "can_fulfill":    True,
            "notes":          "Minimum order 5000L",
            "material":       "diesel",
        },
    ]

    result = send_approval_request(
        material="diesel",
        unit="liters",
        parsed_responses=mock_parsed,
        dry_run=True,
    )

    print(f"\n{'═'*55}")
    print(f"Best vendor: {result['best_vendor']['vendor_name']}")
    print(f"Price: ₹{result['best_vendor']['price_per_unit']}/liter")