# v0.4.0 全面优化报告

## 目标与用户

ProxyGuard ML 的主要用户是毕业设计作者、答辩评审和复现实验的开发者。核心痛点不是缺少更多模型，而是演示时必须稳定完成“数据 → 训练 → 识别 → 对比 → 导出”，同时清楚表达合成数据边界。

本轮保留 FastAPI + Jinja2 + 原生 JavaScript 架构，集中处理可见的 UI 回归、请求边界、容器持久化、安全响应和交付文档。

## 已完成优化

### UI/UX

- 建立深海军蓝、青绿和琥珀组成的安全研究控制台设计系统。
- 统一卡片、按钮、输入、表格、Badge、Toast、空状态、加载状态和焦点样式。
- 移除未使用的 Tailwind CDN，避免运行时生成 CSS 和生产告警。
- 六个页面在 375、768、1440px 完成响应式实测。
- 修复首页、数据页、训练页在手机上的横向滚动和标题挤压。
- 修复数据页图表卡片被预览表格强制等高产生的大面积空白。
- 动态健康状态覆盖全部页面，不再写死“服务在线”。
- 当前导航使用 `aria-current`；抽屉菜单维护 `aria-expanded`、`aria-hidden`、`inert`，支持 Escape 关闭和焦点回归。
- 文件上传区使用真实 label；Toast 区分 status/alert；动画遵守 `prefers-reduced-motion`。
- 增加跟随系统、浅色、深色三态主题；本地保存偏好，并在 CSS 加载前解析以消除首屏闪烁。
- 主题菜单使用 `menuitemradio` 语义，支持方向键、Escape、外部点击和焦点回归；375px 下保持 44px 触控目标。
- 卡片、表格、表单、Badge、Toast、空状态、骨架屏和 Chart.js 图表统一响应主题变化。
- 首页紧凑训练表的时间列保持单行，由表格容器承接横向滚动，避免日期逐字换行。

### API 与安全

- 请求体拒绝未知字段。
- 训练模型名限制为内置枚举并去重。
- 预测要求完整 17 维有限数，单次最多 500 条。
- 设置字段限制 seed、样本数、噪声和比例范围。
- CSV 以 1MiB 分块读取，超过配置上限立即停止。
- Token 使用 `secrets.compare_digest` 常量时间比较。
- 422 响应不回显用户输入，500 响应不暴露异常类型。
- CSP 不再信任 Tailwind 或内联脚本，增加 object、frame 和跨源隔离策略。
- 页面/API 禁止缓存；版本化本地 CSS/JS 使用 immutable 长缓存。

### 数据与部署

- SQLite 默认路径改为 `data/proxyguard.db`，纳入 Compose 的持久化挂载。
- 首次启动自动把旧 `app/proxyguard.db` 备份迁移到新路径。
- 服务启动时把遗留的运行中训练任务标记为“重启中断”。
- Compose 固定项目名，解决纯中文工作区下项目名为空的问题。
- Compose 默认绑定 `127.0.0.1`，增加 init、健康检查和环境变量透传。
- 生产依赖移除 pytest/httpx；CI 改装开发依赖并覆盖 Python 3.10–3.12。
- Makefile 不再用 compileall 成功掩盖 ruff 失败。

## 数据库

SQLite 表结构保持兼容：

- `train_tasks`：训练状态、配置、指标和错误。
- `predict_logs`：预测摘要、标签、置信度和详情。
- `settings`：JSON 编码的配置键值。

完整建表脚本见 `docs/schema.sql`。所有 SQL 继续使用参数绑定；动态更新列来自固定 allowlist。

## API 约束摘要

| 接口 | 主要输入 | 成功 | 常见错误 |
|------|----------|------|----------|
| `POST /api/data/generate` | 1–50000/类、seed、0–5 noise | 200 | 422 契约错误 |
| `POST /api/data/upload` | `.csv`、≤配置上限 | 200 | 400 格式、413 超限 |
| `POST /api/train` | 1–8 个已知模型 | 200 | 400 数据/互斥、422 契约 |
| `POST /api/predict` | 1–500 个完整 17 维样本 | 200 | 400 模型文件、422 契约 |
| `PUT /api/settings` | 显式可选设置字段 | 200 | 400 比例、422 范围 |

写接口在配置 `PROXYGUARD_TOKEN` 后要求 `X-API-Token`。系统不使用 Cookie 会话，因此本轮不引入 Cookie 型 CSRF Token。

## 性能策略

- 删除 Tailwind CDN 请求和运行时编译。
- 静态 CSS/JS 带版本号并使用一年缓存。
- 图表库延迟加载；失败时展示可理解的降级空状态。
- 无依赖主题引导脚本在样式表前执行，主题切换只更新语义令牌与现有图表，不重复请求业务 API。
- 页面隐藏时暂停训练轮询。
- 批量预测、上传大小和预览条数均有上限。
- 宽表只在自身容器滚动，不扩大页面布局。

## 测试与实测

- API 契约：未知字段、模型枚举/去重、批量上限、非有限数、设置范围、流式上传。
- 运行时：数据库路径、环境变量、Token、任务恢复、错误响应、CSP、缓存和依赖分层。
- UI 契约：六页健康钩子、当前导航、移动菜单、上传 label、批量提示和默认参数。
- UI 契约：主题引导顺序、三态菜单、持久化/系统变化、图表刷新、全局 Escape 和时间列防折行。
- 浏览器：375×812、768×1024、1440×1000 六页布局；三态主题、刷新持久化、菜单定位/键盘关闭、图表即时换色和零页面级横向溢出。

执行：

```powershell
pip install -r requirements-dev.txt
python -m ruff check app tests scripts
python -m compileall -q app scripts tests
python -m pytest -q
docker compose config --quiet
```

## 已知边界

- 默认数据仍是可复现合成特征，不代表真实公网检出率。
- Chart.js 仍从固定版本的 jsDelivr 加载；离线环境会显示降级说明而非图表。
- 训练任务仍运行在单个 Uvicorn 进程的后台线程；不支持多 worker 分布式互斥。
- joblib 只能加载本系统生成且位于 `models/` 的文件；不要放入不可信模型文件。
- 本项目是本地优先实验控制台，不包含多用户登录、角色权限或审计平台。
