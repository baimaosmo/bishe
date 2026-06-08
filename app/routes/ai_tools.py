import json
import requests
import urllib3
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, flash
from sqlalchemy import func
from app import db
from app.models import Book, BorrowRecord, Seat, SeatReservation
from datetime import datetime, timedelta

# 隐藏因为跳过 SSL 校验而产生的控制台警告信息
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

@ai_bp.route('/report')
def generate_report():
    # 权限校验：仅限管理员
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可查看数据大屏！', 'error')
        return redirect(url_for('books.book_list'))

    today = datetime.now().date()
    start_date = today - timedelta(days=29)
    date_list = [(start_date + timedelta(days=i)).strftime('%m-%d') for i in range(30)]
    borrow_counts = {
        row.day.strftime('%m-%d'): row.count
        for row in db.session.query(
            func.date(BorrowRecord.borrow_time).label('day'),
            func.count(BorrowRecord.id).label('count')
        ).filter(func.date(BorrowRecord.borrow_time) >= start_date)
        .group_by(func.date(BorrowRecord.borrow_time))
        .all()
    }
    borrow_trend = [borrow_counts.get(day, 0) for day in date_list]

    category_rows = db.session.query(
        Book.category,
        func.count(BorrowRecord.id).label('count')
    ).join(BorrowRecord, BorrowRecord.book_id == Book.id)
    category_rows = category_rows.group_by(Book.category).order_by(func.count(BorrowRecord.id).desc()).all()
    book_categories = [
        {"value": count, "name": category or "未分类"}
        for category, count in category_rows
    ]
    if not book_categories:
        book_categories = [
            {"value": count, "name": category or "未分类"}
            for category, count in db.session.query(Book.category, func.count(Book.id)).group_by(Book.category).all()
        ]

    heat_counts = {}
    for reservation in SeatReservation.query.filter(SeatReservation.start_time >= datetime.combine(start_date, datetime.min.time())).all():
        day_index = reservation.start_time.weekday()
        hour = reservation.start_time.hour
        if hour < 9:
            slot = 0
        elif hour < 11:
            slot = 1
        elif hour < 13:
            slot = 2
        elif hour < 15:
            slot = 3
        elif hour < 17:
            slot = 4
        elif hour < 19:
            slot = 5
        elif hour < 21:
            slot = 6
        else:
            slot = 7
        heat_counts[(day_index, slot)] = heat_counts.get((day_index, slot), 0) + 1
    heatmap_data = [[day, slot, heat_counts.get((day, slot), 0)] for day in range(7) for slot in range(8)]

    total_books = Book.query.count()
    total_borrows = BorrowRecord.query.count()
    active_borrows = BorrowRecord.query.filter_by(status='borrowing').count()
    total_seats = Seat.query.count()
    occupied_seats = Seat.query.filter_by(status='occupied').count()
    top_category = book_categories[0]['name'] if book_categories else '暂无分类数据'
    peak_heat = max(heatmap_data, key=lambda item: item[2]) if heatmap_data else [0, 0, 0]
    days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    hours = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
    occupancy_rate = round(occupied_seats / total_seats * 100, 1) if total_seats else 0

    ai_summary = (
        f"当前馆藏共 {total_books} 本，累计借阅 {total_borrows} 次，仍有 {active_borrows} 本处于借阅中。"
        f"近 30 天借阅最高的分类是【{top_category}】。"
        f"当前座位占用率为 {occupancy_rate}%，近 30 天预约高峰集中在 {days[peak_heat[0]]} {hours[peak_heat[1]]} 左右。"
        "建议管理员结合热门分类补充馆藏，并在座位高峰时段加强巡检与释放异常占座。"
    )

    return render_template(
        'ai/report.html', 
        date_list=json.dumps(date_list),
        borrow_trend=json.dumps(borrow_trend),
        book_categories=json.dumps(book_categories),
        heatmap_data=json.dumps(heatmap_data),
        ai_summary=ai_summary
    )

@ai_bp.route('/smart-search')
def search_page():
    """渲染智能搜索页面"""
    # 修复：增加了未登录的拦截重定向
    if 'account_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('ai/search.html')

@ai_bp.route('/api/match', methods=['POST'])
def api_match():
    """接收前端提问与历史记录，调用 DeepSeek API"""
    if 'account_id' not in session:
        return jsonify({'error': '未登录'}), 401

    # 【修改点 1】不再只接收单句 query，而是接收整个 history 数组
    history = request.json.get('history', [])
    if not history:
        return jsonify({'error': '搜索内容不能为空'}), 400

    # 获取本地真实馆藏数据
    books = Book.query.all()
    catalog_context = "\n".join([
        f"ID:{b.id} | 书名:《{b.title}》 | 作者:{b.author} | 分类:{b.category} | 状态:{b.status}" 
        for b in books
    ])

    system_prompt = f"""
    你是一个专业的图书馆智能助手。请根据用户的提问，从以下真实的【本地馆藏图书列表】中推荐最合适的一到三本书。
    
    【本地馆藏图书列表】：
    {catalog_context}
    
    【回答要求】：
    1. 必须且只能推荐上述列表内存在的图书，绝对不能虚构不存在的书！
    2. 告诉用户为什么推荐这本书，语气要友好、专业。
    3. 如果用户的提问与列表中的任何书都不相关，请委婉地告诉用户馆内暂时没有相关书籍。
    4. 采用清晰的 Markdown 排版，重点内容加粗。
    """

    try:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['DEEPSEEK_API_KEY']}"
        }
        
        # 【修改点 2】将系统提示词与历史记录拼接。
        # history[-10:] 表示只记住最近的 10 条消息（5 轮对话），防止上下文太长导致 Token 爆炸
        messages = [{"role": "system", "content": system_prompt}] + history[-10:]
        
        payload = {
            "model": "deepseek-chat", 
            "messages": messages,
            "temperature": 0.3 
        }

        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        response.raise_for_status() 
        
        result = response.json()
        ai_reply = result['choices'][0]['message']['content']
        
        return jsonify({'reply': ai_reply})

    except Exception as e:
        print(f"DeepSeek API 请求失败: {str(e)}")
        return jsonify({'error': 'AI 引擎暂时开小差了（网络连接不稳定），请稍后再试。'}), 500

@ai_bp.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    if 'account_id' not in session:
        return jsonify({'error': '未登录'}), 401

    data = request.json
    target_type = data.get('target_type')
    book_id = data.get('book_id')
    custom_topic = data.get('custom_topic')
    report_type = data.get('report_type')
    length = data.get('length')
    
    # 【修改点 1】接收前端传来的“旧报告”和“优化要求”
    previous_report = data.get('previous_report')
    refine_prompt = data.get('refine_prompt')

    target_name = ""
    if target_type == 'book' and book_id:
        book = Book.query.get(book_id)
        target_name = f"《{book.title}》（作者：{book.author}）" if book else "未知图书"
    else:
        target_name = custom_topic

    system_prompt = """
    你是一个资深的图书编辑、学术研究员和知识管理专家。
    请根据用户的设定，生成或修改高质量、结构清晰的报告。
    
    【排版与输出要求】：
    1. 必须使用标准且美观的 Markdown 格式。
    2. 使用多级标题（##, ###）划分结构。
    3. 直接输出报告正文，不要包含类似“好的，这是为您修改的报告”等废话。
    """

    # 【修改点 2】根据是否存在优化要求，决定对 AI 说什么
    if previous_report and refine_prompt:
        user_prompt = f"""
        这是你之前生成的报告内容：
        -----------------------
        {previous_report}
        -----------------------
        请根据以下用户的最新要求，对上面的报告进行重新修改和优化，并输出完整的新报告：
        【用户新要求】：{refine_prompt}
        """
    else:
        user_prompt = f"""
        请为以下目标生成一份专业内容：
        - 目标主题/书名：{target_name}
        - 报告类型：{report_type}
        - 篇幅要求：{length}
        """

    try:
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['DEEPSEEK_API_KEY']}"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.5 
        }

        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False)
        response.raise_for_status()
        
        result = response.json()
        report_content = result['choices'][0]['message']['content']
        
        return jsonify({'report': report_content})

    except Exception as e:
        print(f"DeepSeek 报告生成失败: {str(e)}")
        return jsonify({'error': 'AI 引擎生成超时或网络异常，请稍后重试。'}), 500