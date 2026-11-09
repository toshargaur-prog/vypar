import datetime
from typing import List, Dict, Any
from app.database import db_session
from app.upi_generator import generate_upi_link, format_inr

def check_and_queue_followups() -> Dict[str, Any]:
    """
    Automated Follow-Up Engine:
    Scans real customer invoices for overdue payments, clinic checkups, and replenishment.
    Operates on user-entered data only.
    """
    queued_count = 0
    today = datetime.date.today()

    with db_session() as conn:
        cursor = conn.cursor()

        # Fetch active business profile
        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        biz = cursor.fetchone()

        biz_name = biz["name"] if biz else "My Business Store"
        upi_id = biz["upi_id"] if biz and biz["upi_id"] else "mybusiness@upi"

        # ----------------------------------------------------
        # 1. OVERDUE INVOICE PAYMENT REMINDERS
        # ----------------------------------------------------
        cursor.execute("""
        SELECT * FROM invoices 
        WHERE status IN ('UNPAID', 'OVERDUE') 
          AND balance_amount > 0 
          AND due_date <= ?;
        """, (str(today),))
        overdue_invoices = cursor.fetchall()

        for inv in overdue_invoices:
            cursor.execute("""
            SELECT id FROM followups 
            WHERE invoice_id = ? AND followup_type = 'PAYMENT_REMINDER' 
              AND DATE(created_at) = ?;
            """, (inv["id"], str(today)))
            
            if not cursor.fetchone():
                upi_pay_link = generate_upi_link(
                    upi_id=upi_id,
                    payee_name=biz_name,
                    amount=inv["balance_amount"],
                    transaction_note=f"Bill #{inv['invoice_no']}",
                    transaction_ref=inv["invoice_no"]
                )
                
                msg_body = (
                    f"Namaste {inv['customer_name']} ji! 🙏\n\n"
                    f"A gentle reminder from *{biz_name}*: Bill *#{inv['invoice_no']}* for *{format_inr(inv['balance_amount'])}* was due on {inv['due_date']}.\n\n"
                    f"You can pay instantly via UPI (GPay / PhonePe / Paytm):\n"
                    f"👉 {upi_pay_link}\n\n"
                    f"Thank you for your business!"
                )

                cursor.execute("""
                INSERT INTO followups (customer_id, customer_name, phone, invoice_id, followup_type, scheduled_at, status, message_text)
                VALUES (?, ?, ?, ?, 'PAYMENT_REMINDER', CURRENT_TIMESTAMP, 'PENDING', ?);
                """, (inv["customer_id"], inv["customer_name"], inv["customer_phone"], inv["id"], msg_body))
                queued_count += 1

        # ----------------------------------------------------
        # 2. CLINIC APPOINTMENT & CHECKUP FOLLOW-UPS
        # ----------------------------------------------------
        yesterday = str(today - datetime.timedelta(days=1))
        cursor.execute("""
        SELECT * FROM appointments 
        WHERE appointment_date = ? AND status = 'COMPLETED';
        """, (yesterday,))
        completed_appts = cursor.fetchall()

        for appt in completed_appts:
            cursor.execute("""
            SELECT id FROM followups 
            WHERE phone = ? AND followup_type = 'CLINIC_CHECKUP' 
              AND DATE(created_at) = ?;
            """, (appt["phone"], str(today)))
            
            if not cursor.fetchone():
                msg_body = (
                    f"Namaste {appt['patient_name']} ji! 🩺\n\n"
                    f"This is *{biz_name}*. How are you feeling today following your consultation with {appt['doctor_name']}?\n\n"
                    f"Please remember to take your prescribed doses on time. If you have any questions or need a follow-up test, simply reply to this message.\n"
                    f"Wishing you a speedy recovery! 🙏"
                )

                cursor.execute("""
                INSERT INTO followups (customer_id, customer_name, phone, invoice_id, followup_type, scheduled_at, status, message_text)
                VALUES (NULL, ?, ?, NULL, 'CLINIC_CHECKUP', CURRENT_TIMESTAMP, 'PENDING', ?);
                """, (appt["patient_name"], appt["phone"], msg_body))
                queued_count += 1

    return {
        "queued_count": queued_count,
        "status": "SUCCESS",
        "timestamp": datetime.datetime.now().isoformat()
    }


def execute_pending_followups() -> Dict[str, Any]:
    """
    Dispatches all pending follow-ups (records into outbound messages).
    """
    dispatched = []
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM followups WHERE status = 'PENDING';")
        pending = cursor.fetchall()

        for item in pending:
            cursor.execute("""
            UPDATE followups 
            SET status = 'SENT', executed_at = CURRENT_TIMESTAMP 
            WHERE id = ?;
            """, (item["id"],))

            cursor.execute("""
            INSERT INTO messages (phone, sender_name, direction, content, intent, status)
            VALUES (?, 'VyaparAI Automated Follow-Up', 'OUTBOUND', ?, ?, 'DELIVERED');
            """, (item["phone"], item["message_text"], item["followup_type"]))

            dispatched.append({
                "id": item["id"],
                "customer": item["customer_name"],
                "phone": item["phone"],
                "type": item["followup_type"]
            })

    return {
        "dispatched_count": len(dispatched),
        "dispatched_items": dispatched,
        "timestamp": datetime.datetime.now().isoformat()
    }
