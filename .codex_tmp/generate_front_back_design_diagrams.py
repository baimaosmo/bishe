from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "系统总体设计图" / "前后台方向设计图"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_TITLE = load_font(34, True)
FONT_H1 = load_font(25, True)
FONT_BODY = load_font(20)
FONT_SMALL = load_font(17)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw, text, font, width):
    lines = []
    current = ""
    for ch in text:
        trial = current + ch
        if text_size(draw, trial, font)[0] <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def centered_text(draw, xy, text, font=FONT_BODY, fill=BLACK):
    x1, y1, x2, y2 = xy
    lines = []
    for part in text.split("\n"):
        lines.extend(wrap_text(draw, part, font, x2 - x1 - 22))
    line_h = max(text_size(draw, line, font)[1] for line in lines)
    total = len(lines) * line_h + (len(lines) - 1) * 5
    y = y1 + (y2 - y1 - total) / 2
    for line in lines:
        tw = text_size(draw, line, font)[0]
        draw.text((x1 + (x2 - x1 - tw) / 2, y), line, fill=fill, font=font)
        y += line_h + 5


def box(draw, xy, text, font=FONT_BODY):
    draw.rectangle(xy, fill=WHITE, outline=WHITE, width=2)
    centered_text(draw, xy, text, font)


def line(draw, p1, p2, width=3):
    draw.line([p1, p2], fill=WHITE, width=width)


def arrow(draw, p1, p2, width=2, dashed=False):
    if dashed:
        dashed_line(draw, p1, p2, width=width)
    else:
        draw.line([p1, p2], fill=WHITE, width=width)
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    head = 12
    tip = (x2, y2)
    left = (x2 - ux * head + px * head * 0.55, y2 - uy * head + py * head * 0.55)
    right = (x2 - ux * head - px * head * 0.55, y2 - uy * head - py * head * 0.55)
    draw.polygon([tip, left, right], fill=WHITE)


def dashed_line(draw, p1, p2, dash=12, gap=8, width=1):
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length == 0:
        return
    ux, uy = dx / length, dy / length
    pos = 0
    while pos < length:
        end = min(pos + dash, length)
        draw.line([(x1 + ux * pos, y1 + uy * pos), (x1 + ux * end, y1 + uy * end)], fill=WHITE, width=width)
        pos += dash + gap


def save(img, name):
    path = OUT_DIR / name
    img.save(path, dpi=(220, 220))
    return path


def draw_title(draw, w, title):
    tw = text_size(draw, title, FONT_TITLE)[0]
    draw.text(((w - tw) / 2, 30), title, fill=WHITE, font=FONT_TITLE)


def draw_front_module():
    w, h = 1220, 760
    img = Image.new("RGB", (w, h), BLACK)
    draw = ImageDraw.Draw(img)
    draw_title(draw, w, "前台统一用户功能模块图")
    boxes = {
        "root": (500, 95, 720, 155, "前台统一用户"),
        "auth": (55, 270, 235, 335, "注册登录"),
        "search": (285, 270, 465, 335, "图书检索"),
        "detail": (520, 270, 700, 335, "图书详情"),
        "borrow": (755, 270, 935, 335, "借阅归还"),
        "seat": (985, 270, 1165, 335, "座位预约"),
        "favorite": (55, 535, 235, 600, "图书收藏"),
        "review": (285, 535, 465, 600, "图书评价"),
        "cross": (520, 535, 700, 600, "图书漂流"),
        "ai": (755, 535, 935, 600, "AI 智能检索\n个性化推荐"),
        "profile": (985, 535, 1165, 600, "个人中心"),
    }
    cx = (boxes["root"][0] + boxes["root"][2]) / 2
    trunk_y = 220
    line(draw, (cx, boxes["root"][3]), (cx, trunk_y))
    line(draw, (145, trunk_y), (1075, trunk_y))
    for key in ["auth", "search", "detail", "borrow", "seat"]:
        x1, y1, x2, _, _ = boxes[key]
        line(draw, ((x1 + x2) / 2, trunk_y), ((x1 + x2) / 2, y1))
    line(draw, (cx, trunk_y), (cx, 485))
    line(draw, (145, 485), (1075, 485))
    for key in ["favorite", "review", "cross", "ai", "profile"]:
        x1, y1, x2, _, _ = boxes[key]
        line(draw, ((x1 + x2) / 2, 485), ((x1 + x2) / 2, y1))
    for xy in boxes.values():
        box(draw, xy[:4], xy[4], FONT_BODY)
    return save(img, "图4-3_前台统一用户功能模块图.png")


def draw_admin_module():
    w, h = 1220, 760
    img = Image.new("RGB", (w, h), BLACK)
    draw = ImageDraw.Draw(img)
    draw_title(draw, w, "后台管理员功能模块图")
    boxes = {
        "root": (500, 95, 720, 155, "后台管理员"),
        "book": (55, 270, 235, 335, "图书信息维护"),
        "user": (285, 270, 465, 335, "用户账号管理"),
        "import": (520, 270, 700, 335, "学生/教师\n批量导入"),
        "audit": (755, 270, 935, 335, "AI 评价审核"),
        "cross": (985, 270, 1165, 335, "漂流图书管理"),
        "borrow": (55, 535, 235, 600, "借阅数据查看"),
        "seat": (285, 535, 465, 600, "座位数据查看"),
        "dashboard": (520, 535, 700, 600, "数据统计看板"),
        "report": (755, 535, 935, 600, "AI 报告生成"),
        "profile": (985, 535, 1165, 600, "后台权限控制"),
    }
    cx = (boxes["root"][0] + boxes["root"][2]) / 2
    trunk_y = 220
    line(draw, (cx, boxes["root"][3]), (cx, trunk_y))
    line(draw, (145, trunk_y), (1075, trunk_y))
    for key in ["book", "user", "import", "audit", "cross"]:
        x1, y1, x2, _, _ = boxes[key]
        line(draw, ((x1 + x2) / 2, trunk_y), ((x1 + x2) / 2, y1))
    line(draw, (cx, trunk_y), (cx, 485))
    line(draw, (145, 485), (1075, 485))
    for key in ["borrow", "seat", "dashboard", "report", "profile"]:
        x1, y1, x2, _, _ = boxes[key]
        line(draw, ((x1 + x2) / 2, 485), ((x1 + x2) / 2, y1))
    for xy in boxes.values():
        box(draw, xy[:4], xy[4], FONT_BODY)
    return save(img, "图4-5_后台管理员功能模块图.png")


def sequence_diagram(filename, title, lifelines, messages):
    w = 1860
    top = 120
    header_h = 64
    step_gap = 70
    h = top + header_h + 50 + len(messages) * step_gap + 95
    img = Image.new("RGB", (w, h), BLACK)
    draw = ImageDraw.Draw(img)
    draw_title(draw, w, title)
    margin = 120
    usable = w - 2 * margin
    xs = [margin + usable * i / (len(lifelines) - 1) for i in range(len(lifelines))]
    for x, label in zip(xs, lifelines):
        head = (x - 112, top, x + 112, top + header_h)
        box(draw, head, label, FONT_BODY)
        dashed_line(draw, (x, top + header_h), (x, h - 70), width=1)
    y = top + header_h + 55
    for i, (src, dst, label, kind) in enumerate(messages, 1):
        x1, x2 = xs[src], xs[dst]
        is_return = kind == "return"
        arrow(draw, (x1, y), (x2, y), width=2, dashed=is_return)
        text = f"{i}. {label}"
        max_width = max(150, abs(x2 - x1) - 28)
        lines = wrap_text(draw, text, FONT_SMALL, max_width)
        tx = (x1 + x2) / 2
        ly = y - 24 - max(0, len(lines) - 1) * 10
        for line_text in lines:
            tw = text_size(draw, line_text, FONT_SMALL)[0]
            draw.rectangle((tx - tw / 2 - 5, ly - 1, tx + tw / 2 + 5, ly + 20), fill=WHITE)
            draw.text((tx - tw / 2, ly), line_text, fill=BLACK, font=FONT_SMALL)
            ly += 20
        y += step_gap
    return save(img, filename)


def draw_front_sequence():
    return sequence_diagram(
        "图4-4_前台统一用户业务顺序图.png",
        "前台统一用户业务顺序图",
        ["统一用户", "前台页面", "业务控制器", "业务模型", "数据库", "AI服务"],
        [
            (0, 1, "登录后进入前台页面", "call"),
            (0, 1, "发起前台业务操作", "call"),
            (1, 2, "发送前台业务请求", "call"),
            (2, 3, "校验登录状态和业务条件", "call"),
            (3, 4, "读写前台业务数据", "call"),
            (4, 3, "返回业务数据", "return"),
            (2, 5, "调用 AI 检索或推荐", "call"),
            (5, 2, "返回 AI 处理结果", "return"),
            (2, 1, "返回处理结果并渲染页面", "return"),
            (1, 0, "展示前台处理结果", "return"),
        ],
    )


def draw_admin_sequence():
    return sequence_diagram(
        "图4-6_后台管理员业务顺序图.png",
        "后台管理员业务顺序图",
        ["管理员", "后台页面", "管理控制器", "业务模型", "数据库", "AI服务"],
        [
            (0, 1, "登录后台管理页面", "call"),
            (0, 1, "选择后台管理功能", "call"),
            (1, 2, "提交后台管理请求", "call"),
            (2, 3, "校验管理员权限", "call"),
            (3, 4, "读取或更新业务数据", "call"),
            (4, 3, "返回数据处理结果", "return"),
            (2, 5, "调用 AI 审核或报告", "call"),
            (5, 2, "返回 AI 处理结果", "return"),
            (2, 3, "保存后台业务变更", "call"),
            (3, 4, "提交数据库事务", "call"),
            (2, 1, "返回后台处理结果", "return"),
            (1, 0, "展示后台处理结果", "return"),
        ],
    )


def write_text(paths):
    text = """# 前后台方向系统设计说明

## 4.3 前台统一用户功能设计

前台统一用户主要指学生和教师等读者用户。由于学生和教师在系统前台的可用功能基本一致，因此在系统设计中将其抽象为统一用户角色进行描述。统一用户登录系统后，可以进行图书检索、图书详情查看、借阅归还、座位预约、图书收藏、图书评价、图书漂流、AI 智能检索、个性化推荐和个人中心信息查看等操作。前台功能设计强调用户操作的连续性，用户从页面发起请求后，由业务控制器完成登录状态校验和业务条件判断，再通过模型层访问数据库；当业务涉及智能检索或个性化推荐时，系统调用外部 AI 服务辅助生成结果。前台统一用户功能模块如图 4-3 所示，业务处理顺序如图 4-4 所示。

![图4-3 前台统一用户功能模块图](图4-3_前台统一用户功能模块图.png)

图 4-3 前台统一用户功能模块图

![图4-4 前台统一用户业务顺序图](图4-4_前台统一用户业务顺序图.png)

图 4-4 前台统一用户业务顺序图

## 4.4 后台管理员功能设计

后台管理员主要面向系统管理人员，用于维护馆藏资源、用户账号和系统运营数据。管理员登录后台后，可以进行图书信息新增、修改和删除，管理学生、教师和普通用户账号，批量导入学生与教师信息，使用 AI 完成图书评价审核，维护漂流图书信息，查看借阅数据和座位使用数据，并生成数据统计看板和 AI 统计报告。后台功能设计强调权限控制和数据一致性，所有后台请求都需要先校验管理员身份，再根据具体业务访问模型层和数据库；涉及 AI 审核或报告生成时，由控制器组织业务数据并调用 AI 服务，最终将审核状态或报告结果返回后台页面。后台管理员功能模块如图 4-5 所示，业务处理顺序如图 4-6 所示。

![图4-5 后台管理员功能模块图](图4-5_后台管理员功能模块图.png)

图 4-5 后台管理员功能模块图

![图4-6 后台管理员业务顺序图](图4-6_后台管理员业务顺序图.png)

图 4-6 后台管理员业务顺序图
"""
    path = OUT_DIR / "前后台方向系统设计说明.md"
    path.write_text(text, encoding="utf-8")
    manifest = OUT_DIR / "图片清单.md"
    lines = ["# 前后台方向系统设计图清单", ""]
    for p in paths:
        lines.append(f"- {p.stem.replace('_', ' ')}：`{p.name}`")
    lines.append("")
    lines.append("建议在论文中按“前台统一用户模块图、前台统一用户顺序图、后台管理员模块图、后台管理员顺序图”的顺序插入。")
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return path, manifest


def main():
    paths = [
        draw_front_module(),
        draw_front_sequence(),
        draw_admin_module(),
        draw_admin_sequence(),
    ]
    text_path, manifest = write_text(paths)
    print(OUT_DIR)
    for path in paths:
        print(path.name)
    print(text_path.name)
    print(manifest.name)


if __name__ == "__main__":
    main()
