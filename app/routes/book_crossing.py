from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import DriftBook, DriftRequest, Student, User, Teacher
from app import db
from datetime import datetime

crossing_bp = Blueprint('crossing', __name__)


def get_current_account():
    """返回当前登录用户的类型和ID"""
    if 'account_id' not in session:
        return None, None, None
    return session.get('account_type'), session.get('account_id'), session.get('username')


def get_provider_info(account_type, account_id):
    """根据类型和ID获取提供者信息"""
    if account_type == 'student':
        return Student.query.get(account_id)
    if account_type == 'teacher':
        return Teacher.query.get(account_id)
    return User.query.get(account_id)


def get_provider_name(account_type, account_id):
    provider = get_provider_info(account_type, account_id)
    if not provider:
        return '未知'
    return provider.username if account_type == 'user' else provider.name


# 1. 漂流广场（列表页）
@crossing_bp.route('/')
def index():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    status_filter = request.args.get('status', 'drifting')
    course_filter = request.args.get('course', '').strip()
    keyword = request.args.get('keyword', '').strip()

    query = DriftBook.query

    if status_filter in ('drifting', 'claimed'):
        query = query.filter(DriftBook.status == status_filter)
    if course_filter:
        query = query.filter(DriftBook.course_related.contains(course_filter))
    if keyword:
        query = query.filter(DriftBook.title.contains(keyword))

    books = query.order_by(DriftBook.publish_time.desc()).all()

    # 获取所有不重复的课程名，供筛选下拉使用
    all_courses = sorted(set(
        b.course_related for b in DriftBook.query.all() if b.course_related
    ))

    return render_template('crossing/list.html',
                           books=books,
                           status_filter=status_filter,
                           course_filter=course_filter,
                           keyword=keyword,
                           all_courses=all_courses)


# 2. 发布漂流图书
@crossing_bp.route('/publish', methods=['GET', 'POST'])
def publish():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        course_related = request.form.get('course_related', '').strip()
        condition = request.form.get('condition', '良好')
        description = request.form.get('description', '').strip()
        exchange_type = request.form.get('exchange_type', 'free')

        if not title:
            flash('请输入书名！', 'error')
            return redirect(url_for('crossing.publish'))

        acc_type, acc_id, _ = get_current_account()

        book = DriftBook(
            title=title,
            course_related=course_related if course_related else None,
            condition=condition,
            description=f"[{'免费赠送' if exchange_type == 'free' else '希望交换'}]{description}" if description else f"{'免费赠送' if exchange_type == 'free' else '希望交换'}",
            status='drifting'
        )
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

    return render_template('crossing/publish.html')


# 3. 图书详情 & 申请领取
@crossing_bp.route('/detail/<int:book_id>', methods=['GET', 'POST'])
def detail(book_id):
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

    # 该书的申请列表（提供者和管理员可见）
    requests_list = []
    if is_provider or session.get('role') == 'admin':
        requests_list = DriftRequest.query.filter_by(book_id=book.id).order_by(DriftRequest.create_time.desc()).all()

    # 当前用户是否已申请
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


# 4. 提交领取申请
@crossing_bp.route('/request/<int:book_id>', methods=['POST'])
def request_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    book = DriftBook.query.get_or_404(book_id)
    acc_type, acc_id, _ = get_current_account()

    if book.status != 'drifting':
        flash('该书已被领走，无法申请！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    # 不能申请自己的书
    is_provider = (
        (acc_type == 'student' and book.provider_student_id == acc_id) or
        (acc_type == 'teacher' and book.provider_teacher_id == acc_id) or
        (acc_type == 'user' and book.provider_user_id == acc_id)
    )
    if is_provider:
        flash('不能申请自己发布的图书！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    # 检查是否已申请
    existing = DriftRequest.query.filter_by(book_id=book_id).filter(
        (DriftRequest.receiver_user_id == acc_id) if acc_type == 'user'
        else ((DriftRequest.receiver_teacher_id == acc_id) if acc_type == 'teacher'
              else (DriftRequest.receiver_student_id == acc_id))
    ).first()
    if existing:
        flash('您已经提交过申请，请等待提供者处理！', 'error')
        return redirect(url_for('crossing.detail', book_id=book_id))

    message = request.form.get('message', '').strip()
    dr = DriftRequest(book_id=book_id, message=message if message else None)
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


# 5. 我的漂流（管理员可查看全部）
@crossing_bp.route('/my')
def my_crossing():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    acc_type, acc_id, _ = get_current_account()
    is_admin = session.get('role') == 'admin'

    if is_admin:
        # 管理员查看全部
        my_books = DriftBook.query.order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.order_by(DriftRequest.create_time.desc()).all()
        all_requests = DriftRequest.query.order_by(DriftRequest.create_time.desc()).all()
    elif acc_type == 'student':
        my_books = DriftBook.query.filter_by(provider_student_id=acc_id).order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.filter_by(receiver_student_id=acc_id).order_by(DriftRequest.create_time.desc()).all()
    elif acc_type == 'teacher':
        my_books = DriftBook.query.filter_by(provider_teacher_id=acc_id).order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.filter_by(receiver_teacher_id=acc_id).order_by(DriftRequest.create_time.desc()).all()
    else:
        my_books = DriftBook.query.filter_by(provider_user_id=acc_id).order_by(DriftBook.publish_time.desc()).all()
        my_requests = DriftRequest.query.filter_by(receiver_user_id=acc_id).order_by(DriftRequest.create_time.desc()).all()

    # 我收到的申请（针对我发布的每本书的申请）
    received_requests = {}
    for book in my_books:
        reqs = DriftRequest.query.filter_by(book_id=book.id).order_by(DriftRequest.create_time.desc()).all()
        if reqs:
            received_requests[book.id] = reqs

    return render_template('crossing/my.html',
                           my_books=my_books,
                           my_requests=my_requests,
                           received_requests=received_requests,
                           is_admin=is_admin)


# 6. 处理申请（同意/拒绝）
@crossing_bp.route('/handle_request/<int:request_id>/<action>', methods=['POST'])
def handle_request(request_id, action):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if action not in ('accept', 'reject'):
        flash('无效操作！', 'error')
        return redirect(url_for('crossing.my_crossing'))

    dr = DriftRequest.query.get_or_404(request_id)
    book = dr.book
    acc_type, acc_id, _ = get_current_account()

    # 只有书的提供者或管理员才能操作
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
        dr.status = 'accepted'
        book.status = 'claimed'
        # 记录领取者
        if dr.receiver_student_id:
            book.receiver_student_id = dr.receiver_student_id
        elif dr.receiver_teacher_id:
            book.receiver_teacher_id = dr.receiver_teacher_id
        else:
            book.receiver_user_id = dr.receiver_user_id
        # 拒绝该书的其他申请
        other_requests = DriftRequest.query.filter(
            DriftRequest.book_id == book.id,
            DriftRequest.id != dr.id
        ).all()
        for r in other_requests:
            r.status = 'rejected'
        flash(f'已同意申请，该书已标记为"已领走"！', 'success')
    else:
        dr.status = 'rejected'
        flash('已拒绝该申请。', 'success')

    db.session.commit()
    return redirect(url_for('crossing.my_crossing'))


# 7. 管理员删除漂流图书
@crossing_bp.route('/delete/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('crossing.index'))

    book = DriftBook.query.get_or_404(book_id)
    title = book.title
    # 级联删除关联的申请记录
    DriftRequest.query.filter_by(book_id=book.id).delete()
    db.session.delete(book)
    db.session.commit()
    flash(f'已删除漂流图书《{title}》及其所有申请记录。', 'success')
    return redirect(url_for('crossing.index'))


# 8. 管理员编辑漂流图书
@crossing_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('crossing.index'))

    book = DriftBook.query.get_or_404(book_id)

    if request.method == 'POST':
        book.title = request.form.get('title', '').strip() or book.title
        book.course_related = request.form.get('course_related', '').strip() or None
        book.condition = request.form.get('condition', '良好')
        book.description = request.form.get('description', '').strip() or None
        # 管理员可修改状态
        new_status = request.form.get('status')
        if new_status in ('drifting', 'claimed'):
            book.status = new_status

        db.session.commit()
        flash(f'《{book.title}》信息已更新。', 'success')
        return redirect(url_for('crossing.detail', book_id=book.id))

    return render_template('crossing/edit.html', book=book)


# 9. 管理员删除申请记录
@crossing_bp.route('/delete_request/<int:request_id>', methods=['POST'])
def delete_request(request_id):
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
