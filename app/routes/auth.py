# =============================================================================
# app/routes/auth.py — 用户认证与账号管理路由
# 负责: 登录/登出、注册、头像上传、修改密码、批量导入、用户管理
# 蓝图名: auth_bp，挂载在 /auth 前缀下
# 核心设计: 多类型账号统一登录（学生学号 > 教师工号 > 普通用户名）
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models import User, Student, Teacher  # 三张用户表
from app import db  # 数据库实例
import os  # 文件路径操作
import re  # 正则表达式，用于密码强度校验
from uuid import uuid4  # 生成唯一随机字符串，作为头像文件名
from werkzeug.utils import secure_filename  # 清理上传文件名，防止路径穿越攻击
import pandas as pd  # pandas 用于解析 Excel/CSV 批量导入文件
from sqlalchemy.exc import IntegrityError  # 数据库约束冲突异常（如重复主键）

# 创建认证蓝图
auth_bp = Blueprint('auth', __name__)

# 允许上传的头像文件扩展名白名单（安全措施）
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# ==================== 工具函数 ====================

def save_uploaded_avatar(file):
    """
    保存用户上传的头像文件到 static/uploads/avatars/ 目录
    参数: file — Flask request.files 中的文件对象
    返回: 相对路径字符串（如 'uploads/avatars/abc123.jpg'），失败返回 None
    """
    # 检查是否有文件以及文件名是否为空
    if not file or not file.filename:
        return None

    # 清理文件名，去除路径分隔符等危险字符
    filename = secure_filename(file.filename)

    # 检查文件扩展名是否在白名单中（防上传恶意文件）
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in ALLOWED_IMAGE_EXTENSIONS:
        flash('头像格式仅支持 png、jpg、jpeg、gif、webp。', 'error')
        return None

    # 提取扩展名
    ext = filename.rsplit('.', 1)[1].lower()

    # 构建保存目录路径，确保目录存在
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'avatars')
    os.makedirs(upload_dir, exist_ok=True)

    # 生成唯一的文件名（UUID 十六进制 + 扩展名），避免文件名冲突
    saved_name = f'{uuid4().hex}.{ext}'

    # 保存文件到磁盘
    file.save(os.path.join(upload_dir, saved_name))

    # 返回相对路径，存入数据库
    return f'uploads/avatars/{saved_name}'


def current_account():
    """
    获取当前登录用户的 ORM 模型对象
    根据 session 中的 account_type 判断去查哪张表
    返回: Student / Teacher / User 对象，或 None
    """
    if session.get('account_type') == 'student':
        return Student.query.get(session.get('account_id'))
    if session.get('account_type') == 'teacher':
        return Teacher.query.get(session.get('account_id'))
    # 默认查 users 表
    return User.query.get(session.get('account_id'))


def validate_password_strength(password):
    """
    密码强度校验
    规则: 长度≥8、至少一个字母、至少一个数字、非弱密码黑名单
    返回: 错误信息字符串（校验失败）或 None（校验通过）
    """
    # 检查长度
    if len(password or '') < 8:
        return '密码长度不能少于 8 位。'
    # 检查是否包含至少一个字母
    if not re.search(r'[A-Za-z]', password):
        return '密码必须包含至少 1 个字母。'
    # 检查是否包含至少一个数字
    if not re.search(r'\d', password):
        return '密码必须包含至少 1 个数字。'
    # 弱密码黑名单
    if password in {'12345678', 'password', 'Password1'}:
        return '密码过于简单，请更换更安全的密码。'
    return None


# ==================== 登录路由 ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    用户登录 — 支持 GET（显示登录页）和 POST（处理登录表单）
    认证流程: 先匹配学生表(学号) → 再匹配教师表(工号) → 最后匹配普通用户表(用户名)
    """

    # 如果已登录则直接跳转到图书列表页
    if 'account_id' in session:
        return redirect(url_for('books.book_list'))

    # POST 请求 → 处理登录表单提交
    if request.method == 'POST':
        # 从表单获取账号和密码
        account = request.form.get('account')  # 可能是学号、工号或用户名
        password = request.form.get('password')

        # 策略 1：先去学生表中按学号匹配
        student = Student.query.filter_by(student_no=account).first()
        if student and student.check_password(password):
            # 认证通过，将学生信息写入 Session（服务器端会话）
            session['account_id'] = student.id       # 数据库主键
            session['account_type'] = 'student'      # 账号类型标记
            session['username'] = student.name        # 显示名称
            session['role'] = 'student'              # 角色（与 account_type 一致）
            session['avatar'] = student.avatar        # 头像路径
            flash(f'欢迎回来，{student.name} 同学！', 'success')
            return redirect(url_for('books.book_list'))

        # 策略 2：再去教师表中按工号匹配
        teacher = Teacher.query.filter_by(job_no=account).first()
        if teacher and teacher.check_password(password):
            session['account_id'] = teacher.id
            session['account_type'] = 'teacher'
            session['username'] = teacher.name
            session['role'] = 'teacher'
            session['avatar'] = teacher.avatar
            flash(f'欢迎回来，{teacher.name} 老师！', 'success')
            return redirect(url_for('books.book_list'))

        # 策略 3：最后去普通注册用户表中按用户名匹配
        user = User.query.filter_by(username=account).first()
        if user and user.check_password(password):
            session['account_id'] = user.id
            session['account_type'] = 'user'
            session['username'] = user.username
            session['role'] = user.role  # user 或 admin
            session['avatar'] = user.avatar
            flash(f'登录成功，欢迎 {user.username}！', 'success')
            return redirect(url_for('books.book_list'))

        # 三种匹配均失败 → 提示错误，停留在登录页
        flash('账号、学号/工号或密码错误，请重试！', 'error')

    # GET 请求 → 渲染登录页面
    return render_template('auth/login.html')


# ==================== 注册路由 ====================

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    用户自主注册 — 学生和教师可通过此页面自行注册账号
    注册后账号写入对应的 students 或 teachers 表
    注册密码: 自行设定
    """

    if request.method == 'POST':
        # 获取表单数据并去除首尾空白
        account_type = request.form.get('account_type', 'student')  # 默认为学生
        account_no = (request.form.get('account_no') or '').strip()  # 学号或工号
        name = (request.form.get('name') or '').strip()
        gender = (request.form.get('gender') or '').strip()
        major = (request.form.get('major') or '').strip()
        password = request.form.get('password') or ''
        confirm_password = request.form.get('confirm_password') or ''

        # 校验：只支持学生或教师身份注册
        if account_type not in {'student', 'teacher'}:
            flash('请选择正确的注册身份。', 'error')
            return redirect(url_for('auth.register'))

        # 校验：所有必填项不能为空
        if not all([account_no, name, gender, major, password, confirm_password]):
            flash('请完整填写账号、姓名、性别、专业和密码。', 'error')
            return redirect(url_for('auth.register'))

        # 校验：两次密码输入是否一致
        if password != confirm_password:
            flash('两次输入的密码不一致，请重新输入。', 'error')
            return redirect(url_for('auth.register'))

        # 校验：密码强度
        password_error = validate_password_strength(password)
        if password_error:
            flash(password_error, 'error')
            return redirect(url_for('auth.register'))

        # 校验：学号/工号是否已被占用（在三张表中查重）
        if (Student.query.filter_by(student_no=account_no).first() or
            Teacher.query.filter_by(job_no=account_no).first() or
            User.query.filter_by(username=account_no).first()):
            flash('该学号/工号已被注册或占用，请检查后重试。', 'error')
            return redirect(url_for('auth.register'))

        try:
            # 根据选择的身份类型创建不同的对象
            if account_type == 'student':
                new_account = Student(
                    student_no=account_no,
                    name=name,
                    gender=gender,
                    major=major,
                    department=major[:50]  # 院系从专业名截取前 50 个字符
                )
                success_message = '学生账号注册成功，请使用学号登录！'
            else:
                new_account = Teacher(
                    job_no=account_no,
                    name=name,
                    gender=gender,
                    major=major,
                    department=major[:50]
                )
                success_message = '教师账号注册成功，请使用工号登录！'

            # 设置密码（哈希存储）
            new_account.set_password(password)
            # 写入数据库
            db.session.add(new_account)
            db.session.commit()
            flash(success_message, 'success')
            return redirect(url_for('auth.login'))

        except IntegrityError:
            # 捕获唯一约束冲突（并发或边界情况）
            db.session.rollback()
            flash('注册失败：该学号/工号已存在。', 'error')

    # GET 请求 → 渲染注册页面
    return render_template('auth/register.html')


# ==================== 批量导入路由 ====================

@auth_bp.route('/import_students', methods=['GET', 'POST'])
def import_students():
    """
    管理员批量导入学生/教师账号
    支持上传 Excel(.xlsx/.xls) 或 CSV 文件
    导入流程: 校验文件格式 → 校验表头 → 逐行读取并写入数据库
    """

    # 权限校验：只有管理员角色才能导入
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可执行此操作！', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 从表单获取导入类型（student 或 teacher）
        import_type = request.form.get('import_type', 'student')

        # 导入配置字典 — 学生和教师各自需要的列和模型
        import_configs = {
            'student': {
                'label': '学生',                          # 显示名称
                'account_column': '学号',                 # 表格中的账号列名
                'required_columns': ['学号', '姓名', '性别', '专业'],  # 必须包含的列
                'model': Student,                         # 对应的 ORM 模型
                'lookup_field': 'student_no',             # 用于查重的字段
                'password': '123456'                      # 默认初始密码
            },
            'teacher': {
                'label': '教师',
                'account_column': '工号',
                'required_columns': ['工号', '姓名', '性别', '专业'],
                'model': Teacher,
                'lookup_field': 'job_no',
                'password': '123456'
            }
        }

        # 获取对应导入类型的配置
        config = import_configs.get(import_type)
        if not config:
            flash('请选择正确的导入类型！', 'error')
            return redirect(url_for('auth.import_students'))

        # 1. 获取上传的文件对象
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择一个有效的文件！', 'error')
            return redirect(url_for('auth.import_students'))

        # 2. 校验文件扩展名（安全措施：只允许表格类文件）
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            flash('格式错误！仅支持 .xlsx 或 .csv 格式的表格文件！', 'error')
            return redirect(url_for('auth.import_students'))

        try:
            # 3. 使用 pandas 读取文件内容为 DataFrame
            if file.filename.endswith('.csv'):
                # CSV 文件：先尝试 UTF-8 编码，失败则用 GBK
                try:
                    df = pd.read_csv(file, encoding='utf-8-sig')
                except UnicodeDecodeError:
                    # 将文件指针重置到开头后重试
                    file.seek(0)
                    df = pd.read_csv(file, encoding='gbk')
            else:
                # Excel 文件
                df = pd.read_excel(file)

            # 清理列名：去除空格和 UTF-8 BOM 标记
            df.columns = [str(col).strip().lstrip('﻿') for col in df.columns]

            def clean_cell(value):
                """
                清洗单元格数据
                - NaN 值转为空字符串
                - 浮点数（如 2024001.0）转为整数字符串
                - 其余转为字符串并去空格
                """
                if pd.isna(value):
                    return ''
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value).strip()

            # 4. 校验表格表头是否包含所有必要列
            required_columns = config['required_columns']
            if not all(col in df.columns for col in required_columns):
                flash(f"表格缺少必要列！导入{config['label']}请确保表头包含：{'、'.join(required_columns)}", 'error')
                return redirect(url_for('auth.import_students'))

            success_count = 0  # 成功导入计数
            skip_count = 0     # 跳过（已存在）计数
            invalid_count = 0  # 无效（数据不完整）计数

            # 5. 逐行遍历 DataFrame，写入数据库
            for index, row in df.iterrows():
                # 提取并清洗数据
                account_no = clean_cell(row[config['account_column']])
                name = clean_cell(row['姓名'])
                gender = clean_cell(row['性别'])
                major = clean_cell(row['专业'])

                # 如果学号/工号或姓名为空 → 标记无效，跳过
                if not account_no or not name:
                    invalid_count += 1
                    continue

                # 如果该学号/工号已存在 → 标记跳过
                if config['model'].query.filter_by(**{config['lookup_field']: account_no}).first():
                    skip_count += 1
                    continue

                # 构建模型参数字典
                account_data = {
                    config['lookup_field']: account_no,
                    'name': name,
                    'gender': gender,
                    'major': major,
                    'department': major[:50]
                }

                # 创建学生或教师对象，设置默认密码
                new_account = config['model'](**account_data)
                new_account.set_password(config['password'])
                db.session.add(new_account)
                success_count += 1

            # 提交所有新记录
            db.session.commit()
            # 导入完成提示
            flash(
                f"{config['label']}导入完成！成功导入 {success_count} 条数据，"
                f"跳过 {skip_count} 条已存在数据，忽略 {invalid_count} 条无效数据。",
                'success'
            )
            return redirect(url_for('auth.manage_users'))

        except Exception as e:
            # 任何异常都回滚，保证数据一致性
            db.session.rollback()
            flash(f'导入失败，请检查表格内容是否有异常！(错误代码: {str(e)})', 'error')
            return redirect(url_for('auth.import_students'))

    # GET 请求 → 渲染导入页面（文件上传表单）
    return render_template('auth/import.html')


# ==================== 登出路由 ====================

@auth_bp.route('/logout')
def logout():
    """
    用户登出 — 清空 Session 中所有数据，跳转到登录页
    """
    session.clear()  # 清空所有会话数据
    flash('您已成功退出登录。', 'success')
    return redirect(url_for('auth.login'))


# ==================== 修改密码路由 ====================

@auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    """
    用户自助修改密码
    流程: 验证旧密码 → 校验新密码强度 → 更新密码
    """

    # 未登录拦截
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # 获取表单数据
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 表单完整性校验
        if not old_password or not new_password or not confirm_password:
            flash('请填写所有密码字段！', 'error')
            return redirect(url_for('auth.change_password'))

        # 两次新密码一致性校验
        if new_password != confirm_password:
            flash('两次输入的新密码不一致，请重新输入！', 'error')
            return redirect(url_for('auth.change_password'))

        # 新密码强度校验
        password_error = validate_password_strength(new_password)
        if password_error:
            flash(password_error, 'error')
            return redirect(url_for('auth.change_password'))

        # 新旧密码不能相同
        if old_password == new_password:
            flash('新密码不能与当前密码相同。', 'error')
            return redirect(url_for('auth.change_password'))

        # 获取当前用户对象
        account = current_account()
        if not account:
            flash('用户不存在！', 'error')
            return redirect(url_for('auth.login'))

        # 校验旧密码是否正确
        if not account.check_password(old_password):
            flash('当前密码错误！', 'error')
            return redirect(url_for('auth.change_password'))

        # 更新密码并提交
        account.set_password(new_password)
        db.session.commit()
        flash('密码修改成功！', 'success')
        return redirect(url_for('books.profile'))

    # GET 请求 → 重定向到个人中心
    return redirect(url_for('books.profile'))


# ==================== 头像上传路由 ====================

@auth_bp.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    """
    用户上传/更新头像
    仅接受 POST 请求，通过表单中的 avatar 文件字段上传
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取当前登录用户对象
    account = current_account()
    # 调用保存函数处理头像文件
    avatar = save_uploaded_avatar(request.files.get('avatar'))

    if account and avatar:
        # 更新数据库中的头像路径
        account.avatar = avatar
        # 同步更新 Session 中的头像（页面立即生效，无需重新登录）
        session['avatar'] = avatar
        db.session.commit()
        flash('头像更新成功！', 'success')
    elif not avatar:
        flash('请选择有效的头像图片。', 'error')

    # 上传后返回来源页面，若无来源则返回个人中心
    return redirect(request.referrer or url_for('books.profile'))


# ==================== 用户管理路由（管理员专有） ====================

@auth_bp.route('/manage_users')
def manage_users():
    """
    用户管理页面 — 管理员查看所有学生、教师和注册用户
    按三种类型分别查询并传给模板展示
    """

    # 权限拦截：仅管理员
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可访问！', 'error')
        return redirect(url_for('books.book_list'))

    # 分别查询三张用户表的所有记录
    students = Student.query.all()
    teachers = Teacher.query.all()
    users = User.query.all()

    # 渲染管理页面模板
    return render_template('auth/manage_users.html',
                           students=students,
                           teachers=teachers,
                           users=users)


@auth_bp.route('/reset_password/<account_type>/<int:account_id>')
def reset_password(account_type, account_id):
    """
    管理员重置指定用户密码
    参数:
      - account_type: 'student' / 'teacher' / 'user'
      - account_id:   用户主键 ID
    默认密码根据账号类型不同: Teacher@123 / Student@123 / User@123
    """

    # 权限校验
    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))

    # 根据账号类型查找对应记录
    if account_type == 'student':
        account = Student.query.get_or_404(account_id)
        name = account.name
    elif account_type == 'teacher':
        account = Teacher.query.get_or_404(account_id)
        name = account.name
    else:
        account = User.query.get_or_404(account_id)
        name = account.username

    # 确定该类型的默认密码
    default_password = ('Teacher@123' if account_type == 'teacher'
                        else 'Student@123' if account_type == 'student'
                        else 'User@123')

    # 重置密码
    account.set_password(default_password)
    db.session.commit()

    flash(f'已成功将用户【{name}】的密码重置为：{default_password}', 'success')
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/delete_user/<account_type>/<int:account_id>')
def delete_user(account_type, account_id):
    """
    管理员删除指定用户
    安全机制:
      1. 不允许删除当前登录的管理员自己
      2. 如果用户有未归还的图书，外键约束会阻止删除并在前端提示
    """

    # 权限校验
    if session.get('role') != 'admin':
        return redirect(url_for('books.book_list'))

    # 安全锁：防止管理员误删自己的账号
    if account_type == session.get('account_type') and account_id == session.get('account_id'):
        flash('危险操作：您不能删除当前正在使用的管理员账号！', 'error')
        return redirect(url_for('auth.manage_users'))

    # 根据账号类型定位目标记录
    if account_type == 'student':
        account = Student.query.get_or_404(account_id)
    elif account_type == 'teacher':
        account = Teacher.query.get_or_404(account_id)
    else:
        account = User.query.get_or_404(account_id)

    try:
        # 执行删除
        db.session.delete(account)
        db.session.commit()
        flash('该用户已被成功注销并删除。', 'success')

    except IntegrityError:
        # 外键约束阻止删除（如该用户还有借阅记录）
        db.session.rollback()
        flash('删除失败：该用户仍有借阅记录关联，请先清理其借书数据！', 'error')

    return redirect(url_for('auth.manage_users'))
