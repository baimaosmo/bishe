from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "数据库设计"
OUT_DIR.mkdir(parents=True, exist_ok=True)


TABLES = [
    {
        "name": "users",
        "cn": "用户信息表",
        "headers": ["id", "username", "email", "password_hash", "role", "avatar"],
        "rows": [
            [1, "admin", "admin@library.edu.cn", "pbkdf2_admin_001", "admin", "avatars/admin.png"],
            [2, "reader001", "reader001@library.edu.cn", "pbkdf2_user_001", "user", "avatars/user001.png"],
            [3, "reader002", "reader002@library.edu.cn", "pbkdf2_user_002", "user", "avatars/user002.png"],
            [4, "reader003", "reader003@library.edu.cn", "pbkdf2_user_003", "user", "avatars/user003.png"],
        ],
    },
    {
        "name": "students",
        "cn": "学生信息表",
        "headers": ["id", "student_no", "name", "gender", "major", "department", "password_hash", "avatar"],
        "rows": [
            [1, "20210001", "张明", "男", "计算机科学与技术", "计算机学院", "pbkdf2_stu_001", "avatars/student001.png"],
            [2, "20210002", "李雪", "女", "软件工程", "计算机学院", "pbkdf2_stu_002", "avatars/student002.png"],
            [3, "20210003", "王强", "男", "数据科学与大数据技术", "计算机学院", "pbkdf2_stu_003", "avatars/student003.png"],
            [4, "20210004", "赵敏", "女", "信息管理与信息系统", "管理学院", "pbkdf2_stu_004", "avatars/student004.png"],
            [5, "20210005", "陈宇", "男", "人工智能", "计算机学院", "pbkdf2_stu_005", "avatars/student005.png"],
        ],
    },
    {
        "name": "teachers",
        "cn": "教师信息表",
        "headers": ["id", "job_no", "name", "gender", "major", "department", "password_hash", "avatar"],
        "rows": [
            [1, "T202001", "刘老师", "男", "数据库技术", "计算机学院", "pbkdf2_tea_001", "avatars/teacher001.png"],
            [2, "T202002", "周老师", "女", "软件工程", "计算机学院", "pbkdf2_tea_002", "avatars/teacher002.png"],
            [3, "T202003", "孙老师", "男", "人工智能", "计算机学院", "pbkdf2_tea_003", "avatars/teacher003.png"],
        ],
    },
    {
        "name": "publishers",
        "cn": "出版社信息表",
        "headers": ["id", "name", "created_at"],
        "rows": [
            [1, "清华大学出版社", "2026-01-05 09:00:00"],
            [2, "人民邮电出版社", "2026-01-06 09:30:00"],
            [3, "机械工业出版社", "2026-01-07 10:00:00"],
            [4, "电子工业出版社", "2026-01-08 10:30:00"],
        ],
    },
    {
        "name": "books",
        "cn": "图书信息表",
        "headers": ["id", "title", "author", "publisher", "isbn", "category", "floor", "area", "shelf", "status", "description", "cover_image", "add_time"],
        "rows": [
            [1, "Python程序设计基础", "李华", "清华大学出版社", "9787302500011", "计算机", 2, "A区", "A-01", "borrowed", "Python语言基础与案例实践", "covers/python.png", "2026-02-01 09:00:00"],
            [2, "数据库系统概论", "王珊", "高等教育出版社", "9787040406641", "计算机", 2, "A区", "A-02", "available", "数据库原理与关系模型", "covers/database.png", "2026-02-02 09:10:00"],
            [3, "软件工程导论", "张海藩", "清华大学出版社", "9787302500028", "软件工程", 2, "B区", "B-01", "available", "软件工程方法与项目管理", "covers/se.png", "2026-02-03 09:20:00"],
            [4, "人工智能导论", "陈斌", "机械工业出版社", "9787111600030", "人工智能", 3, "A区", "A-03", "borrowed", "人工智能基本理论与应用", "covers/ai.png", "2026-02-04 09:30:00"],
            [5, "Web开发实战", "刘洋", "人民邮电出版社", "9787115500045", "Web开发", 3, "B区", "B-02", "available", "Web前后端开发案例", "covers/web.png", "2026-02-05 09:40:00"],
            [6, "数据结构与算法", "严蔚敏", "清华大学出版社", "9787302500066", "计算机", 2, "C区", "C-01", "available", "常用数据结构与算法分析", "covers/ds.png", "2026-02-06 09:50:00"],
            [7, "机器学习实践", "周志华", "电子工业出版社", "9787121300077", "人工智能", 3, "C区", "C-02", "available", "机器学习算法与实践案例", "covers/ml.png", "2026-02-07 10:00:00"],
            [8, "信息系统分析与设计", "赵磊", "机械工业出版社", "9787111600085", "信息管理", 4, "A区", "A-04", "available", "信息系统建模与设计方法", "covers/is.png", "2026-02-08 10:10:00"],
        ],
    },
    {
        "name": "borrow_records",
        "cn": "借阅记录表",
        "headers": ["id", "user_id", "student_id", "teacher_id", "book_id", "borrow_time", "return_time", "status"],
        "rows": [
            [1, "", 1, "", 1, "2026-03-01 09:10:00", "", "borrowing"],
            [2, "", 2, "", 2, "2026-03-02 10:20:00", "2026-03-10 15:30:00", "returned"],
            [3, "", "", 1, 4, "2026-03-03 11:00:00", "", "borrowing"],
            [4, 2, "", "", 5, "2026-03-04 13:20:00", "2026-03-12 16:00:00", "returned"],
            [5, "", 3, "", 6, "2026-03-05 14:00:00", "2026-03-15 10:00:00", "returned"],
            [6, "", "", 2, 7, "2026-03-06 15:00:00", "2026-03-20 09:30:00", "returned"],
        ],
    },
    {
        "name": "seats",
        "cn": "座位信息表",
        "headers": ["id", "floor", "area", "seat_number", "has_power", "status"],
        "rows": [
            [1, 1, "自习A区", "A101", 1, "occupied"],
            [2, 1, "自习A区", "A102", 0, "free"],
            [3, 1, "自习B区", "B101", 1, "free"],
            [4, 2, "电子阅览区", "E201", 1, "occupied"],
            [5, 2, "电子阅览区", "E202", 1, "free"],
            [6, 3, "安静学习区", "Q301", 0, "free"],
        ],
    },
    {
        "name": "seat_reservations",
        "cn": "座位预约记录表",
        "headers": ["id", "user_id", "student_id", "teacher_id", "seat_id", "start_time", "end_time", "status"],
        "rows": [
            [1, "", 1, "", 1, "2026-03-21 08:30:00", "", "active"],
            [2, "", "", 1, 4, "2026-03-21 09:00:00", "", "active"],
            [3, 2, "", "", 2, "2026-03-20 14:00:00", "2026-03-20 17:00:00", "completed"],
            [4, "", 3, "", 3, "2026-03-19 10:00:00", "2026-03-19 12:00:00", "completed"],
            [5, "", "", 2, 5, "2026-03-18 15:00:00", "2026-03-18 18:00:00", "completed"],
        ],
    },
    {
        "name": "drift_books",
        "cn": "漂流图书信息表",
        "headers": ["id", "title", "course_related", "condition", "description", "status", "publish_time", "provider_user_id", "provider_student_id", "provider_teacher_id", "receiver_user_id", "receiver_student_id", "receiver_teacher_id"],
        "rows": [
            [1, "高等数学辅导书", "高等数学", "良好", "适合大一学生复习使用", "drifting", "2026-03-01 09:00:00", "", 1, "", "", "", ""],
            [2, "Java程序设计", "Java开发", "一般", "书内有少量笔记", "claimed", "2026-03-02 10:00:00", "", 2, "", "", 3, ""],
            [3, "考研英语词汇", "考研英语", "良好", "词汇书保存完整", "drifting", "2026-03-03 11:00:00", 2, "", "", "", "", ""],
            [4, "算法竞赛入门", "算法设计", "较旧", "适合算法入门练习", "drifting", "2026-03-04 12:00:00", "", "", 2, "", "", ""],
        ],
    },
    {
        "name": "drift_requests",
        "cn": "漂流图书申请表",
        "headers": ["id", "book_id", "message", "status", "create_time", "receiver_user_id", "receiver_student_id", "receiver_teacher_id"],
        "rows": [
            [1, 1, "想借来复习高等数学", "pending", "2026-03-05 09:20:00", "", 4, ""],
            [2, 2, "正在学习Java课程", "accepted", "2026-03-06 10:30:00", "", 3, ""],
            [3, 3, "准备考研英语复习", "pending", "2026-03-07 11:40:00", 3, "", ""],
            [4, 4, "想学习算法竞赛基础", "rejected", "2026-03-08 12:10:00", "", 5, ""],
        ],
    },
    {
        "name": "book_favorites",
        "cn": "图书收藏表",
        "headers": ["id", "book_id", "user_id", "student_id", "teacher_id", "created_at"],
        "rows": [
            [1, 2, "", 1, "", "2026-03-10 09:00:00"],
            [2, 3, "", 2, "", "2026-03-10 09:10:00"],
            [3, 5, 2, "", "", "2026-03-10 09:20:00"],
            [4, 7, "", "", 1, "2026-03-10 09:30:00"],
            [5, 8, "", 4, "", "2026-03-10 09:40:00"],
            [6, 6, "", "", 2, "2026-03-10 09:50:00"],
        ],
    },
    {
        "name": "book_reviews",
        "cn": "图书评价表",
        "headers": ["id", "book_id", "user_id", "student_id", "teacher_id", "rating", "content", "status", "created_at"],
        "rows": [
            [1, 2, "", 2, "", 5, "内容系统清晰适合复习数据库基础", "approved", "2026-03-12 10:00:00"],
            [2, 5, 2, "", "", 4, "案例比较完整对Web开发有帮助", "approved", "2026-03-12 10:20:00"],
            [3, 6, "", 3, "", 5, "算法讲解清楚适合课程学习", "pending", "2026-03-13 11:00:00"],
            [4, 7, "", "", 2, 4, "机器学习章节内容较全面", "approved", "2026-03-14 12:00:00"],
            [5, 3, "", 4, "", 3, "部分章节较基础适合入门", "rejected", "2026-03-15 13:00:00"],
        ],
    },
]


def csv_line(values):
    return ",".join(str(v) for v in values)


def sql_value(value):
    if value == "":
        return "NULL"
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def main():
    lines = [
        "数据库表样例数据（逗号分隔版）",
        "",
        "说明：以下数据用于论文数据库设计部分展示。空值位置表示 NULL，外键编号已按样例数据保持对应关系。",
        "",
    ]
    sql_lines = [
        "-- 数据库表样例数据",
        "-- 说明：密码字段为论文展示用示例值，实际系统运行时应使用 Werkzeug 生成的加密哈希。",
        "",
    ]
    for idx, table in enumerate(TABLES, start=1):
        lines.append(f"{idx}. {table['name']}：{table['cn']}样例数据")
        lines.append(csv_line(table["headers"]))
        for row in table["rows"]:
            lines.append(csv_line(row))
        lines.append("")

        columns = ", ".join(table["headers"])
        for row in table["rows"]:
            values = ", ".join(sql_value(value) for value in row)
            sql_lines.append(f"INSERT INTO {table['name']} ({columns}) VALUES ({values});")
        sql_lines.append("")

    out = OUT_DIR / "数据库表样例数据_逗号分隔版.txt"
    out.write_text("\n".join(lines), encoding="utf-8")
    sql_out = OUT_DIR / "数据库表样例数据.sql"
    sql_out.write_text("\n".join(sql_lines), encoding="utf-8")
    print(out)
    print(sql_out)


if __name__ == "__main__":
    main()
