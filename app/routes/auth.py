from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import User
from app import db

# 创建 auth 蓝图
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 简单的表单校验
        if not username or not password:
            flash('用户名和密码不能为空！', 'error')
        elif password != confirm_password:
            flash('两次输入的密码不一致！', 'error')
        elif User.query.filter_by(username=username).first():
            flash('该用户名已被注册！', 'error')
        else:
            # 创建新用户并保存到数据库
            new_user = User(username=username)
            new_user.set_password(password) # 加密密码
            # 如果是第一个注册的用户，默认设为管理员，其他为普通用户
            if User.query.count() == 0:
                new_user.role = 'admin'
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('注册成功，请登录！', 'success')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        # 校验用户是否存在以及密码是否正确
        if user and user.check_password(password):
            # 登录成功，将用户信息写入 session
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('main.dashboard'))
        else:
            flash('用户名或密码错误！', 'error')
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    # 退出登录，清空 session
    session.clear()
    return redirect(url_for('auth.login'))