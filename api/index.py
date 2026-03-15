"""Vercel Serverless Function: 生成 Entrohub 小红书封面图"""

import io
import re
import os

from flask import Flask, request, Response, send_from_directory

app = Flask(__name__, static_folder=None)

API_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(os.path.dirname(API_DIR), "public")
FONTS_DIR = os.path.join(API_DIR, "fonts")
LOGO_FILE = os.path.join(API_DIR, "logo.png")
JAKARTA_FONT = os.path.join(FONTS_DIR, "PlusJakartaSans.ttf")
NOTO_FONT = os.path.join(FONTS_DIR, "NotoSansCJKsc-Bold.otf")

BLUE_PRIMARY = (66, 133, 244)
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)
WIDTH = 1080
HEIGHT = 1080


def has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text))


def create_cover(title):
    from PIL import Image, ImageDraw, ImageFont

    def get_font(size, text=""):
        if has_cjk(text):
            return ImageFont.truetype(NOTO_FONT, size)
        return ImageFont.truetype(JAKARTA_FONT, size)

    def wrap_text(text, font, max_width):
        lines = []
        for paragraph in text.split('\n'):
            if not paragraph.strip():
                lines.append('')
                continue
            current_line = ''
            for char in paragraph:
                test_line = current_line + char
                bbox = font.getbbox(test_line)
                if bbox[2] - bbox[0] > max_width:
                    if current_line:
                        lines.append(current_line)
                    current_line = char
                else:
                    current_line = test_line
            if current_line:
                lines.append(current_line)
        return lines

    img = Image.new('RGB', (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH, 8], fill=BLUE_PRIMARY)
    draw.rectangle([60, 200, 66, HEIGHT - 200], fill=BLUE_PRIMARY)

    font_size = 72 if has_cjk(title) else 64
    title_font = get_font(font_size, title)
    lines = wrap_text(title, title_font, WIDTH - 200)

    line_height = int(font_size * 1.6)
    total_text_height = len(lines) * line_height
    start_y = (HEIGHT - total_text_height) // 2 - 40
    text_x = 100

    for i, line in enumerate(lines):
        draw.text((text_x, start_y + i * line_height), line, fill=BLACK, font=title_font)

    try:
        logo = Image.open(LOGO_FILE).convert("RGBA")
        logo = logo.resize((60, 60), Image.LANCZOS)
        img.paste(logo, (text_x, HEIGHT - 120), logo)
        brand_font = get_font(28)
        draw.text((text_x + 76, HEIGHT - 104), "Entrohub", fill=BLUE_PRIMARY, font=brand_font)
    except Exception:
        pass

    tag_font = get_font(22, "创业者社群 · 柏林")
    draw.text((text_x, HEIGHT - 60), "创业者社群 · 柏林", fill=(150, 150, 150), font=tag_font)

    buf = io.BytesIO()
    img.save(buf, "PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()


@app.route("/")
def index():
    return send_from_directory(PUBLIC_DIR, "index.html")


@app.route("/logo.png")
def logo_static():
    return send_from_directory(PUBLIC_DIR, "logo.png")


@app.route("/api", methods=["GET"])
@app.route("/api/", methods=["GET"])
def generate():
    title = request.args.get("title", "")
    if not title:
        return {"error": "title is required"}, 400
    try:
        img_bytes = create_cover(title)
        return Response(
            img_bytes,
            mimetype="image/png",
            headers={
                "Content-Disposition": "inline; filename=cover.png",
                "Cache-Control": "public, max-age=3600",
            },
        )
    except Exception as e:
        return {"error": str(e)}, 500
