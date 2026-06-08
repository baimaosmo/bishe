from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.models import Seat, SeatReservation
from app import db

seats_bp = Blueprint('seats', __name__)


def current_account_filter():
    if session.get('account_type') == 'student':
        return SeatReservation.student_id == session.get('account_id')
    if session.get('account_type') == 'teacher':
        return SeatReservation.teacher_id == session.get('account_id')
    return SeatReservation.user_id == session.get('account_id')


def assign_current_account(reservation):
    if session.get('account_type') == 'student':
        reservation.student_id = session.get('account_id')
    elif session.get('account_type') == 'teacher':
        reservation.teacher_id = session.get('account_id')
    else:
        reservation.user_id = session.get('account_id')

def cleanup_expired_reservations():
    """
    逻辑核心：自动释放超时的座位 (3小时)
    """
    now = datetime.utcnow()
    expire_threshold = now - timedelta(hours=3)
    
    expired_records = SeatReservation.query.filter(
        SeatReservation.status == 'active',
        SeatReservation.start_time <= expire_threshold
    ).all()
    
    for record in expired_records:
        record.status = 'completed'
        record.end_time = now
        record.seat.status = 'free'
    
    if expired_records:
        db.session.commit()

# 1. 座位可视化大厅
@seats_bp.route('/')
def index():
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    cleanup_expired_reservations()

    current_floor = request.args.get('floor', 1, type=int)
    
    active_reservation = SeatReservation.query.filter(
        current_account_filter(),
        SeatReservation.status == 'active'
    ).first()

    remaining_minutes = None
    show_warning = False
    
    if active_reservation:
        used_delta = datetime.utcnow() - active_reservation.start_time
        used_minutes = used_delta.total_seconds() / 60
        remaining_minutes = int(max(0, 180 - used_minutes))
        
        if remaining_minutes <= 30:
            show_warning = True

    seats = Seat.query.filter_by(floor=current_floor).order_by(Seat.seat_number).all()
    areas = sorted(list(set([s.area for s in seats])))

    # 按区域 → 行(seat_number前缀) 分组，构建更立体的数据结构
    areas_data = {}
    for area_name in areas:
        rows = {}
        for seat in seats:
            if seat.area != area_name:
                continue
            raw = seat.seat_number.rsplit('-', 1)[0] if '-' in seat.seat_number else ''
            # 去掉楼层前缀(如 "1F-A" → "A")，让行标签更简洁
            parts = raw.split('-')
            prefix = parts[-1] if len(parts) > 1 else raw
            if prefix not in rows:
                rows[prefix] = []
            rows[prefix].append(seat)
        areas_data[area_name] = rows

    # 楼层统计数据
    total_seats = len(seats)
    free_seats = sum(1 for s in seats if s.status == 'free')
    occupied_seats = total_seats - free_seats
    occupancy_rate = round(occupied_seats / total_seats * 100) if total_seats > 0 else 0

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
                         occupancy_rate=occupancy_rate)

# ================= 补回缺失的选座路由 =================
# 2. 选座请求处理
@seats_bp.route('/book/<int:seat_id>')
def book_seat(seat_id):
    if 'account_id' not in session: return redirect(url_for('auth.login'))
    
    existing = SeatReservation.query.filter(
        current_account_filter(),
        SeatReservation.status == 'active'
    ).first()
    if existing:
        flash('您当前已经预约了一个座位，请先释放后再选新座！', 'error')
        return redirect(url_for('seats.index'))

    seat = Seat.query.get_or_404(seat_id)
    if seat.status != 'free':
        flash('手慢了，该座位已被抢占！', 'error')
        return redirect(url_for('seats.index'))

    try:
        # 创建预约记录并更新座位状态
        reservation = SeatReservation(seat_id=seat.id)
        assign_current_account(reservation)
        seat.status = 'occupied'
        
        db.session.add(reservation)
        db.session.commit()
        flash(f'选座成功！您的座位号是 {seat.seat_number}。', 'success')
    except Exception as e:
        db.session.rollback()
        flash('选座失败，系统异常。', 'error')

    return redirect(url_for('seats.index'))
# ====================================================

# 3. 退座/释放请求处理
@seats_bp.route('/release/<int:reservation_id>')
def release_seat(reservation_id):
    if 'account_id' not in session: return redirect(url_for('auth.login'))
    
    reservation = SeatReservation.query.get_or_404(reservation_id)
    
    if session.get('account_type') == 'student':
        owns_reservation = reservation.student_id == session['account_id']
    elif session.get('account_type') == 'teacher':
        owns_reservation = reservation.teacher_id == session['account_id']
    else:
        owns_reservation = reservation.user_id == session['account_id']

    if not owns_reservation and session.get('role') != 'admin':
        flash('无权操作！', 'error')
        return redirect(url_for('seats.index'))

    try:
        reservation.status = 'completed'
        reservation.end_time = datetime.utcnow()
        reservation.seat.status = 'free'
        
        db.session.commit()
        flash('座位已成功释放！', 'success')
    except Exception as e:
        db.session.rollback()
        flash('释放失败，请稍后重试。', 'error')

    return redirect(url_for('seats.index'))