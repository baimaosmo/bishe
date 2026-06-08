# =============================================================================
# app/routes/ai_tools.py — AI 智能工具路由
# 负责: AI 智能搜索（多轮对话）、AI 数据大屏报告、AI 报告生成/优化
# 蓝图名: ai_bp，挂载在 /ai 前缀下
# 使用的 AI 模型: DeepSeek Chat API
# =============================================================================

import json
import requests
import urllib3
from flask import Blueprint, render_template, request, jsonify, current_app, session, redirect, url_for, flash
from sqlalchemy import func
from app import db
from app.models import Book, BorrowRecord, Seat, SeatReservation
from datetime import datetime, timedelta

# 禁用 urllib3 的 SSL 证书验证警告（调用 API 时产生）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 创建蓝图（注意这里的 url_prefix 和 __init__.py 中的重复，实际生效的是 __init__.py 里的）
ai_bp = Blueprint('ai', __name__, url_prefix='/ai')


# ==================== 1. AI 数据大屏（管理员） ====================

@ai_bp.route('/report')
def generate_report():
    """
    AI 数据统计大屏 — 仅限管理员访问
    展示: 近30天借阅趋势、图书分类分布、座位使用热力图、AI 自动生成的统计摘要
    """

    # 权限校验
    if session.get('role') != 'admin':
        flash('权限不足，仅管理员可查看数据大屏！', 'error')
        return redirect(url_for('books.book_list'))

    # 构建近 30 天的日期标签列表
    today = datetime.now().date()
    start_date = today - timedelta(days=29)
    date_list = [(start_date + timedelta(days=i)).strftime('%m-%d') for i in range(30)]

    # 查询每天的借阅数量
    borrow_counts = {
        row.day.strftime('%m-%d'): row.count
        for row in db.session.query(
            func.date(BorrowRecord.borrow_time).label('day'),  # 按日期分组
            func.count(BorrowRecord.id).label('count')         # 统计数量
        ).filter(func.date(BorrowRecord.borrow_time) >= start_date)
        .group_by(func.date(BorrowRecord.borrow_time))
        .all()
    }
    # 构建趋势数组（对应 date_list 的顺序）
    borrow_trend = [borrow_counts.get(day, 0) for day in date_list]

    # 查询图书分类借阅排行
    category_rows = db.session.query(
        Book.category,
        func.count(BorrowRecord.id).label('count')
    ).join(BorrowRecord, BorrowRecord.book_id == Book.id)
    category_rows = category_rows.group_by(Book.category).order_by(
        func.count(BorrowRecord.id).desc()
    ).all()

    # 构建分类数据（转换为 ECharts 需要的格式）
    book_categories = [
        {"value": count, "name": category or "未分类"}
        for category, count in category_rows
    ]
    # 如果借阅数据为空，则用全馆藏分布代替
    if not book_categories:
        book_categories = [
            {"value": count, "name": category or "未分类"}
            for category, count in db.session.query(
                Book.category, func.count(Book.id)
            ).group_by(Book.category).all()
        ]

    # 生成座位使用热力图数据（7天 × 8时段）
    heat_counts = {}
    for reservation in SeatReservation.query.filter(
        SeatReservation.start_time >= datetime.combine(start_date, datetime.min.time())
    ).all():
        day_index = reservation.start_time.weekday()  # 周一=0, 周日=6
        hour = reservation.start_time.hour

        # 将小时映射到时段（每2小时一个时段）
        if hour < 9:
            slot = 0     # 08:00 前
        elif hour < 11:
            slot = 1     # 08:00-10:00
        elif hour < 13:
            slot = 2     # 10:00-12:00
        elif hour < 15:
            slot = 3     # 12:00-14:00
        elif hour < 17:
            slot = 4     # 14:00-16:00
        elif hour < 19:
            slot = 5     # 16:00-18:00
        elif hour < 21:
            slot = 6     # 18:00-20:00
        else:
            slot = 7     # 20:00-22:00

        # 累加该时段计数
        heat_counts[(day_index, slot)] = heat_counts.get((day_index, slot), 0) + 1

    # 构建热力图数据 [[day, slot, count], ...]
    heatmap_data = [
        [day, slot, heat_counts.get((day, slot), 0)]
        for day in range(7) for slot in range(8)
    ]

    # 核心统计数据
    total_books = Book.query.count()                                # 馆藏总数
    total_borrows = BorrowRecord.query.count()                      # 累计借阅
    active_borrows = BorrowRecord.query.filter_by(status='borrowing').count()  # 借阅中
    total_seats = Seat.query.count()                                # 座位总数
    occupied_seats = Seat.query.filter_by(status='occupied').count()  # 已占用
    top_category = book_categories[0]['name'] if book_categories else '暂无分类数据'

    # 找到热力峰值
    peak_heat = max(heatmap_data, key=lambda item: item[2]) if heatmap_data else [0, 0, 0]
    days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    hours = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']

    # 座位占用率
    occupancy_rate = round(occupied_seats / total_seats * 100, 1) if total_seats else 0

    # AI 自动生成的数据摘要文本
    ai_summary = (
        f"当前馆藏共 {total_books} 本，累计借阅 {total_borrows} 次，仍有 {active_borrows} 本处于借阅中。"
        f"近 30 天借阅最高的分类是【{top_category}】。"
        f"当前座位占用率为 {occupancy_rate}%，近 30 天预约高峰集中在 {days[peak_heat[0]]} {hours[peak_heat[1]]} 左右。"
        "建议管理员结合热门分类补充馆藏，并在座位高峰时段加强巡检与释放异常占座。"
    )

    # 渲染数据大屏模板（JSON 序列化数据供 ECharts 图表使用）
    return render_template(
        'ai/report.html',
        date_list=json.dumps(date_list),
        borrow_trend=json.dumps(borrow_trend),
        book_categories=json.dumps(book_categories),
        heatmap_data=json.dumps(heatmap_data),
        ai_summary=ai_summary
    )


# ==================== 2. AI 智能搜索页面 ====================

@ai_bp.route('/smart-search')
def search_page():
    """
    AI 智能搜索页面入口 — 渲染搜索对话界面
    用户在页面中输入自然语言检索需求，由 AI 分析并推荐馆藏图书
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    return render_template('ai/search.html')


# ==================== 2.5. AI 报告生成页面 ====================

@ai_bp.route('/generate-report')
def generate_report_page():
    """
    AI 报告生成页面 — 支持新建报告和优化已有报告
    用户可指定主题/图书、报告类型和篇幅，由 AI 生成专业报告
    生成后支持输入 refine_prompt 进行二次修改
    """

    if 'account_id' not in session:
        return redirect(url_for('auth.login'))

    # 获取所有图书供下拉选择
    books = Book.query.order_by(Book.title.asc()).all()

    return render_template('ai/generate_report.html', books=books)


# ==================== 3. AI 智能搜索 API ====================

@ai_bp.route('/api/match', methods=['POST'])
def api_match():
    """
    AI 智能搜索核心 API — 接收前端对话历史和用户提问
    流程:
      1. 读取本地馆藏图书数据，构建上下文
      2. 将上下文 + 对话历史发送给 DeepSeek API
      3. 返回 AI 推荐结果（只推荐馆藏中真实存在的书）
    支持多轮对话：前端将 history 数组传入，后端追加本次消息
    """

    if 'account_id' not in session:
        return jsonify({'error': '未登录'}), 401

    # 获取前端传来的完整对话历史（数组格式，包含之前所有轮次的问答）
    history = request.json.get('history', [])
    if not history:
        return jsonify({'error': '搜索内容不能为空'}), 400

    # 读取本地真实馆藏图书数据，构建 AI 上下文
    books = Book.query.all()
    catalog_context = "\n".join([
        f"ID:{b.id} | 书名:《{b.title}》 | 作者:{b.author} | 分类:{b.category} | 状态:{b.status}"
        for b in books
    ])

    # 系统提示词：定义 AI 角色和推荐规则
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
        # DeepSeek API 地址
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {current_app.config['DEEPSEEK_API_KEY']}"
        }

        # 构建消息列表：系统提示 + 最近 10 条历史（约 5 轮对话）
        # history[-10:] 限制上下文长度，防止 Token 超出限制
        messages = [{"role": "system", "content": system_prompt}] + history[-10:]

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3  # 较低的随机性，确保推荐结果稳定
        }

        # 发送 POST 请求
        response = requests.post(url, headers=headers, json=payload, timeout=30, verify=False,
                                 proxies={"http": None, "https": None})
        response.raise_for_status()  # 检查 HTTP 状态码

        # 提取 AI 回复文本
        result = response.json()
        ai_reply = result['choices'][0]['message']['content']

        # 返回 JSON 响应给前端
        return jsonify({'reply': ai_reply})

    except Exception as e:
        print(f"DeepSeek API 请求失败: {str(e)}")
        return jsonify({'error': 'AI 引擎暂时开小差了（网络连接不稳定），请稍后再试。'}), 500


# ==================== 4. AI 报告生成 API ====================

@ai_bp.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """
    AI 报告生成/优化 API
    支持两种模式:
      - 新建报告: 指定主题/图书/类型/篇幅，由 AI 生成完整报告
      - 优化已有报告: 传入 previous_report + refine_prompt，AI 在原有基础上修改
    """

    if 'account_id' not in session:
        return jsonify({'error': '未登录'}), 401

    # 获取请求参数
    data = request.json
    target_type = data.get('target_type')      # 'book' 或自定义主题
    book_id = data.get('book_id')              # 如果是图书，指定图书 ID
    custom_topic = data.get('custom_topic')    # 自定义主题文本
    report_type = data.get('report_type')      # 报告类型（如 读后感、摘要、分析）
    length = data.get('length')                # 篇幅（短/中/长）

    # 优化模式的参数
    previous_report = data.get('previous_report')  # 旧的报告内容
    refine_prompt = data.get('refine_prompt')      # 用户的优化要求

    # 确定报告目标名称
    target_name = ""
    if target_type == 'book' and book_id:
        book = Book.query.get(book_id)
        target_name = f"《{book.title}》（作者：{book.author}）" if book else "未知图书"
    else:
        target_name = custom_topic

    # 系统提示词：定义 AI 报告生成的角色和格式要求
    system_prompt = """
你是一个资深的图书编辑、学术研究员和知识管理专家。
请根据用户的设定，生成或修改高质量、结构清晰的报告。

【排版与输出要求】：
1. 必须使用标准且美观的 Markdown 格式。
2. 使用多级标题（##, ###）划分结构。
3. 直接输出报告正文，不要包含类似"好的，这是为您修改的报告"等废话。
"""

    # 根据是否优化模式，构造不同的用户提示词
    if previous_report and refine_prompt:
        # 优化模式：将旧报告和新要求一并传给 AI
        user_prompt = f"""
这是你之前生成的报告内容：
-----------------------
{previous_report}
-----------------------
请根据以下用户的最新要求，对上面的报告进行重新修改和优化，并输出完整的新报告：
【用户新要求】：{refine_prompt}
"""
    else:
        # 新建模式：从零生成报告
        user_prompt = f"""
请为以下目标生成一份专业内容：
- 目标主题/书名：{target_name}
- 报告类型：{report_type}
- 篇幅要求：{length}
"""

    try:
        # 调用 DeepSeek API
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
            "temperature": 0.5  # 中等随机性，保证创意但不过于发散
        }

        # 报告生成可能耗时较长，timeout 设为 60 秒
        response = requests.post(url, headers=headers, json=payload, timeout=60, verify=False,
                                 proxies={"http": None, "https": None})
        response.raise_for_status()

        result = response.json()
        report_content = result['choices'][0]['message']['content']

        return jsonify({'report': report_content})

    except Exception as e:
        print(f"DeepSeek 报告生成失败: {str(e)}")
        return jsonify({'error': 'AI 引擎生成超时或网络异常，请稍后重试。'}), 500
