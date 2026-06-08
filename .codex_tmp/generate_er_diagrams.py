import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "实体ER图"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


FONT = load_font(30)
FONT_SMALL = load_font(24)
FONT_TITLE = load_font(34, bold=True)
FONT_CAPTION = load_font(28)


def text_size(draw, text, font):
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        return draw.textsize(text, font=font)


def center_text(draw, box, text, font=FONT, fill="black", underline=False):
    x1, y1, x2, y2 = box
    w, h = text_size(draw, text, font)
    x = x1 + (x2 - x1 - w) / 2
    y = y1 + (y2 - y1 - h) / 2 - 2
    draw.text((x, y), text, font=font, fill=fill)
    if underline:
        draw.line((x, y + h + 3, x + w, y + h + 3), fill=fill, width=2)


def rect_from_center(cx, cy, w, h):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def draw_rect(draw, cx, cy, w, h, text, font=FONT, width=2):
    box = rect_from_center(cx, cy, w, h)
    draw.rectangle(box, fill="white", outline="black", width=width)
    center_text(draw, box, text, font=font)
    return box


def draw_ellipse(draw, cx, cy, w, h, text, primary=False):
    box = rect_from_center(cx, cy, w, h)
    draw.ellipse(box, fill="white", outline="black", width=2)
    center_text(draw, box, text, font=FONT_SMALL, underline=primary)
    return box


def draw_diamond(draw, cx, cy, w, h, text):
    points = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
    draw.polygon(points, outline="black", fill="white")
    draw.line(points + [points[0]], fill="black", width=2)
    center_text(draw, rect_from_center(cx, cy, w * 0.9, h * 0.75), text, font=FONT_SMALL)
    return points


def label(draw, x, y, text, font=FONT_SMALL):
    w, h = text_size(draw, text, font)
    draw.rectangle((x - 4, y - 2, x + w + 4, y + h + 2), fill="white")
    draw.text((x, y), text, font=font, fill="black")


def entity_attribute_diagram(filename, entity, attrs, caption):
    width, height = 1400, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    center = (width / 2, height / 2)

    count = len(attrs)
    radius_x = 470
    radius_y = 285
    start_angle = -90
    oval_boxes = []
    for index, attr in enumerate(attrs):
        angle = math.radians(start_angle + index * 360 / count)
        cx = center[0] + math.cos(angle) * radius_x
        cy = center[1] + math.sin(angle) * radius_y
        text = attr["name"]
        oval_w = max(190, len(text) * 15 + 80)
        oval_h = 76
        draw.line((center[0], center[1], cx, cy), fill="black", width=2)
        oval_boxes.append((cx, cy, oval_w, oval_h, text, attr.get("pk", False)))

    for cx, cy, oval_w, oval_h, text, primary in oval_boxes:
        draw_ellipse(draw, cx, cy, oval_w, oval_h, text, primary=primary)

    draw_rect(draw, center[0], center[1], 260, 90, entity, font=FONT)

    center_text(draw, (0, height - 72, width, height - 20), caption, font=FONT_CAPTION)
    image.save(OUT_DIR / filename)


def draw_connection(draw, start, end, rel, start_card="", end_card=""):
    sx, sy = start
    ex, ey = end
    mx, my = (sx + ex) / 2, (sy + ey) / 2
    draw.line((sx, sy, mx, my), fill="black", width=2)
    draw.line((mx, my, ex, ey), fill="black", width=2)
    draw_diamond(draw, mx, my, 126, 72, rel)
    if start_card:
        label(draw, (sx + mx) / 2, (sy + my) / 2 - 28, start_card)
    if end_card:
        label(draw, (mx + ex) / 2, (my + ey) / 2 - 28, end_card)


def draw_manual_relation(draw, start, diamond, end, rel, start_card="", end_card=""):
    sx, sy = start
    dx, dy = diamond
    ex, ey = end
    draw.line((sx, sy, dx, dy), fill="black", width=2)
    draw.line((dx, dy, ex, ey), fill="black", width=2)
    draw_diamond(draw, dx, dy, 130, 76, rel)
    if start_card:
        label(draw, sx + (dx - sx) * 0.28, sy + (dy - sy) * 0.28 - 28, start_card)
    if end_card:
        label(draw, dx + (ex - dx) * 0.72, dy + (ey - dy) * 0.72 - 28, end_card)


def system_er_diagram():
    width, height = 1700, 1280
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    er_font = load_font(21)
    er_font_small = load_font(18)
    er_font_caption = load_font(26)

    def multiline_center(box, lines, fonts):
        x1, y1, x2, y2 = box
        metrics = [text_size(draw, line, font) for line, font in zip(lines, fonts)]
        total_h = sum(h for _, h in metrics) + 6 * (len(lines) - 1)
        y = y1 + (y2 - y1 - total_h) / 2
        for (line, font), (w, h) in zip(zip(lines, fonts), metrics):
            draw.text((x1 + (x2 - x1 - w) / 2, y), line, font=font, fill="black")
            y += h + 6

    def card(cx, cy, w, h, title, subtitle=""):
        box = rect_from_center(cx, cy, w, h)
        draw.rectangle(box, fill="white", outline="black", width=2)
        if subtitle:
            multiline_center(box, [title, subtitle], [er_font, er_font_small])
        else:
            center_text(draw, box, title, font=er_font)
        return box

    def diamond(cx, cy, w, h, text, rotate=False):
        points = [(cx, cy - h / 2), (cx + w / 2, cy), (cx, cy + h / 2), (cx - w / 2, cy)]
        draw.polygon(points, fill="white", outline="black")
        draw.line(points + [points[0]], fill="black", width=2)
        center_text(draw, rect_from_center(cx, cy, w * 0.92, h * 0.75), text, font=er_font_small, fill="black")

    def cardinality(x, y, text):
        w, h = text_size(draw, text, er_font_small)
        draw.rectangle((x - 7, y - 4, x + w + 7, y + h + 4), fill="white")
        draw.text((x, y), text, font=er_font_small, fill="black")

    def polyline(points, width=2):
        for a, b in zip(points, points[1:]):
            draw.line((a[0], a[1], b[0], b[1]), fill="black", width=width)

    def relation(points_before, rel, points_after, name, s_card, e_card, s_label_pos, e_label_pos, rel_size=(82, 54)):
        polyline(points_before + [rel])
        polyline([rel] + points_after)
        diamond(rel[0], rel[1], rel_size[0], rel_size[1], name)
        cardinality(s_label_pos[0], s_label_pos[1], s_card)
        cardinality(e_label_pos[0], e_label_pos[1], e_card)

    entity_defs = {
        "accounts": (180, 520, 175, 52, "accounts"),
        "users": (80, 315, 145, 50, "users"),
        "students": (280, 315, 155, 50, "students"),
        "teachers": (180, 200, 155, 50, "teachers"),
        "admins": (1280, 500, 155, 50, "admins"),

        "borrow_records": (555, 210, 220, 50, "borrow_records"),
        "book_favorites": (555, 350, 220, 50, "book_favorites"),
        "book_reviews": (555, 490, 220, 50, "book_reviews"),
        "seat_reservations": (555, 665, 245, 50, "seat_reservations"),

        "publishers": (1005, 105, 180, 50, "publishers"),
        "books": (1005, 350, 160, 50, "books"),
        "seats": (1005, 665, 150, 50, "seats"),

        "drift_books": (555, 970, 205, 50, "drift_books"),
        "drift_requests": (1005, 970, 220, 50, "drift_requests"),
    }

    # users、students、teachers 通过 ISA 泛化关系归并到 accounts，业务统一连接 accounts。
    isa_center = (180, 375)
    polyline([(180, 225), (180, 353)])
    polyline([(152, 375), (80, 340)])
    polyline([(208, 375), (280, 340)])
    polyline([(180, 397), (180, 494)])
    diamond(isa_center[0], isa_center[1], 70, 46, "ISA")

    account_bus_x = 305
    draw.line((account_bus_x, 210, account_bus_x, 1105), fill="black", width=2)
    polyline([(268, 520), (account_bus_x, 520)])

    left_relations = [
        (210, "借阅", 445),
        (350, "收藏", 445),
        (490, "评价", 445),
        (665, "预约", 435),
        (970, "发布", 450),
    ]
    for y, name, entity_left in left_relations:
        relation([(account_bus_x, y)], (382, y), [(entity_left, y)], name, "1", "N", (324, y - 33), (418, y - 33), rel_size=(68, 44))

    # 记录实体连接到资源实体。
    relation([(665, 210)], (765, 210), [(900, 210), (900, 325), (925, 325)], "记录", "N", "1", (692, 178), (910, 292), rel_size=(68, 44))
    relation([(665, 350)], (765, 350), [(925, 350)], "收藏", "N", "1", (692, 318), (910, 318), rel_size=(68, 44))
    relation([(665, 490)], (765, 490), [(900, 490), (900, 375), (925, 375)], "评价", "N", "1", (692, 458), (910, 405), rel_size=(68, 44))
    relation([(1005, 130)], (1005, 232), [(1005, 325)], "出版", "1", "N", (1022, 176), (1022, 285), rel_size=(68, 44))
    relation([(678, 665)], (770, 665), [(930, 665)], "使用", "N", "1", (700, 633), (905, 633), rel_size=(68, 44))

    # 漂流图书、漂流申请以及申请人之间的关系。
    relation([(658, 970)], (770, 970), [(895, 970)], "产生", "1", "N", (690, 938), (875, 938), rel_size=(68, 44))
    relation([(account_bus_x, 1105), (740, 1105)], (820, 1105), [(1005, 995)], "申请", "1", "N", (330, 1068), (1020, 1025), rel_size=(68, 44))

    # 管理员是 users 表中 role=admin 的账号角色，图中保留核心管理关系，避免管理线过度交叉。
    relation([(1202, 485)], (1120, 455), [(1085, 375)], "维护", "1", "N", (1160, 450), (1102, 395), rel_size=(68, 44))
    relation([(1202, 500), (880, 500)], (760, 525), [(665, 502)], "审核", "1", "N", (1170, 468), (690, 525), rel_size=(68, 44))
    relation([(1202, 520), (1110, 610)], (1180, 665), [(1080, 665)], "管理", "1", "N", (1170, 540), (1105, 633), rel_size=(68, 44))

    # 最后绘制实体，盖住穿过实体内部的辅助线，使图面更接近论文示例风格。
    for cx, cy, w, h, title in entity_defs.values():
        card(cx, cy, w, h, title)

    note = "注：accounts 为账号抽象实体，users、students、teachers 通过 ISA 关系归并到 accounts；admins 表示 users 表中 role=admin 的管理员角色，负责账号管理、图书维护、评价审核和座位管理等操作。"
    draw.text((55, height - 104), note, font=er_font_small, fill="black")
    center_text(draw, (0, height - 58, width, height - 18), "图 4-13 系统总体 E-R 图", font=er_font_caption)
    image.save(OUT_DIR / "13_系统总体ER图.png")


ENTITY_DEFINITIONS = [
    ("01_学生实体属性图.png", "students", [
        {"name": "id", "pk": True}, {"name": "student_no"}, {"name": "name"}, {"name": "gender"},
        {"name": "major"}, {"name": "department"}, {"name": "password_hash"}, {"name": "avatar"},
    ], "图 4-1 学生实体属性图"),
    ("02_教师实体属性图.png", "teachers", [
        {"name": "id", "pk": True}, {"name": "job_no"}, {"name": "name"}, {"name": "gender"},
        {"name": "major"}, {"name": "department"}, {"name": "password_hash"}, {"name": "avatar"},
    ], "图 4-2 教师实体属性图"),
    ("03_管理员用户实体属性图.png", "users", [
        {"name": "id", "pk": True}, {"name": "username"}, {"name": "email"}, {"name": "password_hash"},
        {"name": "role"}, {"name": "avatar"},
    ], "图 4-3 管理员用户实体属性图"),
    ("04_图书实体属性图.png", "books", [
        {"name": "id", "pk": True}, {"name": "title"}, {"name": "author"}, {"name": "publisher"},
        {"name": "isbn"}, {"name": "category"}, {"name": "floor"}, {"name": "area"},
        {"name": "shelf"}, {"name": "status"}, {"name": "cover_image"}, {"name": "add_time"},
    ], "图 4-4 图书实体属性图"),
    ("05_出版社实体属性图.png", "publishers", [
        {"name": "id", "pk": True}, {"name": "name"}, {"name": "created_at"},
    ], "图 4-5 出版社实体属性图"),
    ("06_借阅记录实体属性图.png", "borrow_records", [
        {"name": "id", "pk": True}, {"name": "user_id"}, {"name": "student_id"}, {"name": "teacher_id"},
        {"name": "book_id"}, {"name": "borrow_time"}, {"name": "return_time"}, {"name": "status"},
    ], "图 4-6 借阅记录实体属性图"),
    ("07_座位实体属性图.png", "seats", [
        {"name": "id", "pk": True}, {"name": "floor"}, {"name": "area"}, {"name": "seat_number"},
        {"name": "has_power"}, {"name": "status"},
    ], "图 4-7 座位实体属性图"),
    ("08_座位预约实体属性图.png", "seat_reservations", [
        {"name": "id", "pk": True}, {"name": "user_id"}, {"name": "student_id"}, {"name": "teacher_id"},
        {"name": "seat_id"}, {"name": "start_time"}, {"name": "end_time"}, {"name": "status"},
    ], "图 4-8 座位预约实体属性图"),
    ("09_图书收藏实体属性图.png", "book_favorites", [
        {"name": "id", "pk": True}, {"name": "book_id"}, {"name": "user_id"}, {"name": "student_id"},
        {"name": "teacher_id"}, {"name": "created_at"},
    ], "图 4-9 图书收藏实体属性图"),
    ("10_图书评价实体属性图.png", "book_reviews", [
        {"name": "id", "pk": True}, {"name": "book_id"}, {"name": "user_id"}, {"name": "student_id"},
        {"name": "teacher_id"}, {"name": "rating"}, {"name": "content"}, {"name": "status"}, {"name": "created_at"},
    ], "图 4-10 图书评价实体属性图"),
    ("11_漂流图书实体属性图.png", "drift_books", [
        {"name": "id", "pk": True}, {"name": "title"}, {"name": "course_related"}, {"name": "condition"},
        {"name": "description"}, {"name": "status"}, {"name": "publish_time"}, {"name": "provider_id"}, {"name": "receiver_id"},
    ], "图 4-11 漂流图书实体属性图"),
    ("12_漂流申请实体属性图.png", "drift_requests", [
        {"name": "id", "pk": True}, {"name": "book_id"}, {"name": "message"}, {"name": "status"},
        {"name": "create_time"}, {"name": "receiver_id"},
    ], "图 4-12 漂流申请实体属性图"),
]


def write_index():
    lines = [
        "# 实体属性图与 E-R 图",
        "",
        "本目录图片按论文图号命名，可直接插入论文。字段名称依据 `app/models.py` 中的 SQLAlchemy 模型整理。",
        "",
    ]
    for filename, _, _, caption in ENTITY_DEFINITIONS:
        lines.append(f"- {caption}：`{filename}`")
    lines.append("- 图 4-13 系统总体 E-R 图：`13_系统总体ER图.png`")
    lines.append("")
    lines.append("说明：总体 E-R 图保留属性图中的全部实体，`users`、`students`、`teachers` 三类账号均可参与读者业务。")
    (OUT_DIR / "图片清单.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    for item in ENTITY_DEFINITIONS:
        entity_attribute_diagram(*item)
    system_er_diagram()
    write_index()
    print(f"generated {len(ENTITY_DEFINITIONS) + 1} images in {OUT_DIR}")


if __name__ == "__main__":
    main()
