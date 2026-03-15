"""Entrohub 封面生成器 - Web 服务"""

import io
import json
import os
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BASE_DIR, "api")
FONTS_DIR = os.path.join(API_DIR, "fonts")
LOGO_FILE = os.path.join(API_DIR, "logo.png")
JAKARTA_FONT = os.path.join(FONTS_DIR, "PlusJakartaSans.ttf")
NOTO_FONT = os.path.join(FONTS_DIR, "NotoSansCJKsc-Bold.otf")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

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


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/api", "/api/"):
            params = parse_qs(parsed.query)
            title = params.get("title", [""])[0]

            if not title:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "title is required"}).encode())
                return

            try:
                img_bytes = create_cover(title)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Disposition", "inline; filename=cover.png")
                self.end_headers()
                self.wfile.write(img_bytes)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        super().do_GET()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"Server running on port {port}")
    server.serve_forever()
