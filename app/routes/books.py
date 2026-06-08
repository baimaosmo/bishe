from datetime import datetime
import os
import re
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from sqlalchemy import func
from werkzeug.utils import secure_filename
from app.models import Book, BorrowRecord, BookFavorite, BookReview, SeatReservation, DriftBook, DriftRequest, Publisher
from app import db
books_bp = Blueprint('books', __name__)
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def save_uploaded_image(file, folder):
    if not file or not file.filename:
        return None
    filename = secure_filename(file.filename)
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
    if session.get('account_type') == 'student':
        return model.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return model.teacher_id == session.get('account_id')
    return model.user_id == session.get('account_id')


def assign_current_account(model):
    if session.get('account_type') == 'student':
        model.student_id = session.get('account_id')
    elif session.get('account_type') == 'teacher':
        model.teacher_id = session.get('account_id')
    else:
        model.user_id = session.get('account_id')


def account_owns(record):
    if session.get('account_type') == 'student':
        return record.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return record.teacher_id == session.get('account_id')
    return record.user_id == session.get('account_id')


def validate_isbn(isbn):
    cleaned = re.sub(r'[-\s]', '', isbn or '')
    if not re.fullmatch(r'\d{10}|\d{13}', cleaned):
        return None, '书籍号/ISBN 必须是 10 位或 13 位数字，可包含短横线。'
    if len(cleaned) == 10:
        total = sum((10 - index) * int(char) for index, char in enumerate(cleaned))
        if total % 11 != 0:
            return None, 'ISBN-10 校验失败，请检查书籍号。'
    else:
        total = sum((1 if index % 2 == 0 else 3) * int(char) for index, char in enumerate(cleaned))
        if total % 10 != 0:
            return None, 'ISBN-13 校验失败，请检查书籍号。'
    return cleaned, None


def get_publishers():
    return Publisher.query.order_by(Publisher.name.asc()).all()


def resolve_publisher_from_form():
    custom_publisher = request.form.get('publisher_custom', '').strip()
    selected_publisher = request.form.get('publisher', '').strip()
    publisher_name = custom_publisher or selected_publisher
    if publisher_name and not Publisher.query.filter_by(name=publisher_name).first():
        db.session.add(Publisher(name=publisher_name))
    return publisher_name

# 1. 图书列表展示路由
@books_bp.route('/list')
def book_list():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取前端传递的搜索关键字
    search_query = request.args.get('q', '').strip()
    
    category = request.args.get('category', '').strip()

    # 构造基础查询
    query = Book.query

    # 如果有搜索关键字，则进行模糊匹配（匹配书名或作者）
    if search_query:
        query = query.filter(
            db.or_(
                Book.title.like(f'%{search_query}%'),
                Book.author.like(f'%{search_query}%'),
                Book.isbn.like(f'%{search_query}%')
            )
        )

    if category:
        query = query.filter(Book.category == category)

    # 执行查询并按时间倒序排列
    books = query.order_by(Book.add_time.desc()).all()
    favorite_book_ids = set()
    if session.get('role') != 'admin':
        favorite_book_ids = {
            favorite.book_id
            for favorite in BookFavorite.query.filter(current_account_filter(BookFavorite)).all()
        }

    return render_template('books/list.html', books=books, search_query=search_query, category=category, favorite_book_ids=favorite_book_ids)

# 2. 添加新图书路由
# 2. 添加新图书路由
@books_bp.route('/add', methods=['GET', 'POST'])
def add_book():
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可添加图书！', 'error')
        return redirect(url_for('books.book_list'))

    if request.method == 'POST':
        # 获取前端表单提交的数据
        isbn = request.form.get('isbn')
        normalized_isbn, isbn_error = validate_isbn(isbn)
        if isbn_error:
            flash(isbn_error, 'error')
            return render_template('books/add.html', publishers=get_publishers())
        title = request.form.get('title')
        author = request.form.get('author')
        publisher = resolve_publisher_from_form()
        category = request.form.get('category')
        description = request.form.get('description')
        
        # ================= 新增：接住位置信息 =================
        floor = request.form.get('floor', type=int)
        area = request.form.get('area')
        shelf = request.form.get('shelf')
        cover_image = save_uploaded_image(request.files.get('cover_image'), 'book_covers')
        # =====================================================

        if Book.query.filter_by(isbn=normalized_isbn).first():
            flash(f'添加失败：ISBN {normalized_isbn} 已存在！', 'error')
        else:
            # 创建新的图书对象，把位置信息传进去
            new_book = Book(
                isbn=normalized_isbn,
                title=title,
                author=author,
                publisher=publisher,
                category=category,
                description=description,
                floor=floor,  # 存入楼层
                area=area,    # 存入区域
                shelf=shelf,  # 存入书架
                cover_image=cover_image,
                status='available' 
            )
            db.session.add(new_book)
            db.session.commit()
            
            flash(f'成功添加图书：《{title}》', 'success')
            return redirect(url_for('books.book_list'))

    return render_template('books/add.html', publishers=get_publishers())
# 1. 处理借阅请求
@books_bp.route('/borrow/<int:book_id>')
def borrow_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    
    book = Book.query.get_or_404(book_id)
    if book.status != 'available':
        flash('该书已被借出或不可用！', 'error')
        return redirect(url_for('books.book_list'))
    
    try:
        new_record = BorrowRecord(book_id=book.id, status='borrowing')
        assign_current_account(new_record)

        book.status = 'borrowed'
        db.session.add(new_record)
        db.session.commit()
        flash(f'成功借阅：《{book.title}》', 'success')
    except Exception as e:
        db.session.rollback()
        flash('借阅失败！', 'error')
        
    return redirect(url_for('books.book_list'))

# 2. 查看“我的借阅”记录
@books_bp.route('/my_borrowing')
def my_borrowing():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    
    records = BorrowRecord.query.filter(
        current_account_filter(BorrowRecord)
    ).order_by(BorrowRecord.borrow_time.desc()).all()

    return render_template('books/my_borrowing.html', records=records)

# 3. 处理归还请求
@books_bp.route('/return/<int:record_id>')
def return_book(record_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    
    record = BorrowRecord.query.get_or_404(record_id)
    
    # 权限检查：只能归还自己的书，除非是管理员
    if not account_owns(record) and session.get('role') != 'admin':
        flash('您没有权限操作此记录！', 'error')
        return redirect(url_for('books.my_borrowing'))

    try:
        # 更新记录状态
        record.status = 'returned'
        record.return_time = datetime.utcnow()
        # 释放图书状态
        record.book.status = 'available'
        
        db.session.commit()
        flash(f'成功归还：《{record.book.title}》。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('归还失败！', 'error')
        
    return redirect(url_for('books.my_borrowing'))
# ... 保持之前的导入不变 ...

# 1. 图书详情页面
@books_bp.route('/detail/<int:book_id>')
def book_detail(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    book = Book.query.get_or_404(book_id)
    is_favorite = False
    user_review = None
    can_review = False

    if session.get('role') != 'admin':
        is_favorite = BookFavorite.query.filter(
            BookFavorite.book_id == book.id,
            current_account_filter(BookFavorite)
        ).first() is not None
        user_review = BookReview.query.filter(
            BookReview.book_id == book.id,
            current_account_filter(BookReview)
        ).first()
        can_review = BorrowRecord.query.filter(
            BorrowRecord.book_id == book.id,
            BorrowRecord.status == 'returned',
            current_account_filter(BorrowRecord)
        ).first() is not None and user_review is None

    approved_reviews = BookReview.query.filter_by(book_id=book.id, status='approved').order_by(BookReview.created_at.desc()).all()
    average_rating = db.session.query(func.avg(BookReview.rating)).filter_by(book_id=book.id, status='approved').scalar()
    return render_template('books/detail.html', book=book, is_favorite=is_favorite, user_review=user_review, can_review=can_review, approved_reviews=approved_reviews, average_rating=average_rating)

# 2. 编辑图书页面（仅限管理员）
# 2. 编辑图书页面（仅限管理员）
@books_bp.route('/edit/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('books.book_list'))
    
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.publisher = resolve_publisher_from_form()
        book.category = request.form.get('category')
        book.description = request.form.get('description')
        
        # ================= 新增：接住并更新位置信息 =================
        book.floor = request.form.get('floor', type=int)
        book.area = request.form.get('area')
        book.shelf = request.form.get('shelf')
        cover_image = save_uploaded_image(request.files.get('cover_image'), 'book_covers')
        if cover_image:
            book.cover_image = cover_image
        # ===========================================================
        
        db.session.commit()
        flash(f'图书《{book.title}》修改成功！', 'success')
        return redirect(url_for('books.book_list'))
        
    return render_template('books/edit.html', book=book, publishers=get_publishers())


@books_bp.route('/favorite/<int:book_id>')
def favorite_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    if session.get('role') == 'admin':
        flash('管理员无需收藏图书。', 'error')
        return redirect(url_for('books.book_detail', book_id=book_id))

    book = Book.query.get_or_404(book_id)
    exists = BookFavorite.query.filter(
        BookFavorite.book_id == book.id,
        current_account_filter(BookFavorite)
    ).first()
    if not exists:
        favorite = BookFavorite(book_id=book.id)
        assign_current_account(favorite)
        db.session.add(favorite)
        db.session.commit()
        flash(f'已收藏《{book.title}》。', 'success')
    return redirect(request.referrer or url_for('books.book_detail', book_id=book.id))


@books_bp.route('/unfavorite/<int:book_id>')
def unfavorite_book(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    favorite = BookFavorite.query.filter(
        BookFavorite.book_id == book_id,
        current_account_filter(BookFavorite)
    ).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash('已取消收藏。', 'success')
    return redirect(request.referrer or url_for('books.my_favorites'))


@books_bp.route('/my_favorites')
def my_favorites():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    favorites = BookFavorite.query.filter(
        current_account_filter(BookFavorite)
    ).order_by(BookFavorite.created_at.desc()).all()
    return render_template('books/my_favorites.html', favorites=favorites)


@books_bp.route('/review/<int:book_id>', methods=['POST'])
def create_review(book_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    book = Book.query.get_or_404(book_id)
    rating = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()

    has_returned = BorrowRecord.query.filter(
        BorrowRecord.book_id == book.id,
        BorrowRecord.status == 'returned',
        current_account_filter(BorrowRecord)
    ).first()
    existing_review = BookReview.query.filter(
        BookReview.book_id == book.id,
        current_account_filter(BookReview)
    ).first()

    if not has_returned:
        flash('归还这本书后才能发表评价。', 'error')
    elif existing_review:
        flash('您已经评价过这本书。', 'error')
    elif not rating or rating < 1 or rating > 5 or len(content) < 5:
        flash('请填写 1-5 星评分，并输入至少 5 个字的评价。', 'error')
    else:
        review = BookReview(book_id=book.id, rating=rating, content=content, status='pending')
        assign_current_account(review)
        db.session.add(review)
        db.session.commit()
        flash('评价已提交，管理员审核通过后将展示。', 'success')

    return redirect(url_for('books.book_detail', book_id=book.id))


@books_bp.route('/profile')
def profile():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    borrow_records = BorrowRecord.query.filter(current_account_filter(BorrowRecord)).order_by(BorrowRecord.borrow_time.desc()).limit(5).all()
    active_borrow_count = BorrowRecord.query.filter(current_account_filter(BorrowRecord), BorrowRecord.status == 'borrowing').count()
    returned_count = BorrowRecord.query.filter(current_account_filter(BorrowRecord), BorrowRecord.status == 'returned').count()
    favorite_count = BookFavorite.query.filter(current_account_filter(BookFavorite)).count()
    review_count = BookReview.query.filter(current_account_filter(BookReview)).count()
    active_seat = SeatReservation.query.filter(current_account_filter(SeatReservation), SeatReservation.status == 'active').first()
    drift_count = DriftBook.query.filter(
        current_account_filter(type('DriftProviderFilter', (), {'user_id': DriftBook.provider_user_id, 'student_id': DriftBook.provider_student_id, 'teacher_id': DriftBook.provider_teacher_id}))
    ).count()
    request_count = DriftRequest.query.filter(
        current_account_filter(type('DriftReceiverFilter', (), {'user_id': DriftRequest.receiver_user_id, 'student_id': DriftRequest.receiver_student_id, 'teacher_id': DriftRequest.receiver_teacher_id}))
    ).count()

    return render_template('books/profile.html',
                           borrow_records=borrow_records,
                           active_borrow_count=active_borrow_count,
                           returned_count=returned_count,
                           favorite_count=favorite_count,
                           review_count=review_count,
                           active_seat=active_seat,
                           drift_count=drift_count,
                           request_count=request_count)


@books_bp.route('/recommendations')
def recommendations():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    favorite_categories = [
        row[0] for row in db.session.query(Book.category)
        .join(BookFavorite, BookFavorite.book_id == Book.id)
        .filter(current_account_filter(BookFavorite), Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(func.count(BookFavorite.id).desc())
        .limit(3)
        .all()
    ]
    borrowed_categories = [
        row[0] for row in db.session.query(Book.category)
        .join(BorrowRecord, BorrowRecord.book_id == Book.id)
        .filter(current_account_filter(BorrowRecord), Book.category.isnot(None))
        .group_by(Book.category)
        .order_by(func.count(BorrowRecord.id).desc())
        .limit(3)
        .all()
    ]
    preferred_categories = list(dict.fromkeys(favorite_categories + borrowed_categories))

    borrowed_book_ids = {
        record.book_id for record in BorrowRecord.query.filter(current_account_filter(BorrowRecord)).all()
    }
    favorite_book_ids = {
        favorite.book_id for favorite in BookFavorite.query.filter(current_account_filter(BookFavorite)).all()
    }
    excluded_ids = borrowed_book_ids | favorite_book_ids

    popular_query = db.session.query(
        Book,
        func.count(BorrowRecord.id).label('borrow_count')
    ).outerjoin(BorrowRecord, BorrowRecord.book_id == Book.id)
    if excluded_ids:
        popular_query = popular_query.filter(~Book.id.in_(excluded_ids))
    popular_books = popular_query.group_by(Book.id).order_by(func.count(BorrowRecord.id).desc(), Book.add_time.desc()).limit(8).all()

    favorite_query = db.session.query(
        Book,
        func.count(BookFavorite.id).label('favorite_count')
    ).outerjoin(BookFavorite, BookFavorite.book_id == Book.id)
    if excluded_ids:
        favorite_query = favorite_query.filter(~Book.id.in_(excluded_ids))
    hot_favorites = favorite_query.group_by(Book.id).order_by(func.count(BookFavorite.id).desc(), Book.add_time.desc()).limit(8).all()

    personalized_books = []
    if preferred_categories:
        personalized_query = Book.query.filter(Book.category.in_(preferred_categories))
        if excluded_ids:
            personalized_query = personalized_query.filter(~Book.id.in_(excluded_ids))
        personalized_books = personalized_query.order_by(Book.add_time.desc()).limit(8).all()

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


@books_bp.route('/admin/interactions')
def manage_interactions():
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可访问！', 'error')
        return redirect(url_for('books.book_list'))

    reviews = BookReview.query.order_by(BookReview.created_at.desc()).all()
    popular_books = db.session.query(Book, func.count(BookFavorite.id).label('favorite_count')).join(BookFavorite, BookFavorite.book_id == Book.id).group_by(Book.id).order_by(func.count(BookFavorite.id).desc()).limit(10).all()
    borrow_records = BorrowRecord.query.order_by(BorrowRecord.borrow_time.desc()).limit(30).all()
    seat_reservations = SeatReservation.query.order_by(SeatReservation.start_time.desc()).limit(30).all()

    return render_template('books/admin_interactions.html', reviews=reviews, popular_books=popular_books, borrow_records=borrow_records, seat_reservations=seat_reservations)


@books_bp.route('/admin/review/<int:review_id>/<action>')
def moderate_review(review_id, action):
    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))

    review = BookReview.query.get_or_404(review_id)
    if action in ['approved', 'rejected']:
        review.status = action
        db.session.commit()
        flash('评价状态已更新。', 'success')
    return redirect(url_for('books.manage_interactions'))

# 3. 删除图书逻辑（仅限管理员）
@books_bp.route('/delete/<int:book_id>')
def delete_book(book_id):
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('books.book_list'))
    
    book = Book.query.get_or_404(book_id)
    # 检查图书是否正在被借阅，如果正在被借阅，不允许删除
    if book.status != 'available':
        flash('该图书处于借出状态，无法删除！', 'error')
        return redirect(url_for('books.book_list'))
        
    db.session.delete(book)
    db.session.commit()
    flash('图书已成功从馆藏库移除。', 'success')
    return redirect(url_for('books.book_list'))