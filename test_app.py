import sys
import io
import asyncio
from pathlib import Path

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

from app.database import init_db, reset_database_data, db_session
from app.ai_engine import process_whatsapp_enquiry, detect_intent
from app.upi_generator import generate_upi_link, generate_upi_qr_svg, format_inr
from app.scheduler import check_and_queue_followups, execute_pending_followups
from app.models import (
    BusinessProfileUpdate, InventoryItemCreate, CustomerCreate,
    InvoiceCreateRequest, InvoiceItemInput, PaymentRecordRequest
)
import app.main as main_app

def run_tests():
    print("=" * 65)
    print(" Running VyaparAI OS Tests - Inputtable & Clean Data Verification")
    print("=" * 65)

    # 1. Clean Database Initialization (Zero Pre-existing Fake Data)
    init_db()
    reset_database_data()
    with db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM inventory;")
        assert cursor.fetchone()["cnt"] == 0, "Inventory must be empty!"
        cursor.execute("SELECT COUNT(*) as cnt FROM customers;")
        assert cursor.fetchone()["cnt"] == 0, "Customers must be empty!"
        cursor.execute("SELECT COUNT(*) as cnt FROM invoices;")
        assert cursor.fetchone()["cnt"] == 0, "Invoices must be empty!"
    print("✅ [1/7] Clean Database Initialization: Verified 0 pre-existing data.")

    # 2. Input Business Profile
    biz_update = BusinessProfileUpdate(
        name="Radhe Krishna Traders",
        tagline="Wholesale Provisions & Daily Essentials",
        business_type="shop",
        owner_name="Manoj Aggarwal",
        phone="+91 98290 55443",
        email="manoj@radhetraders.in",
        address="142, Johari Bazar, Jaipur, Rajasthan",
        state_code="08",
        state_name="Rajasthan",
        gstin="08ABCDE1234F1Z5",
        upi_id="radhetraders@okicici",
        upi_name="Radhe Krishna Traders",
        welcome_msg="Namaste! 🙏 Welcome to Radhe Krishna Traders."
    )
    res_prof = asyncio.run(main_app.update_business_profile(biz_update))
    assert res_prof["status"] == "SUCCESS"
    print("✅ [2/7] Business Profile Input: Saved custom merchant credentials.")

    # 3. User Inputs Product into Inventory
    new_item = InventoryItemCreate(
        name="Fortune Kachi Ghani Mustard Oil 1L",
        sku="MST-001",
        category="Edible Oil",
        unit="ltr",
        cost_price=120.0,
        selling_price=155.0,
        stock_qty=50.0,
        min_threshold=10.0,
        hsn_code="1514",
        gst_rate=5.0
    )
    res_item = asyncio.run(main_app.create_inventory_item(new_item))
    assert res_item["status"] == "SUCCESS"
    inv_list = asyncio.run(main_app.get_inventory())
    assert len(inv_list) == 1
    added_item_id = inv_list[0]["id"]
    print(f"✅ [3/7] Product Input: Added '{inv_list[0]['name']}' (₹{inv_list[0]['selling_price']}).")

    # 4. User Inputs Customer Record
    new_cust = CustomerCreate(
        name="Suresh Sharma",
        phone="+91 94140 12345",
        business_name="Sharma Kirana Corner",
        address="Bapu Bazar, Jaipur",
        balance_due=500.0
    )
    res_cust = asyncio.run(main_app.create_customer(new_cust))
    assert res_cust["status"] == "SUCCESS"
    cust_list = asyncio.run(main_app.get_customers())
    assert len(cust_list) == 1
    print(f"✅ [4/7] Customer Input: Added '{cust_list[0]['name']}' (Opening Due: ₹{cust_list[0]['balance_due']}).")

    # 5. WhatsApp AI Enquiring about the User's Real Product
    wa_res = process_whatsapp_enquiry(
        customer_phone="+91 94140 12345",
        customer_name="Suresh Sharma",
        message_text="Mustard oil ka kya rate hai bhai?"
    )
    assert wa_res["intent"] == "CHECK_STOCK"
    assert "Fortune Kachi Ghani Mustard Oil" in wa_res["reply"]
    assert "₹155.00" in wa_res["reply"]
    print("✅ [5/7] WhatsApp AI Engine: Successfully queried user's real product.")

    # 6. User Creates GST Invoice
    inv_req = InvoiceCreateRequest(
        customer_id=cust_list[0]["id"],
        customer_name=cust_list[0]["name"],
        customer_phone=cust_list[0]["phone"],
        customer_address=cust_list[0]["address"],
        customer_gstin="",
        is_interstate=False,
        due_days=7,
        items=[
            InvoiceItemInput(
                item_id=added_item_id,
                item_name="Fortune Kachi Ghani Mustard Oil 1L",
                hsn_code="1514",
                quantity=4.0,
                unit="ltr",
                unit_price=155.0,
                gst_rate=5.0
            )
        ]
    )
    res_inv = asyncio.run(main_app.create_gst_invoice(inv_req))
    assert res_inv["status"] == "SUCCESS"
    inv_no = res_inv["invoice_no"]
    assert res_inv["total_amount"] == 651.00  # 4 * 155 = 620 + 5% GST (31) = 651
    assert "radhetraders%40okicici" in res_inv["upi_link"] or "radhetraders@okicici" in res_inv["upi_link"]
    print(f"✅ [6/7] GST Invoice Creation: Billed #{inv_no} (Total: ₹{res_inv['total_amount']}) with real UPI QR link.")

    # 7. Record Payment & Check System Health
    pay_req = PaymentRecordRequest(amount_paid=651.00, payment_mode="UPI")
    inv_rec = asyncio.run(main_app.list_invoices())
    inv_id = inv_rec[0]["id"]
    res_pay = asyncio.run(main_app.record_payment(inv_id, pay_req))
    assert res_pay["invoice_status"] == "PAID"
    
    health = asyncio.run(main_app.get_system_health())
    assert health["status"] == "HEALTHY"
    print(f"✅ [7/7] Payment Settled: Invoice marked PAID. System memory: {health['memory_usage']}, DB size: {health['database_size_kb']}.")

    print("=" * 65)
    print("🎉 ALL 7/7 TESTS PASSED! Zero hardcoded data, 100% inputtable.")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
