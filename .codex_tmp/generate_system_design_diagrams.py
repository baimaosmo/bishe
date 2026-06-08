from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "系统总体设计图"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simkai.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT_TITLE = font(34, True)
FONT_H1 = font(25, True)
FONT_H2 = font(22, True)
FONT_BODY = font(20)
FONT_SMALL = font(17)
FONT_TINY = font(15)

BLACK = (20, 20, 20)
GRAY = (92, 92, 92)
LIGHT = (246, 246, 246)
MID = (232, 232, 232)
WHITE = (255, 255, 255)


def new_canvas(w, h, title=None):
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    if title:
        tw = text_size(d, title, FONT_TITLE)[0]
        d.text(((w - tw) / 2, 34), title, fill=BLACK, font=FONT_TITLE)
    return img, d


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw, text, fnt, max_width):
    if "\n" in text:
        lines = []
        for part in text.split("\n"):
            lines.extend(wrap_text(draw, part, fnt, max_width))
        return lines
    lines, current = [], ""
    for ch in text:
        trial = current + ch
        if text_size(draw, trial, fnt)[0] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return lines


def centered_text(draw, box, text, fnt=FONT_BODY, fill=BLACK, line_gap=5):
    x1, y1, x2, y2 = box
    lines = wrap_text(draw, text, fnt, max(10, x2 - x1 - 22))
    heights = [text_size(draw, line, fnt)[1] for line in lines]
    total = sum(heights) + line_gap * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for line, th in zip(lines, heights):
        tw = text_size(draw, line, fnt)[0]
        draw.text((x1 + (x2 - x1 - tw) / 2, y), line, font=fnt, fill=fill)
        y += th + line_gap


def box(draw, xy, text, fnt=FONT_BODY, fill=WHITE, outline=BLACK, width=2, radius=0):
    if radius:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    else:
        draw.rectangle(xy, fill=fill, outline=outline, width=width)
    centered_text(draw, xy, text, fnt)


def line(draw, p1, p2, width=2, fill=BLACK):
    draw.line([p1, p2], fill=fill, width=width)


def arrow(draw, p1, p2, width=2, fill=BLACK, head=12):
    if width > 0:
        draw.line([p1, p2], fill=fill, width=width)
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    tip = (x2, y2)
    left = (x2 - ux * head + px * head * 0.55, y2 - uy * head + py * head * 0.55)
    right = (x2 - ux * head - px * head * 0.55, y2 - uy * head - py * head * 0.55)
    draw.polygon([tip, left, right], fill=fill)


def dashed_line(draw, p1, p2, dash=10, gap=8, fill=GRAY, width=1):
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
        draw.line([(x1 + ux * pos, y1 + uy * pos), (x1 + ux * end, y1 + uy * end)], fill=fill, width=width)
        pos += dash + gap


def save(img, name):
    path = OUT_DIR / name
    img.save(path, dpi=(220, 220))
    return path


def dark_box(draw, xy, text, fnt=FONT_BODY):
    draw.rectangle(xy, fill=WHITE, outline=WHITE, width=2)
    centered_text(draw, xy, text, fnt, fill=BLACK)


def dark_line(draw, p1, p2, width=3):
    draw.line([p1, p2], fill=WHITE, width=width)


def draw_flow_module(filename, title, boxes, edges, w=980, h=620):
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    title_w = text_size(d, title, FONT_H1)[0]
    d.text(((w - title_w) / 2, 28), title, fill=WHITE, font=FONT_H1)

    positioned = {}
    for key, label, xy in boxes:
        positioned[key] = xy

    for src, dst, mode in edges:
        sx1, sy1, sx2, sy2 = positioned[src]
        dx1, dy1, dx2, dy2 = positioned[dst]
        if mode == "down":
            x = (sx1 + sx2) / 2
            dark_line(d, (x, sy2), (x, dy1))
        elif mode == "right":
            y = (sy1 + sy2) / 2
            dark_line(d, (sx2, y), (dx1, y))
        elif mode == "left":
            y = (sy1 + sy2) / 2
            dark_line(d, (sx1, y), (dx2, y))
        elif mode == "elbow_right_down":
            x1 = (sx1 + sx2) / 2
            y1 = sy2
            x2 = (dx1 + dx2) / 2
            y2 = dy1
            mid_y = (y1 + y2) / 2
            dark_line(d, (x1, y1), (x1, mid_y))
            dark_line(d, (x1, mid_y), (x2, mid_y))
            dark_line(d, (x2, mid_y), (x2, y2))
        elif mode == "elbow_down_right":
            x1 = (sx1 + sx2) / 2
            y1 = sy2
            x2 = dx1
            y2 = (dy1 + dy2) / 2
            dark_line(d, (x1, y1), (x1, y2))
            dark_line(d, (x1, y2), (x2, y2))
        elif mode == "elbow_down_left":
            x1 = (sx1 + sx2) / 2
            y1 = sy2
            x2 = dx2
            y2 = (dy1 + dy2) / 2
            dark_line(d, (x1, y1), (x1, y2))
            dark_line(d, (x1, y2), (x2, y2))

    for key, label, xy in boxes:
        dark_box(d, xy, label, FONT_BODY)
    return save(img, filename)


def draw_function_structure():
    w, h = 1800, 1120
    img, d = new_canvas(w, h, "智慧图书馆管理系统功能结构图")

    root = (670, 95, 1130, 155)
    box(d, root, "智慧图书馆管理系统", FONT_H1, fill=LIGHT, width=3)
    stem_y = 225
    line(d, ((root[0] + root[2]) / 2, root[3]), ((root[0] + root[2]) / 2, stem_y), width=3)

    groups = [
        ("读者端功能", ["注册登录", "图书检索与详情", "借阅归还", "座位预约", "收藏与评价", "图书漂流", "个性化推荐", "AI 智能检索", "个人中心"]),
        ("管理端功能", ["图书信息维护", "用户账号管理", "学生/教师批量导入", "AI 评价审核", "漂流图书管理", "借阅与座位数据查看", "数据看板与报告"]),
        ("系统支撑功能", ["多角色权限控制", "Session 状态保持", "SQLAlchemy 数据访问", "文件上传管理", "座位超时释放", "外部 AI 服务调用"]),
    ]
    col_w = 430
    gap = 110
    start_x = (w - (3 * col_w + 2 * gap)) / 2
    header_y = 260
    header_h = 62
    item_h = 54
    item_gap = 18
    header_centers = []
    for idx, (title, items) in enumerate(groups):
        x = start_x + idx * (col_w + gap)
        header = (x, header_y, x + col_w, header_y + header_h)
        header_centers.append((x + col_w / 2, header_y))
        box(d, header, title, FONT_H2, fill=MID, width=3)
        trunk_x = x + col_w / 2
        trunk_top = header[3]
        trunk_bottom = trunk_top + 24 + len(items) * (item_h + item_gap) - item_gap
        line(d, (trunk_x, trunk_top), (trunk_x, trunk_bottom), width=2)
        y = trunk_top + 24
        for item in items:
            item_box = (x + 60, y, x + col_w - 20, y + item_h)
            line(d, (trunk_x, y + item_h / 2), (item_box[0], y + item_h / 2), width=2)
            box(d, item_box, item, FONT_BODY, fill=WHITE, width=2)
            y += item_h + item_gap

    left = header_centers[0][0]
    right = header_centers[-1][0]
    line(d, (left, stem_y), (right, stem_y), width=3)
    for cx, cy in header_centers:
        line(d, (cx, stem_y), (cx, cy), width=3)

    return save(img, "图4-1_系统功能结构图.png")


def draw_module_structure():
    w, h = 1800, 1260
    img, d = new_canvas(w, h, "智慧图书馆管理系统模块结构图")

    left_x, right_x = 150, 1380
    y0 = 115
    layer_h = 140
    gap = 48
    layers = [
        ("表现层", "浏览器页面\nJinja2 模板 / HTML / CSS / JavaScript"),
        ("控制层", "Flask 蓝图路由\nmain / auth / books / seats / crossing / ai"),
        ("业务层", "认证授权  图书管理  借阅归还  座位预约\n收藏评价  图书漂流  推荐服务  统计报告"),
        ("数据访问层", "SQLAlchemy ORM\nUser / Student / Teacher / Book / BorrowRecord / Seat / Review 等模型"),
        ("数据存储层", "MySQL 数据库\n用户表、图书表、借阅表、座位表、评价表、漂流表"),
    ]
    boxes = []
    for i, (name, content) in enumerate(layers):
        y = y0 + i * (layer_h + gap)
        name_box = (left_x, y, left_x + 230, y + layer_h)
        content_box = (left_x + 230, y, right_x, y + layer_h)
        box(d, name_box, name, FONT_H2, fill=MID, width=3)
        box(d, content_box, content, FONT_BODY, fill=WHITE, width=3)
        boxes.append((name_box, content_box))
        if i:
            prev = boxes[i - 1][1]
            arrow(d, ((prev[0] + prev[2]) / 2, prev[3]), ((content_box[0] + content_box[2]) / 2, content_box[1]), width=2)

    ai_box = (1435, y0 + 2 * (layer_h + gap) + 8, 1695, y0 + 2 * (layer_h + gap) + layer_h - 8)
    box(d, ai_box, "外部 AI 服务\n智能检索\n评价审核\n报告生成", FONT_SMALL, fill=LIGHT, width=2)
    business = boxes[2][1]
    arrow(d, (business[2], (business[1] + business[3]) / 2 - 18), (ai_box[0], (ai_box[1] + ai_box[3]) / 2 - 18), width=2)
    arrow(d, (ai_box[0], (ai_box[1] + ai_box[3]) / 2 + 18), (business[2], (business[1] + business[3]) / 2 + 18), width=2)

    note = (150, 1080, 1695, 1155)
    box(d, note, "模块划分依据：以 Flask 蓝图承接请求入口，以业务功能组织处理逻辑，以 ORM 模型统一完成数据库读写。", FONT_SMALL, fill=LIGHT, width=1)
    return save(img, "图4-2_系统模块结构图.png")


def draw_business_modules():
    paths = []
    paths.append(draw_flow_module(
        "图4-3_用户登录模块图.png",
        "用户登录认证模块图",
        [
            ("root", "用户登录", (390, 90, 590, 150)),
            ("input", "输入账号密码", (90, 270, 300, 335)),
            ("match", "匹配账号类型", (390, 270, 590, 335)),
            ("verify", "校验密码与角色", (680, 270, 890, 335)),
            ("session", "写入登录状态", (390, 460, 590, 525)),
        ],
        [
            ("root", "input", "elbow_down_left"),
            ("root", "match", "down"),
            ("root", "verify", "elbow_down_right"),
            ("match", "session", "down"),
        ],
    ))
    paths.append(draw_flow_module(
        "图4-5_图书借阅模块图.png",
        "图书借阅模块图",
        [
            ("root", "图书借阅", (390, 90, 590, 150)),
            ("view", "查看图书详情", (80, 260, 300, 325)),
            ("check", "检查图书状态", (385, 260, 595, 325)),
            ("record", "生成借阅记录", (690, 260, 910, 325)),
            ("status", "更新图书状态", (385, 455, 595, 520)),
        ],
        [
            ("root", "view", "elbow_down_left"),
            ("root", "check", "down"),
            ("root", "record", "elbow_down_right"),
            ("check", "status", "down"),
        ],
    ))
    paths.append(draw_flow_module(
        "图4-7_座位预约模块图.png",
        "座位预约模块图",
        [
            ("root", "座位预约", (390, 90, 590, 150)),
            ("list", "查看座位分布", (70, 260, 295, 325)),
            ("clean", "释放超时座位", (385, 260, 595, 325)),
            ("check", "检查有效预约", (690, 260, 915, 325)),
            ("book", "创建预约记录", (240, 455, 460, 520)),
            ("status", "更新座位状态", (550, 455, 770, 520)),
        ],
        [
            ("root", "list", "elbow_down_left"),
            ("root", "clean", "down"),
            ("root", "check", "elbow_down_right"),
            ("clean", "book", "elbow_down_left"),
            ("clean", "status", "elbow_down_right"),
        ],
    ))
    paths.append(draw_flow_module(
        "图4-9_AI评价审核模块图.png",
        "图书评价 AI 审核模块图",
        [
            ("root", "AI 评价审核", (380, 90, 610, 150)),
            ("list", "查看待审评价", (70, 260, 295, 325)),
            ("send", "提交 AI 审核", (380, 260, 610, 325)),
            ("result", "解析审核结果", (700, 260, 925, 325)),
            ("save", "保存评价状态", (240, 455, 460, 520)),
            ("show", "显示审核理由", (550, 455, 770, 520)),
        ],
        [
            ("root", "list", "elbow_down_left"),
            ("root", "send", "down"),
            ("root", "result", "elbow_down_right"),
            ("send", "save", "elbow_down_left"),
            ("send", "show", "elbow_down_right"),
        ],
    ))
    paths.append(draw_flow_module(
        "图4-11_图书漂流申请模块图.png",
        "图书漂流申请模块图",
        [
            ("root", "图书漂流申请", (370, 90, 620, 150)),
            ("view", "查看漂流图书", (70, 260, 295, 325)),
            ("form", "填写申请留言", (380, 260, 610, 325)),
            ("check", "校验申请条件", (700, 260, 925, 325)),
            ("record", "生成申请记录", (240, 455, 460, 520)),
            ("wait", "等待处理结果", (550, 455, 770, 520)),
        ],
        [
            ("root", "view", "elbow_down_left"),
            ("root", "form", "down"),
            ("root", "check", "elbow_down_right"),
            ("form", "record", "elbow_down_left"),
            ("form", "wait", "elbow_down_right"),
        ],
    ))
    return paths


def sequence_diagram(filename, title, lifelines, messages):
    w = 1900
    top = 120
    header_h = 64
    step_gap = 72
    bottom = 115
    h = top + header_h + 50 + len(messages) * step_gap + bottom
    img = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    title_w = text_size(d, title, FONT_TITLE)[0]
    d.text(((w - title_w) / 2, 34), title, fill=WHITE, font=FONT_TITLE)

    n = len(lifelines)
    margin = 145
    usable = w - margin * 2
    xs = [margin + usable * i / (n - 1) for i in range(n)]
    heads = []
    for x, label in zip(xs, lifelines):
        bw = 220
        head = (x - bw / 2, top, x + bw / 2, top + header_h)
        dark_box(d, head, label, FONT_BODY)
        heads.append(head)
        dashed_line(d, (x, top + header_h), (x, h - 70), dash=14, gap=10, fill=WHITE, width=1)

    y = top + header_h + 55
    for idx, msg in enumerate(messages, start=1):
        src, dst, text = msg[:3]
        style = msg[3] if len(msg) > 3 else "call"
        x1, x2 = xs[src], xs[dst]
        label = f"{idx}. {text}"
        if style == "return":
            dashed_line(d, (x1, y), (x2, y), dash=12, gap=8, fill=WHITE, width=2)
            arrow(d, (x1, y), (x2, y), width=0, fill=WHITE, head=11)
        else:
            arrow(d, (x1, y), (x2, y), width=2, fill=WHITE)
        tx = (x1 + x2) / 2
        tw = text_size(d, label, FONT_SMALL)[0]
        if tw > abs(x2 - x1) - 24:
            lines = wrap_text(d, label, FONT_SMALL, abs(x2 - x1) - 24)
            ly = y - 24 - (len(lines) - 1) * 9
            for line_text in lines:
                lw = text_size(d, line_text, FONT_SMALL)[0]
                d.rectangle((tx - lw / 2 - 4, ly - 1, tx + lw / 2 + 4, ly + 19), fill=WHITE)
                d.text((tx - lw / 2, ly), line_text, font=FONT_SMALL, fill=BLACK)
                ly += 20
        else:
            d.rectangle((tx - tw / 2 - 5, y - 24, tx + tw / 2 + 5, y - 3), fill=WHITE)
            d.text((tx - tw / 2, y - 24), label, font=FONT_SMALL, fill=BLACK)
        y += step_gap

    return save(img, filename)


def draw_sequences():
    paths = []
    paths.append(sequence_diagram(
        "图4-4_用户登录顺序图.png",
        "用户登录认证顺序图",
        ["读者/管理员", "登录页面", "认证控制器", "账号模型", "数据库", "Session"],
        [
            (0, 1, "输入账号和密码并提交"),
            (1, 2, "发送登录请求"),
            (2, 3, "按学号/工号/用户名匹配账号"),
            (3, 4, "查询学生、教师或管理员记录"),
            (4, 3, "返回账号信息", "return"),
            (3, 2, "校验密码散列和角色"),
            (2, 5, "写入账号编号、类型和角色"),
            (2, 1, "返回登录结果", "return"),
            (1, 0, "跳转到图书列表或管理页面", "return"),
        ],
    ))
    paths.append(sequence_diagram(
        "图4-6_图书借阅顺序图.png",
        "图书借阅顺序图",
        ["读者", "图书列表/详情页", "图书控制器", "图书模型", "借阅记录模型", "数据库"],
        [
            (0, 1, "选择可借图书"),
            (1, 2, "提交借阅请求"),
            (2, 3, "读取图书状态"),
            (3, 5, "查询图书记录"),
            (5, 3, "返回图书可借状态", "return"),
            (2, 4, "创建借阅记录并绑定当前账号"),
            (2, 3, "将图书状态更新为已借出"),
            (4, 5, "保存借阅记录"),
            (3, 5, "保存图书状态"),
            (2, 1, "返回借阅成功提示", "return"),
        ],
    ))
    paths.append(sequence_diagram(
        "图4-8_座位预约顺序图.png",
        "座位预约顺序图",
        ["读者", "座位页面", "座位控制器", "座位模型", "预约记录模型", "数据库"],
        [
            (0, 1, "查看座位分布"),
            (1, 2, "请求座位列表"),
            (2, 4, "清理超时未释放预约"),
            (2, 3, "查询空闲座位"),
            (3, 5, "读取座位状态"),
            (5, 3, "返回座位信息", "return"),
            (0, 1, "选择空闲座位"),
            (1, 2, "提交预约请求"),
            (2, 4, "检查当前账号是否已有有效预约"),
            (2, 4, "创建预约记录"),
            (2, 3, "更新座位为占用状态"),
            (2, 1, "返回预约成功提示", "return"),
        ],
    ))
    paths.append(sequence_diagram(
        "图4-10_AI评价审核顺序图.png",
        "图书评价 AI 审核顺序图",
        ["管理员", "互动管理页", "图书控制器", "评价模型", "AI 审核服务", "数据库"],
        [
            (0, 1, "查看待审核评价内容"),
            (0, 1, "点击 AI 审核"),
            (1, 2, "提交评价审核请求"),
            (2, 3, "读取评价、图书和用户信息"),
            (3, 5, "查询评价记录"),
            (5, 3, "返回待审核内容", "return"),
            (2, 4, "发送评价内容和审核规则"),
            (4, 2, "返回通过/驳回及理由", "return"),
            (2, 3, "更新评价审核状态"),
            (3, 5, "保存审核结果"),
            (2, 1, "显示 AI 审核结果", "return"),
        ],
    ))
    paths.append(sequence_diagram(
        "图4-12_图书漂流申请顺序图.png",
        "图书漂流申请顺序图",
        ["申请读者", "漂流页面", "漂流控制器", "漂流图书模型", "申请记录模型", "数据库"],
        [
            (0, 1, "浏览漂流图书详情"),
            (0, 1, "填写领取留言并提交"),
            (1, 2, "发送领取申请"),
            (2, 3, "校验图书状态和提供者"),
            (3, 5, "查询漂流图书"),
            (5, 3, "返回图书状态", "return"),
            (2, 4, "检查是否重复申请"),
            (2, 4, "创建待处理申请记录"),
            (4, 5, "保存申请信息"),
            (2, 1, "返回申请提交结果", "return"),
        ],
    ))
    return paths


def write_manifest(paths):
    manifest = OUT_DIR / "图片清单.md"
    lines = [
        "# 系统总体设计图清单",
        "",
        "以下图片用于论文第 4 章“系统总体设计”模块，可直接插入正文并配套图题。",
        "",
    ]
    for p in paths:
        caption = p.stem.replace("_", " ")
        lines.append(f"- {caption}：`{p.name}`")
    lines.extend([
        "",
        "建议插入顺序：先放系统功能结构图，再放系统模块结构图；主要业务流程按“模块图 + 顺序图”成对插入。",
    ])
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return manifest


def main():
    business_modules = draw_business_modules()
    sequences = draw_sequences()
    paths = [
        draw_function_structure(),
        draw_module_structure(),
    ]
    for module_path, sequence_path in zip(business_modules, sequences):
        paths.extend([module_path, sequence_path])
    manifest = write_manifest(paths)
    print(str(OUT_DIR))
    for p in paths:
        print(p.name)
    print(manifest.name)


if __name__ == "__main__":
    main()
