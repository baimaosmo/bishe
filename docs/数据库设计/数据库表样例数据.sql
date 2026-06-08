-- 数据库表样例数据
-- 说明：密码字段为论文展示用示例值，实际系统运行时应使用 Werkzeug 生成的加密哈希。

INSERT INTO users (id, username, email, password_hash, role, avatar) VALUES (1, 'admin', 'admin@library.edu.cn', 'pbkdf2_admin_001', 'admin', 'avatars/admin.png');
INSERT INTO users (id, username, email, password_hash, role, avatar) VALUES (2, 'reader001', 'reader001@library.edu.cn', 'pbkdf2_user_001', 'user', 'avatars/user001.png');
INSERT INTO users (id, username, email, password_hash, role, avatar) VALUES (3, 'reader002', 'reader002@library.edu.cn', 'pbkdf2_user_002', 'user', 'avatars/user002.png');
INSERT INTO users (id, username, email, password_hash, role, avatar) VALUES (4, 'reader003', 'reader003@library.edu.cn', 'pbkdf2_user_003', 'user', 'avatars/user003.png');

INSERT INTO students (id, student_no, name, gender, major, department, password_hash, avatar) VALUES (1, '20210001', '张明', '男', '计算机科学与技术', '计算机学院', 'pbkdf2_stu_001', 'avatars/student001.png');
INSERT INTO students (id, student_no, name, gender, major, department, password_hash, avatar) VALUES (2, '20210002', '李雪', '女', '软件工程', '计算机学院', 'pbkdf2_stu_002', 'avatars/student002.png');
INSERT INTO students (id, student_no, name, gender, major, department, password_hash, avatar) VALUES (3, '20210003', '王强', '男', '数据科学与大数据技术', '计算机学院', 'pbkdf2_stu_003', 'avatars/student003.png');
INSERT INTO students (id, student_no, name, gender, major, department, password_hash, avatar) VALUES (4, '20210004', '赵敏', '女', '信息管理与信息系统', '管理学院', 'pbkdf2_stu_004', 'avatars/student004.png');
INSERT INTO students (id, student_no, name, gender, major, department, password_hash, avatar) VALUES (5, '20210005', '陈宇', '男', '人工智能', '计算机学院', 'pbkdf2_stu_005', 'avatars/student005.png');

INSERT INTO teachers (id, job_no, name, gender, major, department, password_hash, avatar) VALUES (1, 'T202001', '刘老师', '男', '数据库技术', '计算机学院', 'pbkdf2_tea_001', 'avatars/teacher001.png');
INSERT INTO teachers (id, job_no, name, gender, major, department, password_hash, avatar) VALUES (2, 'T202002', '周老师', '女', '软件工程', '计算机学院', 'pbkdf2_tea_002', 'avatars/teacher002.png');
INSERT INTO teachers (id, job_no, name, gender, major, department, password_hash, avatar) VALUES (3, 'T202003', '孙老师', '男', '人工智能', '计算机学院', 'pbkdf2_tea_003', 'avatars/teacher003.png');

INSERT INTO publishers (id, name, created_at) VALUES (1, '清华大学出版社', '2026-01-05 09:00:00');
INSERT INTO publishers (id, name, created_at) VALUES (2, '人民邮电出版社', '2026-01-06 09:30:00');
INSERT INTO publishers (id, name, created_at) VALUES (3, '机械工业出版社', '2026-01-07 10:00:00');
INSERT INTO publishers (id, name, created_at) VALUES (4, '电子工业出版社', '2026-01-08 10:30:00');

INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (1, 'Python程序设计基础', '李华', '清华大学出版社', '9787302500011', '计算机', 2, 'A区', 'A-01', 'borrowed', 'Python语言基础与案例实践', 'covers/python.png', '2026-02-01 09:00:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (2, '数据库系统概论', '王珊', '高等教育出版社', '9787040406641', '计算机', 2, 'A区', 'A-02', 'available', '数据库原理与关系模型', 'covers/database.png', '2026-02-02 09:10:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (3, '软件工程导论', '张海藩', '清华大学出版社', '9787302500028', '软件工程', 2, 'B区', 'B-01', 'available', '软件工程方法与项目管理', 'covers/se.png', '2026-02-03 09:20:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (4, '人工智能导论', '陈斌', '机械工业出版社', '9787111600030', '人工智能', 3, 'A区', 'A-03', 'borrowed', '人工智能基本理论与应用', 'covers/ai.png', '2026-02-04 09:30:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (5, 'Web开发实战', '刘洋', '人民邮电出版社', '9787115500045', 'Web开发', 3, 'B区', 'B-02', 'available', 'Web前后端开发案例', 'covers/web.png', '2026-02-05 09:40:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (6, '数据结构与算法', '严蔚敏', '清华大学出版社', '9787302500066', '计算机', 2, 'C区', 'C-01', 'available', '常用数据结构与算法分析', 'covers/ds.png', '2026-02-06 09:50:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (7, '机器学习实践', '周志华', '电子工业出版社', '9787121300077', '人工智能', 3, 'C区', 'C-02', 'available', '机器学习算法与实践案例', 'covers/ml.png', '2026-02-07 10:00:00');
INSERT INTO books (id, title, author, publisher, isbn, category, floor, area, shelf, status, description, cover_image, add_time) VALUES (8, '信息系统分析与设计', '赵磊', '机械工业出版社', '9787111600085', '信息管理', 4, 'A区', 'A-04', 'available', '信息系统建模与设计方法', 'covers/is.png', '2026-02-08 10:10:00');

INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (1, NULL, 1, NULL, 1, '2026-03-01 09:10:00', NULL, 'borrowing');
INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (2, NULL, 2, NULL, 2, '2026-03-02 10:20:00', '2026-03-10 15:30:00', 'returned');
INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (3, NULL, NULL, 1, 4, '2026-03-03 11:00:00', NULL, 'borrowing');
INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (4, 2, NULL, NULL, 5, '2026-03-04 13:20:00', '2026-03-12 16:00:00', 'returned');
INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (5, NULL, 3, NULL, 6, '2026-03-05 14:00:00', '2026-03-15 10:00:00', 'returned');
INSERT INTO borrow_records (id, user_id, student_id, teacher_id, book_id, borrow_time, return_time, status) VALUES (6, NULL, NULL, 2, 7, '2026-03-06 15:00:00', '2026-03-20 09:30:00', 'returned');

INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (1, 1, '自习A区', 'A101', 1, 'occupied');
INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (2, 1, '自习A区', 'A102', 0, 'free');
INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (3, 1, '自习B区', 'B101', 1, 'free');
INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (4, 2, '电子阅览区', 'E201', 1, 'occupied');
INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (5, 2, '电子阅览区', 'E202', 1, 'free');
INSERT INTO seats (id, floor, area, seat_number, has_power, status) VALUES (6, 3, '安静学习区', 'Q301', 0, 'free');

INSERT INTO seat_reservations (id, user_id, student_id, teacher_id, seat_id, start_time, end_time, status) VALUES (1, NULL, 1, NULL, 1, '2026-03-21 08:30:00', NULL, 'active');
INSERT INTO seat_reservations (id, user_id, student_id, teacher_id, seat_id, start_time, end_time, status) VALUES (2, NULL, NULL, 1, 4, '2026-03-21 09:00:00', NULL, 'active');
INSERT INTO seat_reservations (id, user_id, student_id, teacher_id, seat_id, start_time, end_time, status) VALUES (3, 2, NULL, NULL, 2, '2026-03-20 14:00:00', '2026-03-20 17:00:00', 'completed');
INSERT INTO seat_reservations (id, user_id, student_id, teacher_id, seat_id, start_time, end_time, status) VALUES (4, NULL, 3, NULL, 3, '2026-03-19 10:00:00', '2026-03-19 12:00:00', 'completed');
INSERT INTO seat_reservations (id, user_id, student_id, teacher_id, seat_id, start_time, end_time, status) VALUES (5, NULL, NULL, 2, 5, '2026-03-18 15:00:00', '2026-03-18 18:00:00', 'completed');

INSERT INTO drift_books (id, title, course_related, condition, description, status, publish_time, provider_user_id, provider_student_id, provider_teacher_id, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (1, '高等数学辅导书', '高等数学', '良好', '适合大一学生复习使用', 'drifting', '2026-03-01 09:00:00', NULL, 1, NULL, NULL, NULL, NULL);
INSERT INTO drift_books (id, title, course_related, condition, description, status, publish_time, provider_user_id, provider_student_id, provider_teacher_id, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (2, 'Java程序设计', 'Java开发', '一般', '书内有少量笔记', 'claimed', '2026-03-02 10:00:00', NULL, 2, NULL, NULL, 3, NULL);
INSERT INTO drift_books (id, title, course_related, condition, description, status, publish_time, provider_user_id, provider_student_id, provider_teacher_id, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (3, '考研英语词汇', '考研英语', '良好', '词汇书保存完整', 'drifting', '2026-03-03 11:00:00', 2, NULL, NULL, NULL, NULL, NULL);
INSERT INTO drift_books (id, title, course_related, condition, description, status, publish_time, provider_user_id, provider_student_id, provider_teacher_id, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (4, '算法竞赛入门', '算法设计', '较旧', '适合算法入门练习', 'drifting', '2026-03-04 12:00:00', NULL, NULL, 2, NULL, NULL, NULL);

INSERT INTO drift_requests (id, book_id, message, status, create_time, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (1, 1, '想借来复习高等数学', 'pending', '2026-03-05 09:20:00', NULL, 4, NULL);
INSERT INTO drift_requests (id, book_id, message, status, create_time, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (2, 2, '正在学习Java课程', 'accepted', '2026-03-06 10:30:00', NULL, 3, NULL);
INSERT INTO drift_requests (id, book_id, message, status, create_time, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (3, 3, '准备考研英语复习', 'pending', '2026-03-07 11:40:00', 3, NULL, NULL);
INSERT INTO drift_requests (id, book_id, message, status, create_time, receiver_user_id, receiver_student_id, receiver_teacher_id) VALUES (4, 4, '想学习算法竞赛基础', 'rejected', '2026-03-08 12:10:00', NULL, 5, NULL);

INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (1, 2, NULL, 1, NULL, '2026-03-10 09:00:00');
INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (2, 3, NULL, 2, NULL, '2026-03-10 09:10:00');
INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (3, 5, 2, NULL, NULL, '2026-03-10 09:20:00');
INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (4, 7, NULL, NULL, 1, '2026-03-10 09:30:00');
INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (5, 8, NULL, 4, NULL, '2026-03-10 09:40:00');
INSERT INTO book_favorites (id, book_id, user_id, student_id, teacher_id, created_at) VALUES (6, 6, NULL, NULL, 2, '2026-03-10 09:50:00');

INSERT INTO book_reviews (id, book_id, user_id, student_id, teacher_id, rating, content, status, created_at) VALUES (1, 2, NULL, 2, NULL, 5, '内容系统清晰适合复习数据库基础', 'approved', '2026-03-12 10:00:00');
INSERT INTO book_reviews (id, book_id, user_id, student_id, teacher_id, rating, content, status, created_at) VALUES (2, 5, 2, NULL, NULL, 4, '案例比较完整对Web开发有帮助', 'approved', '2026-03-12 10:20:00');
INSERT INTO book_reviews (id, book_id, user_id, student_id, teacher_id, rating, content, status, created_at) VALUES (3, 6, NULL, 3, NULL, 5, '算法讲解清楚适合课程学习', 'pending', '2026-03-13 11:00:00');
INSERT INTO book_reviews (id, book_id, user_id, student_id, teacher_id, rating, content, status, created_at) VALUES (4, 7, NULL, NULL, 2, 4, '机器学习章节内容较全面', 'approved', '2026-03-14 12:00:00');
INSERT INTO book_reviews (id, book_id, user_id, student_id, teacher_id, rating, content, status, created_at) VALUES (5, 3, NULL, 4, NULL, 3, '部分章节较基础适合入门', 'rejected', '2026-03-15 13:00:00');
