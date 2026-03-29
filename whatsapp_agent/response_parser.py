"""
response_parser.py
------------------
Parses vendor WhatsApp replies using NVIDIA NIM (Llama 3.3 70B).

The core challenge:
    Vendors reply in freeform text — broken English, Hindi, mixed formats,
    voice note transcriptions, abbreviations. Rule-based parsers fail here.
    LLMs handle this naturally.

Extracts from each reply:
    - price_per_unit    (float)
    - available_qty     (float)
    - lead_time_days    (int)
    - currency          (str)
    - unit              (str)
    - confidence        (high/medium/low)
    - raw_reply         (original text)
    - notes             (anything else vendor mentioned)
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")


# ─────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────

def parse_vendor_reply(
    reply_text: str,
    material: str,
    unit: str,
    vendor_name: str,
) -> dict:
    """
    Uses Llama 3.3 70B to extract structured data from a freeform
    vendor WhatsApp reply.

    Args:
        reply_text:  Raw WhatsApp message from vendor
        material:    Material being quoted (e.g. "diesel")
        unit:        Unit of measurement (e.g. "liters")
        vendor_name: Vendor name for context

    Returns:
        Structured dict with extracted procurement data
    """

    prompt = f"""You are extracting procurement data from a vendor's WhatsApp reply.
The vendor was asked to quote for {material} (unit: {unit}).

Vendor: {vendor_name}
Their reply: "{reply_text}"

Extract the following and respond ONLY with a valid JSON object, nothing else:
{{
  "price_per_unit": <number or null if not mentioned>,
  "available_qty": <number or null if not mentioned>,
  "lead_time_days": <integer number of days or null if not mentioned>,
  "currency": "<INR or USD, default INR>",
  "unit": "<unit mentioned or default to {unit}>",
  "confidence": "<high if all 3 fields found, medium if 2 found, low if 1 or fewer>",
  "can_fulfill": <true if vendor seems able to supply, false if they decline>,
  "notes": "<any other important info like conditions, minimums, payment terms>"
}}

Rules:
- If price mentions "per liter", "per kg", "/L", "/kg" etc, extract just the number
- For lead time: "kal" or "tomorrow" = 1, "2 din" = 2, "next week" = 7
- If reply is just a phone number or "call me", set can_fulfill to true but all fields null
- Currency is INR by default for Indian vendors
- Respond with ONLY the JSON object, no explanation, no markdown"""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,    # Low temperature for consistent extraction
            top_p=0.7,
            max_tokens=300,
            stream=True,
        )

        full_response = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content

        # Clean and parse JSON
        clean = full_response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        parsed = json.loads(clean)
        parsed["raw_reply"]   = reply_text
        parsed["vendor_name"] = vendor_name
        parsed["material"]    = material
        parsed["parse_error"] = False
        return parsed

    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse failed for {vendor_name}: {e}")
        return _fallback_parse(reply_text, vendor_name, material, unit)

    except Exception as e:
        print(f"  [WARN] LLM parse failed for {vendor_name}: {type(e).__name__}: {e}")
        return _fallback_parse(reply_text, vendor_name, material, unit)


def _fallback_parse(
    reply_text: str,
    vendor_name: str,
    material: str,
    unit: str,
) -> dict:
    """
    Fallback parser when LLM fails.
    Does basic number extraction — better than nothing.
    """
    import re

    # Try to find any numbers in the reply
    numbers = re.findall(r'\d+(?:\.\d+)?', reply_text)

    return {
        "price_per_unit": float(numbers[0]) if len(numbers) > 0 else None,
        "available_qty":  float(numbers[1]) if len(numbers) > 1 else None,
        "lead_time_days": int(float(numbers[2])) if len(numbers) > 2 else None,
        "currency":       "INR",
        "unit":           unit,
        "confidence":     "low",
        "can_fulfill":    True,
        "notes":          "Parsed with fallback — LLM unavailable",
        "raw_reply":      reply_text,
        "vendor_name":    vendor_name,
        "material":       material,
        "parse_error":    True,
    }


def parse_all_vendor_replies(vendor_replies: list[dict]) -> list[dict]:
    """
    Parses replies from multiple vendors.

    Args:
        vendor_replies: List of dicts with keys:
            - vendor_name, material, unit, reply_text

    Returns:
        List of parsed response dicts sorted by price ascending
    """
    print(f"\n[RESPONSE PARSER] Parsing {len(vendor_replies)} vendor replies...\n")

    parsed_responses = []
    for reply in vendor_replies:
        print(f"  → Parsing reply from {reply['vendor_name']}...")

        result = parse_vendor_reply(
            reply_text=reply["reply_text"],
            material=reply["material"],
            unit=reply["unit"],
            vendor_name=reply["vendor_name"],
        )
        parsed_responses.append(result)

        # Print what was extracted
        price = f"₹{result['price_per_unit']}/{result['unit']}" if result["price_per_unit"] else "price unknown"
        qty   = f"{result['available_qty']} {result['unit']}" if result["available_qty"] else "qty unknown"
        lead  = f"{result['lead_time_days']}d" if result["lead_time_days"] else "lead unknown"
        print(f"    {price} | {qty} | {lead} | confidence: {result['confidence']}")

    # Sort by price ascending (cheapest first), nulls last
    parsed_responses.sort(
        key=lambda x: (x["price_per_unit"] is None, x["price_per_unit"] or 0)
    )

    return parsed_responses


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate realistic Indian vendor WhatsApp replies
    test_replies = [
        {
            "vendor_name": "Sharma Fuels Pvt Ltd",
            "material":    "diesel",
            "unit":        "liters",
            "reply_text":  "haan bhai available hai, 180 per litre, 8000 litre stock mein hai, kal tak de sakte hain ludhiana se",
        },
        {
            "vendor_name": "Punjab Petroleum Suppliers",
            "material":    "diesel",
            "unit":        "liters",
            "reply_text":  "Price: Rs 175/L | Available: 10000L | Delivery: 2 days from Jalandhar",
        },
        {
            "vendor_name": "Gupta Energy Solutions",
            "material":    "diesel",
            "unit":        "liters",
            "reply_text":  "we can supply 7500 liters at 185 rupees per liter, delivery will take 3-4 days, minimum order 5000L",
        },
        {
            "vendor_name": "Singh Traders",
            "material":    "diesel",
            "unit":        "liters",
            "reply_text":  "call me - 9876543210",
        },
    ]

    print(f"Model: {MODEL}")
    print(f"Testing response parser with {len(test_replies)} mock vendor replies...\n")

    results = parse_all_vendor_replies(test_replies)

    print(f"\n{'═'*60}")
    print(f"  PARSED RESULTS — Ranked by Price")
    print(f"{'═'*60}")

    for i, r in enumerate(results, 1):
        price = f"₹{r['price_per_unit']}/{r['unit']}" if r["price_per_unit"] else "Price not shared"
        qty   = f"{r['available_qty']} {r['unit']}" if r["available_qty"] else "Qty unknown"
        lead  = f"{r['lead_time_days']} days" if r["lead_time_days"] else "Lead time unknown"

        print(f"\n[{i}] {r['vendor_name']}")
        print(f"    Price      : {price}")
        print(f"    Available  : {qty}")
        print(f"    Lead Time  : {lead}")
        print(f"    Confidence : {r['confidence']}")
        if r.get("notes"):
            print(f"    Notes      : {r['notes']}")
        print(f"    Raw reply  : {r['raw_reply'][:60]}...")