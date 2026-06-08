# =============================================================================
# daoru.py — 独立数据库初始化脚本
# 独立于 run.py，可单独运行来快速初始化数据库
# 负责: 建表 → 创建管理员 → 创建示例学生 → 批量生成座位 → 创建漂流图书种子数据
# 运行方式: python daoru.py
# =============================================================================

from app import create_app, db  # 导入工厂函数和数据库实例
from app.models import User, Student, Seat, DriftBook  # 需要的模型类
from sqlalchemy import inspect, text  # inspect 用于反射数据库结构

# 创建 Flask 应用实例
app = create_app()


def ensure_account_schema():
    """
    检查并修复学生/教师表的字段兼容性
    如果 students 或 teachers 表缺少 gender 或 major 列，则自动添加
    """
    # 获取数据库检查器
    inspector = inspect(db.engine)

    # 构建 {表名: {列名集合}} 的字典
    table_columns = {
        table: {column['name'] for column in inspector.get_columns(table)}
        for table in inspector.get_table_names()
    }

    # 为学生表和教师表补充缺失字段
    for table in ['students', 'teachers']:
        if table in table_columns:
            if 'gender' not in table_columns[table]:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN gender VARCHAR(10) NULL'))
            if 'major' not in table_columns[table]:
                db.session.execute(text(f'ALTER TABLE {table} ADD COLUMN major VARCHAR(80) NULL'))

    db.session.commit()


def init_db():
    """
    数据库初始化主函数
    包含: 建表 → 管理员 → 示例学生 → 座位数据 → 漂流图书种子数据
    所有写入都做了幂等检查，重复运行不会产生重复数据
    """
    # 推入应用上下文
    with app.app_context():
        # 自动建表（已存在的不会重复创建）
        db.create_all()
        # 检查并修复表结构
        ensure_account_schema()

        # 1. 创建管理员账号（存放在 users 表）
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')  # role='admin' 赋予管理员权限
            admin.set_password('admin123')
            db.session.add(admin)

        # 2. 批量导入示例学生（存放在 students 表）
        if Student.query.count() == 0:
            student_list = [
                {'no': '2024001', 'name': '张三', 'gender': '男', 'major': '计算机科学与技术'},
                {'no': '2024002', 'name': '李四', 'gender': '女', 'major': '软件工程'},
                {'no': '2024003', 'name': '王五', 'gender': '男', 'major': '人工智能'},
            ]
            for s in student_list:
                stu = Student(
                    student_no=s['no'],
                    name=s['name'],
                    gender=s['gender'],
                    major=s['major'],
                    department=s['major'][:50]  # 院系从专业字段截取
                )
                stu.set_password('123456')  # 初始默认密码
                db.session.add(stu)

        # 3. 批量创建座位数据（3 层 × 多区域 × 多排）
        if Seat.query.count() == 0:
            # 座位配置列表，每个元组: (区域, 座位号, 楼层, 是否有电源)
            seat_configs = [
                # ========== 1F：沉浸式自习大厅 ==========
                # A区 - 靠窗长排 (12座/排 × 4排 = 48个座位)
                *[('A区', f'1F-A-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-B-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-C-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-D-{i:02d}', 1, True) for i in range(1, 13)],

                # B区 - 中央大厅 (12座/排 × 5排 = 60个座位)
                *[('B区', f'1F-E-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-F-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-G-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-H-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-I-{i:02d}', 1, False) for i in range(1, 13)],

                # C区 - 靠墙安静区 (10座/排 × 3排 = 30个座位)
                *[('C区', f'1F-J-{i:02d}', 1, True) for i in range(1, 11)],
                *[('C区', f'1F-K-{i:02d}', 1, True) for i in range(1, 11)],
                *[('C区', f'1F-L-{i:02d}', 1, False) for i in range(1, 11)],

                # ========== 2F：考研专修层 ==========
                # 静音区 (10座/排 × 4排 = 40个座位，全电源)
                *[('静音区', f'2F-A-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-B-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-C-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-D-{i:02d}', 2, True) for i in range(1, 11)],

                # 普通区 (10座/排 × 6排 = 60个座位)
                *[('普通区', f'2F-E-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-F-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-G-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-H-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-I-{i:02d}', 2, True) for i in range(1, 11)],
                *[('普通区', f'2F-J-{i:02d}', 2, True) for i in range(1, 11)],

                # 电子阅览区 (8座/排 × 3排 = 24个座位，全电源)
                *[('电子阅览区', f'2F-E1-{i:02d}', 2, True) for i in range(1, 9)],
                *[('电子阅览区', f'2F-E2-{i:02d}', 2, True) for i in range(1, 9)],
                *[('电子阅览区', f'2F-E3-{i:02d}', 2, True) for i in range(1, 9)],

                # ========== 3F：综合自习层 ==========
                # A区 - 靠窗长排 (12座/排 × 4排 = 48个座位)
                *[('A区', f'3F-A-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-B-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-C-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-D-{i:02d}', 3, True) for i in range(1, 13)],

                # B区 - 中央大厅 (12座/排 × 5排 = 60个座位)
                *[('B区', f'3F-E-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-F-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-G-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-H-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-I-{i:02d}', 3, False) for i in range(1, 13)],

                # 研讨间 (6座/排 × 3排 = 18个座位，全电源)
                *[('研讨间', f'3F-M1-{i:02d}', 3, True) for i in range(1, 7)],
                *[('研讨间', f'3F-M2-{i:02d}', 3, True) for i in range(1, 7)],
                *[('研讨间', f'3F-M3-{i:02d}', 3, True) for i in range(1, 7)],
            ]

            # 逐条创建座位记录
            for area, seat_no, floor, has_power in seat_configs:
                db.session.add(Seat(
                    floor=floor,
                    area=area,
                    seat_number=f'{seat_no}',
                    has_power=has_power,
                    status='free'  # 初始状态：空闲
                ))

        # 4. 添加漂流图书种子数据
        if DriftBook.query.count() == 0:
            # 获取学生张三作为默认提供者
            provider = Student.query.filter_by(student_no='2024001').first()

            drift_seeds = [
                {'title': '《高等数学（第七版）上册》', 'course': '高等数学', 'condition': '良好', 'desc': '免费赠送，书上有少量笔记但整体整洁', 'type': 'free'},
                {'title': '《数据结构（C语言版）》', 'course': '数据结构', 'condition': '良好', 'desc': '希望交换一本《算法导论》或同类算法书', 'type': 'exchange'},
                {'title': '《大学英语四级词汇》', 'course': '大学英语', 'condition': '较旧', 'desc': '免费送，封面有些磨损但内页完整', 'type': 'free'},
                {'title': '《计算机网络（第7版）》', 'course': '计算机网络', 'condition': '全新', 'desc': '几乎没用过，希望换一本《操作系统概念》', 'type': 'exchange'},
                {'title': '《线性代数》', 'course': '线性代数', 'condition': '一般', 'desc': '免费赠送，适合预习用', 'type': 'free'},
                {'title': '《Python编程从入门到实践》', 'course': 'Python程序设计', 'condition': '良好', 'desc': '学完了闲置，免费送给想学Python的同学', 'type': 'free'},
                {'title': '《马克思主义基本原理》', 'course': '马克思主义原理', 'condition': '良好', 'desc': '免费赠送', 'type': 'free'},
                {'title': '《数据库系统概论（第5版）》', 'course': '数据库原理', 'condition': '良好', 'desc': '想换《MySQL必知必会》或《Redis设计与实现》', 'type': 'exchange'},
            ]

            if provider:
                for d in drift_seeds:
                    db.session.add(DriftBook(
                        title=d['title'],
                        course_related=d['course'],
                        condition=d['condition'],
                        # 描述开头标记[免费赠送]或[希望交换]
                        description=f"[{'免费赠送' if d['type'] == 'free' else '希望交换'}] {d['desc']}",
                        status='drifting',  # 初始状态：漂流中
                        provider_student_id=provider.id  # 提供者为张三
                    ))

        # 提交所有数据
        db.session.commit()

        # 打印初始化结果
        seat_count = Seat.query.count()
        drift_count = DriftBook.query.count()
        print("数据库初始化完成！")
        print(f"管理员: admin / admin123")
        print(f"学生体验账号: 2024001 / 123456")
        print(f"座位总数: {seat_count} (1F/2F/3F)")
        print(f"漂流图书: {drift_count} 本")


# 脚本入口
if __name__ == '__main__':
    init_db()
