# =============================================================================
# app/routes/books.py — 图书管理与用户互动路由
# 负责: 图书 CRUD、借阅/归还、收藏、评价(AI审核)、个人中心、推荐、互动管理
# 蓝图名: books_bp，挂载在 /books 前缀下
# =============================================================================

from datetime import datetime
import json  # 解析 AI 返回的 JSON 格式审核结果
import os
import re  # ISBN 校验用的正则表达式
from uuid import uuid4  # 生成唯一文件名
import requests  # 发送 HTTP 请求调用 DeepSeek API
import urllib3  # 禁用 SSL 警告
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy import func  # SQL 聚合函数
from werkzeug.utils import secure_filename  # 安全文件名
from app.models import (
    Book, BorrowRecord, BookFavorite, BookReview,
    SeatReservation, DriftBook, DriftRequest, Publisher,
    Student, Teacher, User
)
from app import db

# 创建蓝图
books_bp = Blueprint('books', __name__)

# 允许上传的图片格式白名单
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# 禁用 urllib3 的 SSL 证书验证警告（调用 DeepSeek API 时产生）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== 通用工具函数 ====================

def save_uploaded_image(file, folder):
    """
    保存上传的图片文件到指定目录
    参数:
      - file: Flask 上传文件对象
      - folder: 子目录名（如 'book_covers'）
    返回: 相对路径字符串，失败返回 None
    """
    if not file or not file.filename:
        return None

    filename = secure_filename(file.filename)

    # 扩展名白名单校验
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
        flash('图片格式仅支持 png、jpg、jpeg、gif、webp。', 'error')
        return None

    ext = filename.rsplit('.', 1)[1].lower()
    upload_dir = os.path.join(current_app.static_folder, 'uploads', folder)
    os.makedirs(upload_dir, exist_ok=True)

    saved_name = f'{uuid4().hex}.{ext}'
    file.save(os.path.join(upload_dir, saved_name))
    return f'uploads/{folder}/{saved_name}'


def current_account_filter(model):
    """
    根据当前 Session 中的账号类型，构造对应模型的查询过滤条件
    例如：如果当前是学生，则返回 model.student_id == session['account_id']
    这样通用函数可以用在任何多账号模型上
    """
    if session.get('account_type') == 'student':
        return model.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return model.teacher_id == session.get('account_id')
    return model.user_id == session.get('account_id')


def assign_current_account(model):
    """
    根据当前 Session 中的账号类型，给模型对象设置对应的外键字段
    例如：如果当前是学生，则 model.student_id = session['account_id']
    """
    if session.get('account_type') == 'student':
        model.student_id = session.get('account_id')
    elif session.get('account_type') == 'teacher':
        model.teacher_id = session.get('account_id')
    else:
        model.user_id = session.get('account_id')


def account_owns(record):
    """
    判断当前登录用户是否"拥有"某条记录
    用于权限校验（如只能归还自己借的书）
    """
    if session.get('account_type') == 'student':
        return record.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return record.teacher_id == session.get('account_id')
    return record.user_id == session.get('account_id')


def validate_isbn(isbn):
    """
    ISBN 校验函数
    支持 ISBN-10（10位）和 ISBN-13（13位），含校验位数学验证
    返回: (清洗后的ISBN字符串, 错误信息或None)
    """
    # 去除短横线和空格
    cleaned = re.sub(r'[-\s]', '', isbn or '')

    # 基本格式校验：必须是 10 位或 13 位纯数字
    if not re.fullmatch(r'\d{10}|\d{13}', cleaned):
        return None, '书籍号/ISBN 必须是 10 位或 13 位数字，可包含短横线。'

    if len(cleaned) == 10:
        # ISBN-10 校验位计算
        total = sum((10 - index) * int(char) for index, char in enumerate(cleaned))
        if total % 11 != 0:
            return None, 'ISBN-10 校验失败，请检查书籍号。'
    else:
        # ISBN-13 校验位计算（交替权重 1 和 3）
        total = sum((1 if index % 2 == 0 else 3) * int(char) for index, char in enumerate(cleaned))
        if total % 10 != 0:
            return None, 'ISBN-13 校验失败，请检查书籍号。'

    return cleaned, None


def get_publishers():
    """获取所有出版社列表，按名称排序，供表单下拉使用"""
    return Publisher.query.order_by(Publisher.name.asc()).all()


def resolve_publisher_from_form():
    """
    从添加/编辑图书表单中解析出版社名称
    优先使用手动输入的自定义出版社；如果该出版社不在数据库中则自动创建
    返回: 出版社名称字符串
    """
    custom_publisher = request.form.get('publisher_custom', '').strip()
    selected_publisher = request.form.get('publisher', '').strip()
    publisher_name = custom_publisher or selected_publisher

    # 如果是新出版社，自动创建到数据库
    if publisher_name and not Publisher.query.filter_by(name=publisher_name).first():
        db.session.add(Publisher(name=publisher_name))

    return publisher_name


def parse_ai_review_result(content):
    """
    解析 DeepSeek API 返回的审核结果
    AI 返回格式: {"status":"approved/rejected","reason":"审核理由"}
    做容错处理：去除 Markdown 标记、提取 JSON
    """
    cleaned = (content or '').strip()

    # 去除可能的 Markdown 代码块标记（```json ... ```）
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # JSON 解析失败，尝试从文本中提取第一个 JSON 对象
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if not match:
            raise ValueError('AI 返回内容不是有效 JSON')
        result = json.loads(match.group(0))

    status = result.get('status')
    reason = (result.get('reason') or '').strip()

    # 校验状态值有效性
    if status not in {'approved', 'rejected'}:
        raise ValueError('AI 返回的审核状态无效')

    # 限制理由长度，防止过长
    return status, reason[:120]


def ai_moderate_review(review):
    """
    调用 DeepSeek API 对图书评价进行 AI 内容审核
    参数: review — BookReview 模型对象
    返回: (status, reason) — 审核状态和理由
    """

    # 系统提示词 — 定义 AI 的审核角色和规则
    system_prompt = """
你是校园图书馆的图书评价审核员。请审核用户提交的图书评价是否适合公开展示。

审核规则：
1. 内容围绕图书阅读体验、书籍质量、作者、内容主题或借阅体验，且表达正常，可以通过。
2. 广告、灌水、无意义文本、辱骂、人身攻击、色情低俗、仇恨歧视、违法违规、泄露隐私、明显与图书无关的内容，必须驳回。
3. 不要因为评价是负面意见就驳回，只要表达文明且与图书有关即可通过。
4. 只输出 JSON，不要输出 Markdown 或其他解释。

输出格式：
{"status":"approved 或 rejected","reason":"一句中文审核理由"}
"""

    # 用户提示词 — 将待审核的评价信息拼接进去
    user_prompt = f"""
图书：{review.book.title if review.book else '未知图书'}
评分：{review.rating}/5
评价内容：{review.content}
"""

    # DeepSeek API 地址
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {current_app.config['DEEPSEEK_API_KEY']}"
    }

    # API 请求体
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,  # 温度=0 确保审核结果稳定一致
        "response_format": {"type": "json_object"}  # 要求 AI 返回 JSON
    }

    # 发送请求（verify=False 跳过 SSL 证书验证）
    response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False,
                             proxies={"http": None, "https": None})
    response.raise_for_status()  # 非 200 状态码会抛出异常

    # 提取 AI 回复内容
    ai_content = response.json()['choices'][0]['message']['content']

    # 解析审核结果
    return parse_ai_review_result(ai_content)


# ==================== 1. 图书列表页 ====================

@books_bp.route('/list')
def book_list():
    """
    图书列表页 — 支持关键词搜索和分类筛选
    搜索范围: 书名、作者、ISBN（模糊匹配）
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取前端传递的搜索参数
    search_query = request.args.get('q', '').strip()  # 关键词
    category = request.args.get('category', '').strip()  # 分类筛选

    # 构造基础查询（从 Book 表出发）
    query = Book.query

    # 如果有搜索关键词，在书名/作者/ISBN 三字段中模糊匹配
    if search_query:
        query = query.filter(
            db.or_(
                Book.title.like(f'%{search_query}%'),
                Book.author.like(f'%{search_query}%'),
                Book.isbn.like(f'%{search_query}%')
            )
        )

    # 如果指定了分类，精确匹配分类
    if category:
        query = query.filter(Book.category == category)

    # 按入库时间倒序排列，最新的在前面
    all_books = query.order_by(Book.add_time.desc()).all()

    # 按 ISBN 分组，统计每组的册数和可借数
    from collections import OrderedDict
    isbn_groups = OrderedDict()  # 保持插入顺序
    for book in all_books:
        if book.isbn not in isbn_groups:
            isbn_groups[book.isbn] = {
                'first_book': book,       # 该ISBN的第一本（用于展示信息）
                'total': 0,
                'available': 0,
                'book_ids': []            # 所有册的ID列表
            }
        isbn_groups[book.isbn]['total'] += 1
        isbn_groups[book.isbn]['book_ids'].append(book.id)
        if book.status == 'available':
            isbn_groups[book.isbn]['available'] += 1

    book_groups = list(isbn_groups.values())

    # 获取当前用户已收藏的图书 ID 集合（用于前端显示收藏状态图标）
    favorite_book_ids = set()
    if session.get('role') != 'admin':
        favorite_book_ids = {
            favorite.book_id
            for favorite in BookFavorite.query.filter(current_account_filter(BookFavorite)).all()
        }

    # 渲染列表模板
    return render_template('books/list.html',
                           book_groups=book_groups,
                           search_query=search_query,
                           category=category,
                           favorite_book_ids=favorite_book_ids)


# ==================== 2. 添加图书（管理员） ====================

@books_bp.route('/add', methods=['GET', 'POST'])
def add_book():
    """
    管理员添加新图书
    GET: 显示添加表单
    POST: 处理表单提交，创建 Book 记录
    """

    # 权限校验
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可添加图书！', 'error')
        return redirect(url_for('books.book_list'))

    if request.method == 'POST':
        # 获取并校验 ISBN
        isbn = request.form.get('isbn')
        normalized_isbn, isbn_error = validate_isbn(isbn)
        if isbn_error:
            flash(isbn_error, 'error')
            return render_template('books/add.html', publishers=get_publishers())

        title = request.form.get('title')
        author = request.form.get('author')
        publisher = resolve_publisher_from_form()  # 自动创建新出版社
        category = request.form.get('category')
        description = request.form.get('description')

        # 馆藏位置信息
        floor = request.form.get('floor', type=int) or 1
        area = request.form.get('area') or 'A区'
        shelf = request.form.get('shelf') or '01架'

        # 入库册数（默认1册）
        copies_count = request.form.get('copies_count', type=int) or 1
        copies_count = max(1, min(copies_count, 50))  # 限制 1~50 册

        # 保存上传的封面图片
        cover_image = save_uploaded_image(request.files.get('cover_image'), 'book_covers')

        # 查询同 ISBN 的已有册数
        existing_copies = Book.query.filter_by(isbn=normalized_isbn).count()

        # 如果该 ISBN 已有记录，从已有记录中继承信息
        if existing_copies > 0:
            existing = Book.query.filter_by(isbn=normalized_isbn).first()
            if not title:
                title = existing.title
            if not author:
                author = existing.author
            if not cover_image:
                cover_image = existing.cover_image
            if not category:
                category = existing.category

        # 解析基础书架号中的数字部分，用于自动递增
        import re as re_module
        shelf_match = re_module.match(r'(\d+)', shelf)
        base_shelf_num = int(shelf_match.group(1)) if shelf_match else 1

        # 批量创建副本
        added = 0
        for i in range(copies_count):
            # 第1册用原始位置，后续册书架号递增
            if i == 0:
                copy_shelf = shelf
            else:
                copy_shelf = f'{base_shelf_num + i:02d}架'

            new_book = Book(
                isbn=normalized_isbn,
                title=title,
                author=author,
                publisher=publisher,
                category=category,
                description=description,
                floor=floor,
                area=area,
                shelf=copy_shelf,
                cover_image=cover_image,
                status='available'
            )
            db.session.add(new_book)
            added += 1

        db.session.commit()
        total = Book.query.filter_by(isbn=normalized_isbn).count()
        if added > 1:
            flash(f'成功入库《{title}》{added} 册（ISBN: {normalized_isbn}），馆藏共 {total} 册。', 'success')
        else:
            flash(f'成功入库《{title}》1 册（ISBN: {normalized_isbn}），馆藏共 {total} 册。', 'success')
        return redirect(url_for('books.book_list'))

    # GET 请求 → 显示添加表单
    return render_template('books/add.html', publishers=get_publishers())


# ==================== 3. 借阅图书 ====================

@books_bp.route('/borrow/<int:book_id>')
def borrow_book(book_id):
    """
    用户借阅图书
    流程: 检查登录 → 检查图书可借 → 创建借阅记录 → 更新图书状态
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取图书，不存在则返回 404
    book = Book.query.get_or_404(book_id)

    # 如果指定册不可借，自动查找同 ISBN 的第一本可借副本
    if book.status != 'available':
        available_copy = Book.query.filter_by(
            isbn=book.isbn, status='available'
        ).first()
        if available_copy:
            book = available_copy
        else:
            flash('该书所有副本均已被借出！', 'error')
            return redirect(url_for('books.book_list'))

    try:
        # 创建借阅记录
        new_record = BorrowRecord(book_id=book.id, status='borrowing')
        # 绑定当前用户到记录
        assign_current_account(new_record)

        # 更新图书状态为已借出
        book.status = 'borrowed'

        db.session.add(new_record)
        db.session.commit()
        flash(f'成功借阅：《{book.title}》', 'success')
    except Exception as e:
        db.session.rollback()
        flash('借阅失败！', 'error')

    return redirect(url_for('books.book_list'))


# ==================== 4. 我的借阅 ====================

@books_bp.route('/my_borrowing')
def my_borrowing():
    """
    查看当前用户的借阅记录列表
    按借阅时间倒序排列
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 查询当前用户的所有借阅记录
    records = BorrowRecord.query.filter(
        current_account_filter(BorrowRecord)
    ).order_by(BorrowRecord.borrow_time.desc()).all()

    return render_template('books/my_borrowing.html', records=records)


# ==================== 5. 归还图书 ====================

@books_bp.route('/return/<int:record_id>')
def return_book(record_id):
    """
    用户归还图书
    流程: 检查登录 → 检查权限（自己或管理员） → 更新记录和图书状态
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取借阅记录
    record = BorrowRecord.query.get_or_404(record_id)

    # 权限检查：只能归还自己的借阅记录，管理员可以归还任意记录
    if not account_owns(record) and session.get('role') != 'admin':
        flash('您没有权限操作此记录！', 'error')
        return redirect(url_for('books.my_borrowing'))

    try:
        # 更新借阅记录状态
        record.status = 'returned'
        record.return_time = datetime.utcnow()  # 记录实际归还时间

        # 释放图书状态为可借
        record.book.status = 'available'

        db.session.commit()
        flash(f'成功归还：《{record.book.title}》。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('归还失败！', 'error')

    # 管理员归还后跳回管理页面，普通用户跳回我的借阅
    if session.get('role') == 'admin':
        return redirect(request.args.get('next') or url_for('books.manage_interactions'))
    return redirect(url_for('books.my_borrowing'))


# ==================== 6. 图书详情页 ====================

@books_bp.route('/detail/<int:book_id>')
def book_detail(book_id):
    """
    图书详情页 — 展示图书完整信息、收藏状态、评价列表、平均评分
    还判断当前用户是否有资格发表评价（需归还过该书）
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取图书
    book = Book.query.get_or_404(book_id)

    # 查询同 ISBN 的所有副本
    copies = Book.query.filter_by(isbn=book.isbn).order_by(Book.id.asc()).all()
    total_copies = len(copies)
    available_copies = sum(1 for c in copies if c.status == 'available')

    # 初始化页面变量
    is_favorite = False    # 是否已收藏
    user_review = None     # 当前用户的评价
    can_review = False     # 是否有资格评价

    if session.get('role') != 'admin':
        # 检查是否已收藏
        is_favorite = BookFavorite.query.filter(
            BookFavorite.book_id == book.id,
            current_account_filter(BookFavorite)
        ).first() is not None

        # 查找当前用户对该书的评价
        user_review = BookReview.query.filter(
            BookReview.book_id == book.id,
            current_account_filter(BookReview)
        ).first()

        # 判断是否可评价：必须已归还该书且尚未评价过
        can_review = (BorrowRecord.query.filter(
            BorrowRecord.book_id == book.id,
            BorrowRecord.status == 'returned',
            current_account_filter(BorrowRecord)
        ).first() is not None) and user_review is None

    # 查询该书所有已审核通过的评价，按时间倒序
    approved_reviews = BookReview.query.filter_by(
        book_id=book.id, status='approved'
    ).order_by(BookReview.created_at.desc()).all()

    # 计算该书的平均评分（只统计已通过的评价）
    average_rating = db.session.query(
        func.avg(BookReview.rating)
    ).filter_by(book_id=book.id, status='approved').scalar()

    return render_template('books/detail.html',
                           book=book,
                           copies=copies,
                           total_copies=total_copies,
                           available_copies=available_copies,
                           is_favorite=is_favorite,
                           user_review=user_review,
                           can_review=can_review,
                           approved_reviews=approved_reviews,
                           average_rating=average_rating)


# ==================== 7. 编辑图书（管理员） ====================

@books_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """
    管理员编辑图书信息
    GET: 显示编辑表单，预填现有数据
    POST: 更新图书字段
    """

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('books.book_list'))

    book = Book.query.get_or_404(book_id)

    # 查询同 ISBN 所有副本
    copies = Book.query.filter_by(isbn=book.isbn).order_by(Book.id.asc()).all()
    copy_count = len(copies)

    if request.method == 'POST':
        # 逐字段更新图书信息
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.publisher = resolve_publisher_from_form()
        book.category = request.form.get('category')
        book.description = request.form.get('description')

        # 更新位置信息
        book.floor = request.form.get('floor', type=int)
        book.area = request.form.get('area')
        book.shelf = request.form.get('shelf')

        # 如果上传了新的封面图，则更新（否则保留原图）
        cover_image = save_uploaded_image(request.files.get('cover_image'), 'book_covers')
        if cover_image:
            book.cover_image = cover_image

        db.session.commit()
        flash(f'图书《{book.title}》修改成功！', 'success')
        return redirect(url_for('books.book_list'))

    # GET → 显示编辑表单
    return render_template('books/edit.html', book=book, copies=copies,
                           copy_count=copy_count, publishers=get_publishers())


# ==================== 8. 收藏图书 ====================

@books_bp.route('/favorite/<int:book_id>')
def favorite_book(book_id):
    """
    用户收藏图书
    前提: 非管理员用户，未收藏过该书
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 管理员无需收藏功能
    if session.get('role') == 'admin':
        flash('管理员无需收藏图书。', 'error')
        return redirect(url_for('books.book_detail', book_id=book_id))

    book = Book.query.get_or_404(book_id)

    # 检查是否已收藏（防止重复收藏）
    exists = BookFavorite.query.filter(
        BookFavorite.book_id == book.id,
        current_account_filter(BookFavorite)
    ).first()

    if not exists:
        # 创建收藏记录
        favorite = BookFavorite(book_id=book.id)
        assign_current_account(favorite)
        db.session.add(favorite)
        db.session.commit()
        flash(f'已收藏《{book.title}》。', 'success')

    # 返回来源页面
    return redirect(request.referrer or url_for('books.book_detail', book_id=book.id))


# ==================== 9. 取消收藏 ====================

@books_bp.route('/unfavorite/<int:book_id>')
def unfavorite_book(book_id):
    """
    用户取消收藏图书
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 查找收藏记录
    favorite = BookFavorite.query.filter(
        BookFavorite.book_id == book_id,
        current_account_filter(BookFavorite)
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash('已取消收藏。', 'success')

    return redirect(request.referrer or url_for('books.my_favorites'))


# ==================== 10. 我的收藏 ====================

@books_bp.route('/my_favorites')
def my_favorites():
    """
    查看当前用户的收藏列表
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    favorites = BookFavorite.query.filter(
        current_account_filter(BookFavorite)
    ).order_by(BookFavorite.created_at.desc()).all()

    return render_template('books/my_favorites.html', favorites=favorites)


# ==================== 11. 发表评价 ====================

@books_bp.route('/review/<int:book_id>', methods=['POST'])
def create_review(book_id):
    """
    用户对图书发表评分和评价
    前置条件:
      1. 用户已归还过该书
      2. 用户尚未对该书发表过评价
      3. 评分 1-5 星，评价至少 5 个字
    提交后状态为 pending，等待管理员 AI 审核
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    book = Book.query.get_or_404(book_id)
    rating = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()

    # 校验：是否已归还该书
    has_returned = BorrowRecord.query.filter(
        BorrowRecord.book_id == book.id,
        BorrowRecord.status == 'returned',
        current_account_filter(BorrowRecord)
    ).first()

    # 校验：是否已评价过
    existing_review = BookReview.query.filter(
        BookReview.book_id == book.id,
        current_account_filter(BookReview)
    ).first()

    # 各项校验
    if not has_returned:
        flash('归还这本书后才能发表评价。', 'error')
    elif existing_review:
        flash('您已经评价过这本书。', 'error')
    elif not rating or rating < 1 or rating > 5 or len(content) < 5:
        flash('请填写 1-5 星评分，并输入至少 5 个字的评价。', 'error')
    else:
        # 创建评价记录，状态为待审核
        review = BookReview(book_id=book.id, rating=rating, content=content, status='pending')
        assign_current_account(review)
        db.session.add(review)
        db.session.commit()
        flash('评价已提交，管理员使用 AI 审核通过后将展示。', 'success')

    return redirect(url_for('books.book_detail', book_id=book.id))


# ==================== 12. 个人中心 ====================

@books_bp.route('/profile')
def profile():
    """
    用户个人中心页面
    展示: 基本信息、借阅统计、收藏数、评价数、当前座位、漂流数据
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 根据账号类型获取用户对象
    account = None
    if session.get('account_type') == 'student':
        account = Student.query.get(session.get('account_id'))
    elif session.get('account_type') == 'teacher':
        account = Teacher.query.get(session.get('account_id'))
    else:
        account = User.query.get(session.get('account_id'))

    # 账号不存在则清空 Session 并跳转登录
    if not account:
        session.clear()
        flash('账号不存在，请重新登录。', 'error')
        return redirect(url_for('auth.login'))

    # 查询各项统计数字
    borrow_records = BorrowRecord.query.filter(
        current_account_filter(BorrowRecord)
    ).order_by(BorrowRecord.borrow_time.desc()).limit(5).all()

    active_borrow_count = BorrowRecord.query.filter(
        current_account_filter(BorrowRecord),
        BorrowRecord.status == 'borrowing'
    ).count()

    returned_count = BorrowRecord.query.filter(
        current_account_filter(BorrowRecord),
        BorrowRecord.status == 'returned'
    ).count()

    favorite_count = BookFavorite.query.filter(
        current_account_filter(BookFavorite)
    ).count()

    review_count = BookReview.query.filter(
        current_account_filter(BookReview)
    ).count()

    # 当前正在使用的座位
    active_seat = SeatReservation.query.filter(
        current_account_filter(SeatReservation),
        SeatReservation.status == 'active'
    ).first()

    # 漂流数据：我发布的漂流图书数
    drift_count = 0
    if session.get('account_type') == 'student':
        drift_count = DriftBook.query.filter_by(provider_student_id=session.get('account_id')).count()
    elif session.get('account_type') == 'teacher':
        drift_count = DriftBook.query.filter_by(provider_teacher_id=session.get('account_id')).count()
    else:
        drift_count = DriftBook.query.filter_by(provider_user_id=session.get('account_id')).count()

    # 漂流数据：我提交的申请数
    request_count = 0
    if session.get('account_type') == 'student':
        request_count = DriftRequest.query.filter_by(receiver_student_id=session.get('account_id')).count()
    elif session.get('account_type') == 'teacher':
        request_count = DriftRequest.query.filter_by(receiver_teacher_id=session.get('account_id')).count()
    else:
        request_count = DriftRequest.query.filter_by(receiver_user_id=session.get('account_id')).count()

    return render_template('books/profile.html',
                           borrow_records=borrow_records,
                           active_borrow_count=active_borrow_count,
                           returned_count=returned_count,
                           favorite_count=favorite_count,
                           review_count=review_count,
                           active_seat=active_seat,
                           drift_count=drift_count,
                           request_count=request_count,
                           account=account)


# ==================== 13. 个性化图书推荐 ====================

@books_bp.route('/recommendations')
def recommendations():
    """
    个性化图书推荐页面
    推荐策略（按优先级排序）:
      1. 偏好分类推荐 — 基于用户收藏和借阅的 Top3 分类
      2. 热门借阅 — 全馆借阅次数最多的图书（排除已借/已收藏的）
      3. 热门收藏 — 全馆收藏数最多的图书（排除已借/已收藏的）
      4. 最新上架 — 最近入库的图书（排除已借/已收藏的）
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取用户收藏最多的 3 个分类
    favorite_categories = [
        row[0] for row in db.session.query(Book.category)
        .join(BookFavorite, BookFavorite.book_id == Book.id)
        .filter(current_account_filter(BookFavorite), Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(func.count(BookFavorite.id).desc())
        .limit(3)
        .all()
    ]

    # 获取用户借阅最多的 3 个分类
    borrowed_categories = [
        row[0] for row in db.session.query(Book.category)
        .join(BorrowRecord, BorrowRecord.book_id == Book.id)
        .filter(current_account_filter(BorrowRecord), Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(func.count(BorrowRecord.id).desc())
        .limit(3)
        .all()
    ]

    # 合并并去重（保持顺序）
    preferred_categories = list(dict.fromkeys(favorite_categories + borrowed_categories))

    # 收集用户已借阅和已收藏的图书 ID（这些不会出现在推荐中）
    borrowed_book_ids = {
        record.book_id for record in BorrowRecord.query.filter(current_account_filter(BorrowRecord)).all()
    }
    favorite_book_ids = {
        favorite.book_id for favorite in BookFavorite.query.filter(current_account_filter(BookFavorite)).all()
    }
    excluded_ids = borrowed_book_ids | favorite_book_ids  # 排除集合

    # 热门借阅推荐 — 按借阅次数降序
    popular_query = db.session.query(
        Book,
        func.count(BorrowRecord.id).label('borrow_count')
    ).outerjoin(BorrowRecord, BorrowRecord.book_id == Book.id)  # 左外连接
    if excluded_ids:
        popular_query = popular_query.filter(~Book.id.in_(excluded_ids))  # 排除已有图书
    popular_books = popular_query.group_by(Book.id).order_by(
        func.count(BorrowRecord.id).desc(), Book.add_time.desc()
    ).limit(8).all()

    # 热门收藏推荐 — 按收藏次数降序
    favorite_query = db.session.query(
        Book,
        func.count(BookFavorite.id).label('favorite_count')
    ).outerjoin(BookFavorite, BookFavorite.book_id == Book.id)
    if excluded_ids:
        favorite_query = favorite_query.filter(~Book.id.in_(excluded_ids))
    hot_favorites = favorite_query.group_by(Book.id).order_by(
        func.count(BookFavorite.id).desc(), Book.add_time.desc()
    ).limit(8).all()

    # 偏好分类推荐 — 优先展示用户喜欢的分类中的最新图书
    personalized_books = []
    if preferred_categories:
        personalized_query = Book.query.filter(Book.category.in_(preferred_categories))
        if excluded_ids:
            personalized_query = personalized_query.filter(~Book.id.in_(excluded_ids))
        personalized_books = personalized_query.order_by(Book.add_time.desc()).limit(8).all()

    # 最新上架推荐
    latest_books = Book.query
    if excluded_ids:
        latest_books = latest_books.filter(~Book.id.in_(excluded_ids))
    latest_books = latest_books.order_by(Book.add_time.desc()).limit(8).all()

    return render_template('books/recommendations.html',
                           preferred_categories=preferred_categories,
                           popular_books=popular_books,
                           hot_favorites=hot_favorites,
                           personalized_books=personalized_books,
                           latest_books=latest_books,
                           favorite_book_ids=favorite_book_ids)


# ==================== 14. 互动管理（管理员） ====================

@books_bp.route('/admin/interactions')
def manage_interactions():
    """
    管理员互动管理页面
    展示: 所有评价（含审核状态）、热门收藏排行、最近借阅/预约记录
    """

    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可访问！', 'error')
        return redirect(url_for('books.book_list'))

    # 所有评价（按时间倒序）
    reviews = BookReview.query.order_by(BookReview.created_at.desc()).all()

    # 热门收藏排行 Top10
    popular_books = db.session.query(
        Book, func.count(BookFavorite.id).label('favorite_count')
    ).join(BookFavorite, BookFavorite.book_id == Book.id).group_by(
        Book.id
    ).order_by(func.count(BookFavorite.id).desc()).limit(10).all()

    # 当前在借图书（未归还的）
    active_borrowings = BorrowRecord.query.filter_by(status='borrowing')\
        .order_by(BorrowRecord.borrow_time.desc()).all()

    # 最近借阅记录 30 条
    borrow_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(30).all()

    # 最近座位预约 30 条
    seat_reservations = SeatReservation.query.order_by(SeatReservation.start_time.desc()).limit(30).all()

    return render_template('books/admin_interactions.html',
                           reviews=reviews,
                           popular_books=popular_books,
                           active_borrowings=active_borrowings,
                           borrow_records=borrow_records,
                           seat_reservations=seat_reservations,
                           now=datetime.utcnow())


# ==================== 15. 人工审核评价（已废弃，改用 AI） ====================

@books_bp.route('/admin/review/<int:review_id>/<action>')
def moderate_review(review_id, action):
    """
    管理员手动审核评价 — 已废弃，转而使用 AI 自动审核
    """

    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))

    BookReview.query.get_or_404(review_id)
    flash('评价审核已改为 AI 审核，请点击"AI 审核"按钮处理。', 'error')
    return redirect(url_for('books.manage_interactions'))


# ==================== 16. AI 自动审核评价 ====================

@books_bp.route('/admin/review/<int:review_id>/ai', methods=['POST'])
def ai_review_moderate(review_id):
    """
    调用 DeepSeek API 对评价进行智能审核
    审核结果直接写入评价的 status 字段
    """

    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))

    review = BookReview.query.get_or_404(review_id)

    try:
        # 调用 AI 审核
        status, reason = ai_moderate_review(review)
        review.status = status  # 写入审核结果
        db.session.commit()

        status_text = '通过' if status == 'approved' else '驳回'
        flash(f'AI 审核完成：已{status_text}。理由：{reason or "符合审核规则"}', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'AI 审核失败，评价仍保持待审核状态。错误信息：{str(e)}', 'error')

    return redirect(url_for('books.manage_interactions'))


# ==================== 17. 删除图书（管理员） ====================

@books_bp.route('/delete/<int:book_id>')
def delete_book(book_id):
    """
    管理员删除图书
    限制: 正在被借出的图书无法删除
    级联删除: 关联的收藏、评价记录会自动删除（ORM cascade 配置）
    """

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('books.book_list'))

    book = Book.query.get_or_404(book_id)

    # 安全检查：借出状态的图书不能删除
    if book.status != 'available':
        flash('该图书处于借出状态，无法删除！', 'error')
        return redirect(url_for('books.book_list'))

    # 执行删除（级联删除收藏和评价）
    db.session.delete(book)
    db.session.commit()
    flash('图书已成功从馆藏库移除。', 'success')
    return redirect(url_for('books.book_list'))
