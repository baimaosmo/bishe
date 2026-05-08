from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User, Student
from app import db
import pandas as pd
from sqlalchemy.exc import IntegrityError

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'account_id' in session:
        return redirect(url_for('books.book_list'))

    if request.method == 'POST':
        account = request.form.get('account') # 可能是用户名，也可能是学号
        password = request.form.get('password')

        # 策略 1：先去导入的“学生表”里找
        student = Student.query.filter_by(student_no=account).first()
        if student and student.check_password(password):
            session['account_id'] = student.id
            session['account_type'] = 'student'
            session['username'] = student.name
            session['role'] = 'student'
            flash(f'欢迎回来，{student.name} 同学！', 'success')
            return redirect(url_for('books.book_list'))

        # 策略 2：如果学生表没有，再去“注册用户表”里找
        user = User.query.filter_by(username=account).first()
        if user and user.check_password(password):
            session['account_id'] = user.id
            session['account_type'] = 'user'
            session['username'] = user.username
            session['role'] = user.role
            flash(f'登录成功，欢迎 {user.username}！', 'success')
            return redirect(url_for('books.book_list'))

        # 如果都没找到
        flash('账号(学号)或密码错误，请重试！', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('用户名已存在，请更换一个。', 'error')
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录！', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/register.html')



@auth_bp.route('/import_students', methods=['GET', 'POST'])
def import_students():
    # 权限校验：只有管理员可以导入学生
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可执行此操作！', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 1. 获取上传的文件
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择一个有效的文件！', 'error')
            return redirect(url_for('auth.import_students'))

        # 2. 校验文件格式
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            flash('格式错误！仅支持 .xlsx 或 .csv 格式的表格文件！', 'error')
            return redirect(url_for('auth.import_students'))

        try:
            # 3. 使用 pandas 读取表格
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            # 4. 校验表头是否包含我们需要的列（学号、姓名、院系）
            required_columns = ['学号', '姓名', '院系']
            if not all(col in df.columns for col in required_columns):
                flash('表格缺少必要列！请确保表头包含：学号、姓名、院系', 'error')
                return redirect(url_for('auth.import_students'))

            success_count = 0
            skip_count = 0

            # 5. 遍历表格数据并写入数据库
            for index, row in df.iterrows():
                # 提取并清理数据（去除前后空格）
                stu_no = str(row['学号']).strip()
                name = str(row['姓名']).strip()
                dept = str(row['院系']).strip()

                # 检查该学号是否已经存在
                if Student.query.filter_by(student_no=stu_no).first():
                    skip_count += 1
                    continue  # 如果存在就跳过，防止报错

                # 创建学生对象
                new_student = Student(student_no=stu_no, name=name, department=dept)
                new_student.set_password('123456') # 统一设置默认密码
                db.session.add(new_student)
                success_count += 1

            db.session.commit()
            flash(f'导入完成！成功导入 {success_count} 条数据，跳过 {skip_count} 条已存在数据。', 'success')
            return redirect(url_for('books.book_list')) # 导入成功后跳回首页或用户管理页

        except Exception as e:
            db.session.rollback()
            flash(f'导入失败，请检查表格内容是否有异常！(错误代码: {str(e)})', 'error')
            return redirect(url_for('auth.import_students'))

    # 如果是 GET 请求，则渲染上传页面
    return render_template('auth/import.html')
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('auth.login'))

# ==================== 修改密码（自助） ====================
@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 表单校验
        if not old_password or not new_password or not confirm_password:
            flash('请填写所有密码字段！', 'error')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('两次输入的新密码不一致，请重新输入！', 'error')
            return redirect(url_for('auth.change_password'))

        if len(new_password) < 6:
            flash('新密码长度不能少于 6 位！', 'error')
            return redirect(url_for('auth.change_password'))

        # 根据账户类型查找用户
        account_type = session.get('account_type')
        account_id = session.get('account_id')

        if account_type == 'student':
            account = Student.query.get(account_id)
        else:
            account = User.query.get(account_id)

        if not account:
            flash('用户不存在！', 'error')
            return redirect(url_for('auth.login'))

        # 验证旧密码
        if not account.check_password(old_password):
            flash('当前密码错误！', 'error')
            return redirect(url_for('auth.change_password'))

        # 更新密码
        account.set_password(new_password)
        db.session.commit()
        flash('密码修改成功！', 'success')
        return redirect(url_for('books.book_list'))

    return render_template('auth/change_password.html')


# ==================== 用户与权限管理功能 ====================

@auth_bp.route('/manage_users')
def manage_users():
    # 权限拦截
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可访问！', 'error')
        return redirect(url_for('books.book_list'))
    
    # 分别查询两张表的数据
    students = Student.query.all()
    users = User.query.all()
    
    return render_template('auth/manage_users.html', students=students, users=users)

@auth_bp.route('/reset_password/<account_type>/<int:account_id>')
def reset_password(account_type, account_id):
    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))
        
    if account_type == 'student':
        account = Student.query.get_or_404(account_id)
        name = account.name
    else:
        account = User.query.get_or_404(account_id)
        name = account.username
        
    # 一键重置密码为默认值 123456
    account.set_password('123456')
    db.session.commit()
    
    flash(f'已成功将用户【{name}】的密码重置为：123456', 'success')
    return redirect(url_for('auth.manage_users'))

@auth_bp.route('/delete_user/<account_type>/<int:account_id>')
def delete_user(account_type, account_id):
    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))
        
    # 安全锁：防止管理员把自己删了
    if account_type == session.get('account_type') and account_id == session.get('account_id'):
        flash('危险操作：您不能删除当前正在使用的管理员账号！', 'error')
        return redirect(url_for('auth.manage_users'))

    if account_type == 'student':
        account = Student.query.get_or_404(account_id)
    else:
        account = User.query.get_or_404(account_id)
        
    try:
        db.session.delete(account)
        db.session.commit()
        flash('该用户已被成功注销并删除。', 'success')
    except IntegrityError:
        # 如果该用户还有未归还的图书记录，数据库的外键约束会阻止删除，这里做优雅拦截
        db.session.rollback()
        flash('删除失败：该用户仍有借阅记录关联，请先清理其借书数据！', 'error')
        
    return redirect(url_for('auth.manage_users'))