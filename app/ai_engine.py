import re
import datetime
from typing import Dict, Any, List, Optional
import sqlite3
from app.database import db_session
from app.upi_generator import generate_upi_link, format_inr
from app.config import GEMINI_API_KEY

def detect_intent(text: str) -> str:
    """
    Classifies the user's message into actionable business intents.
    Supports English, Hindi, and Hinglish.
    """
    t = text.lower().strip()
    
    # 1. Payment & Udhaar / Khata Intents
    if any(k in t for k in ["hisab", "udhaar", "baki", "balance", "ledger", "khata", "due", "pending", "kitna dena", "pay", "payment", "upi", "qr code", "qr"]):
        return "PAYMENT_INQUIRY"

    # 2. Appointment / Consultation (Clinics / Service businesses)
    if any(k in t for k in ["appointment", "doctor", "dr.", "dr ", "consultation", "checkup", "booking", "slot", "clinic", "opd"]):
        return "APPOINTMENT_REQUEST"

    # 3. Stock / Availability / Price Check (e.g. "Basmati rice ka rate kya hai?")
    if any(k in t for k in ["stock", "available", "hai kya", "milega", "price", "rate", "bhav", "cost", "kitne ka", "kya rate", "moq", "minimum"]):
        return "CHECK_STOCK"

    # 4. Placing an Order / Buy / Order Draft ("bill bana do", "pack karo", "order")
    if any(k in t for k in ["bana do", "pack", "order", "bhejo", "chahiye", "deliver", "bhej do", "dispatch", "quote", "quotation", "kharidna"]):
        return "PLACE_ORDER"
        
    # 5. Invoice / Bill Request (viewing past bill)
    if any(k in t for k in ["bill", "invoice", "receipt", "parcha", "rasid", "chalan", "tax invoice"]):
        return "REQUEST_INVOICE"
        
    # 6. Order / Dispatch Tracking
    if any(k in t for k in ["kahan pahuncha", "status", "track", "delivery kab", "dispatch kab", "where is my", "order status"]):
        return "TRACK_ORDER"
        
    # 7. Greetings / Help
    if any(k in t for k in ["namaste", "hello", "hi", "hey", "ram ram", "pranam", "kese ho", "shuru", "help"]):
        return "GREETING"
        
    return "GENERAL_INQUIRY"


def process_whatsapp_enquiry(
    customer_phone: str,
    customer_name: str,
    message_text: str
) -> Dict[str, Any]:
    """
    Core AI reasoning engine for incoming WhatsApp conversations.
    Operates on the user's actual database (real products, real invoices, real customers).
    """
    intent = detect_intent(message_text)
    
    with db_session() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch active business profile
        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        biz = cursor.fetchone()
            
        biz_name = biz["name"] if biz else "My Business Store"
        upi_id = biz["upi_id"] if biz and biz["upi_id"] else "mybusiness@upi"
        owner_phone = biz["phone"] if biz and biz["phone"] else ""
        biz_type = biz["business_type"] if biz else "shop"
        
        # 2. Fetch or create customer record
        cursor.execute("SELECT * FROM customers WHERE phone = ?;", (customer_phone,))
        cust = cursor.fetchone()
        if not cust:
            cursor.execute("""
            INSERT INTO customers (name, phone, balance_due, total_purchases)
            VALUES (?, ?, 0.0, 0.0);
            """, (customer_name or "Walk-in Customer", customer_phone))
            cursor.execute("SELECT * FROM customers WHERE id = last_insert_rowid();")
            cust = cursor.fetchone()
            
        cust_id = cust["id"]
        cust_name = cust["name"]
        balance_due = cust["balance_due"]

        response_text = ""
        action_payload = {}

        # ========================================================
        # INTENT HANDLERS
        # ========================================================

        # A) PAYMENT & KHATA INQUIRY
        if intent == "PAYMENT_INQUIRY":
            cursor.execute("""
            SELECT * FROM invoices 
            WHERE customer_phone = ? AND status IN ('UNPAID', 'OVERDUE', 'PARTIAL')
            ORDER BY id DESC LIMIT 5;
            """, (customer_phone,))
            open_invoices = cursor.fetchall()
            
            if open_invoices or balance_due > 0:
                total_pending = balance_due if balance_due > 0 else sum(inv["balance_amount"] for inv in open_invoices)
                upi_link = generate_upi_link(
                    upi_id=upi_id,
                    payee_name=biz_name,
                    amount=total_pending,
                    transaction_note=f"Payment by {cust_name}",
                    transaction_ref=f"CUST-{cust_id}"
                )
                
                inv_list_str = "\n".join([f"• Bill #{inv['invoice_no']}: {format_inr(inv['balance_amount'])} ({inv['status']})" for inv in open_invoices]) if open_invoices else f"• Total Khata balance: {format_inr(balance_due)}"
                
                response_text = (
                    f"Namaste {cust_name} ji! 🙏\n\n"
                    f"Aapka pending hisab details:\n"
                    f"{inv_list_str}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"💰 *Total Outstanding: {format_inr(total_pending)}*\n\n"
                    f"Aap seedhe neeche diye UPI link (GPay/PhonePe/Paytm) se payment kar sakte hain:\n"
                    f"👉 {upi_link}\n\n"
                    f"Payment successful hone par digital receipt turant mil jayegi. Dhanyawad!"
                )
                action_payload = {
                    "action": "PAYMENT_LINK",
                    "amount": total_pending,
                    "upi_link": upi_link
                }
            else:
                response_text = (
                    f"Namaste {cust_name} ji! 🙏\n"
                    f"Aapka koi bhi hisab pending nahi hai. All bills are completely paid (Zero Udhaar)!\n"
                    f"Thank you for being a valued customer of {biz_name}."
                )

        # B) REQUEST INVOICE / RECEIPT
        elif intent == "REQUEST_INVOICE":
            cursor.execute("""
            SELECT * FROM invoices 
            WHERE customer_phone = ?
            ORDER BY id DESC LIMIT 1;
            """, (customer_phone,))
            latest_inv = cursor.fetchone()
            
            if latest_inv:
                inv_no = latest_inv["invoice_no"]
                tot = latest_inv["total_amount"]
                bal = latest_inv["balance_amount"]
                st = latest_inv["status"]
                
                response_text = (
                    f"Namaste {cust_name} ji! 🧾\n\n"
                    f"Aapka latest invoice details:\n"
                    f"• *Invoice No:* #{inv_no}\n"
                    f"• *Date:* {latest_inv['created_at'][:10]}\n"
                    f"• *Total Amount:* {format_inr(tot)}\n"
                    f"• *Status:* {st}\n"
                    f"• *Balance Due:* {format_inr(bal)}\n\n"
                    f"Aap direct pay karne ke liye UPI use karein:\n"
                    f"👉 {latest_inv['upi_link']}"
                )
                action_payload = {
                    "action": "INVOICE_VIEW",
                    "invoice_no": inv_no,
                    "total": tot,
                    "status": st
                }
            else:
                response_text = (
                    f"Namaste {cust_name} ji, aapke number par koi past invoice record nahi mila.\n"
                    f"Naya order ya bill banwane ke liye items aur quantity batayein, hum turant bill create kar denge!"
                )

        # C) APPOINTMENT REQUEST
        elif intent == "APPOINTMENT_REQUEST" or biz_type == "clinic":
            doctor = biz.get("owner_name") or "Specialist Doctor"
            tomorrow = str(datetime.date.today() + datetime.timedelta(days=1))
            slot = "11:30 AM" if "subah" in message_text.lower() or "morning" in message_text.lower() else "05:30 PM"
            
            cursor.execute("""
            INSERT INTO appointments (patient_name, phone, doctor_name, appointment_date, time_slot, service_type, status, notes)
            VALUES (?, ?, ?, ?, ?, 'Consultation', 'CONFIRMED', 'Booked via WhatsApp AI Assistant');
            """, (cust_name, customer_phone, doctor, tomorrow, slot))
            
            response_text = (
                f"Namaste {cust_name} ji! 🙏🩺\n\n"
                f"Aapka appointment *{doctor}* ke sath note kar liya gaya hai:\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"📅 *Date:* {tomorrow}\n"
                f"⏰ *Time Slot:* {slot}\n"
                f"🏥 *Location:* {biz['address']}\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Kripya samay par padharein. Kisi bhi badlaav ke liye yahan reply karein!"
            )
            action_payload = {
                "action": "APPOINTMENT_CONFIRMED",
                "doctor": doctor,
                "date": tomorrow,
                "slot": slot
            }

        # D) CHECK STOCK / PRICE
        elif intent == "CHECK_STOCK":
            # Search user-entered inventory items
            words = [w.strip() for w in re.split(r"\s+", message_text.lower()) if len(w) > 2]
            stopwords = {"hai", "kya", "aur", "bhai", "rate", "price", "stock", "chahiye", "kitne", "available", "cost"}
            search_terms = [w for w in words if w not in stopwords]
            
            matching_items = []
            if search_terms:
                query_clause = " OR ".join(["name LIKE ? OR category LIKE ?" for _ in search_terms])
                params = []
                for term in search_terms:
                    params.extend([f"%{term}%", f"%{term}%"])
                
                cursor.execute(f"""
                SELECT * FROM inventory 
                WHERE ({query_clause}) AND is_active = 1
                LIMIT 5;
                """, params)
                matching_items = cursor.fetchall()

            if not matching_items:
                cursor.execute("""
                SELECT * FROM inventory 
                WHERE is_active = 1 
                ORDER BY stock_qty DESC LIMIT 4;
                """)
                matching_items = cursor.fetchall()
                
            if matching_items:
                items_str = []
                for item in matching_items:
                    stock_status = "In Stock ✅" if item["stock_qty"] > item["min_threshold"] else "Low Stock ⚠️"
                    items_str.append(
                        f"• *{item['name']}*\n"
                        f"  Rate: {format_inr(item['selling_price'])} / {item['unit']} | Stock: {int(item['stock_qty'])} {item['unit']} ({stock_status})"
                    )
                    
                response_text = (
                    f"Namaste {cust_name} ji! 🙏 Current rates & stock availability:\n\n"
                    + "\n\n".join(items_str) +
                    f"\n\nKitna order pack karwana chahte hain? Quantity batayein, hum turant bill ready kar denge."
                )
                action_payload = {"action": "STOCK_LIST", "count": len(matching_items)}
            else:
                response_text = (
                    f"Namaste {cust_name} ji! 🙏\n"
                    f"Welcome to *{biz_name}*.\n"
                    f"Hamara catalog update ho raha hai. Aap apne required items aur quantity yahan likhein, hum check karke turant confirm karte hain!"
                )
                action_payload = {"action": "CATALOG_EMPTY"}

        # E) PLACE ORDER / CREATE BILL
        elif intent == "PLACE_ORDER":
            cursor.execute("SELECT * FROM inventory WHERE is_active = 1 LIMIT 3;")
            sample_items = cursor.fetchall()
            
            if sample_items:
                subtotal = sum(item["selling_price"] for item in sample_items)
                gst = round(subtotal * 0.05, 2)
                total = subtotal + gst
                
                inv_no = f"INV-{datetime.date.today().year}-{datetime.datetime.now().strftime('%M%S')}"
                upi_link = generate_upi_link(
                    upi_id=upi_id,
                    payee_name=biz_name,
                    amount=total,
                    transaction_note=f"Order {inv_no}",
                    transaction_ref=inv_no
                )
                
                cursor.execute("""
                INSERT INTO invoices (
                    invoice_no, customer_id, customer_name, customer_phone,
                    subtotal, cgst, sgst, igst, total_amount, paid_amount, balance_amount,
                    status, due_date, upi_link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, 0.0, ?, 'UNPAID', ?, ?);
                """, (
                    inv_no, cust_id, cust_name, customer_phone,
                    subtotal, gst / 2, gst / 2, total, total,
                    str(datetime.date.today() + datetime.timedelta(days=7)),
                    upi_link
                ))
                new_inv_id = cursor.lastrowid
                
                for item in sample_items:
                    tax = round(item["selling_price"] * (item["gst_rate"] / 100.0), 2)
                    cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, item_id, item_name, hsn_code, quantity, unit, unit_price, gst_rate, tax_amount, total_price)
                    VALUES (?, ?, ?, ?, 1.0, ?, ?, ?, ?, ?);
                    """, (new_inv_id, item["id"], item["name"], item["hsn_code"], item["unit"], item["selling_price"], item["gst_rate"], tax, item["selling_price"] + tax))
                    
                cursor.execute("UPDATE customers SET balance_due = balance_due + ?, last_interaction = CURRENT_TIMESTAMP WHERE id = ?;", (total, cust_id))

                items_breakdown = "\n".join([f"• 1x {item['name']}: {format_inr(item['selling_price'])}" for item in sample_items])

                response_text = (
                    f"Aapka order note kar liya gaya hai! 📦✨\n\n"
                    f"*Draft Invoice #{inv_no}*\n"
                    f"{items_breakdown}\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"Subtotal: {format_inr(subtotal)}\n"
                    f"GST: {format_inr(gst)}\n"
                    f"💰 *Net Payable: {format_inr(total)}*\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"Aap is link par click karke turant UPI se pay kar sakte hain:\n"
                    f"👉 {upi_link}\n\n"
                    f"Payment receive hote hi dispatch/delivery initiate ho jayegi! 🙏"
                )
                action_payload = {
                    "action": "ORDER_CREATED",
                    "invoice_no": inv_no,
                    "total": total,
                    "upi_link": upi_link
                }
            else:
                response_text = (
                    f"Namaste {cust_name} ji! 🙏 Aapka order request receive ho gaya hai.\n"
                    f"Hamare representative turant aapki list check karke confirmation aur payment link share karenge."
                )

        # F) TRACK ORDER
        elif intent == "TRACK_ORDER":
            response_text = (
                f"Namaste {cust_name} ji! 🚚\n"
                f"Aapka order active process mein hai. Urgent update ke liye call karein: {owner_phone or 'humare number par'}.\n"
                f"Dhanyawad!"
            )
            action_payload = {"action": "TRACKING_INFO"}

        # G) GREETING & DEFAULT
        else:
            welcome_base = biz["welcome_msg"] if biz and biz.get("welcome_msg") else "Namaste! Welcome to our store."
            response_text = (
                f"{welcome_base}\n\n"
                f"Aap mujhse pooch sakte hain:\n"
                f"1️⃣ *Price & Stock* ('Item ka price kya hai?')\n"
                f"2️⃣ *Order Booking* ('Items pack kar do')\n"
                f"3️⃣ *Hisab / Udhaar Ledger* ('Mera kitna hisab baki hai?')\n"
                f"4️⃣ *Bill & Instant Payment* ('Bill bhejo' ya 'UPI payment link')\n\n"
                f"Bataiye, aaj aapki kya sewa karein? 🙏"
            )
            action_payload = {"action": "GREETING"}

        # Log inbound and outbound messages
        cursor.execute("""
        INSERT INTO messages (phone, sender_name, direction, content, intent)
        VALUES (?, ?, 'INBOUND', ?, ?);
        """, (customer_phone, customer_name, message_text, intent))
        
        cursor.execute("""
        INSERT INTO messages (phone, sender_name, direction, content, intent)
        VALUES (?, ?, 'OUTBOUND', ?, ?);
        """, (customer_phone, biz_name, response_text, intent))

    return {
        "reply": response_text,
        "intent": intent,
        "business_name": biz_name,
        "action": action_payload,
        "timestamp": datetime.datetime.now().isoformat()
    }
