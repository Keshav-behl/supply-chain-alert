"""
outbound_rfq.py
---------------
Sends RFQ messages to vendors via WhatsApp using Twilio.
Also sends a summary alert to the owner.

Twilio Sandbox Setup:
    1. Go to console.twilio.com
    2. Messaging → Try it out → Send a WhatsApp message
    3. Follow sandbox join instructions on your phone
    4. Add your Twilio credentials to .env
"""

import os
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio credentials from .env
TWILIO_SID      = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN    = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM     = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
OWNER_NUMBER    = os.getenv("ALERT_PHONE_NUMBER")


def get_twilio_client() -> Client:
    """Initializes and returns Twilio client."""
    if not TWILIO_SID or not TWILIO_TOKEN:
        raise EnvironmentError(
            "Twilio credentials missing. Add TWILIO_ACCOUNT_SID and "
            "TWILIO_AUTH_TOKEN to your .env file."
        )
    return Client(TWILIO_SID, TWILIO_TOKEN)


def format_whatsapp_number(number: str) -> str:
    """Ensures number is in whatsapp:+91XXXXXXXXXX format."""
    number = number.strip()
    if not number.startswith("whatsapp:"):
        number = f"whatsapp:{number}"
    return number


def send_whatsapp_message(to: str, message: str, dry_run: bool = False) -> bool:
    """
    Sends a single WhatsApp message via Twilio.

    Args:
        to:      Recipient WhatsApp number
        message: Message text
        dry_run: If True, prints message instead of sending (for testing)

    Returns:
        True if sent successfully, False otherwise
    """
    to_formatted = format_whatsapp_number(to)

    if dry_run:
        print(f"\n  [DRY RUN] Would send to {to_formatted}:")
        print(f"  {'─'*50}")
        print(f"  {message}")
        print(f"  {'─'*50}")
        return True

    try:
        client = get_twilio_client()
        msg = client.messages.create(
            from_=TWILIO_FROM,
            to=to_formatted,
            body=message,
        )
        print(f"  [SENT] {to_formatted} — SID: {msg.sid}")
        return True

    except Exception as e:
        print(f"  [ERROR] Failed to send to {to_formatted}: {e}")
        return False


def send_rfqs_to_vendors(rfqs: list[dict], dry_run: bool = True) -> list[dict]:
    """
    Sends RFQ messages to all vendors for at-risk materials.

    Args:
        rfqs:    List of RFQ dicts from rfq_generator
        dry_run: True = print only (default), False = actually send

    Returns:
        Updated RFQ list with send status
    """
    if dry_run:
        print(f"\n[WHATSAPP AGENT] DRY RUN MODE — messages will be printed, not sent")
        print(f"  Set dry_run=False to send real WhatsApp messages\n")
    else:
        print(f"\n[WHATSAPP AGENT] Sending RFQs to {len(rfqs)} vendors...\n")

    updated_rfqs = []
    for rfq in rfqs:
        success = send_whatsapp_message(
            to=rfq["whatsapp"],
            message=rfq["message"],
            dry_run=dry_run,
        )
        updated_rfqs.append({
            **rfq,
            "status": "sent" if success else "failed",
        })

    sent    = sum(1 for r in updated_rfqs if r["status"] == "sent")
    failed  = sum(1 for r in updated_rfqs if r["status"] == "failed")
    print(f"\n  Summary: {sent} sent, {failed} failed")

    return updated_rfqs


def send_owner_alert(
    at_risk_materials: list[dict],
    rfqs: list[dict],
    dry_run: bool = True,
):
    """
    Sends a summary alert to the owner on WhatsApp.
    Tells them what was detected and what action was taken.
    """
    if not OWNER_NUMBER:
        print("  [WARN] ALERT_PHONE_NUMBER not set in .env — skipping owner alert")
        return

    # Build summary message
    critical = [m for m in at_risk_materials if m["urgency"] == "CRITICAL"]
    high     = [m for m in at_risk_materials if m["urgency"] == "HIGH"]

    lines = ["🚨 Supply Chain Alert\n"]

    if critical:
        lines.append("CRITICAL:")
        for m in critical:
            lines.append(f"  - {m['material'].capitalize()} ({m['current_stock_days']}d stock)")

    if high:
        lines.append("\nHIGH RISK:")
        for m in high:
            lines.append(f"  - {m['material'].capitalize()} ({m['current_stock_days']}d stock)")

    lines.append(f"\nRFQs sent to {len(rfqs)} backup vendors.")
    lines.append("Replies expected within 6 hours.")
    lines.append("\nReply STOP to pause alerts.")

    message = "\n".join(lines)

    print(f"\n[OWNER ALERT] Notifying owner...")
    send_whatsapp_message(
        to=OWNER_NUMBER,
        message=message,
        dry_run=dry_run,
    )


def run_vendor_outreach(
    at_risk_materials: list[dict],
    rfqs: list[dict],
    dry_run: bool = True,
) -> list[dict]:
    """
    Main function. Sends all RFQs and owner alert.

    Args:
        at_risk_materials: From inventory threshold_checker
        rfqs:              From rfq_generator
        dry_run:           True = test mode (default)

    Returns:
        Updated RFQs with send status
    """
    if not rfqs:
        print("\n[VENDOR AGENT] No RFQs to send.")
        return []

    # Send RFQs to vendors
    updated_rfqs = send_rfqs_to_vendors(rfqs, dry_run=dry_run)

    # Send summary to owner
    send_owner_alert(at_risk_materials, updated_rfqs, dry_run=dry_run)

    return updated_rfqs