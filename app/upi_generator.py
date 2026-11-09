import urllib.parse
import io
import qrcode
import qrcode.image.svg

def generate_upi_link(
    upi_id: str,
    payee_name: str,
    amount: float,
    transaction_note: str = "",
    transaction_ref: str = ""
) -> str:
    """
    Generates a standardized NPCI UPI Deep Link conforming to Indian Banking specs.
    Works seamlessly with BHIM, PhonePe, Google Pay, Paytm, CRED, AmazonPay, and Mobile Banking apps.
    """
    params = {
        "pa": upi_id.strip(),
        "pn": payee_name.strip(),
        "am": f"{amount:.2f}",
        "cu": "INR"
    }
    if transaction_note:
        params["tn"] = transaction_note.strip()
    if transaction_ref:
        params["tr"] = transaction_ref.strip()
        
    query_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    return f"upi://pay?{query_string}"


def generate_upi_qr_svg(upi_link: str) -> str:
    """
    Generates an ultra-crisp, scalable SVG QR Code for printing or web display.
    Requires ZERO external C/binary dependencies (pure SVG path generation).
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
        image_factory=qrcode.image.svg.SvgPathImage
    )
    qr.add_data(upi_link)
    qr.make(fit=True)
    
    img = qr.make_image(attrib={'class': 'upi-qr-svg'})
    stream = io.BytesIO()
    img.save(stream)
    return stream.getvalue().decode("utf-8")


def format_inr(amount: float) -> str:
    """
    Formats a number into standard Indian numbering format (e.g. 1,23,456.75).
    """
    s = f"{amount:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]
    
    if len(integer_part) <= 3:
        formatted = integer_part
    else:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted = ",".join(groups) + "," + last3
        
    return f"₹{formatted}.{decimal_part}"
