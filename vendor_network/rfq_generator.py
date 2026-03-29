"""
rfq_generator.py
----------------
Uses NVIDIA NIM API (Llama 3.3 70B) to generate professional RFQ
messages tailored to each vendor and disruption context.
"""

import os
from datetime import datetime, timedelta, UTC
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# NVIDIA NIM CLIENT
# ─────────────────────────────────────────────

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY"),
)

MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")


def generate_rfq(
    vendor: dict,
    material: dict,
    disruption_headline: str,
    owner_name: str = "Procurement Team",
    company_name: str = "our manufacturing unit",
) -> str:
    """
    Uses NVIDIA NIM to generate a WhatsApp RFQ message via streaming.
    """
    monthly_usage   = material.get("monthly_usage", 100)
    needed_quantity = round(monthly_usage * 1.5)
    unit            = material.get("unit", "units")
    material_name   = material.get("material", "material").capitalize()
    needed_by       = (datetime.now(UTC) + timedelta(days=5)).strftime("%d %B %Y")

    prompt = f"""You are drafting a WhatsApp message from a manufacturer to a backup supplier.
The manufacturer urgently needs raw materials due to a supply chain disruption.

Context:
- Sender: {owner_name} from {company_name}
- Recipient: {vendor['contact']} at {vendor['name']}
- Material needed: {material_name}
- Quantity: {needed_quantity} {unit}
- Needed by: {needed_by}
- Disruption reason: {disruption_headline}
- Vendor lead time: {vendor['typical_lead_days']} days
- Vendor location: {vendor['location']}

Write a WhatsApp message that:
1. Is professional but conversational (WhatsApp tone, not email)
2. States what is needed, how much, and by when
3. Briefly explains the supply disruption without being alarmist
4. Asks for price per unit, available quantity, and earliest delivery
5. Is under 120 words
6. Ends with sender name and a clear call to action

Plain text only. No markdown. No asterisks. No bullet points.
Write only the message itself, nothing else."""

    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            top_p=0.7,
            max_tokens=300,
            stream=True,       # NVIDIA NIM works best with streaming
        )

        # Collect streamed chunks into full response
        full_response = ""
        for chunk in completion:
            if chunk.choices and chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content

        return full_response.strip()

    except Exception as e:
        print(f"  [WARN] NVIDIA NIM API failed: {type(e).__name__}: {e}")
        # Fallback template
        return (
            f"Hi {vendor['contact']},\n\n"
            f"This is {owner_name} from {company_name}. "
            f"We urgently need {needed_quantity} {unit} of {material_name} "
            f"by {needed_by} due to a disruption with our primary supplier.\n\n"
            f"Could you share your best price per {unit}, "
            f"available quantity, and earliest delivery date?\n\n"
            f"Thank you,\n{owner_name}"
        )


def generate_rfqs_for_material(
    vendors: list[dict],
    material: dict,
    disruption_headline: str,
) -> list[dict]:
    """Generates RFQ messages for all vendors of an at-risk material."""
    material_name = material.get("material", "material").capitalize()
    print(f"\n  [RFQ GENERATOR] Drafting messages for {material_name}...")

    rfqs = []
    for vendor in vendors:
        print(f"    -> Drafting for {vendor['name']}...")
        message = generate_rfq(
            vendor=vendor,
            material=material,
            disruption_headline=disruption_headline,
        )
        rfqs.append({
            **vendor,
            "material": material.get("material"),
            "message":  message,
            "status":   "pending",
        })

    return rfqs


# ─────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────

if __name__ == "__main__":
    mock_vendor = {
        "name":              "Sharma Fuels Pvt Ltd",
        "contact":           "Rajesh Sharma",
        "whatsapp":          "+919876543210",
        "location":          "Ludhiana, Punjab",
        "reliability_score": 4.5,
        "typical_lead_days": 2,
    }

    mock_material = {
        "material":           "diesel",
        "current_stock_days": 15,
        "minimum_safe_days":  30,
        "unit":               "liters",
        "monthly_usage":      5000,
    }

    disruption = "Fuel shortage hits India as Iran war disrupts crude oil imports"

    print(f"Model : {MODEL}")
    print(f"Generating RFQ via NVIDIA NIM (streaming)...\n")

    message = generate_rfq(mock_vendor, mock_material, disruption)

    print("─" * 55)
    print(message)
    print("─" * 55)