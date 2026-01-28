import io

import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.http import HttpResponse

DPI = 300
QR_SIZE_MM=110
QR_MARGIN_MM=48.6
QR_TITLE_MARGIN_MM=1900
QR_TEXT_MARGIN_MM=1990


def paste_rgba_on_white(img_rgba: Image.Image) -> Image.Image:
    if img_rgba.mode != "RGBA":
        return img_rgba.convert("RGB")
    bg = Image.new("RGB", img_rgba.size, (255, 255, 255))
    bg.paste(img_rgba, mask=img_rgba.split()[3])
    return bg


def generate_qr_code(template, data, title, text, *,
                     qr_code_top=QR_MARGIN_MM,
                     title_margin=QR_TITLE_MARGIN_MM,
                     text_margin=QR_TEXT_MARGIN_MM,
                     qr_code_size=QR_SIZE_MM,
                     font_name="Orbitron-Black.ttf",
                     title_font_size=100,
                     text_font_size=250,
                     ):
    base = Image.open(settings.BASE_DIR / "assets" / "qrcode" / template).convert("RGBA")
    base = paste_rgba_on_white(base)

    W, H = base.size
    draw = ImageDraw.Draw(base)
    qr_px = mm_to_px(qr_code_size)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.ERROR_CORRECT_H,
        box_size=10,
        border=1
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_px, qr_px), Image.NEAREST)

    x = (W - qr_px) // 2
    y = mm_to_px(qr_code_top)
    base.paste(qr_img, (x, y))

    font_title = ImageFont.truetype(settings.BASE_DIR / "assets" / "fonts" / font_name, size=title_font_size)
    font_text = ImageFont.truetype(settings.BASE_DIR / "assets" / "fonts" / font_name, size=text_font_size)

    def draw_text(txt, fnt, margin):
        bbox = draw.textbbox((0, 0), txt, font=fnt)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2

        draw.text((x, margin), txt, font=fnt, fill="white", stroke_fill="black", stroke_width=3)

    draw_text(title, font_title, title_margin)
    draw_text(text, font_text, text_margin)

    base.info.clear()

    return base

def render_qr_png_file(img_file):
    with open(img_file, "rb") as f:
        return HttpResponse(f.read(), content_type="image/png")


def mm_to_px(mm: float, dpi: int = DPI) -> int:
    return int(round(mm * dpi / 25.4))


def base36encode(number, alphabet='0123456789abcdefghijklmnopqrstuvwxyz'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36

def base36decode(number):
    return int(number, 36)
