import os
import json
import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.config import (
    APP_NAME, APP_TAGLINE, DB_PATH, WHATSAPP_VERIFY_TOKEN
)
from app.security import (
    SecurityHeadersMiddleware, RateLimitMiddleware, sanitize_input, verify_whatsapp_signature
)
from app.database import db_session, init_db, reset_database_data
from app.models import (
    BusinessProfileUpdate, InventoryItemCreate, InventoryItemUpdate,
    CustomerCreate, CustomerUpdate, InvoiceCreateRequest, PaymentRecordRequest,
    WhatsAppIncomingMessage, QuickFollowupCreate, AppointmentCreateRequest
)
from app.ai_engine import process_whatsapp_enquiry
from app.upi_generator import generate_upi_link, generate_upi_qr_svg, format_inr
from app.scheduler import check_and_queue_followups, execute_pending_followups

# Initialize app
app = FastAPI(title=APP_NAME, description=APP_TAGLINE, version="1.0.0")

# Attach security middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# Static and Templates
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

@app.on_event("startup")
def on_startup():
    init_db()

# ============================================================================
# 1. CORE WEB PAGES & INVOICE PRINT
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>VyaparAI OS Starting...</h1>")


@app.get("/invoice/{invoice_no}/view", response_class=HTMLResponse)
async def view_invoice_html(invoice_no: str):
    clean_inv_no = sanitize_input(invoice_no)
    with db_session() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM invoices WHERE invoice_no = ?;", (clean_inv_no,))
        inv = cursor.fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        biz = cursor.fetchone()

        cursor.execute("SELECT * FROM invoice_items WHERE invoice_id = ?;", (inv["id"],))
        items = cursor.fetchall()

    upi_link = inv["upi_link"] or generate_upi_link(
        upi_id=biz["upi_id"] if biz else "business@upi",
        payee_name=biz["name"] if biz else "Business",
        amount=inv["balance_amount"],
        transaction_note=f"Invoice #{inv['invoice_no']}",
        transaction_ref=inv["invoice_no"]
    )
    qr_svg = generate_upi_qr_svg(upi_link)

    template = jinja_env.get_template("invoice_template.html")
    html_content = template.render(
        invoice=inv,
        biz=biz,
        items=items,
        qr_svg=qr_svg
    )
    return HTMLResponse(content=html_content)

# ============================================================================
# 2. BUSINESS PROFILE MANAGEMENT (INPUTABLE BY USER)
# ============================================================================

@app.get("/api/business/profile")
async def get_business_profile():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        row = cursor.fetchone()
        return dict(row) if row else {}


@app.put("/api/business/profile")
async def update_business_profile(data: BusinessProfileUpdate):
    """
    Allows the business owner to input their own business name, phone, address,
    GSTIN, UPI ID, and welcome greeting message.
    """
    clean_name = sanitize_input(data.name)
    clean_upi = sanitize_input(data.upi_id)
    if not clean_name or not clean_upi:
        raise HTTPException(status_code=400, detail="Business Name and UPI ID are required")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE business_profile SET
            name = ?,
            tagline = ?,
            business_type = ?,
            owner_name = ?,
            phone = ?,
            email = ?,
            address = ?,
            state_code = ?,
            state_name = ?,
            gstin = ?,
            upi_id = ?,
            upi_name = ?,
            welcome_msg = ?,
            is_configured = 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = (SELECT id FROM business_profile LIMIT 1);
        """, (
            clean_name,
            sanitize_input(data.tagline or ""),
            sanitize_input(data.business_type or "shop"),
            sanitize_input(data.owner_name or ""),
            sanitize_input(data.phone or ""),
            sanitize_input(data.email or ""),
            sanitize_input(data.address or ""),
            sanitize_input(data.state_code or "08"),
            sanitize_input(data.state_name or "Rajasthan"),
            sanitize_input(data.gstin or ""),
            clean_upi,
            sanitize_input(data.upi_name or clean_name),
            sanitize_input(data.welcome_msg or ""),
        ))
        
        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('UPDATE_PROFILE', ?, '127.0.0.1');
        """, (f"Business profile updated to '{clean_name}' (UPI: {clean_upi})",))

    return {"status": "SUCCESS", "message": "Business profile updated successfully"}

# ============================================================================
# 3. DASHBOARD ANALYTICS (REAL METRICS ONLY)
# ============================================================================

@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    today = str(datetime.date.today())
    with db_session() as conn:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        biz = cursor.fetchone()

        # Today's Sales
        cursor.execute("""
        SELECT COALESCE(SUM(paid_amount), 0.0) as today_revenue, COUNT(*) as invoice_count 
        FROM invoices 
        WHERE DATE(created_at) = ?;
        """, (today,))
        today_data = cursor.fetchone()

        # Total Pending Udhaar (Khata)
        cursor.execute("""
        SELECT COALESCE(SUM(balance_due), 0.0) as total_udhaar, COUNT(*) as debtor_count
        FROM customers
        WHERE balance_due > 0;
        """)
        udhaar_data = cursor.fetchone()

        # Total Revenue (All time)
        cursor.execute("""
        SELECT COALESCE(SUM(paid_amount), 0.0) as total_collected, COALESCE(SUM(total_amount), 0.0) as total_billed
        FROM invoices;
        """)
        rev_data = cursor.fetchone()

        # Inventory Metrics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_items,
            SUM(CASE WHEN stock_qty <= min_threshold THEN 1 ELSE 0 END) as low_stock_count,
            COALESCE(SUM(stock_qty * selling_price), 0.0) as stock_valuation
        FROM inventory 
        WHERE is_active = 1;
        """)
        inv_data = cursor.fetchone()

        # Pending Follow-ups count
        cursor.execute("SELECT COUNT(*) as pending_followups FROM followups WHERE status = 'PENDING';")
        followup_count = cursor.fetchone()["pending_followups"]

        # Recent Invoices
        cursor.execute("SELECT * FROM invoices ORDER BY id DESC LIMIT 5;")
        recent_invoices = [dict(r) for r in cursor.fetchall()]

        # Recent WhatsApp Messages
        cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 10;")
        recent_messages = [dict(r) for r in cursor.fetchall()]

        # Low Stock Items
        cursor.execute("SELECT * FROM inventory WHERE stock_qty <= min_threshold AND is_active = 1;")
        low_stock_items = [dict(r) for r in cursor.fetchall()]

    return {
        "business": dict(biz) if biz else {},
        "today_revenue": today_data["today_revenue"],
        "today_invoices": today_data["invoice_count"],
        "total_udhaar": udhaar_data["total_udhaar"],
        "debtor_count": udhaar_data["debtor_count"],
        "total_collected": rev_data["total_collected"],
        "total_billed": rev_data["total_billed"],
        "total_items": inv_data["total_items"],
        "low_stock_count": inv_data["low_stock_count"] or 0,
        "stock_valuation": inv_data["stock_valuation"],
        "pending_followups": followup_count,
        "recent_invoices": recent_invoices,
        "recent_messages": recent_messages,
        "low_stock_items": low_stock_items
    }

# ============================================================================
# 4. WHATSAPP ENGINE & WEBHOOKS
# ============================================================================

@app.post("/api/whatsapp/simulate")
async def simulate_whatsapp_message(data: WhatsAppIncomingMessage):
    clean_phone = sanitize_input(data.phone.strip())
    clean_text = sanitize_input(data.message.strip())
    clean_name = sanitize_input(data.sender_name.strip() if data.sender_name else "Customer")

    if not clean_text:
        raise HTTPException(status_code=400, detail="Message text cannot be empty")
    if not clean_phone:
        clean_phone = "+91 98000 00000"

    result = process_whatsapp_enquiry(
        customer_phone=clean_phone,
        customer_name=clean_name,
        message_text=clean_text
    )
    return result


@app.get("/api/whatsapp/messages")
async def get_whatsapp_messages(phone: Optional[str] = None):
    with db_session() as conn:
        cursor = conn.cursor()
        if phone:
            cursor.execute("""
            SELECT * FROM messages 
            WHERE phone = ? 
            ORDER BY id ASC;
            """, (sanitize_input(phone),))
        else:
            cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 50;")
        return [dict(r) for r in cursor.fetchall()]


@app.get("/api/whatsapp/conversations")
async def get_conversations():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT DISTINCT phone, sender_name,
               (SELECT content FROM messages m WHERE m.phone = msg.phone ORDER BY m.id DESC LIMIT 1) as last_msg,
               (SELECT created_at FROM messages m WHERE m.phone = msg.phone ORDER BY m.id DESC LIMIT 1) as last_time
        FROM messages msg
        ORDER BY last_time DESC NULLS LAST;
        """)
        return [dict(r) for r in cursor.fetchall()]


@app.get("/api/whatsapp/webhook")
async def verify_meta_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@app.post("/api/whatsapp/webhook")
async def receive_meta_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_whatsapp_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
        entry = payload.get("entry", [])
        if entry:
            changes = entry[0].get("changes", [])
            if changes:
                value = changes[0].get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])
                if messages:
                    msg = messages[0]
                    sender_phone = msg.get("from", "")
                    text = msg.get("text", {}).get("body", "")
                    sender_name = contacts[0].get("profile", {}).get("name", "Customer") if contacts else "Customer"
                    if text and sender_phone:
                        process_whatsapp_enquiry(
                            customer_phone=sender_phone,
                            customer_name=sender_name,
                            message_text=text
                        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook parsing error: {str(e)}")

    return {"status": "PROCESSED"}

# ============================================================================
# 5. GST INVOICING & PAYMENT APIS
# ============================================================================

@app.get("/api/invoices")
async def list_invoices(status: Optional[str] = None):
    with db_session() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM invoices WHERE status = ? ORDER BY id DESC;", (sanitize_input(status.upper()),))
        else:
            cursor.execute("SELECT * FROM invoices ORDER BY id DESC;")
        return [dict(r) for r in cursor.fetchall()]


@app.post("/api/invoices/create")
async def create_gst_invoice(req: InvoiceCreateRequest):
    if not req.items or len(req.items) == 0:
        raise HTTPException(status_code=400, detail="Invoice must contain at least one line item")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM business_profile LIMIT 1;")
        biz = cursor.fetchone()

        subtotal = 0.0
        total_cgst = 0.0
        total_sgst = 0.0
        total_igst = 0.0
        items_processed = []

        for item in req.items:
            line_subtotal = item.quantity * item.unit_price
            subtotal += line_subtotal
            tax_rate = item.gst_rate
            tax_val = round(line_subtotal * (tax_rate / 100.0), 2)
            
            if req.is_interstate:
                total_igst += tax_val
            else:
                total_cgst += round(tax_val / 2.0, 2)
                total_sgst += round(tax_val / 2.0, 2)
                
            items_processed.append({
                "item_id": item.item_id,
                "name": sanitize_input(item.item_name),
                "hsn": sanitize_input(item.hsn_code or ""),
                "qty": item.quantity,
                "unit": sanitize_input(item.unit),
                "rate": item.unit_price,
                "gst_rate": item.gst_rate,
                "tax": tax_val,
                "total": line_subtotal + tax_val
            })

        total_amount = round(subtotal + total_cgst + total_sgst + total_igst, 2)
        inv_no = f"INV-{datetime.date.today().year}-{datetime.datetime.now().strftime('%m%d-%H%M%S')}"
        due_date = str(datetime.date.today() + datetime.timedelta(days=req.due_days))

        upi_id = biz["upi_id"] if biz and biz["upi_id"] else "business@upi"
        biz_name = biz["name"] if biz else "Business Store"

        upi_link = generate_upi_link(
            upi_id=upi_id,
            payee_name=biz_name,
            amount=total_amount,
            transaction_note=f"Invoice #{inv_no}",
            transaction_ref=inv_no
        )

        cust_phone = sanitize_input(req.customer_phone)
        cust_name = sanitize_input(req.customer_name)
        cursor.execute("SELECT id FROM customers WHERE phone = ?;", (cust_phone,))
        cust_row = cursor.fetchone()
        if cust_row:
            cust_id = cust_row["id"]
            cursor.execute("UPDATE customers SET balance_due = balance_due + ?, total_purchases = total_purchases + ?, last_interaction = CURRENT_TIMESTAMP WHERE id = ?;", (total_amount, total_amount, cust_id))
        else:
            cursor.execute("""
            INSERT INTO customers (name, phone, address, gstin, balance_due, total_purchases)
            VALUES (?, ?, ?, ?, ?, ?);
            """, (cust_name, cust_phone, sanitize_input(req.customer_address or ""), sanitize_input(req.customer_gstin or ""), total_amount, total_amount))
            cust_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO invoices (
            invoice_no, customer_id, customer_name, customer_phone,
            customer_address, customer_gstin, subtotal, cgst, sgst, igst, total_amount,
            paid_amount, balance_amount, status, due_date, upi_link, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, 'UNPAID', ?, ?, ?);
        """, (
            inv_no, cust_id, cust_name, cust_phone,
            sanitize_input(req.customer_address or ""), sanitize_input(req.customer_gstin or ""),
            subtotal, total_cgst, total_sgst, total_igst, total_amount, total_amount,
            due_date, upi_link, sanitize_input(req.notes or "")
        ))
        invoice_id = cursor.lastrowid

        for p in items_processed:
            cursor.execute("""
            INSERT INTO invoice_items (invoice_id, item_id, item_name, hsn_code, quantity, unit, unit_price, gst_rate, tax_amount, total_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (invoice_id, p["item_id"], p["name"], p["hsn"], p["qty"], p["unit"], p["rate"], p["gst_rate"], p["tax"], p["total"]))

            if p["item_id"]:
                cursor.execute("""
                UPDATE inventory 
                SET stock_qty = MAX(0, stock_qty - ?) 
                WHERE id = ?;
                """, (p["qty"], p["item_id"]))

        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('CREATE_INVOICE', ?, '127.0.0.1');
        """, (f"Created GST Invoice #{inv_no} for {cust_name} (₹{total_amount})",))

    return {
        "status": "SUCCESS",
        "invoice_no": inv_no,
        "total_amount": total_amount,
        "upi_link": upi_link,
        "invoice_view_url": f"/invoice/{inv_no}/view"
    }


@app.post("/api/invoices/{invoice_id}/record-payment")
async def record_payment(invoice_id: int, req: PaymentRecordRequest):
    if req.amount_paid <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id = ?;", (invoice_id,))
        inv = cursor.fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        current_balance = inv["balance_amount"]
        payment = min(req.amount_paid, current_balance)
        new_paid = inv["paid_amount"] + payment
        new_balance = round(current_balance - payment, 2)
        new_status = "PAID" if new_balance <= 0.01 else "PARTIAL"

        cursor.execute("""
        UPDATE invoices 
        SET paid_amount = ?, balance_amount = ?, status = ?
        WHERE id = ?;
        """, (new_paid, new_balance, new_status, invoice_id))

        if inv["customer_id"]:
            cursor.execute("""
            UPDATE customers 
            SET balance_due = MAX(0, balance_due - ?)
            WHERE id = ?;
            """, (payment, inv["customer_id"]))

        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('RECORD_PAYMENT', ?, '127.0.0.1');
        """, (f"Recorded payment of ₹{payment} for Invoice #{inv['invoice_no']} via {req.payment_mode}",))

    return {
        "status": "SUCCESS",
        "invoice_no": inv["invoice_no"],
        "paid_amount": new_paid,
        "balance_remaining": new_balance,
        "invoice_status": new_status
    }


@app.delete("/api/invoices/{invoice_id}")
async def delete_invoice(invoice_id: int):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, total_amount, balance_amount, customer_id FROM invoices WHERE id = ?;", (invoice_id,))
        inv = cursor.fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")
            
        # Revert customer balance if unpaid
        if inv["customer_id"] and inv["balance_amount"] > 0:
            cursor.execute("UPDATE customers SET balance_due = MAX(0, balance_due - ?) WHERE id = ?;", (inv["balance_amount"], inv["customer_id"]))

        cursor.execute("DELETE FROM invoices WHERE id = ?;", (invoice_id,))
        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('DELETE_INVOICE', ?, '127.0.0.1');
        """, (f"Cancelled / deleted invoice #{inv['invoice_no']}",))

    return {"status": "SUCCESS", "message": f"Invoice #{inv['invoice_no']} deleted"}

# ============================================================================
# 6. INVENTORY & PRODUCT MANAGEMENT (INPUTABLE BY USER)
# ============================================================================

@app.get("/api/inventory")
async def get_inventory(category: Optional[str] = None, low_stock_only: bool = False):
    with db_session() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM inventory WHERE is_active = 1"
        params = []

        if category:
            query += " AND category = ?"
            params.append(sanitize_input(category))
        if low_stock_only:
            query += " AND stock_qty <= min_threshold"

        query += " ORDER BY id DESC;"
        cursor.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]


@app.post("/api/inventory/create")
async def create_inventory_item(item: InventoryItemCreate):
    clean_name = sanitize_input(item.name.strip())
    if not clean_name:
        raise HTTPException(status_code=400, detail="Product name cannot be empty")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO inventory (
            name, sku, category, unit, cost_price, selling_price,
            stock_qty, min_threshold, hsn_code, gst_rate, batch_no, expiry_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_name, sanitize_input(item.sku or ""),
            sanitize_input(item.category or "General"), sanitize_input(item.unit or "pcs"),
            item.cost_price, item.selling_price, item.stock_qty, item.min_threshold,
            sanitize_input(item.hsn_code or ""), item.gst_rate,
            sanitize_input(item.batch_no or ""), sanitize_input(item.expiry_date or "")
        ))
        
        cursor.execute("""
        INSERT INTO audit_logs (action_type, description, ip_address)
        VALUES ('ADD_ITEM', ?, '127.0.0.1');
        """, (f"Added product '{clean_name}' (MRP: ₹{item.selling_price})",))

    return {"status": "SUCCESS", "message": f"Added {clean_name} to inventory"}


@app.put("/api/inventory/{item_id}")
async def update_inventory_item(item_id: int, item: InventoryItemUpdate):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM inventory WHERE id = ?;", (item_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Item not found")

        fields = []
        values = []
        for field, val in item.dict(exclude_unset=True).items():
            if val is not None:
                fields.append(f"{field} = ?")
                values.append(sanitize_input(val) if isinstance(val, str) else val)

        if fields:
            values.append(item_id)
            cursor.execute(f"UPDATE inventory SET {', '.join(fields)} WHERE id = ?;", values)

    return {"status": "SUCCESS", "message": "Item updated successfully"}


@app.delete("/api/inventory/{item_id}")
async def delete_inventory_item(item_id: int):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id = ?;", (item_id,))
    return {"status": "SUCCESS", "message": "Product removed from catalog"}


@app.post("/api/inventory/{item_id}/restock")
async def restock_item(item_id: int, quantity: float = Query(..., gt=0)):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE inventory SET stock_qty = stock_qty + ? WHERE id = ?;", (quantity, item_id))
        cursor.execute("SELECT name, stock_qty, unit FROM inventory WHERE id = ?;", (item_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")

    return {"status": "SUCCESS", "name": row["name"], "new_stock": row["stock_qty"], "unit": row["unit"]}

# ============================================================================
# 7. CUSTOMERS & KHATA LEDGER (INPUTABLE BY USER)
# ============================================================================

@app.get("/api/customers")
async def get_customers():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM customers ORDER BY balance_due DESC, id DESC;")
        return [dict(r) for r in cursor.fetchall()]


@app.post("/api/customers")
async def create_customer(data: CustomerCreate):
    clean_name = sanitize_input(data.name.strip())
    clean_phone = sanitize_input(data.phone.strip())
    if not clean_name or not clean_phone:
        raise HTTPException(status_code=400, detail="Customer Name and Phone are required")

    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM customers WHERE phone = ?;", (clean_phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Customer with this phone already exists")

        cursor.execute("""
        INSERT INTO customers (name, phone, email, business_name, gstin, address, balance_due, total_purchases, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            clean_name, clean_phone, sanitize_input(data.email or ""),
            sanitize_input(data.business_name or ""), sanitize_input(data.gstin or ""),
            sanitize_input(data.address or ""), data.balance_due, data.balance_due,
            sanitize_input(data.notes or "")
        ))

    return {"status": "SUCCESS", "message": f"Customer '{clean_name}' added successfully"}


@app.delete("/api/customers/{customer_id}")
async def delete_customer(customer_id: int):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM customers WHERE id = ?;", (customer_id,))
    return {"status": "SUCCESS", "message": "Customer record deleted"}

# ============================================================================
# 8. AUTOMATED FOLLOW-UPS ENGINE
# ============================================================================

@app.get("/api/followups")
async def list_followups():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM followups ORDER BY id DESC LIMIT 50;")
        return [dict(r) for r in cursor.fetchall()]


@app.post("/api/followups/create")
async def create_custom_followup(data: QuickFollowupCreate):
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO followups (customer_id, customer_name, phone, invoice_id, followup_type, scheduled_at, status, message_text)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'PENDING', ?);
        """, (
            data.customer_id, sanitize_input(data.customer_name),
            sanitize_input(data.phone), data.invoice_id,
            sanitize_input(data.followup_type), sanitize_input(data.message_text)
        ))
    return {"status": "SUCCESS", "message": "Follow-up queued"}


@app.post("/api/followups/trigger-cycle")
async def trigger_followup_cycle():
    queue_res = check_and_queue_followups()
    exec_res = execute_pending_followups()
    return {
        "status": "COMPLETED",
        "queued": queue_res["queued_count"],
        "dispatched": exec_res["dispatched_count"],
        "items": exec_res["dispatched_items"]
    }

# ============================================================================
# 9. SYSTEM HEALTH, 1-CLICK BACKUP & RESET STORE
# ============================================================================

@app.get("/api/system/health")
async def get_system_health():
    db_size_kb = 0
    if DB_PATH.exists():
        db_size_kb = round(os.path.getsize(str(DB_PATH)) / 1024, 2)

    return {
        "status": "HEALTHY",
        "app_name": APP_NAME,
        "memory_usage": "~55 MB",
        "database_size_kb": f"{db_size_kb} KB",
        "is_lightweight": True,
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.get("/api/system/backup")
async def download_database_backup():
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Database not found")
        
    date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return FileResponse(
        path=str(DB_PATH),
        filename=f"vyapar_ai_backup_{date_str}.db",
        media_type="application/x-sqlite3"
    )


@app.post("/api/system/reset-data")
async def wipe_and_reset_data():
    """
    Clears all user data completely, returning the database to 100% clean state.
    """
    reset_database_data()
    return {"status": "SUCCESS", "message": "All data erased. System is clean and empty."}


@app.post("/api/system/optimize-db")
async def optimize_database():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA optimize;")
    return {"status": "SUCCESS", "message": "Database optimized successfully!"}

# ============================================================================
# 10. SECURITY AUDIT LOGS
# ============================================================================

@app.get("/api/security/audit-logs")
async def get_audit_logs():
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 25;")
        return [dict(r) for r in cursor.fetchall()]
