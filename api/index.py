"""Vercel Serverless Function: 生成 Entrohub 小红书封面图"""

import io
import json
import os
import re
from urllib.parse import parse_qs, urlparse

API_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(API_DIR, "fonts")
LOGO_FILE = os.path.join(API_DIR, "logo.png")
JAKARTA_FONT = os.path.join(FONTS_DIR, "PlusJakartaSans.ttf")
NOTO_FONT = os.path.join(FONTS_DIR, "NotoSansCJKsc-Bold.otf")
PUBLIC_DIR = os.path.join(os.path.dirname(API_DIR), "public")

BLUE_PRIMARY = (66, 133, 244)
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)
WIDTH = 1080
HEIGHT = 1440


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

    tag_font = get_font(22, "华人创业者社群 · 德国")
    draw.text((text_x, HEIGHT - 60), "华人创业者社群 · 德国", fill=(150, 150, 150), font=tag_font)

    buf = io.BytesIO()
    img.save(buf, "PNG", quality=95)
    buf.seek(0)
    return buf.getvalue()


def app(environ, start_response):
    """Pure WSGI app - no Flask"""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")

    if path == "/" or path == "":
        html_path = os.path.join(PUBLIC_DIR, "index.html")
        with open(html_path, "rb") as f:
            body = f.read()
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]

    if path == "/logo.png":
        logo_path = os.path.join(PUBLIC_DIR, "logo.png")
        with open(logo_path, "rb") as f:
            body = f.read()
        start_response("200 OK", [("Content-Type", "image/png")])
        return [body]

    if path in ("/api", "/api/") and method == "GET":
        qs = environ.get("QUERY_STRING", "")
        params = parse_qs(qs)
        title = params.get("title", [""])[0]

        if not title:
            body = json.dumps({"error": "title is required"}).encode()
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [body]

        try:
            img_bytes = create_cover(title)
            start_response("200 OK", [
                ("Content-Type", "image/png"),
                ("Content-Disposition", "inline; filename=cover.png"),
                ("Cache-Control", "public, max-age=3600"),
            ])
            return [img_bytes]
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode()
            start_response("500 Internal Server Error", [("Content-Type", "application/json")])
            return [body]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]
