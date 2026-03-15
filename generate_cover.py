#!/usr/bin/env python3
"""
Entrohub 小红书封面图生成器

用法:
    python generate_cover.py "你的标题文字"
    python generate_cover.py "你的标题文字" --style dark
    python generate_cover.py "你的标题文字" --style gradient
    python generate_cover.py "你的标题文字" --output cover.png
"""

import argparse
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 路径
SCRIPT_DIR = Path(__file__).parent
LOGO_PATH = SCRIPT_DIR / "logo.png"
JAKARTA_FONT = Path.home() / "Library/Fonts/PlusJakartaSans[wght].ttf"
PINGFANG_FONT = "/System/Library/Fonts/PingFang.ttc"

# 品牌色
BLUE_PRIMARY = (66, 133, 244)       # #4285F4
BLUE_DARK = (30, 64, 175)           # #1E40AF
ORANGE_ACCENT = (232, 115, 74)      # #E8734A
WHITE = (255, 255, 255)
BLACK = (33, 33, 33)                # #212121
LIGHT_GRAY = (245, 245, 250)        # #F5F5FA

# 尺寸
WIDTH = 1080
HEIGHT = 1080


def has_cjk(text: str) -> bool:
    """检测文本是否包含中日韩字符"""
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff]', text))


def get_font(size: int, text: str = "") -> ImageFont.FreeTypeFont:
    """根据文本内容选择字体：中文用苹方，英文用 Jakarta"""
    if has_cjk(text):
        return ImageFont.truetype(PINGFANG_FONT, size)
    return ImageFont.truetype(str(JAKARTA_FONT), size)


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """手动换行，支持中英文混排"""
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


def create_cover(
    title: str,
    style: str = "light",
    output_path: str | None = None,
) -> str:
    """生成封面图"""

    img = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # 背景
    if style == "dark":
        bg_color = BLUE_DARK
        text_color = WHITE
        subtitle_color = (180, 200, 255)
    elif style == "gradient":
        # 蓝色渐变
        for y in range(HEIGHT):
            r = int(BLUE_PRIMARY[0] + (BLUE_DARK[0] - BLUE_PRIMARY[0]) * y / HEIGHT)
            g = int(BLUE_PRIMARY[1] + (BLUE_DARK[1] - BLUE_PRIMARY[1]) * y / HEIGHT)
            b = int(BLUE_PRIMARY[2] + (BLUE_DARK[2] - BLUE_PRIMARY[2]) * y / HEIGHT)
            draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
        text_color = WHITE
        subtitle_color = (200, 220, 255)
    else:  # light
        bg_color = WHITE
        text_color = BLACK
        subtitle_color = BLUE_PRIMARY
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=bg_color)

    if style in ("dark",):
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=bg_color)

    # 顶部装饰条
    if style == "light":
        draw.rectangle([0, 0, WIDTH, 8], fill=BLUE_PRIMARY)

    # 左侧装饰线
    if style == "light":
        draw.rectangle([60, 200, 66, HEIGHT - 200], fill=BLUE_PRIMARY)

    # 标题文字
    font_size = 72 if has_cjk(title) else 64
    title_font = get_font(font_size, title)
    max_text_width = WIDTH - 200 if style == "light" else WIDTH - 160

    lines = wrap_text(title, title_font, max_text_width)

    # 计算文字总高度，垂直居中
    line_height = int(font_size * 1.6)
    total_text_height = len(lines) * line_height
    start_y = (HEIGHT - total_text_height) // 2 - 40

    text_x = 100 if style == "light" else 80

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        draw.text((text_x, y), line, fill=text_color, font=title_font)

    # 底部: logo + 品牌名
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_size = 60
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)

        logo_y = HEIGHT - 120
        logo_x = text_x

        # 如果背景不是白色，给 logo 加白色圆形底
        if style != "light":
            circle_bg = Image.new("RGBA", (logo_size + 10, logo_size + 10), (0, 0, 0, 0))
            circle_draw = ImageDraw.Draw(circle_bg)
            circle_draw.ellipse([0, 0, logo_size + 10, logo_size + 10], fill=(255, 255, 255, 230))
            img.paste(circle_bg, (logo_x - 5, logo_y - 5), circle_bg)

        img.paste(logo, (logo_x, logo_y), logo)

        # 品牌名
        brand_font = get_font(28)
        draw.text(
            (logo_x + logo_size + 16, logo_y + 16),
            "Entrohub",
            fill=subtitle_color if style != "light" else BLUE_PRIMARY,
            font=brand_font,
        )
    except FileNotFoundError:
        pass

    # 底部标签线
    tag_font = get_font(22)
    tag_text = "创业者社群 · 柏林"
    if has_cjk(tag_text):
        tag_font = get_font(22, tag_text)
    draw.text(
        (text_x, HEIGHT - 60),
        tag_text,
        fill=subtitle_color if style != "light" else (150, 150, 150),
        font=tag_font,
    )

    # 保存
    if output_path is None:
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', title)[:30]
        output_path = str(SCRIPT_DIR / f"output_{safe_name}.png")

    img.save(output_path, "PNG", quality=95)
    print(f"封面已生成: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Entrohub 小红书封面生成器")
    parser.add_argument("title", help="封面标题文字")
    parser.add_argument(
        "--style",
        choices=["light", "dark", "gradient"],
        default="light",
        help="封面风格 (默认: light)",
    )
    parser.add_argument("--output", "-o", help="输出文件路径")

    args = parser.parse_args()
    create_cover(args.title, args.style, args.output)


if __name__ == "__main__":
    main()
