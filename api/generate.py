"""Vercel Serverless Function: 生成 Entrohub 小红书封面图"""

import io
import re
from pathlib import Path

from flask import Flask, request, Response
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# 路径
BASE_DIR = Path(__file__).parent.parent
FONTS_DIR = BASE_DIR / "fonts"
LOGO_PATH = BASE_DIR / "public" / "logo.png"

JAKARTA_FONT = FONTS_DIR / "PlusJakartaSans.ttf"
NOTO_FONT = FONTS_DIR / "NotoSansCJKsc-Bold.otf"

# 品牌色
BLUE_PRIMARY = (66, 133, 244)
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)

WIDTH = 1080
HEIGHT = 1080


def has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text))


def get_font(size, text=""):
    if has_cjk(text):
        return ImageFont.truetype(str(NOTO_FONT), size)
    return ImageFont.truetype(str(JAKARTA_FONT), size)


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


def create_cover(title):
    img = Image.new('RGB', (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, WIDTH, 8], fill=BLUE_PRIMARY)
    draw.rectangle([60, 200, 66, HEIGHT - 200], fill=BLUE_PRIMARY)

    font_size = 72 if has_cjk(title) else 64
    title_font = get_font(font_size, title)
    max_text_width = WIDTH - 200
    lines = wrap_text(title, title_font, max_text_width)

    line_height = int(font_size * 1.6)
    total_text_height = len(lines) * line_height
    start_y = (HEIGHT - total_text_height) // 2 - 40
    text_x = 100

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        draw.text((text_x, y), line, fill=BLACK, font=title_font)

    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo = logo.resize((60, 60), Image.LANCZOS)
        img.paste(logo, (text_x, HEIGHT - 120), logo)
        brand_font = get_font(28)
        draw.text((text_x + 76, HEIGHT - 104), "Entrohub", fill=BLUE_PRIMARY, font=brand_font)
    except FileNotFoundError:
        pass

    tag_font = get_font(22, "创业者社群 · 柏林")
    draw.text((text_x, HEIGHT - 60), "创业者社群 · 柏林", fill=(150, 150, 150), font=tag_font)

    buf = io.BytesIO()
    img.save(buf, "PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()


@app.route("/api/generate", methods=["GET"])
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
