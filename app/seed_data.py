# =============================================================================
# app/seed_data.py — 种子数据生成模块
# 被 run.py 调用，用于快速初始化开发/测试环境中的全套示例数据
# 包含: 多类型用户、出版社、图书、座位、借阅记录、预约记录、
#        漂流数据、收藏、评价、以及近30天的大量模拟数据
# 所有函数都做幂等处理 — 重复调用不会产生重复数据
# =============================================================================

import random  # 用于生成随机模拟数据
from datetime import datetime, timedelta  # 时间计算

from app import db
from app.models import (
    Book, BookFavorite, BookReview, BorrowRecord,
    DriftBook, DriftRequest, Publisher,
    Seat, SeatReservation, Student, Teacher, User,
)


def dt(value):
    """
    字符串转 datetime 工具函数
    参数: value — 'YYYY-MM-DD HH:MM:SS' 格式的字符串
    返回: datetime 对象
    """
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def first_or_create(model, defaults=None, **filters):
    """
    通用"如果不存在则创建"工具函数（幂等操作）
    参数:
      - model: SQLAlchemy 模型类
      - defaults: 创建时使用的额外字段字典
      - **filters: 用于查找的过滤条件
    返回: (instance, created) — 模型实例和是否为新创建的布尔值
    """
    # 先查是否存在
    instance = model.query.filter_by(**filters).first()
    if instance:
        return instance, False  # 已存在，直接返回

    # 不存在则创建
    params = dict(filters)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    db.session.add(instance)
    db.session.flush()  # flush 生成 ID 但不提交事务
    return instance, True


# ==================== 1. 创建多类型用户账号 ====================

def seed_accounts():
    """
    创建系统需要的各种用户账号
    - admin: 管理员（users 表）
    - reader001~003: 普通注册用户（users 表）
    - 20210001~20210005: 学生用户（students 表）
    - T202001~T202003: 教师用户（teachers 表）
    """

    # ----- 普通用户（users 表） -----
    users = [
        ("admin", "admin@library.edu.cn", "Admin@123", "admin", "avatars/admin.png"),
        ("reader001", "reader001@library.edu.cn", "User@123", "user", "avatars/user001.png"),
        ("reader002", "reader002@library.edu.cn", "User@123", "user", "avatars/user002.png"),
        ("reader003", "reader003@library.edu.cn", "User@123", "user", "avatars/user003.png"),
    ]
    for username, email, password, role, avatar in users:
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username, email=email, role=role, avatar=avatar)
            user.set_password(password)
            db.session.add(user)
        elif not user.password_hash:
            # 账号存在但没密码（兼容旧数据修复）
            user.set_password(password)

    # ----- 学生用户（students 表） -----
    students = [
        ("20210001", "张明", "男", "计算机科学与技术", "计算机学院", "avatars/student001.png"),
        ("20210002", "李雪", "女", "软件工程", "计算机学院", "avatars/student002.png"),
        ("20210003", "王强", "男", "数据科学与大数据技术", "计算机学院", "avatars/student003.png"),
        ("20210004", "赵敏", "女", "信息管理与信息系统", "管理学院", "avatars/student004.png"),
        ("20210005", "陈宇", "男", "人工智能", "计算机学院", "avatars/student005.png"),
    ]
    for student_no, name, gender, major, department, avatar in students:
        student = Student.query.filter_by(student_no=student_no).first()
        if not student:
            student = Student(
                student_no=student_no, name=name, gender=gender,
                major=major, department=department, avatar=avatar,
            )
            student.set_password("Student@123")  # 默认密码
            db.session.add(student)
        elif not student.password_hash:
            student.set_password("Student@123")

    # ----- 教师用户（teachers 表） -----
    teachers = [
        ("T202001", "刘老师", "男", "数据库技术", "计算机学院", "avatars/teacher001.png"),
        ("T202002", "周老师", "女", "软件工程", "计算机学院", "avatars/teacher002.png"),
        ("T202003", "孙老师", "男", "人工智能", "计算机学院", "avatars/teacher003.png"),
    ]
    for job_no, name, gender, major, department, avatar in teachers:
        teacher = Teacher.query.filter_by(job_no=job_no).first()
        if not teacher:
            teacher = Teacher(
                job_no=job_no, name=name, gender=gender,
                major=major, department=department, avatar=avatar,
            )
            teacher.set_password("Teacher@123")  # 默认密码
            db.session.add(teacher)
        elif not teacher.password_hash:
            teacher.set_password("Teacher@123")


# ==================== 2. 创建出版社和图书 ====================

def seed_publishers_and_books():
    """
    创建预置出版社和示例图书数据
    图书包含完整的馆藏位置信息、封面图片路径、简介等
    """

    # 创建 5 个常见出版社
    for name in ["清华大学出版社", "人民邮电出版社", "机械工业出版社", "电子工业出版社", "高等教育出版社"]:
        first_or_create(Publisher, name=name)

    # 定义 8 本示例图书
    books = [
        ("Python程序设计基础", "李华", "清华大学出版社", "9787302500011", "计算机", 2, "A区", "A-01", "borrowed", "Python语言基础与案例实践", "uploads/book_covers/python.png", "2026-02-01 09:00:00"),
        ("数据库系统概论", "王珊", "高等教育出版社", "9787040406641", "计算机", 2, "A区", "A-02", "available", "数据库原理与关系模型", "uploads/book_covers/database.png", "2026-02-02 09:10:00"),
        ("软件工程导论", "张海藩", "清华大学出版社", "9787302500028", "软件工程", 2, "B区", "B-01", "available", "软件工程方法与项目管理", "uploads/book_covers/se.png", "2026-02-03 09:20:00"),
        ("人工智能导论", "陈斌", "机械工业出版社", "9787111600030", "人工智能", 3, "A区", "A-03", "borrowed", "人工智能基本理论与应用", "uploads/book_covers/ai.png", "2026-02-04 09:30:00"),
        ("Web开发实战", "刘洋", "人民邮电出版社", "9787115500045", "Web开发", 3, "B区", "B-02", "available", "Web前后端开发案例", "uploads/book_covers/web.png", "2026-02-05 09:40:00"),
        ("数据结构与算法", "严蔚敏", "清华大学出版社", "9787302500066", "计算机", 2, "C区", "C-01", "available", "常用数据结构与算法分析", "uploads/book_covers/ds.png", "2026-02-06 09:50:00"),
        ("机器学习实践", "周志华", "电子工业出版社", "9787121300077", "人工智能", 3, "C区", "C-02", "available", "机器学习算法与实践案例", "uploads/book_covers/ml.png", "2026-02-07 10:00:00"),
        ("信息系统分析与设计", "赵磊", "机械工业出版社", "9787111600085", "信息管理", 4, "A区", "A-04", "available", "信息系统建模与设计方法", "uploads/book_covers/is.png", "2026-02-08 10:10:00"),
    ]

    for title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time in books:
        first_or_create(
            Book,
            isbn=isbn,  # 用 ISBN 做唯一查找键
            defaults={
                "title": title,
                "author": author,
                "publisher": publisher,
                "category": category,
                "floor": floor,
                "area": area,
                "shelf": shelf,
                "status": status,
                "description": description,
                "cover_image": cover_image,
                "add_time": dt(add_time),
            },
        )
        # 如果图书已存在但封面路径变了，则更新封面
        book = Book.query.filter_by(isbn=isbn).first()
        if book and book.cover_image != cover_image:
            book.cover_image = cover_image

    # 为部分图书创建副本（同ISBN多册）
    extra_copies = [
        ("9787302500011", 2, "B区", "B-03"),   # Python程序设计基础 第2册
        ("9787040406641", 2, "B区", "B-04"),   # 数据库系统概论 第2册
        ("9787302500066", 2, "C区", "C-03"),   # 数据结构与算法 第2册
    ]
    for isbn, floor, area, shelf in extra_copies:
        existing = Book.query.filter_by(isbn=isbn).first()
        if existing:
            # 检查该ISBN是否已有副本
            copy_count = Book.query.filter_by(isbn=isbn).count()
            if copy_count < 2:
                new_copy = Book(
                    isbn=isbn,
                    title=existing.title,
                    author=existing.author,
                    publisher=existing.publisher,
                    category=existing.category,
                    description=existing.description,
                    cover_image=existing.cover_image,
                    floor=floor,
                    area=area,
                    shelf=shelf,
                    status='available',
                    add_time=existing.add_time
                )
                db.session.add(new_copy)


# ==================== 3. 创建座位 ====================

def seed_seats():
    """
    创建少量示例座位（daoru.py 中已经有大量座位，这里补充不同区域的）
    """
    seats = [
        (1, "自习A区", "A101", True, "occupied"),    # 已被占用
        (1, "自习A区", "A102", False, "free"),         # 空闲无电源
        (1, "自习B区", "B101", True, "free"),          # 空闲有电源
        (2, "电子阅览区", "E201", True, "occupied"),    # 被占用
        (2, "电子阅览区", "E202", True, "free"),
        (3, "安静学习区", "Q301", False, "free"),
    ]
    for floor, area, seat_number, has_power, status in seats:
        first_or_create(
            Seat,
            seat_number=seat_number,
            defaults={"floor": floor, "area": area, "has_power": has_power, "status": status},
        )


# ==================== 4. 构建跨表引用字典 ====================

def account_refs():
    """
    构建全局 ID 引用字典，方便后续种子数据中通过唯一标识（如学号、ISBN）快速找到对应的模型对象
    返回: {"users": {username: User}, "students": {student_no: Student}, ...}
    """
    return {
        "users": {u.username: u for u in User.query.all()},
        "students": {s.student_no: s for s in Student.query.all()},
        "teachers": {t.job_no: t for t in Teacher.query.all()},
        "books": {b.isbn: b for b in Book.query.all()},
        "seats": {s.seat_number: s for s in Seat.query.all()},
    }


# ==================== 5. 创建借阅记录 ====================

def seed_borrow_records(refs):
    """
    创建示例借阅记录
    每条记录通过 student_no / job_no / username 定位借阅者
    """
    records = [
        # (学号, 工号, 用户名, ISBN, 借阅时间, 归还时间, 状态)
        ("20210001", None, None, "9787302500011", "2026-03-01 09:10:00", None, "borrowing"),
        ("20210002", None, None, "9787040406641", "2026-03-02 10:20:00", "2026-03-10 15:30:00", "returned"),
        (None, "T202001", None, "9787111600030", "2026-03-03 11:00:00", None, "borrowing"),
        (None, None, "reader001", "9787115500045", "2026-03-04 13:20:00", "2026-03-12 16:00:00", "returned"),
        ("20210003", None, None, "9787302500066", "2026-03-05 14:00:00", "2026-03-15 10:00:00", "returned"),
        (None, "T202002", None, "9787121300077", "2026-03-06 15:00:00", "2026-03-20 09:30:00", "returned"),
    ]
    for student_no, job_no, username, isbn, borrow_time, return_time, status in records:
        book = refs["books"][isbn]

        # 幂等检查：通过 book_id + borrow_time 判断是否已存在
        exists = BorrowRecord.query.filter_by(book_id=book.id, borrow_time=dt(borrow_time)).first()
        if exists:
            continue

        # 创建借阅记录
        record = BorrowRecord(book_id=book.id, borrow_time=dt(borrow_time), status=status)
        if return_time:
            record.return_time = dt(return_time)

        # 绑定借阅者（三选一）
        if student_no:
            record.student_id = refs["students"][student_no].id
        if job_no:
            record.teacher_id = refs["teachers"][job_no].id
        if username:
            record.user_id = refs["users"][username].id

        db.session.add(record)


# ==================== 6. 创建座位预约记录 ====================

def seed_seat_reservations(refs):
    """
    创建示例座位预约记录
    """
    reservations = [
        # (学号, 工号, 用户名, 座位号, 入座时间, 离座时间, 状态)
        ("20210001", None, None, "A101", "2026-03-21 08:30:00", None, "active"),
        (None, "T202001", None, "E201", "2026-03-21 09:00:00", None, "active"),
        (None, None, "reader001", "A102", "2026-03-20 14:00:00", "2026-03-20 17:00:00", "completed"),
        ("20210003", None, None, "B101", "2026-03-19 10:00:00", "2026-03-19 12:00:00", "completed"),
        (None, "T202002", None, "E202", "2026-03-18 15:00:00", "2026-03-18 18:00:00", "completed"),
    ]
    for student_no, job_no, username, seat_number, start_time, end_time, status in reservations:
        seat = refs["seats"][seat_number]

        # 幂等检查
        exists = SeatReservation.query.filter_by(seat_id=seat.id, start_time=dt(start_time)).first()
        if exists:
            continue

        # 创建预约记录
        reservation = SeatReservation(seat_id=seat.id, start_time=dt(start_time), status=status)
        if end_time:
            reservation.end_time = dt(end_time)

        # 绑定预约者
        if student_no:
            reservation.student_id = refs["students"][student_no].id
        if job_no:
            reservation.teacher_id = refs["teachers"][job_no].id
        if username:
            reservation.user_id = refs["users"][username].id

        db.session.add(reservation)


# ==================== 7. 创建漂流图书数据 ====================

def seed_drift_data(refs):
    """
    创建漂流图书和领取申请记录
    """
    # 漂流图书数据
    drift_books = [
        # (书名, 课程, 新旧程度, 描述, 状态, 发布时间, 提供者用户名, 提供者学号, 提供者工号, 领取者用户名, 领取者学号, 领取者工号)
        ("高等数学辅导书", "高等数学", "良好", "适合大一学生复习使用", "drifting", "2026-03-01 09:00:00", None, "20210001", None, None, None, None),
        ("Java程序设计", "Java开发", "一般", "书内有少量笔记", "claimed", "2026-03-02 10:00:00", None, "20210002", None, None, "20210003", None),
        ("考研英语词汇", "考研英语", "良好", "词汇书保存完整", "drifting", "2026-03-03 11:00:00", "reader001", None, None, None, None, None),
        ("算法竞赛入门", "算法设计", "较旧", "适合算法入门练习", "drifting", "2026-03-04 12:00:00", None, None, "T202002", None, None, None),
    ]
    for title, course, condition, description, status, publish_time, provider_user, provider_student, provider_teacher, receiver_user, receiver_student, receiver_teacher in drift_books:
        drift_book, created = first_or_create(
            DriftBook,
            title=title,
            defaults={
                "course_related": course,
                "condition": condition,
                "description": description,
                "status": status,
                "publish_time": dt(publish_time),
            },
        )
        # 新建时绑定提供者和领取者
        if created:
            if provider_user:
                drift_book.provider_user_id = refs["users"][provider_user].id
            if provider_student:
                drift_book.provider_student_id = refs["students"][provider_student].id
            if provider_teacher:
                drift_book.provider_teacher_id = refs["teachers"][provider_teacher].id
            if receiver_user:
                drift_book.receiver_user_id = refs["users"][receiver_user].id
            if receiver_student:
                drift_book.receiver_student_id = refs["students"][receiver_student].id
            if receiver_teacher:
                drift_book.receiver_teacher_id = refs["teachers"][receiver_teacher].id

    db.session.flush()  # flush 确保 drift_book 的 ID 已生成

    # 构建 {书名: DriftBook对象} 的映射
    drift_map = {book.title: book for book in DriftBook.query.all()}

    # 领取申请数据
    requests = [
        # (漂流书名, 留言, 状态, 申请时间, 申请者用户名, 申请者学号, 申请者工号)
        ("高等数学辅导书", "想借来复习高等数学", "pending", "2026-03-05 09:20:00", None, "20210004", None),
        ("Java程序设计", "正在学习Java课程", "accepted", "2026-03-06 10:30:00", None, "20210003", None),
        ("考研英语词汇", "准备考研英语复习", "pending", "2026-03-07 11:40:00", "reader002", None, None),
        ("算法竞赛入门", "想学习算法竞赛基础", "rejected", "2026-03-08 12:10:00", None, "20210005", None),
    ]
    for title, message, status, create_time, receiver_user, receiver_student, receiver_teacher in requests:
        book = drift_map[title]

        # 幂等检查
        exists = DriftRequest.query.filter_by(book_id=book.id, message=message).first()
        if exists:
            continue

        # 创建申请记录
        request = DriftRequest(book_id=book.id, message=message, status=status, create_time=dt(create_time))
        if receiver_user:
            request.receiver_user_id = refs["users"][receiver_user].id
        if receiver_student:
            request.receiver_student_id = refs["students"][receiver_student].id
        if receiver_teacher:
            request.receiver_teacher_id = refs["teachers"][receiver_teacher].id
        db.session.add(request)


# ==================== 8. 创建互动数据（收藏 + 评价） ====================

def seed_interactions(refs):
    """
    创建图书收藏和评价数据
    """

    # 收藏数据
    favorites = [
        # (ISBN, 用户名, 学号, 工号, 收藏时间)
        ("9787040406641", None, "20210001", None, "2026-03-10 09:00:00"),
        ("9787302500028", None, "20210002", None, "2026-03-10 09:10:00"),
        ("9787115500045", "reader001", None, None, "2026-03-10 09:20:00"),
        ("9787121300077", None, None, "T202001", "2026-03-10 09:30:00"),
        ("9787111600085", None, "20210004", None, "2026-03-10 09:40:00"),
        ("9787302500066", None, None, "T202002", "2026-03-10 09:50:00"),
    ]
    for isbn, username, student_no, job_no, created_at in favorites:
        book = refs["books"][isbn]

        # 构建查询条件
        query = BookFavorite.query.filter_by(book_id=book.id)
        if username:
            query = query.filter_by(user_id=refs["users"][username].id)
        if student_no:
            query = query.filter_by(student_id=refs["students"][student_no].id)
        if job_no:
            query = query.filter_by(teacher_id=refs["teachers"][job_no].id)

        # 幂等检查
        if query.first():
            continue

        # 创建收藏记录
        favorite = BookFavorite(book_id=book.id, created_at=dt(created_at))
        if username:
            favorite.user_id = refs["users"][username].id
        if student_no:
            favorite.student_id = refs["students"][student_no].id
        if job_no:
            favorite.teacher_id = refs["teachers"][job_no].id
        db.session.add(favorite)

    # 评价数据
    reviews = [
        # (ISBN, 用户名, 学号, 工号, 评分, 内容, 审核状态, 创建时间)
        ("9787040406641", None, "20210002", None, 5, "内容系统清晰适合复习数据库基础", "approved", "2026-03-12 10:00:00"),
        ("9787115500045", "reader001", None, None, 4, "案例比较完整对Web开发有帮助", "approved", "2026-03-12 10:20:00"),
        ("9787302500066", None, "20210003", None, 5, "算法讲解清楚适合课程学习", "pending", "2026-03-13 11:00:00"),
        ("9787121300077", None, None, "T202002", 4, "机器学习章节内容较全面", "approved", "2026-03-14 12:00:00"),
        ("9787302500028", None, "20210004", None, 3, "部分章节较基础适合入门", "rejected", "2026-03-15 13:00:00"),
    ]
    for isbn, username, student_no, job_no, rating, content, status, created_at in reviews:
        book = refs["books"][isbn]

        # 幂等检查：通过 book_id + content 判断是否已存在
        exists = BookReview.query.filter_by(book_id=book.id, content=content).first()
        if exists:
            continue

        # 创建评价记录
        review = BookReview(book_id=book.id, rating=rating, content=content, status=status, created_at=dt(created_at))
        if username:
            review.user_id = refs["users"][username].id
        if student_no:
            review.student_id = refs["students"][student_no].id
        if job_no:
            review.teacher_id = refs["teachers"][job_no].id
        db.session.add(review)


# ==================== 9. 生成近 30 天海量模拟数据 ====================

def seed_bulk_recent_data(refs):
    """
    为 AI 数据大屏生成近 30 天的丰富借阅和座位预约模拟数据
    每天随机生成 3~10 条借阅 + 6~20 条座位预约
    这些数据驱动前端数据看板的折线图、饼图和热力图
    """
    random.seed(42)  # 固定随机种子，确保每次生成的数据一致

    today = datetime.now().date()
    start = today - timedelta(days=29)  # 30 天前

    # 获取所有图书和座位
    books = list(refs["books"].values())
    seats = list(refs["seats"].values())

    # 汇总所有用户账号到一个列表
    all_accounts = []
    for s in refs["students"].values():
        all_accounts.append(("student", s))
    for t in refs["teachers"].values():
        all_accounts.append(("teacher", t))
    for u in refs["users"].values():
        all_accounts.append(("user", u))

    # ----- 生成借阅记录：近 30 天每天 3~10 条 -----
    recent_borrow = BorrowRecord.query.filter(
        BorrowRecord.borrow_time >= datetime.combine(start, datetime.min.time())
    ).count()
    if recent_borrow == 0:  # 只有没有近期数据时才生成
        for days_ago in range(29, -1, -1):  # 从 30 天前到今天
            date = start + timedelta(days=days_ago)
            count = random.randint(3, 10)  # 每天随机 3~10 条
            for _ in range(count):
                hour = random.randint(8, 20)    # 随机借阅小时（8:00-20:00）
                minute = random.randint(0, 59)  # 随机分钟
                borrow_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                book = random.choice(books)
                acct_type, acct = random.choice(all_accounts)

                # 55% 概率已归还
                is_returned = random.random() < 0.55
                return_time = None
                status = "borrowing"
                if is_returned and days_ago > 1:  # 至少借出 1 天才归还
                    return_days = random.randint(1, min(days_ago, 10))
                    return_time = borrow_time + timedelta(days=return_days, hours=random.randint(0, 4))
                    if return_time.date() <= today:
                        status = "returned"
                    else:
                        return_time = None  # 归还日期在未来，视为未还

                # 创建记录并绑定借阅者
                record = BorrowRecord(book_id=book.id, borrow_time=borrow_time, status=status)
                if return_time:
                    record.return_time = return_time
                if acct_type == "student":
                    record.student_id = acct.id
                elif acct_type == "teacher":
                    record.teacher_id = acct.id
                else:
                    record.user_id = acct.id
                db.session.add(record)
        print("已生成近30天借阅记录")

    # ----- 生成座位预约记录：近 30 天每天 6~20 条 -----
    recent_seat = SeatReservation.query.filter(
        SeatReservation.start_time >= datetime.combine(start, datetime.min.time())
    ).count()
    if recent_seat == 0:
        for days_ago in range(29, -1, -1):
            date = start + timedelta(days=days_ago)
            weekday = date.weekday()
            # 工作日预约多，周末少
            count = random.randint(10, 20) if weekday < 5 else random.randint(4, 10)
            for _ in range(count):
                hour = random.choice([8, 9, 10, 11, 14, 15, 16, 18, 19, 20])  # 常见预约时段
                minute = random.randint(0, 59)
                start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
                seat = random.choice(seats)
                acct_type, acct = random.choice(all_accounts)

                # 60% 概率已完成
                is_completed = random.random() < 0.6
                end_time = None
                status = "active"
                if is_completed and days_ago > 0:
                    end_time = start_time + timedelta(hours=random.choice([1, 2, 3]))
                    if end_time.date() <= today:
                        status = "completed"
                    else:
                        end_time = None

                reservation = SeatReservation(seat_id=seat.id, start_time=start_time, status=status)
                if end_time:
                    reservation.end_time = end_time
                if acct_type == "student":
                    reservation.student_id = acct.id
                elif acct_type == "teacher":
                    reservation.teacher_id = acct.id
                else:
                    reservation.user_id = acct.id
                db.session.add(reservation)
        print("已生成近30天座位预约记录")

    # ----- 补充更多座位（丰富座位选择） -----
    extra_seats = [
        (1, "自习A区", "A103", True),
        (1, "自习A区", "A104", False),
        (1, "自习A区", "A105", True),
        (1, "自习B区", "B102", False),
        (1, "自习B区", "B103", True),
        (1, "自习B区", "B104", False),
        (2, "电子阅览区", "E203", True),
        (2, "电子阅览区", "E204", True),
        (2, "电子阅览区", "E205", False),
        (2, "静音自习区", "J201", True),
        (2, "静音自习区", "J202", False),
        (2, "静音自习区", "J203", True),
        (3, "安静学习区", "Q302", False),
        (3, "安静学习区", "Q303", True),
        (3, "安静学习区", "Q304", False),
        (3, "安静学习区", "Q305", True),
        (3, "研讨间", "Y301", True),
        (3, "研讨间", "Y302", True),
        (3, "研讨间", "Y303", False),
    ]
    for floor, area, seat_number, has_power in extra_seats:
        first_or_create(
            Seat,
            seat_number=seat_number,
            defaults={"floor": floor, "area": area, "has_power": has_power, "status": "free"},
        )


# ==================== 主入口函数 ====================

def seed_sample_data():
    """
    种子数据主函数 — 按顺序调用各子函数完成数据初始化
    调用顺序: 账号 → 出版社/图书 → 座位 → 借阅 → 预约 → 漂流 → 互动 → 批量模拟数据
    每一步都依赖上一步的 flush 结果，主函数最后统一 commit
    """
    seed_accounts()               # 1. 创建用户
    seed_publishers_and_books()    # 2. 创建出版社和图书
    seed_seats()                   # 3. 创建示例座位
    db.session.flush()             # flush 确保所有 ID 已生成

    refs = account_refs()          # 构建引用字典
    seed_borrow_records(refs)      # 4. 创建借阅记录
    seed_seat_reservations(refs)   # 5. 创建座位预约
    seed_drift_data(refs)          # 6. 创建漂流数据
    seed_interactions(refs)        # 7. 创建收藏和评价

    db.session.flush()             # 再次 flush，更新引用
    refs = account_refs()
    seed_bulk_recent_data(refs)    # 8. 生成近 30 天海量模拟数据

    db.session.commit()            # 所有数据统一提交
