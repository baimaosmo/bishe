from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "app" / "static" / "uploads" / "book_covers"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\simsun.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


TITLE_FONT = font(34, True)
SUB_FONT = font(18)
SMALL_FONT = font(15)


COVERS = [
    ("python.png", "Python\n程序设计基础", "编程入门", (37, 99, 235), (255, 211, 67)),
    ("database.png", "数据库\n系统概论", "数据管理", (24, 92, 84), (135, 206, 180)),
    ("se.png", "软件工程\n导论", "系统开发", (86, 64, 162), (191, 165, 255)),
    ("ai.png", "人工智能\n导论", "智能技术", (26, 38, 87), (94, 234, 212)),
    ("web.png", "Web开发\n实战", "前后端应用", (174, 70, 44), (255, 185, 120)),
    ("ds.png", "数据结构\n与算法", "算法思维", (63, 91, 47), (176, 218, 132)),
    ("ml.png", "机器学习\n实践", "模型训练", (83, 44, 121), (246, 167, 255)),
    ("is.png", "信息系统\n分析与设计", "系统建模", (64, 76, 96), (180, 205, 230)),
]


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def center_text(draw, lines, y, fnt, fill):
    for line in lines:
        tw, th = text_size(draw, line, fnt)
        draw.text(((360 - tw) / 2, y), line, font=fnt, fill=fill)
        y += th + 10
    return y


def draw_cover(filename, title, subtitle, base, accent):
    img = Image.new("RGB", (360, 520), base)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, 360, 520), fill=base)
    draw.rectangle((24, 24, 336, 496), outline=(245, 245, 245), width=3)
    draw.rectangle((42, 42, 318, 478), outline=accent, width=2)

    draw.polygon([(0, 0), (210, 0), (0, 160)], fill=tuple(min(255, c + 28) for c in base))
    draw.polygon([(360, 520), (145, 520), (360, 360)], fill=tuple(max(0, c - 35) for c in base))
    draw.rectangle((65, 115, 295, 125), fill=accent)
    draw.rectangle((80, 390, 280, 398), fill=accent)

    title_lines = title.split("\n")
    center_text(draw, title_lines, 165, TITLE_FONT, (255, 255, 255))

    sw, sh = text_size(draw, subtitle, SUB_FONT)
    draw.rounded_rectangle((88, 315, 272, 355), radius=8, fill=(255, 255, 255))
    draw.text(((360 - sw) / 2, 323), subtitle, font=SUB_FONT, fill=base)

    footer = "智慧图书馆馆藏"
    fw, fh = text_size(draw, footer, SMALL_FONT)
    draw.text(((360 - fw) / 2, 438), footer, font=SMALL_FONT, fill=(245, 245, 245))

    img.save(OUT_DIR / filename)


def main():
    for cover in COVERS:
        draw_cover(*cover)
    print(OUT_DIR)
    for filename, *_ in COVERS:
        print(filename)


if __name__ == "__main__":
    main()
