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

WIDTH = 1024
HEIGHT = 1365

CATEGORY_COLORS = {
    "创业洞察": (66, 133, 244),    # 蓝
    "成员故事": (232, 115, 74),    # 橙
    "活动预告": (52, 168, 83),     # 绿
    "幕后故事": (142, 68, 223),    # 紫
    "活动复盘": (233, 81, 127),    # 粉
}

CATEGORY_LABELS = {
    "创业洞察": "创业认知",
    "成员故事": "Builders Meet Builders",
    "活动预告": "UPCOMING EVENT",
    "幕后故事": "BEHIND THE SCENES",
    "活动复盘": "EVENT REVIEW",
}

BG_COLORS = {
    "warm_white": (252, 250, 245),
    "light_cream": (245, 240, 230),
    "muted_yellow": (245, 235, 200),
    "charcoal": (35, 35, 35),
}


def has_cjk(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text))


def create_cover(title, category="", fontsize=0, bg="warm_white"):
    from PIL import Image, ImageDraw, ImageFont

    def get_font(size, text=""):
        if has_cjk(text):
            return ImageFont.truetype(NOTO_FONT, size)
        return ImageFont.truetype(JAKARTA_FONT, size)

    def text_width(text, font):
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0]

    def wrap_title(text, font, max_chars_per_line=8):
        """按最多 max_chars_per_line 个字符换行"""
        lines = []
        for paragraph in text.split('\n'):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            while len(paragraph) > max_chars_per_line:
                lines.append(paragraph[:max_chars_per_line])
                paragraph = paragraph[max_chars_per_line:]
            if paragraph:
                lines.append(paragraph)
        return lines

    # 颜色
    bg_color = BG_COLORS.get(bg, BG_COLORS["warm_white"])
    is_dark = bg == "charcoal"
    text_color = (255, 255, 255) if is_dark else (33, 33, 33)
    subtle_color = (120, 120, 120) if not is_dark else (160, 160, 160)
    accent = CATEGORY_COLORS.get(category, (66, 133, 244))

    img = Image.new('RGB', (WIDTH, HEIGHT), bg_color)
    draw = ImageDraw.Draw(img)

    # === 顶部 10%: 栏目标签 ===
    top_area_h = int(HEIGHT * 0.10)
    label_text = CATEGORY_LABELS.get(category, "ENTROHUB")
    label_font = get_font(24, label_text)
    lw = text_width(label_text, label_font)
    label_x = (WIDTH - lw) // 2
    label_y = top_area_h // 2
    draw.text((label_x, label_y), label_text, fill=accent, font=label_font)

    # === 中间 60%: 大标题 ===
    title_area_top = int(HEIGHT * 0.12)
    title_area_bottom = int(HEIGHT * 0.70)
    title_area_h = title_area_bottom - title_area_top

    font_size = fontsize if fontsize else (80 if has_cjk(title) else 72)
    title_font = get_font(font_size, title)

    max_chars = max(4, int(WIDTH * 0.8 / font_size)) if has_cjk(title) else 20
    lines = wrap_title(title, title_font, max_chars)
    # 限制最多4行
    lines = lines[:4]

    line_height = int(font_size * 1.5)
    total_text_h = len(lines) * line_height
    start_y = title_area_top + (title_area_h - total_text_h) // 2

    for i, line in enumerate(lines):
        lw = text_width(line, title_font)
        x = (WIDTH - lw) // 2
        y = start_y + i * line_height
        draw.text((x, y), line, fill=text_color, font=title_font)

    # === 底部 30%: 视觉锚点 + 品牌 ===
    bottom_area_top = int(HEIGHT * 0.70)

    # 分隔线
    line_y = bottom_area_top + 20
    line_w = 60
    draw.line(
        [(WIDTH // 2 - line_w, line_y), (WIDTH // 2 + line_w, line_y)],
        fill=accent, width=3
    )

    # Logo
    try:
        logo = Image.open(LOGO_FILE).convert("RGBA")
        logo_size = 80
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

        logo_x = (WIDTH - logo_size) // 2
        logo_y = line_y + 40

        if is_dark:
            circle_bg = Image.new("RGBA", (logo_size + 16, logo_size + 16), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle_bg)
            circle_draw.ellipse(
                [0, 0, logo_size + 16, logo_size + 16],
                fill=(255, 255, 255, 200)
            )
            img.paste(circle_bg, (logo_x - 8, logo_y - 8), circle_bg)

        img.paste(logo, (logo_x, logo_y), logo)
    except Exception:
        logo_y = line_y + 40

    # ENTROHUB 品牌文字
    brand_font = get_font(22)
    brand_text = "ENTROHUB"
    bw = text_width(brand_text, brand_font)
    brand_x = (WIDTH - bw) // 2
    brand_y = logo_y + 90
    draw.text((brand_x, brand_y), brand_text, fill=subtle_color, font=brand_font)

    # 副标语
    tagline_font = get_font(18, "华人创业者社群 · 德国")
    tagline = "华人创业者社群 · 德国"
    tw = text_width(tagline, tagline_font)
    tag_x = (WIDTH - tw) // 2
    tag_y = brand_y + 36
    draw.text((tag_x, tag_y), tagline, fill=subtle_color, font=tagline_font)

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
            category = params.get("category", [""])[0]
            fontsize = int(params.get("fontsize", ["0"])[0] or 0)
            bg = params.get("bg", ["warm_white"])[0]

            if not title:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "title is required"}).encode())
                return

            try:
                img_bytes = create_cover(title, category, fontsize, bg)
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
