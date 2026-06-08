from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "活动图图片"
INPUT_FILES = [
    BASE_DIR / "读者用户功能活动图.puml",
    BASE_DIR / "管理员用户功能活动图.puml",
]

FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\Noto Sans SC (TrueType).otf"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\simsun.ttc"),
]


def pick_font():
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    return None


FONT_PATH = pick_font()


def font(size, bold=False):
    if bold:
        bold_path = Path(r"C:\Windows\Fonts\msyhbd.ttc")
        if bold_path.exists():
            return ImageFont.truetype(str(bold_path), size)
    if FONT_PATH:
        return ImageFont.truetype(str(FONT_PATH), size)
    return ImageFont.load_default()


TITLE_FONT = font(30, bold=True)
NODE_FONT = font(22)
SMALL_FONT = font(18)


def text_size(draw, text, used_font):
    lines = text.split("\n")
    widths = []
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=used_font)
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])
    return max(widths, default=0), sum(heights) + max(0, len(lines) - 1) * 8


def parse_blocks(text):
    pattern = re.compile(r"@startuml[^\n]*\n(.*?)@enduml", re.S)
    return pattern.findall(text)


def parse_activity(block):
    title_match = re.search(r"^title\s+(.+)$", block, re.M)
    title = title_match.group(1).strip() if title_match else "活动图"

    actions = []
    in_body = False
    for raw in block.splitlines():
        line = raw.strip()
        if line == "start":
            in_body = True
            continue
        if not in_body:
            continue
        if line == "stop":
            break
        if line in {"fork", "fork again", "end fork"}:
            actions.append(line)
            continue
        if line.startswith(":") and line.endswith(";"):
            label = line[1:-1].replace("\\n", "\n")
            actions.append(label)

    pre_actions = []
    branches = []
    current = None
    in_fork = False
    post_actions = []
    seen_fork_end = False

    for item in actions:
        if item == "fork":
            in_fork = True
            current = []
            branches.append(current)
        elif item == "fork again":
            current = []
            branches.append(current)
        elif item == "end fork":
            in_fork = False
            current = None
            seen_fork_end = True
        elif in_fork and current is not None:
            current.append(item)
        elif seen_fork_end:
            post_actions.append(item)
        else:
            pre_actions.append(item)

    return title, pre_actions, branches, post_actions


def node_dimensions(draw, label):
    w, h = text_size(draw, label, NODE_FONT)
    return max(180, w + 44), max(56, h + 28)


def draw_centered_text(draw, box, text, used_font, fill):
    x1, y1, x2, y2 = box
    lines = text.split("\n")
    total_w, total_h = text_size(draw, text, used_font)
    y = y1 + ((y2 - y1) - total_h) / 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=used_font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        x = x1 + ((x2 - x1) - w) / 2
        draw.text((x, y), line, font=used_font, fill=fill)
        y += h + 8


def draw_arrow(draw, x1, y1, x2, y2, width=3):
    draw.line((x1, y1, x2, y2), fill="black", width=width)
    if y2 >= y1:
        pts = [(x2, y2), (x2 - 8, y2 - 13), (x2 + 8, y2 - 13)]
    else:
        pts = [(x2, y2), (x2 - 8, y2 + 13), (x2 + 8, y2 + 13)]
    draw.polygon(pts, fill="black")


def draw_node(draw, cx, y, label):
    w, h = node_dimensions(draw, label)
    box = (cx - w / 2, y, cx + w / 2, y + h)
    draw.rounded_rectangle(box, radius=18, fill="black", outline="black", width=2)
    draw_centered_text(draw, box, label, NODE_FONT, "white")
    return box


def safe_filename(title):
    name = re.sub(r'[\\/:*?"<>|]+', "_", title)
    return name.strip() or "活动图"


def render_activity(title, pre_actions, branches, post_actions, output_path):
    probe = Image.new("RGB", (10, 10), "white")
    draw = ImageDraw.Draw(probe)

    branch_count = max(1, len(branches))
    all_labels = pre_actions + post_actions + [label for branch in branches for label in branch]
    max_node_width = max((node_dimensions(draw, label)[0] for label in all_labels), default=180)
    col_gap = max(300, int(max_node_width + 80))
    margin_x = 80
    center_x = margin_x + (branch_count - 1) * col_gap / 2 + 140
    width = int(max(780, margin_x * 2 + (branch_count - 1) * col_gap + 280))

    y = 28
    title_w, title_h = text_size(draw, title, TITLE_FONT)
    y += title_h + 30
    y += 28 + 30

    for label in pre_actions:
        _, h = node_dimensions(draw, label)
        y += h + 42

    if branches:
        y += 28
        branch_heights = []
        for branch in branches:
            bh = 0
            for label in branch:
                _, h = node_dimensions(draw, label)
                bh += h + 42
            branch_heights.append(max(70, bh))
        y += max(branch_heights) + 28

    for label in post_actions:
        _, h = node_dimensions(draw, label)
        y += h + 42

    height = int(y + 70)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Title
    draw_centered_text(draw, (0, 18, width, 64), title, TITLE_FONT, "black")

    current_y = 78
    start_r = 18
    draw.ellipse(
        (center_x - start_r, current_y, center_x + start_r, current_y + start_r * 2),
        fill="black",
        outline="black",
    )
    prev_bottom = current_y + start_r * 2
    current_y = prev_bottom + 26

    for label in pre_actions:
        box = draw_node(draw, center_x, current_y, label)
        draw_arrow(draw, center_x, prev_bottom, center_x, box[1] - 2)
        prev_bottom = box[3]
        current_y = prev_bottom + 42

    if branches:
        fork_y = current_y
        left_x = margin_x
        right_x = width - margin_x
        draw.rounded_rectangle((left_x, fork_y, right_x, fork_y + 10), radius=4, fill="black")
        draw_arrow(draw, center_x, prev_bottom, center_x, fork_y - 2)

        branch_top = fork_y + 50
        branch_centers = [
            center_x - (branch_count - 1) * col_gap / 2 + index * col_gap
            for index in range(branch_count)
        ]

        branch_bottoms = []
        for cx, branch in zip(branch_centers, branches):
            draw_arrow(draw, cx, fork_y + 10, cx, branch_top - 2)
            by = branch_top
            local_prev = branch_top
            for index, label in enumerate(branch):
                box = draw_node(draw, cx, by, label)
                if index > 0:
                    draw_arrow(draw, cx, local_prev, cx, box[1] - 2)
                local_prev = box[3]
                by = box[3] + 42
            branch_bottoms.append(local_prev)

        join_y = max(branch_bottoms) + 38
        draw.rounded_rectangle((left_x, join_y, right_x, join_y + 10), radius=4, fill="black")
        for cx, bottom in zip(branch_centers, branch_bottoms):
            draw_arrow(draw, cx, bottom, cx, join_y - 2)
        prev_bottom = join_y + 10
        current_y = prev_bottom + 42

    for label in post_actions:
        box = draw_node(draw, center_x, current_y, label)
        draw_arrow(draw, center_x, prev_bottom, center_x, box[1] - 2)
        prev_bottom = box[3]
        current_y = prev_bottom + 42

    end_y = current_y
    draw_arrow(draw, center_x, prev_bottom, center_x, end_y - 2)
    draw.ellipse((center_x - 16, end_y, center_x + 16, end_y + 32), fill="white", outline="black", width=3)
    draw.ellipse((center_x - 9, end_y + 7, center_x + 9, end_y + 25), fill="black")

    image.save(output_path)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    created = []
    for input_file in INPUT_FILES:
        text = input_file.read_text(encoding="utf-8-sig")
        for block in parse_blocks(text):
            title, pre_actions, branches, post_actions = parse_activity(block)
            output_path = OUTPUT_DIR / f"{safe_filename(title)}.png"
            render_activity(title, pre_actions, branches, post_actions, output_path)
            created.append(output_path)
    print(f"generated {len(created)} images")
    for path in created:
        print(path)


if __name__ == "__main__":
    main()
