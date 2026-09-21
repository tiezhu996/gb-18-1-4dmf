# 在线题库与刷题平台

面向学生的移动端优先在线刷题学习平台，支持多种练习模式和学习数据分析。

## 快速启动（Docker Compose）

```bash
docker compose up -d
```

服务启动后访问：

- **前端页面**: http://localhost:8006
- **后端 API**: http://localhost:3006
- **API 文档**: http://localhost:3006/docs

默认账号：
- 管理员：`admin` / `admin123`
- 学生：`student` / `student123`

## 项目主要功能

- **题库管理后台**：支持单选题、多选题、判断题、填空题的录入与管理，支持按学科、知识点、难度等级分类，支持 Excel/CSV 批量导入
- **学科与知识点体系**：多级知识点树结构（学科→章→节→知识点），支持搜索快速定位，题目数量统计
- **顺序练习模式**：按知识点顺序依次作答，即时反馈答案与解析，支持上/下一题切换，自动保存练习进度
- **随机练习模式**：按学科/知识点随机抽取指定数量题目，支持设定题目数量（10/20/50题）和难度范围
- **模拟考试模式**：倒计时答题，答题进度自动保存，刷新页面恢复剩余时间；到达截止时间后未交卷的答卷按已保存答案自动结算（结算仅一次，重复/并发交卷回读首次报告），交卷后一次性显示成绩和详细解析
- **错题本**：自动收集错题，按知识点分类归档，支持错题重练和标记已掌握
- **学习数据分析**：练习总量统计、正确率趋势图、知识点掌握度雷达图，自动识别薄弱知识点并推荐针对性练习

## 本地开发方式

### 后端开发

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload --port 3006
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

## 访问地址

| 服务 | 本地开发 | Docker 部署 |
|------|----------|-------------|
| 前端 | http://localhost:8006 | http://localhost:8006 |
| 后端 API | http://localhost:3006 | http://localhost:3006 |
| API 文档 | http://localhost:3006/docs | http://localhost:3006/docs |
| MongoDB | - | localhost:2802 |
| Redis | - | localhost:6406 |

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端框架 | Vue 3 + TypeScript |
| 移动端 UI 库 | Vant 4 |
| 状态管理 | Pinia + 持久化 |
| 路由管理 | Vue Router 4 |
| 构建工具 | Vite 5 |
| 图表库 | ECharts 5 |
| HTTP 客户端 | Axios |
| 后端框架 | FastAPI |
| Python 版本 | Python 3.11 |
| 数据库 | MongoDB |
| 数据库驱动 | Motor（异步） |
| 缓存 | Redis |
| 认证 | JWT |
| 密码加密 | Passlib (bcrypt) |
| 容器化 | Docker + Docker Compose |

## 项目目录结构

```
在线题库与刷题平台/
├── backend/                    # 后端 FastAPI 项目
│   ├── app/
│   │   ├── core/              # 核心配置
│   │   │   ├── config.py      # 配置管理
│   │   │   ├── database.py    # MongoDB 初始化
│   │   │   ├── redis.py       # Redis 初始化
│   │   │   └── security.py    # 密码加密/JWT
│   │   ├── data/              # 数据初始化
│   │   │   └── init_data.py   # 示例数据
│   │   ├── modules/           # 业务模块
│   │   │   ├── auth/          # 用户认证
│   │   │   ├── knowledge/     # 知识点体系
│   │   │   ├── questions/     # 题库管理
│   │   │   ├── practice/      # 练习模式
│   │   │   ├── exam/          # 模拟考试
│   │   │   ├── errors/        # 错题本
│   │   │   └── analysis/      # 学习分析
│   │   └── main.py            # 应用入口
│   ├── requirements.txt       # Python 依赖
│   └── Dockerfile             # 后端 Docker 镜像
├── frontend/                   # 前端 Vue 项目
│   ├── src/
│   │   ├── api/               # API 请求
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── styles/            # 全局样式
│   │   ├── types/             # TypeScript 类型定义
│   │   ├── views/             # 页面组件
│   │   │   ├── Login.vue      # 登录/注册
│   │   │   ├── Home.vue       # 首页
│   │   │   ├── Subjects.vue   # 学科列表
│   │   │   ├── KnowledgeTree.vue # 知识点树
│   │   │   ├── Practice.vue   # 练习页面
│   │   │   ├── Exam.vue       # 模拟考试
│   │   │   ├── ExamResult.vue # 考试结果
│   │   │   ├── ErrorBook.vue  # 错题本
│   │   │   ├── Analysis.vue   # 学习分析
│   │   │   └── Profile.vue    # 个人中心
│   │   ├── App.vue            # 根组件
│   │   └── main.ts            # 应用入口
│   ├── package.json           # 前端依赖
│   ├── vite.config.ts         # Vite 配置
│   ├── tsconfig.json          # TypeScript 配置
│   ├── nginx.conf             # Nginx 配置
│   └── Dockerfile             # 前端 Docker 镜像
├── docker-compose.yml         # Docker Compose 编排
├── .env.example               # 环境变量示例
└── README.md                  # 项目说明
```

## 环境变量说明

复制 `.env.example` 为 `.env` 并根据需要修改：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MONGO_ROOT_USERNAME | admin | MongoDB 管理员用户名 |
| MONGO_ROOT_PASSWORD | admin123 | MongoDB 管理员密码 |
| MONGO_DB | exam_platform | 数据库名称 |
| REDIS_PASSWORD | redis123 | Redis 连接密码 |
| SECRET_KEY | your-secret-key... | JWT 签名密钥，生产环境必须修改 |
| ACCESS_TOKEN_EXPIRE_MINUTES | 1440 | Token 过期时间（分钟） |
| CORS_ORIGINS | * | 允许的跨域来源 |

## Docker 部署说明

### 端口映射

| 内部端口 | 外部端口 | 服务 |
|----------|----------|------|
| 27017 | 2802 | MongoDB |
| 6379 | 6406 | Redis |
| 8000 | 3006 | Backend API |
| 80 | 8006 | Frontend (Nginx) |

### 数据卷

- `mongo-data`：MongoDB 数据持久化
- `redis-data`：Redis 数据持久化

### 常用 Docker 命令

```bash
# 启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# 停止服务
docker compose stop

# 重启服务
docker compose restart

# 停止并删除容器（保留数据）
docker compose down

# 停止并删除容器和数据卷（慎用！）
docker compose down -v

# 重新构建镜像
docker compose build
docker compose up -d --build
```

### 常见问题

**1. 端口冲突**

如果端口已被占用，修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8006:80"  # 将 8006 修改为其他端口
```

**2. 数据库连接失败**

检查 MongoDB 是否健康：
```bash
docker compose logs mongodb
```

**3. 前端无法调用后端 API**

检查 Nginx 配置和后端服务是否正常启动：
```bash
docker compose logs frontend
docker compose logs backend
```

**4. 重新初始化数据**

如果需要清空所有数据重新初始化：
```bash
docker compose down -v
docker compose up -d
```

## License

MIT
