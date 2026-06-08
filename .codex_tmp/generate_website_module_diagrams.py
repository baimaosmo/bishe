from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "系统总体设计图" / "网站功能模块设计图"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\simhei.ttf" if bold else r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


FONT_TITLE = font(32, True)
FONT_H1 = font(23, True)
FONT_BODY = font(19)
FONT_SMALL = font(17)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def text_size(draw, text, fnt):
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, fnt, width):
    lines = []
    for part in text.split("\n"):
        current = ""
        for ch in part:
            trial = current + ch
            if text_size(draw, trial, fnt)[0] <= width or not current:
                current = trial
            else:
                lines.append(current)
                current = ch
        if current:
            lines.append(current)
    return lines or [""]


def centered(draw, xy, text, fnt=FONT_BODY, fill=BLACK):
    x1, y1, x2, y2 = xy
    lines = wrap(draw, text, fnt, x2 - x1 - 18)
    hs = [text_size(draw, line, fnt)[1] for line in lines]
    total = sum(hs) + 5 * (len(lines) - 1)
    y = y1 + (y2 - y1 - total) / 2
    for line, h in zip(lines, hs):
        tw = text_size(draw, line, fnt)[0]
        draw.text((x1 + (x2 - x1 - tw) / 2, y), font=fnt, fill=fill, text=line)
        y += h + 5


def box(draw, xy, text, fnt=FONT_BODY):
    draw.rectangle(xy, fill=WHITE, outline=WHITE, width=2)
    centered(draw, xy, text, fnt, BLACK)


def line(draw, p1, p2, width=3):
    draw.line([p1, p2], fill=WHITE, width=width)


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


def save(img, filename):
    path = OUT_DIR / filename
    img.save(path, dpi=(220, 220))
    return path


def draw_title(draw, width, title):
    tw = text_size(draw, title, FONT_TITLE)[0]
    draw.text(((width - tw) / 2, 30), title, font=FONT_TITLE, fill=WHITE)


def draw_tree(filename, title, root_label, items):
    w, h = 1280, 760
    img = Image.new("RGB", (w, h), BLACK)
    draw = ImageDraw.Draw(img)
    draw_title(draw, w, title)

    root = (500, 95, 780, 160)
    root_cx = (root[0] + root[2]) / 2
    box(draw, root, root_label, FONT_H1)

    cols = 4
    item_w, item_h = 210, 66
    x_positions = [90, 390, 690, 990]
    y_positions = [300, 540]
    top_y = 225
    bottom_y = 475

    line(draw, (root_cx, root[3]), (root_cx, top_y))
    line(draw, (x_positions[0] + item_w / 2, top_y), (x_positions[-1] + item_w / 2, top_y))
    if len(items) > cols:
        line(draw, (root_cx, top_y), (root_cx, bottom_y))
        line(draw, (x_positions[0] + item_w / 2, bottom_y), (x_positions[-1] + item_w / 2, bottom_y))

    for idx, item in enumerate(items):
        row = idx // cols
        col = idx % cols
        x = x_positions[col]
        y = y_positions[row]
        trunk_y = top_y if row == 0 else bottom_y
        line(draw, (x + item_w / 2, trunk_y), (x + item_w / 2, y))
        box(draw, (x, y, x + item_w, y + item_h), item, FONT_BODY)

    return save(img, filename)


def sequence_diagram(filename, title, lifelines, messages):
    width = 1860
    top = 120
    header_h = 64
    step_gap = 70
    height = top + header_h + 50 + len(messages) * step_gap + 95
    img = Image.new("RGB", (width, height), BLACK)
    draw = ImageDraw.Draw(img)
    draw_title(draw, width, title)

    margin = 120
    usable = width - 2 * margin
    xs = [margin + usable * i / (len(lifelines) - 1) for i in range(len(lifelines))]
    for x, label in zip(xs, lifelines):
        head = (x - 112, top, x + 112, top + header_h)
        box(draw, head, label, FONT_BODY)
        dashed_line(draw, (x, top + header_h), (x, height - 70), width=1)

    y = top + header_h + 55
    for idx, (src, dst, label, kind) in enumerate(messages, start=1):
        x1, x2 = xs[src], xs[dst]
        arrow(draw, (x1, y), (x2, y), width=2, dashed=(kind == "return"))
        text = f"{idx}. {label}"
        max_width = max(150, abs(x2 - x1) - 28)
        lines = wrap(draw, text, FONT_SMALL, max_width)
        tx = (x1 + x2) / 2
        ly = y - 24 - max(0, len(lines) - 1) * 10
        for line_text in lines:
            tw = text_size(draw, line_text, FONT_SMALL)[0]
            draw.rectangle((tx - tw / 2 - 5, ly - 1, tx + tw / 2 + 5, ly + 20), fill=WHITE)
            draw.text((tx - tw / 2, ly), line_text, fill=BLACK, font=FONT_SMALL)
            ly += 20
        y += step_gap
    return save(img, filename)


MODULES = [
    {
        "module_title": "用户认证与个人中心模块图",
        "sequence_title": "用户认证与个人中心顺序图",
        "root": "认证与个人中心",
        "items": ["注册登录", "统一账号识别", "Session 状态保持", "修改密码", "上传头像", "借阅记录", "收藏记录", "漂流记录"],
        "heading": "用户认证与个人中心模块",
        "text": "用户认证与个人中心模块负责系统登录入口和用户个人数据展示。系统支持普通注册用户、学生和教师等多类型账号登录，登录时根据账号标识匹配对应用户表，并将账号编号、账号类型和角色信息写入 Session。用户登录后可以修改密码、上传头像，并在个人中心查看借阅记录、收藏记录、评价记录、座位预约和图书漂流相关信息。该模块为其他业务模块提供身份识别和权限判断基础。",
        "lifelines": ["统一用户", "登录页面", "首页", "个人中心页面", "资料修改页面"],
        "messages": [
            (0, 1, "进入登录页面", "call"),
            (0, 1, "输入账号和密码", "call"),
            (0, 1, "点击登录按钮", "call"),
            (1, 2, "登录成功后进入首页", "return"),
            (0, 2, "点击个人中心", "call"),
            (2, 3, "打开个人中心页面", "return"),
            (0, 3, "查看借阅、收藏和漂流记录", "call"),
            (0, 3, "点击修改资料或密码", "call"),
            (3, 4, "进入资料修改页面", "return"),
            (0, 4, "提交修改内容", "call"),
            (4, 3, "显示修改结果", "return"),
        ],
    },
    {
        "module_title": "图书资源与借阅模块图",
        "sequence_title": "图书资源与借阅顺序图",
        "root": "图书资源与借阅",
        "items": ["图书列表", "条件检索", "图书详情", "馆藏位置", "借阅图书", "归还图书", "借阅记录", "状态同步"],
        "heading": "图书资源与借阅模块",
        "text": "图书资源与借阅模块是系统的核心业务模块。前台用户可以浏览图书列表，根据书名、作者、分类等条件检索图书，并查看图书详情、封面、简介和馆藏位置。用户借阅图书时，系统需要检查图书是否处于可借状态，生成借阅记录并同步更新图书状态；用户归还图书时，系统更新借阅记录的归还时间，并将图书状态恢复为可借。管理员则可以在后台维护图书基础信息。",
        "lifelines": ["统一用户", "图书列表页面", "图书详情页面", "借阅记录页面", "操作结果页面"],
        "messages": [
            (0, 1, "进入图书列表页面", "call"),
            (0, 1, "输入检索条件", "call"),
            (1, 1, "显示图书检索结果", "return"),
            (0, 1, "选择目标图书", "call"),
            (1, 2, "进入图书详情页面", "return"),
            (0, 2, "点击借阅图书", "call"),
            (2, 4, "显示借阅成功提示", "return"),
            (0, 3, "进入我的借阅页面", "call"),
            (0, 3, "点击归还图书", "call"),
            (3, 4, "显示归还成功提示", "return"),
        ],
    },
    {
        "module_title": "座位预约模块图",
        "sequence_title": "座位预约顺序图",
        "root": "座位预约",
        "items": ["座位列表", "楼层区域筛选", "空闲状态查看", "预约座位", "有效预约检查", "释放座位", "超时清理", "预约记录"],
        "heading": "座位预约模块",
        "text": "座位预约模块用于实现图书馆学习座位的在线查看和预约。用户可以按照楼层、区域和座位状态查看座位分布，选择空闲座位后提交预约请求。系统在创建预约记录前会检查用户是否已有有效预约，避免重复占用座位。用户离座时可以主动释放座位，系统也会对超时未释放的预约记录进行清理，从而保证座位状态与实际使用情况保持一致。",
        "lifelines": ["统一用户", "座位列表页面", "座位筛选页面", "预约确认页面", "预约结果页面"],
        "messages": [
            (0, 1, "进入座位列表页面", "call"),
            (0, 2, "选择楼层和区域", "call"),
            (2, 1, "显示筛选后的座位", "return"),
            (0, 1, "查看空闲座位", "call"),
            (0, 1, "选择目标座位", "call"),
            (1, 3, "进入预约确认页面", "return"),
            (0, 3, "点击确认预约", "call"),
            (3, 4, "显示预约成功结果", "return"),
            (0, 1, "需要离座时点击释放", "call"),
            (1, 4, "显示释放成功结果", "return"),
        ],
    },
    {
        "module_title": "收藏评价与AI审核模块图",
        "sequence_title": "收藏评价与AI审核顺序图",
        "root": "收藏评价与审核",
        "items": ["收藏图书", "取消收藏", "我的收藏", "提交评价", "评价状态", "待审核列表", "AI 审核", "审核结果保存"],
        "heading": "收藏评价与 AI 审核模块",
        "text": "收藏评价与 AI 审核模块用于增强用户与图书资源之间的交互。用户可以收藏感兴趣的图书，也可以在归还图书后提交评价。新提交的评价默认处于待审核状态，管理员在后台查看评价内容后触发 AI 审核，由 AI 根据评价内容和审核规则返回通过或驳回结果，系统再保存评价状态。只有审核通过的评价才会在图书详情页面展示。",
        "lifelines": ["统一用户", "图书详情页面", "评价填写页面", "管理员审核页面", "审核结果页面"],
        "messages": [
            (0, 1, "进入图书详情页面", "call"),
            (0, 1, "点击收藏图书", "call"),
            (1, 1, "显示收藏成功提示", "return"),
            (0, 1, "点击发表评价", "call"),
            (1, 2, "进入评价填写页面", "return"),
            (0, 2, "填写评分和评价内容", "call"),
            (0, 2, "提交评价", "call"),
            (2, 3, "评价进入待审核列表", "return"),
            (3, 3, "管理员点击AI审核", "call"),
            (3, 4, "显示审核通过或驳回结果", "return"),
        ],
    },
    {
        "module_title": "图书漂流模块图",
        "sequence_title": "图书漂流顺序图",
        "root": "图书漂流",
        "items": ["发布漂流图书", "漂流图书列表", "查看详情", "提交领取申请", "重复申请检查", "处理申请", "更新漂流状态", "我的漂流"],
        "heading": "图书漂流模块",
        "text": "图书漂流模块用于支持校园内闲置图书共享。用户可以发布自己的漂流图书，填写书名、关联课程、新旧程度和补充说明等信息。其他用户可以查看漂流图书详情并提交领取申请，系统会检查图书状态、申请人身份和是否重复申请。图书提供者或管理员处理申请后，系统更新申请状态和图书漂流状态，实现图书资源在用户之间流转。",
        "lifelines": ["统一用户", "漂流列表页面", "发布漂流页面", "漂流详情页面", "领取申请页面", "我的漂流页面"],
        "messages": [
            (0, 1, "进入漂流列表页面", "call"),
            (0, 1, "点击发布漂流图书", "call"),
            (1, 2, "进入发布漂流页面", "return"),
            (0, 2, "填写图书信息并发布", "call"),
            (2, 1, "返回漂流列表", "return"),
            (0, 1, "选择漂流图书", "call"),
            (1, 3, "进入漂流详情页面", "return"),
            (0, 3, "点击申请领取", "call"),
            (3, 4, "进入领取申请页面", "return"),
            (0, 4, "填写留言并提交", "call"),
            (4, 5, "显示我的漂流申请", "return"),
        ],
    },
    {
        "module_title": "AI智能服务模块图",
        "sequence_title": "AI智能服务顺序图",
        "root": "AI 智能服务",
        "items": ["馆藏上下文组织", "智能检索", "图书匹配", "个性化推荐", "评价审核", "统计报告生成", "AI 接口调用", "结果展示"],
        "heading": "AI 智能服务模块",
        "text": "AI 智能服务模块用于提升系统的智能化服务能力。系统根据本地馆藏、借阅、收藏、评价和统计数据组织上下文，通过外部 AI 服务完成智能检索、图书匹配、评价审核和统计报告生成。AI 服务不直接操作数据库，而是由系统控制器整理请求数据并接收返回结果，再将结果展示给前台用户或后台管理员。",
        "lifelines": ["用户/管理员", "AI功能入口", "智能检索页面", "报告生成页面", "结果展示页面"],
        "messages": [
            (0, 1, "进入AI功能入口", "call"),
            (0, 1, "选择智能检索功能", "call"),
            (1, 2, "进入智能检索页面", "return"),
            (0, 2, "输入检索需求", "call"),
            (0, 2, "提交智能检索", "call"),
            (2, 4, "显示图书匹配结果", "return"),
            (0, 1, "选择报告生成功能", "call"),
            (1, 3, "进入报告生成页面", "return"),
            (0, 3, "点击生成统计报告", "call"),
            (3, 4, "显示AI报告结果", "return"),
        ],
    },
    {
        "module_title": "后台用户与导入管理模块图",
        "sequence_title": "后台用户与导入管理顺序图",
        "root": "用户与导入管理",
        "items": ["用户列表", "学生管理", "教师管理", "普通用户管理", "批量导入学生", "批量导入教师", "重置密码", "删除账号"],
        "heading": "后台用户与导入管理模块",
        "text": "后台用户与导入管理模块面向管理员使用，用于维护系统账号数据。管理员可以查看学生、教师和普通注册用户信息，支持批量导入学生和教师账号，并可对异常账号进行重置密码或删除处理。该模块与登录认证模块配合，为系统多类型用户统一登录和权限控制提供数据基础。",
        "lifelines": ["管理员", "用户管理页面", "导入页面", "用户编辑页面", "操作结果页面"],
        "messages": [
            (0, 1, "进入用户管理页面", "call"),
            (1, 1, "显示学生教师用户列表", "return"),
            (0, 1, "点击批量导入", "call"),
            (1, 2, "进入导入页面", "return"),
            (0, 2, "选择学生或教师类型", "call"),
            (0, 2, "上传导入文件", "call"),
            (2, 4, "显示导入结果", "return"),
            (0, 1, "选择用户账号", "call"),
            (1, 3, "进入用户编辑页面", "return"),
            (0, 3, "重置密码或删除账号", "call"),
            (3, 4, "显示管理结果", "return"),
        ],
    },
    {
        "module_title": "后台数据统计与运营管理模块图",
        "sequence_title": "后台数据统计与运营管理顺序图",
        "root": "数据统计与运营",
        "items": ["借阅数据查看", "座位数据查看", "热门收藏统计", "评价管理", "漂流图书管理", "数据看板", "AI 报告", "运营决策辅助"],
        "heading": "后台数据统计与运营管理模块",
        "text": "后台数据统计与运营管理模块用于帮助管理员掌握系统运行情况。管理员可以查看近期借阅记录、座位预约记录、热门收藏图书和评价数据，也可以管理漂流图书信息。系统通过数据看板汇总关键运营数据，并结合 AI 报告生成功能，为图书馆资源维护、座位管理和用户服务优化提供参考。",
        "lifelines": ["管理员", "数据看板页面", "借阅座位页面", "评价漂流页面", "AI报告页面"],
        "messages": [
            (0, 1, "进入数据看板页面", "call"),
            (1, 1, "显示统计概览", "return"),
            (0, 1, "查看借阅和座位数据", "call"),
            (1, 2, "进入借阅座位页面", "return"),
            (0, 2, "筛选记录并查看详情", "call"),
            (0, 1, "查看评价和漂流数据", "call"),
            (1, 3, "进入评价漂流页面", "return"),
            (0, 3, "处理运营数据", "call"),
            (0, 1, "点击生成AI报告", "call"),
            (1, 4, "进入AI报告页面", "return"),
            (4, 0, "显示统计报告", "return"),
        ],
    },
]


def write_docs(entries):
    lines = [
        "# 网站功能模块设计说明",
        "",
        "本节在前台统一用户和后台管理员两个角色方向的基础上，进一步对系统中的主要功能模块进行细化设计。每个模块均给出功能模块图和顺序图：模块图用于描述模块内部功能点，顺序图用于描述用户在网站页面中的实际操作流程，包括进入页面、填写信息、点击按钮、提交表单和查看处理结果等步骤。",
        "",
    ]
    for section_no, (module, module_fig, module_file, sequence_fig, sequence_file) in enumerate(entries, start=5):
        lines.append(f"## 4.{section_no} {module['heading']}")
        lines.append("")
        lines.append(module["text"])
        lines.append("")
        lines.append(f"![图4-{module_fig} {module['module_title']}]({module_file})")
        lines.append("")
        lines.append(f"图 4-{module_fig} {module['module_title']}")
        lines.append("")
        lines.append(f"![图4-{sequence_fig} {module['sequence_title']}]({sequence_file})")
        lines.append("")
        lines.append(f"图 4-{sequence_fig} {module['sequence_title']}")
        lines.append("")

    doc = OUT_DIR / "网站功能模块设计说明.md"
    doc.write_text("\n".join(lines), encoding="utf-8")

    manifest = OUT_DIR / "图片清单.md"
    manifest_lines = ["# 网站功能模块设计图清单", ""]
    for module, module_fig, module_file, sequence_fig, sequence_file in entries:
        manifest_lines.append(f"- 图4-{module_fig} {module['module_title']}：`{module_file}`")
        manifest_lines.append(f"- 图4-{sequence_fig} {module['sequence_title']}：`{sequence_file}`")
    manifest_lines.append("")
    manifest_lines.append("建议插入位置：放在系统总体设计章节的功能模块设计小节中，位于前后台角色总模块图之后，并按“模块图 + 顺序图”成对插入。")
    manifest.write_text("\n".join(manifest_lines), encoding="utf-8")
    return doc, manifest


def main():
    entries = []
    for i, module in enumerate(MODULES):
        module_fig = 7 + i * 2
        sequence_fig = module_fig + 1
        module_file = f"图4-{module_fig}_{module['module_title']}.png"
        sequence_file = f"图4-{sequence_fig}_{module['sequence_title']}.png"
        draw_tree(module_file, module["module_title"], module["root"], module["items"])
        sequence_diagram(sequence_file, module["sequence_title"], module["lifelines"], module["messages"])
        entries.append((module, module_fig, module_file, sequence_fig, sequence_file))

    doc, manifest = write_docs(entries)
    print(OUT_DIR)
    for _, _, module_file, _, sequence_file in entries:
        print(module_file)
        print(sequence_file)
    print(doc.name)
    print(manifest.name)


if __name__ == "__main__":
    main()
