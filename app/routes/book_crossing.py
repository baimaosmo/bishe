# =============================================================================
# app/routes/book_crossing.py — 图书漂流角路由
# 负责: 漂流图书的发布、浏览、申请、审批、编辑和删除
# 蓝图名: crossing_bp，挂载在 /crossing 前缀下
# 业务流程: 用户发布漂流图书 → 其他用户浏览并申请 → 提供者同意/拒绝 → 图书状态变更
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import DriftBook, DriftRequest, Student, User, Teacher
from app import db
from datetime import datetime

# 创建蓝图
crossing_bp = Blueprint('crossing', __name__)


# ==================== 工具函数 ====================

def get_current_account():
    """
    获取当前登录用户的类型和 ID
    返回: (account_type, account_id, username) 三元组
    """
    if 'account_id' not in session:
        return None, None, None
    return session.get('account_type'), session.get('account_id'), session.get('username')


def get_provider_info(account_type, account_id):
    """
    根据账号类型和 ID 获取用户 ORM 对象
    返回: Student / Teacher / User 对象
    """
    if account_type == 'student':
        return Student.query.get(account_id)
    if account_type == 'teacher':
        return Teacher.query.get(account_id)
    return User.query.get(account_id)


def get_provider_name(account_type, account_id):
    """
    根据账号类型和 ID 获取用户显示名称
    """
    provider = get_provider_info(account_type, account_id)
    if not provider:
        return '未知'
    # 普通用户显示 username，学生和教师显示真实姓名
    return provider.username if account_type == 'user' else provider.name


# ==================== 1. 漂流广场（图书列表页） ====================

@crossing_bp.route('/')
def index():
    """
    漂流广场主页 — 展示所有漂流图书列表
    支持筛选: 状态(drifting/claimed)、课程、关键词搜索
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取筛选参数
    status_filter = request.args.get('status', 'drifting')  # 默认显示漂流中的
    course_filter = request.args.get('course', '').strip()  # 课程筛选
    keyword = request.args.get('keyword', '').strip()        # 关键词搜索

    # 构建查询
    query = DriftBook.query

    # 状态筛选
    if status_filter in ('drifting', 'claimed'):
        query = query.filter(DriftBook.status == status_filter)

    # 课程筛选（模糊匹配）
    if course_filter:
        query = query.filter(DriftBook.course_related.contains(course_filter))

    # 关键词搜索（匹配书名）
    if keyword:
        query = query.filter(DriftBook.title.contains(keyword))

    # 按发布时间倒序
    books = query.order_by(DriftBook.publish_time.desc()).all()

    # 收集所有不重复的课程名，供筛选下拉框使用
    all_courses = sorted(set(
        b.course_related for b in DriftBook.query.all() if b.course_related
    ))

    return render_template('crossing/list.html',
                           books=books,
                           status_filter=status_filter,
                           course_filter=course_filter,
                           keyword=keyword,
                           all_courses=all_courses)


# ==================== 2. 发布漂流图书 ====================

@crossing_bp.route('/publish', methods=['GET', 'POST'])
def publish():
    """
    用户发布漂流图书
    GET: 显示发布表单
    POST: 创建漂流图书记录
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 获取表单数据
        title = request.form.get('title', '').strip()
        course_related = request.form.get('course_related', '').strip()
        condition = request.form.get('condition', '良好')  # 新旧程度
        description = request.form.get('description', '').strip()
        exchange_type = request.form.get('exchange_type', 'free')  # 免费赠送 or 希望交换

        # 书名必填
        if not title:
            flash('请输入书名！', 'error')
            return redirect(url_for('crossing.publish'))

        # 获取当前用户信息
        acc_type, acc_id, _ = get_current_account()

        # 构造描述文本：在开头标注[免费赠送]或[希望交换]
        full_description = (
            f"[{'免费赠送' if exchange_type == 'free' else '希望交换'}]{description}"
            if description
            else f"{'免费赠送' if exchange_type == 'free' else '希望交换'}"
        )

        # 创建漂流图书记录
        book = DriftBook(
            title=title,
            course_related=course_related if course_related else None,
            condition=condition,
            description=full_description,
            status='drifting'  # 初始状态：漂流中
        )

        # 绑定提供者（三选一）
        if acc_type == 'student':
            book.provider_student_id = acc_id
        elif acc_type == 'teacher':
            book.provider_teacher_id = acc_id
        else:
            book.provider_user_id = acc_id

        db.session.add(book)
        db.session.commit()
        flash(f'《{title}》已成功发布到漂流角！', 'success')
        return redirect(url_for('crossing.index'))

    # GET → 显示发布表单
    return render_template('crossing/publish.html')


# ==================== 3. 漂流图书详情 & 申请管理 ====================

@crossing_bp.route('/detail/<int:book_id>', methods=['GET', 'POST'])
def detail(book_id):
    """
    漂流图书详情页
    展示: 图书信息、提供者信息、申请列表（提供者/管理员可见）
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    book = DriftBook.query.get_or_404(book_id)
    acc_type, acc_id, _ = get_current_account()

    # 判断当前用户是否是该书的提供者
    is_provider = (
        (acc_type == 'student' and book.provider_student_id == acc_id) or
        (acc_type == 'teacher' and book.provider_teacher_id == acc_id) or
        (acc_type == 'user' and book.provider_user_id == acc_id)
    )

    # 该书的申请列表（仅提供者和管理员可见）
    requests_list = []
    if is_provider or session.get('role') == 'admin':
        requests_list = DriftRequest.query.filter_by(
            book_id=book.id
        ).order_by(DriftRequest.create_time.desc()).all()

    # 检查当前用户是否已经申请过
    already_requested = DriftRequest.query.filter_by(book_id=book.id).filter(
        (DriftRequest.receiver_user_id == acc_id) if acc_type == 'user'
        else ((DriftRequest.receiver_teacher_id == acc_id) if acc_type == 'teacher'
              else (DriftRequest.receiver_student_id == acc_id))
    ).first()

    return render_template('crossing/detail.html',
                           book=book,
                           is_provider=is_provider,
                           requests_list=requests_list,
                           already_requested=already_requested)


# ==================== 4. 提交领取申请 ====================

@crossing_bp.route('/request/<int:book_id>', methods=['POST'])
def request_book(book_id):
    """
    用户申请领取漂流图书
    限制:
      1. 图书必须是 drifting 状态（未被领走）
      2. 不能申请自己发布的图书
      3. 同一用户对同一图书只能申请一次
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    book = DriftBook.query.get_or_404(book_id)
    acc_type, acc_id, _ = get_current_account()

    # 校验图书状态
    if book.status != 'drifting':
        flash('该书已被领走，无法申请！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    # 校验：不能申请自己的书
    is_provider = (
        (acc_type == 'student' and book.provider_student_id == acc_id) or
        (acc_type == 'teacher' and book.provider_teacher_id == acc_id) or
        (acc_type == 'user' and book.provider_user_id == acc_id)
    )
    if is_provider:
        flash('不能申请自己发布的图书！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    # 校验：是否已经申请过
    existing = DriftRequest.query.filter_by(book_id=book_id).filter(
        (DriftRequest.receiver_user_id == acc_id) if acc_type == 'user'
        else ((DriftRequest.receiver_teacher_id == acc_id) if acc_type == 'teacher'
              else (DriftRequest.receiver_student_id == acc_id))
    ).first()
    if existing:
        flash('您已经提交过申请，请等待提供者处理！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    # 创建申请记录
    message = request.form.get('message', '').strip()  # 给提供者的留言
    dr = DriftRequest(book_id=book_id, message=message if message else None)

    # 绑定申请人
    if acc_type == 'student':
        dr.receiver_student_id = acc_id
    elif acc_type == 'teacher':
        dr.receiver_teacher_id = acc_id
    else:
        dr.receiver_user_id = acc_id

    db.session.add(dr)
    db.session.commit()
    flash('申请已提交，请等待提供者确认！', 'success')
    return redirect(url_for('crossing.detail', book_id=book_id))


# ==================== 5. 我的漂流（提供者查看/管理员查看全部） ====================

@crossing_bp.route('/my')
def my_crossing():
    """
    我的漂流页面
    - 普通用户: 查看自己发布的漂流图书和提交的申请
    - 管理员: 查看所有漂流图书和申请
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    acc_type, acc_id, _ = get_current_account()
    is_admin = session.get('role') == 'admin'

    if is_admin:
        # 管理员查看全部数据
        my_books = DriftBook.query.order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.order_by(DriftRequest.create_time.desc()).all()
    elif acc_type == 'student':
        # 学生查看自己发布的书
        my_books = DriftBook.query.filter_by(
            provider_student_id=acc_id
        ).order_by(DriftBook.publish_time.desc()).all()
        # 学生查看自己提交的申请
        my_requests = DriftRequest.query.filter_by(
            receiver_student_id=acc_id
        ).order_by(DriftRequest.create_time.desc()).all()
    elif acc_type == 'teacher':
        my_books = DriftBook.query.filter_by(
            provider_teacher_id=acc_id
        ).order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.filter_by(
            receiver_teacher_id=acc_id
        ).order_by(DriftRequest.create_time.desc()).all()
    else:
        my_books = DriftBook.query.filter_by(
            provider_user_id=acc_id
        ).order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.filter_by(
            receiver_user_id=acc_id
        ).order_by(DriftRequest.create_time.desc()).all()

    # 构建"我收到的申请"字典 {book_id: [request列表]}
    received_requests = {}
    for book in my_books:
        reqs = DriftRequest.query.filter_by(
            book_id=book.id
        ).order_by(DriftRequest.create_time.desc()).all()
        if reqs:
            received_requests[book.id] = reqs

    return render_template('crossing/my.html',
                           my_books=my_books,
                           my_requests=my_requests,
                           received_requests=received_requests,
                           is_admin=is_admin)


# ==================== 6. 处理申请（同意/拒绝） ====================

@crossing_bp.route('/handle_request/<int:request_id>/<action>', methods=['POST'])
def handle_request(request_id, action):
    """
    提供者处理领取申请
    action = 'accept': 同意申请 → 图书状态变为 claimed，拒绝其他申请
    action = 'reject': 拒绝申请
    权限: 只有该书的提供者或管理员可以操作
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 校验操作类型
    if action not in ('accept', 'reject'):
        flash('无效操作！', 'error')
        return redirect(url_for('crossing.my_crossing'))

    dr = DriftRequest.query.get_or_404(request_id)
    book = dr.book  # 通过关系属性获取关联的漂流图书
    acc_type, acc_id, _ = get_current_account()

    # 权限校验：只有提供者或管理员可以处理
    is_provider = (
        (acc_type == 'student' and book.provider_student_id == acc_id) or
        (acc_type == 'teacher' and book.provider_teacher_id == acc_id) or
        (acc_type == 'user' and book.provider_user_id == acc_id)
    )
    is_admin = session.get('role') == 'admin'
    if not is_provider and not is_admin:
        flash('无权操作！', 'error')
        return redirect(url_for('crossing.my_crossing'))

    if action == 'accept':
        # 同意申请
        dr.status = 'accepted'
        book.status = 'claimed'  # 图书状态标记为已领取

        # 记录领取者到漂流图书的 receiver 字段
        if dr.receiver_student_id:
            book.receiver_student_id = dr.receiver_student_id
        elif dr.receiver_teacher_id:
            book.receiver_teacher_id = dr.receiver_teacher_id
        else:
            book.receiver_user_id = dr.receiver_user_id

        # 自动拒绝该书的其他所有待处理申请
        other_requests = DriftRequest.query.filter(
            DriftRequest.book_id == book.id,
            DriftRequest.id != dr.id  # 排除当前被接受的申请
        ).all()
        for r in other_requests:
            r.status = 'rejected'

        flash(f'已同意申请，该书已标记为"已领走"！', 'success')
    else:
        # 拒绝申请
        dr.status = 'rejected'
        flash('已拒绝该申请。', 'success')

    db.session.commit()
    return redirect(url_for('crossing.my_crossing'))


# ==================== 7. 删除漂流图书（管理员） ====================

@crossing_bp.route('/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    """
    管理员删除漂流图书
    级联删除：自动删除该书的所有关联申请记录
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('crossing.index'))

    book = DriftBook.query.get_or_404(book_id)
    title = book.title

    # 先手动删除该书的关联申请记录
    DriftRequest.query.filter_by(book_id=book.id).delete()
    # 再删除漂流图书本身
    db.session.delete(book)
    db.session.commit()
    flash(f'已删除漂流图书《{title}》及其所有申请记录。', 'success')
    return redirect(url_for('crossing.index'))


# ==================== 8. 编辑漂流图书（管理员） ====================

@crossing_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    """
    管理员编辑漂流图书信息
    GET: 显示编辑表单
    POST: 更新图书字段（包括状态）
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('crossing.index'))

    book = DriftBook.query.get_or_404(book_id)

    if request.method == 'POST':
        # 更新各字段
        book.title = request.form.get('title', '').strip() or book.title
        book.course_related = request.form.get('course_related', '').strip() or None
        book.condition = request.form.get('condition', '良好')
        book.description = request.form.get('description', '').strip() or None

        # 管理员可以手动修改状态
        new_status = request.form.get('status')
        if new_status in ('drifting', 'claimed'):
            book.status = new_status

        db.session.commit()
        flash(f'《{book.title}》信息已更新。', 'success')
        return redirect(url_for('crossing.detail', book_id=book.id))

    # GET → 显示编辑表单
    return render_template('crossing/edit.html', book=book)


# ==================== 9. 删除申请记录（管理员） ====================

@crossing_bp.route('/delete_request/<int:request_id>', methods=['POST'])
def delete_request(request_id):
    """
    管理员删除指定申请记录
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('crossing.index'))

    dr = DriftRequest.query.get_or_404(request_id)
    book_id = dr.book_id
    db.session.delete(dr)
    db.session.commit()
    flash('已删除该申请记录。', 'success')
    return redirect(url_for('crossing.detail', book_id=book_id))
