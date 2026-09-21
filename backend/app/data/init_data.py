from datetime import datetime
from app.core.security import get_password_hash


async def init_sample_data(db):
    existing_admin = await db.users.find_one({"username": "admin"})
    if not existing_admin:
        admin_user = {
            "username": "admin",
            "email": "admin@example.com",
            "hashed_password": get_password_hash("admin123"),
            "role": "admin",
            "created_at": datetime.utcnow(),
            "avatar": None,
            "stats": {
                "total_practiced": 0,
                "total_correct": 0,
                "streak_days": 0
            }
        }
        await db.users.insert_one(admin_user)

    existing_student = await db.users.find_one({"username": "student"})
    if not existing_student:
        student_user = {
            "username": "student",
            "email": "student@example.com",
            "hashed_password": get_password_hash("student123"),
            "role": "student",
            "created_at": datetime.utcnow(),
            "avatar": None,
            "stats": {
                "total_practiced": 0,
                "total_correct": 0,
                "streak_days": 0
            }
        }
        await db.users.insert_one(student_user)

    subjects_count = await db.subjects.count_documents({})
    if subjects_count == 0:
        subjects = [
            {"name": "数学", "icon": "📐", "description": "高中数学知识点练习", "color": "#1890ff", "created_at": datetime.utcnow()},
            {"name": "英语", "icon": "📚", "description": "英语词汇语法练习", "color": "#52c41a", "created_at": datetime.utcnow()},
            {"name": "物理", "icon": "⚛️", "description": "物理基础知识练习", "color": "#fa8c16", "created_at": datetime.utcnow()},
            {"name": "化学", "icon": "🧪", "description": "化学基础知识练习", "color": "#eb2f96", "created_at": datetime.utcnow()}
        ]

        subject_results = await db.subjects.insert_many(subjects)
        subject_ids = [str(id) for id in subject_results.inserted_ids]

        for i, subject_id in enumerate(subject_ids):
            subject_name = subjects[i]["name"]
            await _init_knowledge_tree(db, subject_id, subject_name)
            await _init_sample_questions(db, subject_id, subject_name)


async def _init_knowledge_tree(db, subject_id, subject_name):
    chapters = []
    sections = []
    knowledge_points = []

    if subject_name == "数学":
        chapters = [
            {"name": "第一章 集合与逻辑", "level": 1, "order": 1},
            {"name": "第二章 函数", "level": 1, "order": 2},
            {"name": "第三章 导数", "level": 1, "order": 3}
        ]
    elif subject_name == "英语":
        chapters = [
            {"name": "第一章 词汇", "level": 1, "order": 1},
            {"name": "第二章 语法", "level": 1, "order": 2},
            {"name": "第三章 阅读理解", "level": 1, "order": 3}
        ]
    elif subject_name == "物理":
        chapters = [
            {"name": "第一章 力学", "level": 1, "order": 1},
            {"name": "第二章 电学", "level": 1, "order": 2},
            {"name": "第三章 光学", "level": 1, "order": 3}
        ]
    elif subject_name == "化学":
        chapters = [
            {"name": "第一章 物质结构", "level": 1, "order": 1},
            {"name": "第二章 化学反应", "level": 1, "order": 2},
            {"name": "第三章 有机化学", "level": 1, "order": 3}
        ]

    chapter_ids = []
    for chapter in chapters:
        doc = {
            **chapter,
            "subject_id": subject_id,
            "parent_id": None,
            "description": "",
            "created_at": datetime.utcnow()
        }
        result = await db.knowledge_nodes.insert_one(doc)
        chapter_ids.append(str(result.inserted_id))

    section_names = {
        "数学": ["第一节 集合", "第二节 逻辑", "第一节 函数概念", "第二节 函数性质", "第一节 导数概念", "第二节 导数应用"],
        "英语": ["第一节 词汇基础", "第二节 词汇拓展", "第一节 时态语态", "第二节 从句", "第一节 细节理解", "第二节 推理判断"],
        "物理": ["第一节 牛顿运动定律", "第二节 运动学", "第一节 电路", "第二节 电场", "第一节 几何光学", "第二节 物理光学"],
        "化学": ["第一节 原子结构", "第二节 化学键", "第一节 氧化还原", "第二节 化学平衡", "第一节 烃类", "第二节 烃的衍生物"]
    }

    section_ids = []
    for idx, chapter_id in enumerate(chapter_ids):
        section_start = idx * 2
        for i in range(2):
            doc = {
                "name": section_names[subject_name][section_start + i],
                "level": 2,
                "subject_id": subject_id,
                "parent_id": chapter_id,
                "order": i + 1,
                "description": "",
                "created_at": datetime.utcnow()
            }
            result = await db.knowledge_nodes.insert_one(doc)
            section_ids.append(str(result.inserted_id))

    knowledge_names = {
        "数学": [
            ["集合的概念", "集合的运算"], ["命题", "充分必要条件"],
            ["函数的定义域值域", "函数的表示"], ["单调性", "奇偶性"],
            ["导数的定义", "导数公式"], ["极值问题", "单调性应用"]
        ],
        "英语": [
            ["核心词汇3500", "高频词汇"], ["词根词缀", "同义辨析"],
            ["时态", "被动语态"], ["定语从句", "状语从句"],
            ["事实细节", "指代题"], ["主旨大意", "推理判断"]
        ],
        "物理": [
            ["牛顿第一定律", "牛顿第二定律"], ["匀变速运动", "自由落体"],
            ["欧姆定律", "串并联电路"], ["电场强度", "电势"],
            ["光的反射折射", "透镜成像"], ["干涉衍射", "偏振"]
        ],
        "化学": [
            ["原子结构", "核外电子排布"], ["离子键", "共价键"],
            ["氧化还原反应", "氧化剂还原剂"], ["化学平衡移动", "平衡常数"],
            ["烷烃", "烯烃"], ["醇", "醛酸酯"]
        ]
    }

    for idx, section_id in enumerate(section_ids):
        for i, name in enumerate(knowledge_names[subject_name][idx]):
            doc = {
                "name": name,
                "level": 3,
                "subject_id": subject_id,
                "parent_id": section_id,
                "order": i + 1,
                "description": "",
                "created_at": datetime.utcnow()
            }
            await db.knowledge_nodes.insert_one(doc)


async def _init_sample_questions(db, subject_id, subject_name):
    knowledge_cursor = db.knowledge_nodes.find({
        "subject_id": subject_id,
        "level": 3
    }).limit(6)
    knowledge_nodes = await knowledge_cursor.to_list(length=6)
    knowledge_ids = [str(k["_id"]) for k in knowledge_nodes]

    if not knowledge_ids:
        return

    sample_questions = _get_sample_questions_by_subject(subject_name)

    for i, question in enumerate(sample_questions[:10]):
        k_idx = i % len(knowledge_ids)
        question_doc = {
            "type": question["type"],
            "content": question["content"],
            "options": question.get("options"),
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation"),
            "subject_id": subject_id,
            "knowledge_ids": [knowledge_ids[k_idx]],
            "difficulty": question["difficulty"],
            "tags": question.get("tags", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "stats": {"answered": 0, "correct": 0}
        }
        await db.questions.insert_one(question_doc)


def _get_sample_questions_by_subject(subject_name):
    if subject_name == "数学":
        return [
            {
                "type": "single_choice",
                "content": "集合 {1, 2, 3} 的子集个数为（）",
                "options": [
                    {"key": "A", "content": "6个"},
                    {"key": "B", "content": "7个"},
                    {"key": "C", "content": "8个"},
                    {"key": "D", "content": "9个"}
                ],
                "correct_answer": "C",
                "explanation": "n个元素的集合有2^n个子集，3个元素有2^3=8个子集。",
                "difficulty": "easy",
                "tags": ["集合"]
            },
            {
                "type": "single_choice",
                "content": "设集合 A = {x | x² - 3x + 2 = 0}，则 A = （）",
                "options": [
                    {"key": "A", "content": "{1}"},
                    {"key": "B", "content": "{2}"},
                    {"key": "C", "content": "{1, 2}"},
                    {"key": "D", "content": "{-1, -2}"}
                ],
                "correct_answer": "C",
                "explanation": "解方程x² - 3x + 2 = 0，得x=1或x=2，所以A={1, 2}。",
                "difficulty": "easy",
                "tags": ["集合", "方程"]
            },
            {
                "type": "single_choice",
                "content": "函数 f(x) = √(x-1) 的定义域是（）",
                "options": [
                    {"key": "A", "content": "x > 1"},
                    {"key": "B", "content": "x ≥ 1"},
                    {"key": "C", "content": "x > 0"},
                    {"key": "D", "content": "x ≥ 0"}
                ],
                "correct_answer": "B",
                "explanation": "根号内必须非负，即x-1≥0，所以x≥1。",
                "difficulty": "easy",
                "tags": ["函数", "定义域"]
            },
            {
                "type": "true_false",
                "content": "奇函数的图像关于原点对称。",
                "options": None,
                "correct_answer": "A",
                "explanation": "奇函数满足f(-x) = -f(x)，其图像关于原点对称。",
                "difficulty": "easy",
                "tags": ["函数", "奇偶性"]
            },
            {
                "type": "fill_blank",
                "content": "函数 f(x) = x³ 在点 x=1 处的导数值为______。",
                "options": None,
                "correct_answer": "3",
                "explanation": "f'(x) = 3x²，所以f'(1) = 3×1² = 3。",
                "difficulty": "medium",
                "tags": ["导数"]
            },
            {
                "type": "multiple_choice",
                "content": "下列函数中，在区间(0, +∞)上是增函数的有（）",
                "options": [
                    {"key": "A", "content": "y = x²"},
                    {"key": "B", "content": "y = 2^x"},
                    {"key": "C", "content": "y = -x + 1"},
                    {"key": "D", "content": "y = log₂x"}
                ],
                "correct_answer": ["A", "B", "D"],
                "explanation": "y=x²、y=2^x、y=log₂x在(0, +∞)上都是增函数，y=-x+1是减函数。",
                "difficulty": "medium",
                "tags": ["函数", "单调性"]
            },
            {
                "type": "single_choice",
                "content": "设 f(x) = x² + 2x，则 f(x) 的最小值为（）",
                "options": [
                    {"key": "A", "content": "-2"},
                    {"key": "B", "content": "-1"},
                    {"key": "C", "content": "0"},
                    {"key": "D", "content": "1"}
                ],
                "correct_answer": "B",
                "explanation": "f(x) = x² + 2x = (x+1)² - 1，当x=-1时，最小值为-1。",
                "difficulty": "easy",
                "tags": ["函数", "最值"]
            },
            {
                "type": "single_choice",
                "content": "已知 f(x) = e^x，则 f'(x) = （）",
                "options": [
                    {"key": "A", "content": "e^x"},
                    {"key": "B", "content": "xe^(x-1)"},
                    {"key": "C", "content": "e^(x-1)"},
                    {"key": "D", "content": "lnx"}
                ],
                "correct_answer": "A",
                "explanation": "指数函数e^x的导数是它本身，即(e^x)' = e^x。",
                "difficulty": "easy",
                "tags": ["导数"]
            },
            {
                "type": "fill_blank",
                "content": "集合 {a, b} 与 {b, c} 的交集是______。",
                "options": None,
                "correct_answer": "{b}",
                "explanation": "两个集合的交集是它们共有的元素组成的集合。",
                "difficulty": "easy",
                "tags": ["集合"]
            },
            {
                "type": "single_choice",
                "content": "命题\"若x² > 0，则x > 0\"是（）",
                "options": [
                    {"key": "A", "content": "真命题"},
                    {"key": "B", "content": "假命题"},
                    {"key": "C", "content": "无法判断"},
                    {"key": "D", "content": "以上都不对"}
                ],
                "correct_answer": "B",
                "explanation": "当x=-1时，x²=1>0，但x=-1<0，所以原命题为假命题。",
                "difficulty": "medium",
                "tags": ["逻辑", "命题"]
            }
        ]
    elif subject_name == "英语":
        return [
            {
                "type": "single_choice",
                "content": "The book is ______ the table.",
                "options": [
                    {"key": "A", "content": "in"},
                    {"key": "B", "content": "on"},
                    {"key": "C", "content": "at"},
                    {"key": "D", "content": "by"}
                ],
                "correct_answer": "B",
                "explanation": "表示在...上面用介词on。书在桌子上用on the table。",
                "difficulty": "easy",
                "tags": ["介词"]
            },
            {
                "type": "single_choice",
                "content": "She ______ to school every day.",
                "options": [
                    {"key": "A", "content": "go"},
                    {"key": "B", "content": "goes"},
                    {"key": "C", "content": "went"},
                    {"key": "D", "content": "going"}
                ],
                "correct_answer": "B",
                "explanation": "every day表示一般现在时，主语she是第三人称单数，动词用goes。",
                "difficulty": "easy",
                "tags": ["时态"]
            },
            {
                "type": "fill_blank",
                "content": "The opposite of \"hot\" is ______.",
                "options": None,
                "correct_answer": "cold",
                "explanation": "hot（热的）的反义词是cold（冷的）。",
                "difficulty": "easy",
                "tags": ["词汇"]
            },
            {
                "type": "single_choice",
                "content": "This is the house ______ I lived in ten years ago.",
                "options": [
                    {"key": "A", "content": "which"},
                    {"key": "B", "content": "where"},
                    {"key": "C", "content": "that"},
                    {"key": "D", "content": "both A and C"}
                ],
                "correct_answer": "D",
                "explanation": "先行词是house，关系代词在从句中作宾语，可以用which或that。",
                "difficulty": "medium",
                "tags": ["定语从句"]
            },
            {
                "type": "true_false",
                "content": "\"Beautiful\" means \"very ugly\".",
                "options": None,
                "correct_answer": "B",
                "explanation": "beautiful的意思是美丽的，ugly的意思是丑陋的，两者是反义词。",
                "difficulty": "easy",
                "tags": ["词汇"]
            },
            {
                "type": "single_choice",
                "content": "By the time he arrived, we ______ for two hours.",
                "options": [
                    {"key": "A", "content": "have waited"},
                    {"key": "B", "content": "had waited"},
                    {"key": "C", "content": "waited"},
                    {"key": "D", "content": "were waiting"}
                ],
                "correct_answer": "B",
                "explanation": "by the time引导的从句用过去时，主句用过去完成时。",
                "difficulty": "medium",
                "tags": ["时态"]
            },
            {
                "type": "multiple_choice",
                "content": "Which of the following are correct?",
                "options": [
                    {"key": "A", "content": "He is taller than me."},
                    {"key": "B", "content": "She runs fastest in her class."},
                    {"key": "C", "content": "This is most interesting book."},
                    {"key": "D", "content": "He is as tall as his brother."}
                ],
                "correct_answer": ["A", "B", "D"],
                "explanation": "C选项缺少定冠词the，应为\"the most interesting book\"。",
                "difficulty": "medium",
                "tags": ["比较级", "最高级"]
            },
            {
                "type": "fill_blank",
                "content": "The past tense of \"eat\" is ______.",
                "options": None,
                "correct_answer": "ate",
                "explanation": "eat是不规则动词，过去式为ate，过去分词为eaten。",
                "difficulty": "easy",
                "tags": ["动词", "时态"]
            },
            {
                "type": "single_choice",
                "content": "I don't know ______ he will come tomorrow.",
                "options": [
                    {"key": "A", "content": "that"},
                    {"key": "B", "content": "whether"},
                    {"key": "C", "content": "what"},
                    {"key": "D", "content": "which"}
                ],
                "correct_answer": "B",
                "explanation": "whether表示是否，引导宾语从句。",
                "difficulty": "medium",
                "tags": ["从句"]
            },
            {
                "type": "true_false",
                "content": "\"Advice\" is a countable noun.",
                "options": None,
                "correct_answer": "B",
                "explanation": "advice是不可数名词，不能用an advice，要说a piece of advice。",
                "difficulty": "medium",
                "tags": ["名词", "可数性"]
            }
        ]
    elif subject_name == "物理":
        return [
            {
                "type": "single_choice",
                "content": "牛顿第一定律又称为（）",
                "options": [
                    {"key": "A", "content": "惯性定律"},
                    {"key": "B", "content": "加速度定律"},
                    {"key": "C", "content": "作用力与反作用力定律"},
                    {"key": "D", "content": "万有引力定律"}
                ],
                "correct_answer": "A",
                "explanation": "牛顿第一定律也称为惯性定律，描述了物体在不受外力或合外力为零时的运动状态。",
                "difficulty": "easy",
                "tags": ["力学", "牛顿定律"]
            },
            {
                "type": "fill_blank",
                "content": "物体做自由落体运动时，加速度约为______ m/s²。",
                "options": None,
                "correct_answer": "9.8",
                "explanation": "自由落体加速度约为9.8 m/s²，方向竖直向下。",
                "difficulty": "easy",
                "tags": ["运动学", "自由落体"]
            },
            {
                "type": "single_choice",
                "content": "在串联电路中，各处电流的关系是（）",
                "options": [
                    {"key": "A", "content": "处处相等"},
                    {"key": "B", "content": "电阻越大，电流越大"},
                    {"key": "C", "content": "电阻越大，电流越小"},
                    {"key": "D", "content": "无法确定"}
                ],
                "correct_answer": "A",
                "explanation": "串联电路中电流处处相等，I = I₁ = I₂ = ...",
                "difficulty": "easy",
                "tags": ["电路", "串联"]
            },
            {
                "type": "true_false",
                "content": "光在真空中的传播速度约为3×10⁸ m/s。",
                "options": None,
                "correct_answer": "A",
                "explanation": "光在真空中的传播速度是一个重要的物理常数，约为3×10⁸ m/s。",
                "difficulty": "easy",
                "tags": ["光学", "光速"]
            },
            {
                "type": "single_choice",
                "content": "电场强度的单位是（）",
                "options": [
                    {"key": "A", "content": "V/m"},
                    {"key": "B", "content": "N/C"},
                    {"key": "C", "content": "V/A"},
                    {"key": "D", "content": "A and B"}
                ],
                "correct_answer": "D",
                "explanation": "电场强度的单位可以是V/m（伏特每米）或N/C（牛顿每库仑），两者等价。",
                "difficulty": "medium",
                "tags": ["电场", "单位"]
            },
            {
                "type": "multiple_choice",
                "content": "下列属于矢量的物理量有（）",
                "options": [
                    {"key": "A", "content": "位移"},
                    {"key": "B", "content": "速度"},
                    {"key": "C", "content": "时间"},
                    {"key": "D", "content": "力"}
                ],
                "correct_answer": ["A", "B", "D"],
                "explanation": "矢量既有大小又有方向，位移、速度、力都是矢量。时间是标量，只有大小。",
                "difficulty": "easy",
                "tags": ["物理量", "矢量"]
            },
            {
                "type": "single_choice",
                "content": "一个物体从静止开始做匀加速直线运动，加速度为2m/s²，则第3秒末的速度为（）",
                "options": [
                    {"key": "A", "content": "2 m/s"},
                    {"key": "B", "content": "4 m/s"},
                    {"key": "C", "content": "6 m/s"},
                    {"key": "D", "content": "8 m/s"}
                ],
                "correct_answer": "C",
                "explanation": "v = v₀ + at = 0 + 2×3 = 6 m/s",
                "difficulty": "easy",
                "tags": ["运动学", "匀变速"]
            },
            {
                "type": "fill_blank",
                "content": "欧姆定律的数学表达式是______。",
                "options": None,
                "correct_answer": "I=U/R",
                "explanation": "欧姆定律：在一段电路中，电流I与电压U成正比，与电阻R成反比，即I=U/R。",
                "difficulty": "easy",
                "tags": ["电路", "欧姆定律"]
            },
            {
                "type": "single_choice",
                "content": "光的折射定律中，入射角i和折射角r的关系是（）",
                "options": [
                    {"key": "A", "content": "sin i / sin r = 常数"},
                    {"key": "B", "content": "i / r = 常数"},
                    {"key": "C", "content": "i = r"},
                    {"key": "D", "content": "i > r"}
                ],
                "correct_answer": "A",
                "explanation": "根据斯涅尔定律，sin i / sin r = n₂/n₁ = 常数，称为相对折射率。",
                "difficulty": "medium",
                "tags": ["光学", "折射"]
            },
            {
                "type": "true_false",
                "content": "作用力与反作用力作用在同一物体上。",
                "options": None,
                "correct_answer": "B",
                "explanation": "作用力与反作用力分别作用在两个不同的物体上。平衡力才作用在同一物体上。",
                "difficulty": "easy",
                "tags": ["力学", "牛顿第三定律"]
            }
        ]
    else:
        return [
            {
                "type": "single_choice",
                "content": "下列物质中，属于化合物的是（）",
                "options": [
                    {"key": "A", "content": "氧气"},
                    {"key": "B", "content": "水"},
                    {"key": "C", "content": "铁"},
                    {"key": "D", "content": "空气"}
                ],
                "correct_answer": "B",
                "explanation": "化合物是由两种或两种以上元素组成的纯净物。水(H₂O)由氢和氧两种元素组成，是化合物。",
                "difficulty": "easy",
                "tags": ["物质分类"]
            },
            {
                "type": "fill_blank",
                "content": "水的化学式是______。",
                "options": None,
                "correct_answer": "H₂O",
                "explanation": "水分子由两个氢原子和一个氧原子组成，化学式为H₂O。",
                "difficulty": "easy",
                "tags": ["化学式"]
            },
            {
                "type": "single_choice",
                "content": "下列反应中，属于氧化还原反应的是（）",
                "options": [
                    {"key": "A", "content": "NaOH + HCl = NaCl + H₂O"},
                    {"key": "B", "content": "CaCO₃ = CaO + CO₂↑"},
                    {"key": "C", "content": "2H₂ + O₂ = 2H₂O"},
                    {"key": "D", "content": "AgNO₃ + NaCl = AgCl↓ + NaNO₃"}
                ],
                "correct_answer": "C",
                "explanation": "氧化还原反应有化合价的升降。2H₂ + O₂ = 2H₂O中，氢从0价变为+1价，氧从0价变为-2价。",
                "difficulty": "medium",
                "tags": ["氧化还原"]
            },
            {
                "type": "true_false",
                "content": "甲烷(CH₄)是最简单的烷烃。",
                "options": None,
                "correct_answer": "A",
                "explanation": "甲烷是最简单的烷烃，只含一个碳原子，化学式为CH₄。",
                "difficulty": "easy",
                "tags": ["有机化学", "烷烃"]
            },
            {
                "type": "single_choice",
                "content": "原子序数为11的元素是（）",
                "options": [
                    {"key": "A", "content": "氧"},
                    {"key": "B", "content": "钠"},
                    {"key": "C", "content": "镁"},
                    {"key": "D", "content": "铝"}
                ],
                "correct_answer": "B",
                "explanation": "原子序数等于质子数，钠的原子序数是11，核外电子排布为2,8,1。",
                "difficulty": "easy",
                "tags": ["原子结构", "元素周期表"]
            },
            {
                "type": "multiple_choice",
                "content": "下列物质中，含有共价键的有（）",
                "options": [
                    {"key": "A", "content": "NaCl"},
                    {"key": "B", "content": "H₂O"},
                    {"key": "C", "content": "CO₂"},
                    {"key": "D", "content": "O₂"}
                ],
                "correct_answer": ["B", "C", "D"],
                "explanation": "非金属元素之间通常形成共价键。H₂O、CO₂、O₂都含有共价键，NaCl是离子键。",
                "difficulty": "medium",
                "tags": ["化学键"]
            },
            {
                "type": "single_choice",
                "content": "化学平衡的特征不包括（）",
                "options": [
                    {"key": "A", "content": "正逆反应速率相等"},
                    {"key": "B", "content": "各组分浓度不变"},
                    {"key": "C", "content": "反应停止进行"},
                    {"key": "D", "content": "是动态平衡"}
                ],
                "correct_answer": "C",
                "explanation": "化学平衡时正逆反应都在进行，只是速率相等，并不是反应停止。",
                "difficulty": "medium",
                "tags": ["化学平衡"]
            },
            {
                "type": "fill_blank",
                "content": "乙醇的官能团是______。",
                "options": None,
                "correct_answer": "羟基",
                "explanation": "乙醇(C₂H₅OH)的官能团是羟基(-OH)。",
                "difficulty": "easy",
                "tags": ["有机化学", "官能团"]
            },
            {
                "type": "single_choice",
                "content": "下列关于催化剂的说法正确的是（）",
                "options": [
                    {"key": "A", "content": "催化剂改变反应速率，不改变平衡"},
                    {"key": "B", "content": "催化剂改变反应速率，也改变平衡"},
                    {"key": "C", "content": "催化剂不改变反应速率，改变平衡"},
                    {"key": "D", "content": "催化剂不改变反应速率，也不改变平衡"}
                ],
                "correct_answer": "A",
                "explanation": "催化剂只改变反应速率（正逆反应速率都改变），不影响化学平衡的位置。",
                "difficulty": "medium",
                "tags": ["化学平衡", "催化剂"]
            },
            {
                "type": "true_false",
                "content": "所有的酸都含有氧元素。",
                "options": None,
                "correct_answer": "B",
                "explanation": "氢氯酸(HCl)就是一种无氧酸，不含氧元素。",
                "difficulty": "easy",
                "tags": ["酸的分类"]
            }
        ]

    return []
