from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Book, BorrowRecord   # <--- 重点是这行，把 BorrowRecord 加进来
from app import db
books_bp = Blueprint('books', __name__)

# 1. 图书列表展示路由
@books_bp.route('/list')
def book_list():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取前端传递的搜索关键字
    search_query = request.args.get('q', '').strip()
    
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

    # 执行查询并按时间倒序排列
    books = query.order_by(Book.add_time.desc()).all()
    
    return render_template('books/list.html', books=books, search_query=search_query)

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
        title = request.form.get('title')
        author = request.form.get('author')
        publisher = request.form.get('publisher')
        category = request.form.get('category')
        description = request.form.get('description')
        
        # ================= 新增：接住位置信息 =================
        floor = request.form.get('floor', type=int) 
        area = request.form.get('area')
        shelf = request.form.get('shelf')
        # =====================================================

        if Book.query.filter_by(isbn=isbn).first():
            flash(f'添加失败：ISBN {isbn} 已存在！', 'error')
        else:
            # 创建新的图书对象，把位置信息传进去
            new_book = Book(
                isbn=isbn,
                title=title,
                author=author,
                publisher=publisher,
                category=category,
                description=description,
                floor=floor,  # 存入楼层
                area=area,    # 存入区域
                shelf=shelf,  # 存入书架
                status='available' 
            )
            db.session.add(new_book)
            db.session.commit()
            
            flash(f'成功添加图书：《{title}》', 'success')
            return redirect(url_for('books.book_list'))

    return render_template('books/add.html')
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
        
        # 【核心】：判断当前登录的是什么身份，存入对应的外键
        if session.get('account_type') == 'student':
            new_record.student_id = session['account_id']
        else:
            new_record.user_id = session['account_id']
            
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
    
    # 【核心】：根据身份去对应的外键字段里查数据
    if session.get('account_type') == 'student':
        records = BorrowRecord.query.filter_by(student_id=session['account_id'], status='borrowing').all()
    else:
        records = BorrowRecord.query.filter_by(user_id=session['account_id'], status='borrowing').all()
        
    return render_template('books/my_borrowing.html', records=records)

# 3. 处理归还请求
@books_bp.route('/return/<int:record_id>')
def return_book(record_id):
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    
    record = BorrowRecord.query.get_or_404(record_id)
    
    # 权限检查：只能归还自己的书，除非是管理员
    if record.user_id != session['account_id'] and session.get('role') != 'admin':
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
    return render_template('books/detail.html', book=book)

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
        book.publisher = request.form.get('publisher')
        book.category = request.form.get('category')
        book.description = request.form.get('description')
        
        # ================= 新增：接住并更新位置信息 =================
        book.floor = request.form.get('floor', type=int)
        book.area = request.form.get('area')
        book.shelf = request.form.get('shelf')
        # ===========================================================
        
        db.session.commit()
        flash(f'图书《{book.title}》修改成功！', 'success')
        return redirect(url_for('books.book_list'))
        
    return render_template('books/edit.html', book=book)

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