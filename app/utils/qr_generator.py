import qrcode
import io
import base64


def generate_qr_code(data: str) -> str:
    """
    Generates a QR code for the given data (e.g. a token number or a URL)
    and returns it as a base64-encoded PNG string, ready to embed directly
    in an <img> tag via src="data:image/png;base64,...".
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    return img_base64