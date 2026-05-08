from app import create_app, db
from app.models import User, Student, Seat, DriftBook

app = create_app()

def init_db():
    with app.app_context():
        db.create_all()

        # 1. 创建管理员 (存在 users 表)
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)

        # 2. 批量导入本校学生 (存在 students 表)
        if Student.query.count() == 0:
            student_list = [
                {'no': '2024001', 'name': '张三', 'dept': '计算机学院'},
                {'no': '2024002', 'name': '李四', 'dept': '软件学院'},
                {'no': '2024003', 'name': '王五', 'dept': '人工智能学院'},
            ]
            for s in student_list:
                stu = Student(student_no=s['no'], name=s['name'], department=s['dept'])
                stu.set_password('123456') # 初始密码
                db.session.add(stu)

        # 3. 批量创建座位数据 (3层 × 多区域 × 多排)
        if Seat.query.count() == 0:
            seat_configs = [
                # ========== 1F：沉浸式自习大厅 ==========
                # A区 - 靠窗长排 (12座/排 × 4排)
                *[('A区', f'1F-A-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-B-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-C-{i:02d}', 1, True) for i in range(1, 13)],
                *[('A区', f'1F-D-{i:02d}', 1, True) for i in range(1, 13)],
                # B区 - 中央大厅 (12座/排 × 5排)
                *[('B区', f'1F-E-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-F-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-G-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-H-{i:02d}', 1, False) for i in range(1, 13)],
                *[('B区', f'1F-I-{i:02d}', 1, False) for i in range(1, 13)],
                # C区 - 靠墙安静区 (10座/排 × 3排)
                *[('C区', f'1F-J-{i:02d}', 1, True) for i in range(1, 11)],
                *[('C区', f'1F-K-{i:02d}', 1, True) for i in range(1, 11)],
                *[('C区', f'1F-L-{i:02d}', 1, False) for i in range(1, 11)],

                # ========== 2F：考研专修层 ==========
                # 静音区 (10座/排 × 4排，全电源)
                *[('静音区', f'2F-A-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-B-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-C-{i:02d}', 2, True) for i in range(1, 11)],
                *[('静音区', f'2F-D-{i:02d}', 2, True) for i in range(1, 11)],
                # 普通区 (10座/排 × 6排)
                *[('普通区', f'2F-E-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-F-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-G-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-H-{i:02d}', 2, False) for i in range(1, 11)],
                *[('普通区', f'2F-I-{i:02d}', 2, True) for i in range(1, 11)],
                *[('普通区', f'2F-J-{i:02d}', 2, True) for i in range(1, 11)],
                # 电子阅览区 (8座/排 × 3排，全电源)
                *[('电子阅览区', f'2F-E1-{i:02d}', 2, True) for i in range(1, 9)],
                *[('电子阅览区', f'2F-E2-{i:02d}', 2, True) for i in range(1, 9)],
                *[('电子阅览区', f'2F-E3-{i:02d}', 2, True) for i in range(1, 9)],

                # ========== 3F：综合自习层 ==========
                # A区 - 靠窗长排 (12座/排 × 4排)
                *[('A区', f'3F-A-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-B-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-C-{i:02d}', 3, True) for i in range(1, 13)],
                *[('A区', f'3F-D-{i:02d}', 3, True) for i in range(1, 13)],
                # B区 - 中央大厅 (12座/排 × 5排)
                *[('B区', f'3F-E-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-F-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-G-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-H-{i:02d}', 3, False) for i in range(1, 13)],
                *[('B区', f'3F-I-{i:02d}', 3, False) for i in range(1, 13)],
                # 研讨间 (6座/排 × 3排，全电源)
                *[('研讨间', f'3F-M1-{i:02d}', 3, True) for i in range(1, 7)],
                *[('研讨间', f'3F-M2-{i:02d}', 3, True) for i in range(1, 7)],
                *[('研讨间', f'3F-M3-{i:02d}', 3, True) for i in range(1, 7)],
            ]

            for area, seat_no, floor, has_power in seat_configs:
                db.session.add(Seat(
                    floor=floor,
                    area=area,
                    seat_number=f'{seat_no}',
                    has_power=has_power,
                    status='free'
                ))

        # 4. 添加图书漂流角种子数据
        if DriftBook.query.count() == 0:
            # 获取学生张三 (2024001) 作为默认提供者
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
                        description=f"[{'免费赠送' if d['type'] == 'free' else '希望交换'}] {d['desc']}",
                        status='drifting',
                        provider_student_id=provider.id
                    ))

        db.session.commit()
        seat_count = Seat.query.count()
        drift_count = DriftBook.query.count()
        print("✅ 数据库初始化完成！")
        print(f"管理员: admin / admin123")
        print(f"学生体验账号: 2024001 / 123456")
        print(f"座位总数: {seat_count} (1F/2F/3F)")
        print(f"漂流图书: {drift_count} 本")

if __name__ == '__main__':
    init_db()