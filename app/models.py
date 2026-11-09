from pydantic import BaseModel, Field
from typing import List, Optional

class BusinessProfileUpdate(BaseModel):
    name: str
    tagline: Optional[str] = ""
    business_type: Optional[str] = "shop"
    owner_name: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    address: Optional[str] = ""
    state_code: Optional[str] = "08"
    state_name: Optional[str] = "Rajasthan"
    gstin: Optional[str] = ""
    upi_id: str
    upi_name: Optional[str] = ""
    welcome_msg: Optional[str] = ""

class InventoryItemCreate(BaseModel):
    name: str
    sku: Optional[str] = ""
    category: Optional[str] = "General"
    unit: Optional[str] = "pcs"
    cost_price: float = 0.0
    selling_price: float
    stock_qty: float = 0.0
    min_threshold: float = 5.0
    hsn_code: Optional[str] = ""
    gst_rate: float = 18.0
    batch_no: Optional[str] = ""
    expiry_date: Optional[str] = ""

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None
    stock_qty: Optional[float] = None
    min_threshold: Optional[float] = None
    hsn_code: Optional[str] = None
    gst_rate: Optional[float] = None
    batch_no: Optional[str] = None
    expiry_date: Optional[str] = None
    is_active: Optional[int] = None

class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    business_name: Optional[str] = ""
    gstin: Optional[str] = ""
    address: Optional[str] = ""
    balance_due: float = 0.0
    notes: Optional[str] = ""

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    business_name: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    balance_due: Optional[float] = None
    notes: Optional[str] = None

class InvoiceItemInput(BaseModel):
    item_id: Optional[int] = None
    item_name: str
    hsn_code: Optional[str] = ""
    quantity: float
    unit: str = "pcs"
    unit_price: float
    gst_rate: float = 18.0

class InvoiceCreateRequest(BaseModel):
    customer_id: Optional[int] = None
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = ""
    customer_gstin: Optional[str] = ""
    items: List[InvoiceItemInput]
    is_interstate: bool = False  # If True, charge IGST; If False, charge CGST + SGST
    due_days: int = 7
    notes: Optional[str] = ""

class PaymentRecordRequest(BaseModel):
    amount_paid: float
    payment_mode: str = "UPI"  # "UPI", "CASH", "NETBANKING", "CHEQUE"
    notes: Optional[str] = ""

class WhatsAppIncomingMessage(BaseModel):
    phone: str
    message: str
    sender_name: Optional[str] = "Customer"

class QuickFollowupCreate(BaseModel):
    customer_name: str
    phone: str
    followup_type: str = "PAYMENT_REMINDER"
    message_text: str
    customer_id: Optional[int] = None
    invoice_id: Optional[int] = None

class AppointmentCreateRequest(BaseModel):
    patient_name: str
    phone: str
    doctor_name: str
    appointment_date: str
    time_slot: str
    service_type: str = "Consultation"
    notes: Optional[str] = ""

