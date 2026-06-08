# =============================================================================
# app/routes/seats.py — 座位预约管理路由
# 负责: 座位可视化大厅、选座、释放座位、超时自动释放
# 蓝图名: seats_bp，挂载在 /seats 前缀下
# 核心规则: 每位用户同时只能预约一个座位，单次使用时限 3 小时
# =============================================================================

from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Seat, SeatReservation
from app import db

# 创建蓝图
seats_bp = Blueprint('seats', __name__)

# 楼层布局配置字典 — 定义每层楼的名称、描述、地标和区域布局
# 这些配置驱动前端 seat/index.html 的动态渲染
FLOOR_LAYOUTS = {
    1: {
        'name': '1F 沉浸式自习大厅',
        'description': '入口、服务台和开放自习区集中在一层，适合快速入座和短时学习。',
        'landmarks': [
            {'label': '主入口', 'icon': 'fa-door-open', 'class': 'landmark-entry'},
            {'label': '服务台', 'icon': 'fa-circle-info', 'class': 'landmark-service'},
            {'label': '靠窗采光带', 'icon': 'fa-window-maximize', 'class': 'landmark-window'},
            {'label': '馆藏书架', 'icon': 'fa-book', 'class': 'landmark-stack'},
        ],
        'areas': {
            'A区': {'title': 'A区 靠窗长排', 'hint': '临窗采光，电源覆盖较多', 'class': 'area-window', 'grid': 'lg:col-span-5 lg:row-span-2'},
            'B区': {'title': 'B区 中央大厅', 'hint': '主通道旁，座位密集', 'class': 'area-central', 'grid': 'lg:col-span-4 lg:row-span-2'},
            'C区': {'title': 'C区 靠墙安静区', 'hint': '靠近书架和侧墙，更安静', 'class': 'area-quiet', 'grid': 'lg:col-span-3 lg:row-span-2'},
        }
    },
    2: {
        'name': '2F 考研专修层',
        'description': '二层以安静学习为主，含静音区、普通区和电子阅览区。',
        'landmarks': [
            {'label': '楼梯/电梯', 'icon': 'fa-elevator', 'class': 'landmark-entry'},
            {'label': '静音提示区', 'icon': 'fa-volume-xmark', 'class': 'landmark-service'},
            {'label': '电子阅览设备', 'icon': 'fa-desktop', 'class': 'landmark-stack'},
            {'label': '窗边自习带', 'icon': 'fa-window-maximize', 'class': 'landmark-window'},
        ],
        'areas': {
            '静音区': {'title': '静音区', 'hint': '适合考研和深度自习，电源覆盖高', 'class': 'area-quiet', 'grid': 'lg:col-span-4 lg:row-span-2'},
            '普通区': {'title': '普通区', 'hint': '二层主体座位区，靠近通道', 'class': 'area-central', 'grid': 'lg:col-span-5 lg:row-span-2'},
            '电子阅览区': {'title': '电子阅览区', 'hint': '靠近设备区，适合电脑学习', 'class': 'area-digital', 'grid': 'lg:col-span-3 lg:row-span-2'},
        }
    },
    3: {
        'name': '3F 综合自习层',
        'description': '三层兼顾个人自习和小组研讨，研讨间相对独立。',
        'landmarks': [
            {'label': '楼梯/电梯', 'icon': 'fa-elevator', 'class': 'landmark-entry'},
            {'label': '开放阅览区', 'icon': 'fa-book-open-reader', 'class': 'landmark-service'},
            {'label': '研讨间走廊', 'icon': 'fa-people-group', 'class': 'landmark-stack'},
            {'label': '窗边长桌', 'icon': 'fa-window-maximize', 'class': 'landmark-window'},
        ],
        'areas': {
            'A区': {'title': 'A区 靠窗长排', 'hint': '窗边连续座位，适合个人自习', 'class': 'area-window', 'grid': 'lg:col-span-5 lg:row-span-2'},
            'B区': {'title': 'B区 中央大厅', 'hint': '开放式座位，离主通道近', 'class': 'area-central', 'grid': 'lg:col-span-4 lg:row-span-2'},
            '研讨间': {'title': '研讨间', 'hint': '小组学习区域，电源覆盖', 'class': 'area-discussion', 'grid': 'lg:col-span-3 lg:row-span-2'},
        }
    }
}


# ==================== 工具函数 ====================

def current_account_filter():
    """
    返回当前用户的座位预约查询过滤条件
    """
    if session.get('account_type') == 'student':
        return SeatReservation.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return SeatReservation.teacher_id == session.get('account_id')
    return SeatReservation.user_id == session.get('account_id')


def assign_current_account(reservation):
    """
    给预约记录绑定当前用户的外键
    """
    if session.get('account_type') == 'student':
        reservation.student_id = session.get('account_id')
    elif session.get('account_type') == 'teacher':
        reservation.teacher_id = session.get('account_id')
    else:
        reservation.user_id = session.get('account_id')


def seat_sort_key(seat):
    """
    座位排序键函数 — 将座位号按行和数字排序
    例如: 1F-A-01 → 按行(A)排，同行走数字(1)排
    """
    parts = seat.seat_number.split('-')
    row = parts[-2] if len(parts) >= 2 else ''  # 提取行号（如 A, B, C）
    number = parts[-1] if parts else ''           # 提取数字（如 01, 02）
    try:
        number = int(number)  # 数字转整数便于排序
    except ValueError:
        pass
    return row, number


def cleanup_expired_reservations():
    """
    自动释放超时座位（3 小时时限）
    逻辑: 查找所有 status='active' 且 start_time 距今超过 3 小时的预约
    将其状态改为 completed，释放对应座位
    """
    now = datetime.utcnow()
    # 计算 3 小时前的时间点
    expire_threshold = now - timedelta(hours=3)

    # 查询所有超时的活跃预约记录
    expired_records = SeatReservation.query.filter(
        SeatReservation.status == 'active',
        SeatReservation.start_time <= expire_threshold  # 入座时间早于 3 小时前
    ).all()

    # 逐条处理超时记录
    for record in expired_records:
        record.status = 'completed'  # 预约状态 → 已完成
        record.end_time = now        # 记录离座时间
        record.seat.status = 'free'  # 座位状态 → 空闲

    # 如果有超时记录则提交
    if expired_records:
        db.session.commit()


# ==================== 1. 座位可视化大厅 ====================

@seats_bp.route('/')
def index():
    """
    座位预约主页面 — 展示选定楼层的座位布局和实时状态
    支持切换楼层（通过 ?floor= 参数）
    显示当前用户的活跃预约及剩余时间
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 进入页面前先清理所有超时预约
    cleanup_expired_reservations()

    # 获取当前查看的楼层（默认 1 楼）
    current_floor = request.args.get('floor', 1, type=int)

    # 查询当前用户的活跃预约记录（用于显示"你当前在 X 号座位"）
    active_reservation = SeatReservation.query.filter(
        current_account_filter(),
        SeatReservation.status == 'active'
    ).first()

    # 计算剩余时间
    remaining_minutes = None
    show_warning = False  # 是否显示"即将超时"警告

    if active_reservation:
        # 计算已使用分钟数
        used_delta = datetime.utcnow() - active_reservation.start_time
        used_minutes = used_delta.total_seconds() / 60
        # 剩余分钟 = 180 - 已使用（最少为 0）
        remaining_minutes = int(max(0, 180 - used_minutes))

        # 剩余 ≤ 30 分钟时显示警告
        if remaining_minutes <= 30:
            show_warning = True

    # 查询当前楼层的所有座位
    seats = Seat.query.filter_by(floor=current_floor).order_by(Seat.seat_number).all()

    # 获取当前楼层的所有区域名（去重排序）
    areas = sorted(list(set([s.area for s in seats])))

    # 构建按区域 → 行分组的数据结构，供前端渲染座位网格
    areas_data = {}
    for area_name in areas:
        rows = {}
        for seat in sorted(seats, key=seat_sort_key):
            if seat.area != area_name:
                continue
            # 提取行前缀（如 "1F-A-01" → "A"）
            raw = seat.seat_number.rsplit('-', 1)[0] if '-' in seat.seat_number else ''
            parts = raw.split('-')
            prefix = parts[-1] if len(parts) > 1 else raw
            if prefix not in rows:
                rows[prefix] = []
            rows[prefix].append(seat)
        # 按行名排序
        areas_data[area_name] = dict(sorted(rows.items(), key=lambda item: item[0]))

    # 获取当前楼层的布局配置（包括地标、区域样式等）
    floor_layout = FLOOR_LAYOUTS.get(current_floor, {
        'name': f'{current_floor}F 自习区',
        'description': '当前楼层座位布局。',
        'landmarks': [],
        'areas': {}
    })

    # 计算楼层统计数据
    total_seats = len(seats)
    free_seats = sum(1 for s in seats if s.status == 'free')
    occupied_seats = total_seats - free_seats
    occupancy_rate = round(occupied_seats / total_seats * 100) if total_seats > 0 else 0

    # 渲染座位大厅模板
    return render_template('seats/index.html',
                           seats=seats,
                           areas=areas,
                           areas_data=areas_data,
                           current_floor=current_floor,
                           active_reservation=active_reservation,
                           remaining_minutes=remaining_minutes,
                           show_warning=show_warning,
                           total_seats=total_seats,
                           free_seats=free_seats,
                           occupied_seats=occupied_seats,
                           occupancy_rate=occupancy_rate,
                           floor_layout=floor_layout)


# ==================== 2. 选座处理 ====================

@seats_bp.route('/book/<int:seat_id>')
def book_seat(seat_id):
    """
    用户预约座位
    校验规则:
      1. 用户当前不能有正在使用中的预约
      2. 目标座位必须是空闲状态
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 检查用户是否已有活跃预约
    existing = SeatReservation.query.filter(
        current_account_filter(),
        SeatReservation.status == 'active'
    ).first()
    if existing:
        flash('您当前已经预约了一个座位，请先释放后再选新座！', 'error')
        return redirect(url_for('seats.index'))

    # 检查目标座位是否空闲
    seat = Seat.query.get_or_404(seat_id)
    if seat.status != 'free':
        flash('手慢了，该座位已被抢占！', 'error')
        return redirect(url_for('seats.index'))

    try:
        # 创建预约记录并绑定用户
        reservation = SeatReservation(seat_id=seat.id)
        assign_current_account(reservation)

        # 更新座位状态为已占用
        seat.status = 'occupied'

        db.session.add(reservation)
        db.session.commit()
        flash(f'选座成功！您的座位号是 {seat.seat_number}。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('选座失败，系统异常。', 'error')

    return redirect(url_for('seats.index'))


# ==================== 3. 退座/释放处理 ====================

@seats_bp.route('/release/<int:reservation_id>')
def release_seat(reservation_id):
    """
    用户释放座位（提前离座）
    权限: 只能释放自己的预约，管理员可以释放任意预约
    释放后: 预约状态 → completed，座位状态 → free
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    reservation = SeatReservation.query.get_or_404(reservation_id)

    # 权限校验：判断是否是自己的预约
    if session.get('account_type') == 'student':
        owns_reservation = reservation.student_id == session['account_id']
    elif session.get('account_type') == 'teacher':
        owns_reservation = reservation.teacher_id == session['account_id']
    else:
        owns_reservation = reservation.user_id == session['account_id']

    # 非本人且非管理员 → 拒绝
    if not owns_reservation and session.get('role') != 'admin':
        flash('无权操作！', 'error')
        return redirect(url_for('seats.index'))

    try:
        # 更新预约记录
        reservation.status = 'completed'
        reservation.end_time = datetime.utcnow()

        # 释放座位
        reservation.seat.status = 'free'

        db.session.commit()
        flash('座位已成功释放！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('释放失败，请稍后重试。', 'error')

    return redirect(url_for('seats.index'))
