import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "vyapar_ai.db"

# Security & App Settings
APP_NAME = "VyaparAI OS"
APP_TAGLINE = "The Intelligent Operating System for Bharat's Businesses"
SECRET_KEY = os.getenv("SECRET_KEY", "vyapar-ai-zero-cost-secure-token-2026-bharat")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "vyapar_ai_webhook_verify_secure_token")
WHATSAPP_APP_SECRET = os.getenv("WHATSAPP_APP_SECRET", "")  # Used for HMAC-SHA256 validation if available
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Rate limiting
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))  # per minute
RATE_LIMIT_WINDOW = 60  # seconds

# Preset Business Profiles
BUSINESS_PRESETS = {
    "shop": {
        "name": "Sharma Kirana & General Store",
        "tagline": "Daily Grocery, Essentials & Household Items",
        "business_type": "shop",
        "owner_name": "Rameshwar Sharma",
        "phone": "+91 98765 43210",
        "email": "sharma.kirana@vyaparai.local",
        "address": "Shop #14, Main Vyapar Marg, Jaipur, Rajasthan - 302001",
        "state_code": "08",
        "state_name": "Rajasthan",
        "gstin": "08AABCS1429B1Z2",
        "upi_id": "sharmakirana@upi",
        "upi_name": "Sharma Kirana Store",
        "currency": "INR",
        "symbol": "₹",
        "welcome_msg": "Namaste! 🙏 Welcome to Sharma Kirana Store. You can ask for prices, order groceries, check your udhaar balance, or get an instant bill!"
    },
    "distributor": {
        "name": "Bharat FMCG & Wholesale Distributors",
        "tagline": "Bulk Provisions, Edible Oils, Spices & Packaged Goods",
        "business_type": "distributor",
        "owner_name": "Kailash Gupta",
        "phone": "+91 98111 22334",
        "email": "orders@bharatdistributors.local",
        "address": "Plot 42, GIDC Industrial Logistics Park, Ahmedabad, Gujarat - 382445",
        "state_code": "24",
        "state_name": "Gujarat",
        "gstin": "24AAECB9981K1Z5",
        "upi_id": "bharatdistributors@hdfcbank",
        "upi_name": "Bharat Wholesale Distributors",
        "currency": "INR",
        "symbol": "₹",
        "welcome_msg": "Namaste! Welcome to Bharat Wholesale Distribution Hub. Check bulk rates, minimum order quantities (MOQ), place dealer orders, or check dispatch & ledger status."
    },
    "clinic": {
        "name": "Arogya Care Clinic & Diagnostic Center",
        "tagline": "General OPD, Pathology & Specialist Consultations",
        "business_type": "clinic",
        "owner_name": "Dr. Sunita Deshmukh (MBBS, MD)",
        "phone": "+91 98222 55667",
        "email": "care@arogyaclinic.local",
        "address": "Health Plaza, 2nd Cross, Indiranagar, Bengaluru, Karnataka - 560038",
        "state_code": "29",
        "state_name": "Karnataka",
        "gstin": "29AAAAA0000A1Z5",
        "upi_id": "arogyaclinic@sbi",
        "upi_name": "Arogya Care Clinic",
        "currency": "INR",
        "symbol": "₹",
        "welcome_msg": "Namaste! 🙏 Welcome to Arogya Care Clinic. Book doctor consultations, check lab test availability, download prescriptions & bills, or ask clinic timings."
    },
    "manufacturer": {
        "name": "Apex Precision Engineering & Fabrication",
        "tagline": "CNC Machining, Industrial Hardware & Metal Components",
        "business_type": "manufacturer",
        "owner_name": "Vikramaditya Rao",
        "phone": "+91 99000 88776",
        "email": "sales@apexprecision.local",
        "address": "Sector 58, Phase 2, Industrial Area, Noida, Uttar Pradesh - 201301",
        "state_code": "09",
        "state_name": "Uttar Pradesh",
        "gstin": "09AAKFP1234D1Z8",
        "upi_id": "apexengg@kotak",
        "upi_name": "Apex Precision Engineering",
        "currency": "INR",
        "symbol": "₹",
        "welcome_msg": "Greetings from Apex Precision Engineering. Inquire about manufacturing specifications, request batch quotation, track custom job orders, or view GST tax invoices."
    }
}
