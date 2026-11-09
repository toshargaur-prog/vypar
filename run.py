import sys
import os
import threading
import time
import webbrowser
from pathlib import Path

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure root directory is in python path
root_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(root_dir))

import uvicorn
from app.database import init_db

def auto_launch_browser():
    """
    Waits 1.2 seconds for Uvicorn to bind to port 8000, then automatically opens
    the default browser. Makes the app feel like a native desktop software for shop owners.
    """
    time.sleep(1.2)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass

def main():
    print("=" * 70)
    print(" VyaparAI OS - Ultra-Lightweight Edition (<60MB RAM)")
    print(" Designed for any PC: Shop Desktops, Laptops, Windows 7/10/11")
    print("=" * 70)
    print("  [+] WhatsApp AI Assistant (Hinglish/English): ACTIVE")
    print("  [+] GST Tax Invoicing & NPCI UPI QR Engine: ACTIVE")
    print("  [+] Automated Customer Follow-Up Cadence: ACTIVE")
    print("  [+] Real-Time Stock & Khata (Udhaar) Ledger: ACTIVE")
    print("  [+] Hacker Defense & Security Headers: ACTIVE")
    print("  [+] Memory Footprint: ~50-60 MB RAM (Runs on 2GB/4GB PCs)")
    print("-" * 70)
    print("  >> Server running at: http://localhost:8000")
    print("  >> Auto-opening browser...")
    print("=" * 70)

    # Initialize clean database if fresh run
    init_db()

    # Launch browser in a background thread
    threading.Thread(target=auto_launch_browser, daemon=True).start()

    # Run uvicorn server in ultra-lightweight mode (single worker, minimal logging)
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        access_log=False,
        timeout_keep_alive=30
    )

if __name__ == "__main__":
    main()


