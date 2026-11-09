# ⚡ VyaparAI OS (व्यापार AI)
### The AI Operating System for Bharat's MSMEs — Indian Shops, Distributors, Clinics & Manufacturers

---

## 🌟 1. Startup Name Suggestions & Brand Identity

Here are 5 startup names tailored for the Indian business ecosystem:

| Startup Name | Tagline | Brand Strategy & Market Fit |
| :--- | :--- | :--- |
| **1. VyaparAI OS (व्यापार AI)** *(Recommended)* | *The Intelligent Operating System for Bharat's Businesses* | Universal resonance. Every Indian trader, shopkeeper, and manufacturer understands "Vyapar". Friendly, authoritative, and memorable. |
| **2. KuberFlow (कुबेर)** | *AI Cash Flow, Invoicing & WhatsApp Collections* | Focuses on cash velocity, instant UPI recovery, and eradicating bad debts/unpaid Udhaar. Named after Kuber, the deity of wealth. |
| **3. DukaanOS** | *Smart Storefront, Inventory & WhatsApp AI* | Simple, punchy, and direct. Ideal for rapid retail shop and wholesale distributor adoption. |
| **4. UdyogMate (उद्योग मेट)** | *Autonomous ERP for Clinics, Manufacturers & Distributors* | Emphasizes industrial, fabrication, and healthcare operations with higher perceived enterprise B2B value. |
| **5. BahiKhata AI** | *Traditional Trust, Autonomous AI Speed* | Appeals to traditional merchants transitioning from paper ledger notebooks (Bahi Khata) to modern digital software. |

---

## 💡 2. Zero-Cost / ₹0 Budget Architecture

To ensure **zero financial investment** from you:

1. **Zero Database Hosting Costs**: Uses SQLite with WAL (Write-Ahead Logging) and thread-safe sessions. Runs embedded directly inside your app with zero monthly database cloud bills ($0/month).
2. **Zero Paid AI Token Cost**: Built with a high-speed local Indian business heuristic and intent engine that handles Hinglish, Hindi, and English in `< 5ms` with zero paid API calls. It also includes an optional integration with the free tier of Google Gemini API.
3. **Zero WhatsApp API Cost for Testing**: Features a built-in, realistic **WhatsApp Web Simulator** that replicates customer chats, typing indicators, quick reply pills, and order placement right in the browser. When you are ready to launch live, it connects to Meta's WhatsApp Cloud API (which offers 1,000 free service conversations per month).
4. **Zero Frontend Framework License / Build Tool Fees**: Built with vanilla CSS & JavaScript, meaning zero build pipelines, zero package subscription costs, and lightning-fast loading speeds on low-spec shop laptops and mobile browsers.

---

## 🛡️ 3. Hacker Defense & Security Architecture

VyaparAI OS includes enterprise-grade security controls to protect MSMEs against common cyber attacks:

- **100% Parameterized SQL Statements**: All database operations use SQLite parameter substitution (`?`). String concatenation is completely prohibited, defending against SQL Injection (SQLi) attacks.
- **Sliding-Window Rate Limiter**: An in-memory token bucket rate limiter restricts traffic per IP address (120 requests/min), protecting your server from Denial-of-Service (DoS) and automated credential stuffing.
- **Input Sanitization & Output Encoding**: All incoming customer strings, product names, and invoice notes are stripped of `<script>`, `onerror`, and malicious payloads to defend against Cross-Site Scripting (XSS).
- **HMAC-SHA256 Webhook Verification**: Out-of-the-box support for Meta's `X-Hub-Signature-256` header ensures only legitimate WhatsApp servers can submit customer messages and order updates.
- **Hardened HTTP Security Headers**:
  - `Content-Security-Policy (CSP)`
  - `X-Frame-Options: SAMEORIGIN` (Anti-Clickjacking)
  - `X-Content-Type-Options: nosniff` (Anti-MIME Sniffing)
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
- **Tamper-Evident Security Audit Logs**: Financial edits, payment recordings, and configuration changes are timestamped and recorded in an immutable audit ledger.

---

## 🚀 4. Core Features & Capabilities

### 1️⃣ WhatsApp AI Assistant (Hinglish / Hindi / English)
- **Domain Specialization**: Presets for 4 distinct Indian business models:
  - **Retail / Kirana Shop**: Price checks ("Bhai oil aur rice ka rate kya hai?"), stock availability, quick order packing, and Udhaar balance check.
  - **FMCG & Wholesale Distributor**: Minimum Order Quantities (MOQ), master carton rates, dealer ledger status.
  - **Healthcare Clinic & Pathology**: Doctor OPD slot booking, test availability (CBC, Lipid profile), prescription medicine checks.
  - **Small Manufacturer & Fabrication**: M12 bolts, CNC machined shaft quotes, raw material stock, job order tracking.
- **Natural Language Comprehension**: Handles conversational Hinglish naturally and returns itemized quotes, payment links, and confirmations.

### 2️⃣ GST Invoicing & Instant NPCI UPI Payments
- **GST-Compliant Engine**: Handles Intra-state supply (CGST 9% + SGST 9%) vs. Inter-state supply (IGST 18%), HSN/SAC codes, and tax breakdowns.
- **Dynamic UPI QR Codes**: Generates real NPCI standard links (`upi://pay?pa=...&pn=...&am=...&cu=INR&tn=...`) and crisp, vector SVG QR codes scannable by Google Pay, PhonePe, Paytm, BHIM, and CRED.
- **Printable Tax Invoice**: One-click thermal/A4 print view at `/invoice/{invoice_no}/view` with company stamp, items table, and UPI QR code embedded directly into the bill.
- **Payment Lifecycle Tracking**: Manages `UNPAID`, `PARTIAL`, `PAID`, and `OVERDUE` states with instant balance adjustments.

### 3️⃣ Automated Customer Follow-Up Engine
- **Overdue Payment Recovery**: Scans overdue bills and generates polite, personalized WhatsApp reminders with direct UPI pay links.
- **Abandoned Quote Nudges**: Re-engages potential buyers after 24 hours of inquiry.
- **Post-Service Patient Checkups**: Automatically checks in on clinic patients the day after their doctor consultation.
- **Replenishment Alerts**: Reminds grocery and distributor clients when staple items are due for re-order.

### 4️⃣ Real-Time Inventory & Khata (Udhaar) Ledger
- **Stock Tracking**: Tracks cost price, MRP, margin, unit (kg, ltr, pcs, box, strip), and safety thresholds.
- **Low Stock Badges & Quick Restock**: Automatically flags items running low and allows instant restocking in one click.
- **Customer Khata**: Keeps track of debit, credit, balance due, and total lifetime purchases per customer.

---

## 🏃 5. How to Run Locally

### 1. Launch the Server
In PowerShell or Terminal:
```powershell
cd C:\Users\Tosha\.gemini\antigravity\scratch\vyapar-ai-os
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

### 2. Open the Web Application
Open your browser and navigate to:
```
http://localhost:8000
```

### 3. Interactive Testing
- Switch business modes using the top dropdown (Shop, Distributor, Clinic, Manufacturer).
- Open the **WhatsApp AI Assistant** tab, select a customer persona, and type in Hinglish (or click any of the quick query buttons).
- Click **+ New GST Bill** to generate a tax invoice with an embedded UPI QR code.
- Go to the **Auto Follow-Ups** tab and click **⚡ Run Follow-Up Engine Now** to watch automated payment reminders trigger.
- Check the **Hacker Defense** tab to review real-time audit logs and security parameters.
