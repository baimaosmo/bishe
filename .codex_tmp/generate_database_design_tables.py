from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "数据库设计"
OUT_DIR.mkdir(parents=True, exist_ok=True)


TABLES = [
    {
        "name": "users",
        "cn": "用户信息表",
        "desc": "用于保存普通注册用户和管理员账号信息，其中 role 字段用于区分普通用户和管理员。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "用户编号"),
            ("username", "varchar(50)", "No", "No", "Not null", "用户名"),
            ("email", "varchar(120)", "No", "No", "Null", "邮箱"),
            ("password_hash", "varchar(255)", "No", "No", "Not null", "加密后的密码"),
            ("role", "varchar(20)", "No", "No", "Null", "角色，user/admin"),
            ("avatar", "varchar(255)", "No", "No", "Null", "头像路径"),
        ],
    },
    {
        "name": "students",
        "cn": "学生信息表",
        "desc": "用于保存管理员批量导入的学生账号信息，学生使用学号登录系统。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "学生编号"),
            ("student_no", "varchar(20)", "No", "No", "Not null", "学号"),
            ("name", "varchar(50)", "No", "No", "Not null", "学生姓名"),
            ("gender", "varchar(10)", "No", "No", "Null", "性别"),
            ("major", "varchar(80)", "No", "No", "Null", "专业"),
            ("department", "varchar(50)", "No", "No", "Null", "院系"),
            ("password_hash", "varchar(255)", "No", "No", "Not null", "加密后的密码"),
            ("avatar", "varchar(255)", "No", "No", "Null", "头像路径"),
        ],
    },
    {
        "name": "teachers",
        "cn": "教师信息表",
        "desc": "用于保存管理员批量导入的教师账号信息，教师使用工号登录系统。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "教师编号"),
            ("job_no", "varchar(20)", "No", "No", "Not null", "工号"),
            ("name", "varchar(50)", "No", "No", "Not null", "教师姓名"),
            ("gender", "varchar(10)", "No", "No", "Null", "性别"),
            ("major", "varchar(80)", "No", "No", "Null", "专业或研究方向"),
            ("department", "varchar(50)", "No", "No", "Null", "院系或部门"),
            ("password_hash", "varchar(255)", "No", "No", "Not null", "加密后的密码"),
            ("avatar", "varchar(255)", "No", "No", "Null", "头像路径"),
        ],
    },
    {
        "name": "publishers",
        "cn": "出版社信息表",
        "desc": "用于保存图书出版社基础信息，便于维护图书来源数据。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "出版社编号"),
            ("name", "varchar(100)", "No", "No", "Not null", "出版社名称"),
            ("created_at", "datetime", "No", "No", "Null", "创建时间"),
        ],
    },
    {
        "name": "books",
        "cn": "图书信息表",
        "desc": "用于保存图书馆馆藏图书的基础信息、馆藏位置、借阅状态和封面信息。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "图书编号"),
            ("title", "varchar(100)", "No", "No", "Not null", "书名"),
            ("author", "varchar(50)", "No", "No", "Not null", "作者"),
            ("publisher", "varchar(100)", "No", "No", "Null", "出版社"),
            ("isbn", "varchar(20)", "No", "No", "Not null", "ISBN 号"),
            ("category", "varchar(50)", "No", "No", "Null", "图书分类"),
            ("floor", "int", "No", "No", "Null", "所在楼层"),
            ("area", "varchar(20)", "No", "No", "Null", "所在区域"),
            ("shelf", "varchar(20)", "No", "No", "Null", "书架号"),
            ("status", "varchar(20)", "No", "No", "Null", "图书状态，available/borrowed"),
            ("description", "text", "No", "No", "Null", "图书简介"),
            ("cover_image", "varchar(255)", "No", "No", "Null", "封面图片路径"),
            ("add_time", "datetime", "No", "No", "Null", "入库时间"),
        ],
    },
    {
        "name": "borrow_records",
        "cn": "借阅记录表",
        "desc": "用于保存用户借阅和归还图书的记录，支持普通用户、学生和教师三类账号。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "借阅记录编号"),
            ("user_id", "int", "No", "Yes", "Null", "普通用户编号，关联 users.id"),
            ("student_id", "int", "No", "Yes", "Null", "学生编号，关联 students.id"),
            ("teacher_id", "int", "No", "Yes", "Null", "教师编号，关联 teachers.id"),
            ("book_id", "int", "No", "Yes", "Not null", "图书编号，关联 books.id"),
            ("borrow_time", "datetime", "No", "No", "Null", "借阅时间"),
            ("return_time", "datetime", "No", "No", "Null", "归还时间"),
            ("status", "varchar(20)", "No", "No", "Null", "借阅状态，borrowing/returned"),
        ],
    },
    {
        "name": "seats",
        "cn": "座位信息表",
        "desc": "用于保存图书馆座位的楼层、区域、编号、电源配置和使用状态。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "座位编号"),
            ("floor", "int", "No", "No", "Not null", "所在楼层"),
            ("area", "varchar(50)", "No", "No", "Not null", "所属区域"),
            ("seat_number", "varchar(20)", "No", "No", "Not null", "座位号"),
            ("has_power", "tinyint(1)", "No", "No", "Null", "是否有电源"),
            ("status", "varchar(20)", "No", "No", "Null", "座位状态，free/occupied"),
        ],
    },
    {
        "name": "seat_reservations",
        "cn": "座位预约记录表",
        "desc": "用于保存用户预约和释放座位的记录，支持普通用户、学生和教师三类账号。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "预约记录编号"),
            ("user_id", "int", "No", "Yes", "Null", "普通用户编号，关联 users.id"),
            ("student_id", "int", "No", "Yes", "Null", "学生编号，关联 students.id"),
            ("teacher_id", "int", "No", "Yes", "Null", "教师编号，关联 teachers.id"),
            ("seat_id", "int", "No", "Yes", "Not null", "座位编号，关联 seats.id"),
            ("start_time", "datetime", "No", "No", "Null", "入座时间"),
            ("end_time", "datetime", "No", "No", "Null", "离座时间"),
            ("status", "varchar(20)", "No", "No", "Null", "预约状态，active/completed"),
        ],
    },
    {
        "name": "drift_books",
        "cn": "漂流图书信息表",
        "desc": "用于保存用户发布的漂流图书信息，以及提供者、领取者和漂流状态。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "漂流图书编号"),
            ("title", "varchar(100)", "No", "No", "Not null", "书名"),
            ("course_related", "varchar(100)", "No", "No", "Null", "关联课程"),
            ("condition", "varchar(20)", "No", "No", "Null", "新旧程度"),
            ("description", "text", "No", "No", "Null", "补充描述或交换条件"),
            ("status", "varchar(20)", "No", "No", "Null", "漂流状态，drifting/claimed"),
            ("publish_time", "datetime", "No", "No", "Null", "发布时间"),
            ("provider_user_id", "int", "No", "Yes", "Null", "提供者普通用户编号，关联 users.id"),
            ("provider_student_id", "int", "No", "Yes", "Null", "提供者学生编号，关联 students.id"),
            ("provider_teacher_id", "int", "No", "Yes", "Null", "提供者教师编号，关联 teachers.id"),
            ("receiver_user_id", "int", "No", "Yes", "Null", "领取者普通用户编号，关联 users.id"),
            ("receiver_student_id", "int", "No", "Yes", "Null", "领取者学生编号，关联 students.id"),
            ("receiver_teacher_id", "int", "No", "Yes", "Null", "领取者教师编号，关联 teachers.id"),
        ],
    },
    {
        "name": "drift_requests",
        "cn": "漂流图书申请表",
        "desc": "用于保存用户对漂流图书提交的领取申请及申请处理状态。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "申请编号"),
            ("book_id", "int", "No", "Yes", "Not null", "漂流图书编号，关联 drift_books.id"),
            ("message", "text", "No", "No", "Null", "给提供者的留言"),
            ("status", "varchar(20)", "No", "No", "Null", "申请状态，pending/accepted/rejected"),
            ("create_time", "datetime", "No", "No", "Null", "申请时间"),
            ("receiver_user_id", "int", "No", "Yes", "Null", "申请者普通用户编号，关联 users.id"),
            ("receiver_student_id", "int", "No", "Yes", "Null", "申请者学生编号，关联 students.id"),
            ("receiver_teacher_id", "int", "No", "Yes", "Null", "申请者教师编号，关联 teachers.id"),
        ],
    },
    {
        "name": "book_favorites",
        "cn": "图书收藏表",
        "desc": "用于保存用户收藏图书的记录，支持普通用户、学生和教师三类账号。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "收藏编号"),
            ("book_id", "int", "No", "Yes", "Not null", "图书编号，关联 books.id"),
            ("user_id", "int", "No", "Yes", "Null", "普通用户编号，关联 users.id"),
            ("student_id", "int", "No", "Yes", "Null", "学生编号，关联 students.id"),
            ("teacher_id", "int", "No", "Yes", "Null", "教师编号，关联 teachers.id"),
            ("created_at", "datetime", "No", "No", "Null", "收藏时间"),
        ],
    },
    {
        "name": "book_reviews",
        "cn": "图书评价表",
        "desc": "用于保存用户对图书提交的评价内容、评分和 AI 审核状态。",
        "fields": [
            ("id", "int", "Yes", "No", "Not null", "评价编号"),
            ("book_id", "int", "No", "Yes", "Not null", "图书编号，关联 books.id"),
            ("user_id", "int", "No", "Yes", "Null", "普通用户编号，关联 users.id"),
            ("student_id", "int", "No", "Yes", "Null", "学生编号，关联 students.id"),
            ("teacher_id", "int", "No", "Yes", "Null", "教师编号，关联 teachers.id"),
            ("rating", "int", "No", "No", "Not null", "评分"),
            ("content", "text", "No", "No", "Not null", "评价内容"),
            ("status", "varchar(20)", "No", "No", "Null", "审核状态，pending/approved/rejected"),
            ("created_at", "datetime", "No", "No", "Null", "评价时间"),
        ],
    },
]


def md_table(fields):
    lines = [
        "| 字段名 | 数据类型 | 主键 | 外键 | 可否为空 | 信息备注 |",
        "|---|---|---|---|---|---|",
    ]
    for row in fields:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main():
    lines = [
        "# 数据库表结构设计",
        "",
        "本系统采用 MySQL 数据库存储业务数据，并通过 SQLAlchemy ORM 模型完成数据访问。数据库表结构主要围绕用户账号、馆藏图书、借阅记录、座位预约、图书漂流、收藏评价和后台统计管理等业务设计。各数据表字段结构如下所示。",
        "",
    ]
    for idx, table in enumerate(TABLES, start=1):
        lines.append(f"{idx}. `{table['name']}`：{table['cn']}如表 4-{idx} 所示。")
        lines.append("")
        lines.append(f"**表 4-{idx} {table['cn']} `{table['name']}`**")
        lines.append("")
        lines.append(md_table(table["fields"]))
        lines.append("")
        lines.append(f"说明：{table['desc']}")
        lines.append("")

    out = OUT_DIR / "数据库表结构设计.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    tsv_lines = [
        "数据库表结构设计（Word 可粘贴表格版）",
        "",
        "说明：以下表格使用制表符分隔，复制到 Word 后可直接粘贴为表格；如未自动成表，可在 Word 中选择“插入 -> 表格 -> 文本转换成表格”，分隔符选择“制表符”。",
        "",
    ]
    headers = ["字段名", "数据类型", "主键", "外键", "可否为空", "信息备注"]
    for idx, table in enumerate(TABLES, start=1):
        tsv_lines.append(f"{idx}. {table['name']}：{table['cn']}如表 4-{idx} 所示。")
        tsv_lines.append(f"表 4-{idx} {table['cn']} {table['name']}")
        tsv_lines.append("\t".join(headers))
        for row in table["fields"]:
            tsv_lines.append("\t".join(row))
        tsv_lines.append("")

    tsv_out = OUT_DIR / "数据库表结构设计_Word可粘贴表格版.txt"
    tsv_out.write_text("\n".join(tsv_lines), encoding="utf-8")

    csv_lines = [
        "数据库表结构设计（逗号分隔版）",
        "",
        "说明：以下表格使用英文逗号分隔，每行格式为：字段名,数据类型,主键,外键,可否为空,信息备注。",
        "",
    ]
    for idx, table in enumerate(TABLES, start=1):
        csv_lines.append(f"{idx}. {table['name']}：{table['cn']}如表 4-{idx} 所示。")
        csv_lines.append(f"表 4-{idx} {table['cn']} {table['name']}")
        csv_lines.append(",".join(headers))
        for row in table["fields"]:
            csv_lines.append(",".join(row))
        csv_lines.append("")

    csv_out = OUT_DIR / "数据库表结构设计_逗号分隔版.txt"
    csv_out.write_text("\n".join(csv_lines), encoding="utf-8")
    print(out)
    print(tsv_out)
    print(csv_out)


if __name__ == "__main__":
    main()
