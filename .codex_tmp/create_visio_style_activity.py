# -*- coding: utf-8 -*-
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont


ROOT = Path.cwd()
OUT = ROOT / ".codex_tmp" / "visio_style_activity"
OUT.mkdir(parents=True, exist_ok=True)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\Noto Sans SC (TrueType).otf",
    r"C:\Windows\Fonts\NotoSansSC-VF.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)


def get_font(size, bold=False):
    if bold:
        for p in [
            r"C:\Windows\Fonts\Noto Sans SC Bold (TrueType).otf",
            r"C:\Windows\Fonts\msyhbd.ttc",
            r"C:\Windows\Fonts\simhei.ttf",
        ]:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size)
    return ImageFont.load_default()


F_TITLE = get_font(34, bold=True)
F_NODE = get_font(23)
F_DECISION = get_font(20)
F_LABEL = get_font(18)

COLOR = {
    "bg": "#FFFFFF",
    "canvas": "#FBFCFE",
    "border": "#C9D3E3",
    "line": "#404040",
    "action_fill": "#DAE8FC",
    "action_stroke": "#6C8EBF",
    "decision_fill": "#FFF2CC",
    "decision_stroke": "#D6B656",
    "text": "#111111",
}


def text_box(draw, text, font):
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=5, align="center")
    return box[2] - box[0], box[3] - box[1]


def wrap(draw, text, font, max_width):
    lines = []
    current = ""
    for ch in text:
        candidate = current + ch
        if not current or text_box(draw, candidate, font)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = ch
    if current:
        lines.append(current)
    return "\n".join(lines)


def draw_title(draw, text, width):
    draw.text((width / 2, 42), text, font=F_TITLE, fill=COLOR["text"], anchor="mm")
    draw.line((70, 75, width - 70, 75), fill=COLOR["border"], width=2)


def draw_start(draw, cx, cy):
    draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), fill="#111111", outline="#111111")


def draw_end(draw, cx, cy):
    draw.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill="#FFFFFF", outline="#111111", width=3)
    draw.ellipse((cx - 11, cy - 11, cx + 11, cy + 11), fill="#111111", outline="#111111")


def draw_action(draw, box, text):
    x, y, w, h = box
    draw.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=14,
        fill=COLOR["action_fill"],
        outline=COLOR["action_stroke"],
        width=3,
    )
    label = wrap(draw, text, F_NODE, w - 28)
    draw.multiline_text((x + w / 2, y + h / 2), label, font=F_NODE, fill=COLOR["text"], anchor="mm", align="center", spacing=5)


def draw_decision(draw, box, text):
    x, y, w, h = box
    points = [(x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h), (x, y + h / 2)]
    draw.polygon(points, fill=COLOR["decision_fill"], outline=COLOR["decision_stroke"])
    draw.line(points + [points[0]], fill=COLOR["decision_stroke"], width=3)
    label = wrap(draw, text, F_DECISION, w - 36)
    draw.multiline_text((x + w / 2, y + h / 2), label, font=F_DECISION, fill=COLOR["text"], anchor="mm", align="center", spacing=5)


def arrow_head(draw, a, b):
    angle = math.atan2(b[1] - a[1], b[0] - a[0])
    size = 14
    p1 = (b[0] + size * math.cos(angle + math.pi * 0.82), b[1] + size * math.sin(angle + math.pi * 0.82))
    p2 = (b[0] + size * math.cos(angle - math.pi * 0.82), b[1] + size * math.sin(angle - math.pi * 0.82))
    draw.polygon([b, p1, p2], fill=COLOR["line"])


def draw_arrow(draw, points, label=None, label_at=None):
    for a, b in zip(points, points[1:]):
        draw.line((a[0], a[1], b[0], b[1]), fill=COLOR["line"], width=3)
    arrow_head(draw, points[-2], points[-1])
    if label:
        if label_at is None:
            a, b = points[len(points) // 2 - 1], points[len(points) // 2]
            lx, ly = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        else:
            lx, ly = label_at
        tw, th = text_box(draw, label, F_LABEL)
        draw.rounded_rectangle((lx - tw / 2 - 8, ly - th / 2 - 5, lx + tw / 2 + 8, ly + th / 2 + 5), radius=5, fill="#FFFFFF")
        draw.text((lx, ly), label, font=F_LABEL, fill=COLOR["text"], anchor="mm")


def canvas(title, w, h):
    img = Image.new("RGB", (w, h), COLOR["bg"])
    draw = ImageDraw.Draw(img)
    draw_title(draw, title, w)
    draw.rounded_rectangle((45, 95, w - 45, h - 45), radius=8, fill=COLOR["canvas"], outline=COLOR["border"], width=2)
    return img, draw


def save(img, name):
    path = OUT / name
    img.save(path)
    return path


def diagram_login():
    w, h = 1500, 1020
    img, d = canvas("登录系统活动图", w, h)
    draw_start(d, 750, 110)
    boxes = [
        ("a", "打开登录页面", (610, 145, 280, 70)),
        ("b", "输入账号和密码", (610, 245, 280, 70)),
        ("s", "是否为有效学生账号", (590, 360, 320, 120), "decision"),
        ("t", "是否为有效教师账号", (590, 535, 320, 120), "decision"),
        ("u", "是否为有效注册用户账号", (590, 710, 320, 120), "decision"),
        ("ss", "写入学生会话信息", (1030, 385, 310, 70)),
        ("st", "写入教师会话信息", (1030, 560, 310, 70)),
        ("su", "写入用户会话信息", (1030, 735, 310, 70)),
        ("f", "提示账号或密码错误", (165, 560, 310, 70)),
        ("l", "进入图书列表页", (610, 875, 280, 70)),
    ]
    for _, text, box, *typ in boxes:
        draw_decision(d, box, text) if typ else draw_action(d, box, text)
    draw_arrow(d, [(750, 124), (750, 145)])
    draw_arrow(d, [(750, 215), (750, 245)])
    draw_arrow(d, [(750, 315), (750, 360)])
    draw_arrow(d, [(910, 420), (1030, 420)], "是", (970, 400))
    draw_arrow(d, [(1185, 455), (1185, 850), (890, 910)])
    draw_arrow(d, [(750, 480), (750, 535)], "否", (775, 510))
    draw_arrow(d, [(910, 595), (1030, 595)], "是", (970, 575))
    draw_arrow(d, [(1185, 630), (1185, 850), (890, 915)])
    draw_arrow(d, [(750, 655), (750, 710)], "否", (775, 685))
    draw_arrow(d, [(910, 770), (1030, 770)], "是", (970, 750))
    draw_arrow(d, [(1185, 805), (1185, 850), (890, 920)])
    draw_arrow(d, [(590, 770), (475, 595)], "否", (540, 670))
    draw_arrow(d, [(165, 595), (120, 595), (120, 280), (610, 280)])
    draw_arrow(d, [(750, 945), (750, 975)])
    draw_end(d, 750, 975)
    return save(img, "01_登录系统活动图.png")


def diagram_borrow():
    w, h = 1500, 1510
    img, d = canvas("图书借阅与归还活动图", w, h)
    draw_start(d, 750, 110)
    actions = [
        ("用户登录系统", (610, 145, 280, 62)),
        ("进入图书列表或详情页", (610, 235, 280, 62)),
        ("选择目标图书", (610, 325, 280, 62)),
        ("点击借阅图书", (610, 415, 280, 62)),
        ("生成借阅记录", (610, 660, 280, 62)),
        ("图书状态改为已借出", (610, 750, 280, 62)),
        ("进入我的借阅页面", (610, 840, 280, 62)),
        ("点击归还图书", (610, 930, 280, 62)),
        ("记录归还时间", (1015, 1050, 300, 62)),
        ("借阅状态改为已归还", (1015, 1140, 300, 62)),
        ("图书状态恢复为可借", (1015, 1230, 300, 62)),
        ("提交图书评价", (1015, 1320, 300, 62)),
        ("提示图书不可借", (185, 540, 310, 62)),
        ("提示无权操作", (185, 1050, 310, 62)),
    ]
    for text, box in actions:
        draw_action(d, box, text)
    draw_decision(d, (590, 515, 320, 120), "图书是否可借")
    draw_decision(d, (590, 1025, 320, 120), "是否为本人借阅记录")
    for y1, y2 in [(124, 145), (207, 235), (297, 325), (387, 415), (477, 515), (635, 660), (722, 750), (812, 840), (902, 930), (992, 1025)]:
        draw_arrow(d, [(750, y1), (750, y2)])
    draw_arrow(d, [(750, 635), (750, 660)], "是", (775, 648))
    draw_arrow(d, [(590, 575), (495, 575)], "否", (540, 555))
    draw_arrow(d, [(185, 571), (110, 571), (110, 1450), (750, 1450)])
    draw_arrow(d, [(910, 1085), (1015, 1085)], "是", (965, 1065))
    for y1, y2 in [(1112, 1140), (1202, 1230), (1292, 1320)]:
        draw_arrow(d, [(1165, y1), (1165, y2)])
    draw_arrow(d, [(1165, 1382), (1165, 1450), (750, 1450)])
    draw_arrow(d, [(590, 1085), (495, 1085)], "否", (540, 1065))
    draw_arrow(d, [(185, 1081), (110, 1081), (110, 1450), (750, 1450)])
    draw_arrow(d, [(750, 1450), (750, 1475)])
    draw_end(d, 750, 1475)
    return save(img, "02_图书借阅与归还活动图.png")


def diagram_seat():
    w, h = 1500, 1410
    img, d = canvas("座位预约活动图", w, h)
    draw_start(d, 750, 110)
    for text, box in [
        ("用户登录系统", (610, 145, 280, 62)),
        ("进入座位预约页面", (610, 235, 280, 62)),
        ("系统清理超时预约", (610, 325, 280, 62)),
        ("选择楼层并查看座位状态", (610, 415, 280, 62)),
        ("选择空闲座位", (610, 505, 280, 62)),
        ("生成座位预约记录", (1015, 805, 310, 62)),
        ("座位状态改为占用", (1015, 895, 310, 62)),
        ("显示预约信息和剩余时间", (1015, 985, 310, 62)),
        ("用户释放座位", (1015, 1075, 310, 62)),
        ("预约状态改为已完成", (1015, 1165, 310, 62)),
        ("座位状态恢复为空闲", (1015, 1255, 310, 62)),
        ("提示先释放当前座位", (165, 625, 330, 62)),
        ("提示座位不可预约", (165, 805, 330, 62)),
    ]:
        draw_action(d, box, text)
    draw_decision(d, (590, 605, 320, 120), "是否已有有效预约")
    draw_decision(d, (590, 785, 320, 120), "座位是否空闲")
    for y1, y2 in [(124, 145), (207, 235), (297, 325), (387, 415), (477, 505), (567, 605), (725, 785)]:
        draw_arrow(d, [(750, y1), (750, y2)])
    draw_arrow(d, [(590, 665), (495, 656)], "是", (540, 640))
    draw_arrow(d, [(165, 656), (110, 656), (110, 1350), (750, 1350)])
    draw_arrow(d, [(750, 725), (750, 785)], "否", (775, 755))
    draw_arrow(d, [(910, 845), (1015, 836)], "是", (965, 820))
    for y1, y2 in [(867, 895), (957, 985), (1047, 1075), (1137, 1165), (1227, 1255)]:
        draw_arrow(d, [(1170, y1), (1170, y2)])
    draw_arrow(d, [(1170, 1317), (1170, 1350), (750, 1350)])
    draw_arrow(d, [(590, 845), (495, 836)], "否", (540, 820))
    draw_arrow(d, [(165, 836), (110, 836), (110, 1350), (750, 1350)])
    draw_arrow(d, [(750, 1350), (750, 1375)])
    draw_end(d, 750, 1375)
    return save(img, "03_座位预约活动图.png")


def diagram_crossing():
    w, h = 1500, 1840
    img, d = canvas("图书漂流活动图", w, h)
    draw_start(d, 750, 110)
    for text, box in [
        ("用户登录系统", (600, 145, 300, 62)),
        ("发布漂流图书", (600, 235, 300, 62)),
        ("保存漂流图书", (600, 485, 300, 62)),
        ("其他用户浏览漂流广场", (600, 575, 300, 62)),
        ("查看漂流图书详情", (600, 665, 300, 62)),
        ("提交领取申请", (600, 1265, 300, 62)),
        ("提供者或管理员查看申请", (600, 1355, 300, 62)),
        ("申请状态改为已同意", (1010, 1485, 300, 62)),
        ("图书状态改为已领走", (1010, 1575, 300, 62)),
        ("其他申请自动驳回", (1010, 1665, 300, 62)),
        ("申请状态改为已驳回", (180, 1485, 300, 62)),
        ("提示填写书名", (180, 360, 300, 62)),
        ("提示图书已被领走", (180, 790, 300, 62)),
        ("提示不能申请自己的图书", (180, 960, 300, 62)),
        ("提示不能重复申请", (180, 1130, 300, 62)),
    ]:
        draw_action(d, box, text)
    for text, box in [
        ("书名是否为空", (590, 335, 320, 120)),
        ("图书是否已被领走", (590, 765, 320, 120)),
        ("是否为本人发布", (590, 935, 320, 120)),
        ("是否重复申请", (590, 1105, 320, 120)),
        ("是否同意申请", (590, 1455, 320, 120)),
    ]:
        draw_decision(d, box, text)
    for y1, y2 in [(124, 145), (207, 235), (297, 335), (455, 485), (547, 575), (637, 665), (727, 765), (885, 935), (1055, 1105), (1225, 1265), (1327, 1355), (1417, 1455)]:
        draw_arrow(d, [(750, y1), (750, y2)])
    draw_arrow(d, [(590, 395), (480, 391)], "是", (535, 370))
    draw_arrow(d, [(180, 391), (120, 391), (120, 266), (600, 266)])
    draw_arrow(d, [(750, 455), (750, 485)], "否", (775, 470))
    for y, box_y, label in [(825, 821, "是"), (995, 991, "是"), (1165, 1161, "是")]:
        draw_arrow(d, [(590, y), (480, box_y)], label, (535, y - 20))
        draw_arrow(d, [(180, box_y + 31), (110, box_y + 31), (110, 1770), (750, 1770)])
    draw_arrow(d, [(750, 885), (750, 935)], "否", (775, 910))
    draw_arrow(d, [(750, 1055), (750, 1105)], "否", (775, 1080))
    draw_arrow(d, [(750, 1225), (750, 1265)], "否", (775, 1240))
    draw_arrow(d, [(910, 1515), (1010, 1516)], "同意", (965, 1494))
    draw_arrow(d, [(1160, 1547), (1160, 1575)])
    draw_arrow(d, [(1160, 1637), (1160, 1665)])
    draw_arrow(d, [(1160, 1727), (1160, 1770), (750, 1770)])
    draw_arrow(d, [(590, 1515), (480, 1516)], "驳回", (535, 1494))
    draw_arrow(d, [(180, 1516), (110, 1516), (110, 1770), (750, 1770)])
    draw_arrow(d, [(750, 1770), (750, 1805)])
    draw_end(d, 750, 1805)
    return save(img, "04_图书漂流活动图.png")


def diagram_review():
    w, h = 1500, 1130
    img, d = canvas("图书评价审核活动图", w, h)
    draw_start(d, 750, 110)
    for text, box in [
        ("用户归还图书", (610, 145, 280, 62)),
        ("提交评分和评价内容", (610, 235, 280, 62)),
        ("评价状态设为待审核", (610, 485, 280, 62)),
        ("管理员登录系统", (610, 575, 280, 62)),
        ("进入互动管理页面", (610, 665, 280, 62)),
        ("查看评价内容", (610, 755, 280, 62)),
        ("审核通过", (1015, 890, 300, 62)),
        ("评价在图书详情页展示", (1015, 980, 300, 62)),
        ("审核驳回", (185, 890, 300, 62)),
        ("评价不公开展示", (185, 980, 300, 62)),
        ("提示评价不符合要求", (185, 360, 300, 62)),
    ]:
        draw_action(d, box, text)
    draw_decision(d, (590, 335, 320, 120), "评价是否符合要求")
    draw_decision(d, (590, 855, 320, 120), "评价内容是否合规")
    for y1, y2 in [(124, 145), (207, 235), (297, 335), (455, 485), (547, 575), (637, 665), (727, 755), (817, 855)]:
        draw_arrow(d, [(750, y1), (750, y2)])
    draw_arrow(d, [(590, 395), (485, 391)], "否", (535, 370))
    draw_arrow(d, [(185, 391), (110, 391), (110, 1070), (750, 1070)])
    draw_arrow(d, [(750, 455), (750, 485)], "是", (775, 470))
    draw_arrow(d, [(910, 915), (1015, 921)], "是", (965, 900))
    draw_arrow(d, [(1165, 952), (1165, 980)])
    draw_arrow(d, [(1165, 1042), (1165, 1070), (750, 1070)])
    draw_arrow(d, [(590, 915), (485, 921)], "否", (535, 900))
    draw_arrow(d, [(335, 952), (335, 980)])
    draw_arrow(d, [(335, 1042), (335, 1070), (750, 1070)])
    draw_arrow(d, [(750, 1070), (750, 1095)])
    draw_end(d, 750, 1095)
    return save(img, "05_图书评价审核活动图.png")


def diagram_admin_book():
    w, h = 1500, 1120
    img, d = canvas("管理员图书信息管理活动图", w, h)
    draw_start(d, 750, 110)
    for text, box in [
        ("管理员登录系统", (610, 145, 280, 62)),
        ("进入图书管理页面", (610, 235, 280, 62)),
        ("填写新增图书信息", (1015, 360, 310, 62)),
        ("修改已有图书信息", (1015, 535, 310, 62)),
        ("选择删除图书", (180, 535, 310, 62)),
        ("保存图书信息", (1015, 855, 310, 62)),
        ("删除图书记录", (180, 700, 310, 62)),
        ("返回图书列表", (610, 980, 280, 62)),
        ("提示信息错误", (610, 700, 280, 62)),
    ]:
        draw_action(d, box, text)
    draw_decision(d, (590, 335, 320, 120), "选择管理操作")
    draw_decision(d, (1005, 680, 330, 120), "图书信息是否合法")
    draw_arrow(d, [(750, 124), (750, 145)])
    draw_arrow(d, [(750, 207), (750, 235)])
    draw_arrow(d, [(750, 297), (750, 335)])
    draw_arrow(d, [(910, 395), (1015, 391)], "新增", (965, 370))
    draw_arrow(d, [(1170, 422), (1170, 680)])
    draw_arrow(d, [(910, 395), (1015, 566)], "编辑", (975, 525))
    draw_arrow(d, [(1170, 597), (1170, 680)])
    draw_arrow(d, [(590, 395), (490, 566)], "删除", (525, 500))
    draw_arrow(d, [(335, 597), (335, 700)])
    draw_arrow(d, [(490, 731), (610, 1011)])
    draw_arrow(d, [(1170, 800), (1170, 855)], "是", (1195, 825))
    draw_arrow(d, [(1170, 917), (1170, 1011), (890, 1011)])
    draw_arrow(d, [(1005, 740), (890, 731)], "否", (945, 715))
    draw_arrow(d, [(610, 731), (505, 731), (505, 265), (750, 265)])
    draw_arrow(d, [(750, 1042), (750, 1085)])
    draw_end(d, 750, 1085)
    return save(img, "06_管理员图书信息管理活动图.png")


def make_sheet(paths):
    thumbs = []
    for p in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((360, 260))
        thumbs.append((Path(p).name, im.copy()))
    sheet = Image.new("RGB", (860, 990), "#FFFFFF")
    d = ImageDraw.Draw(sheet)
    for i, (name, im) in enumerate(thumbs):
        x = 30 + (i % 2) * 430
        y = 20 + (i // 2) * 320
        sheet.paste(im, (x, y))
        d.text((x, y + 270), name, font=get_font(18), fill="#111111")
    sheet_path = OUT / "活动图总览.png"
    sheet.save(sheet_path)
    return sheet_path


if __name__ == "__main__":
    paths = [
        diagram_login(),
        diagram_borrow(),
        diagram_seat(),
        diagram_crossing(),
        diagram_review(),
        diagram_admin_book(),
    ]
    sheet = make_sheet(paths)
    print(str(sheet))
    for p in paths:
        print(str(p))
