# 更新日志

本文件记录项目重要变更。  
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

## [0.4.0] — 2026-07-16

### 新增
- 严格 Pydantic 请求契约：模型枚举、设置范围、17 维预测样本与 500 条批量上限
- SQLite 旧路径自动迁移与服务重启后训练任务恢复
- Docker Compose 固定项目名、健康检查、本地回环绑定和完整环境变量透传
- API、运行时、页面语义回归测试
- 跟随系统 / 浅色 / 深色三态主题，支持无闪烁首屏、持久化和系统外观实时同步

### 变更
- 全站重建设计系统：深海军蓝侧栏、青绿信号色、统一交互状态和三档响应式布局
- 手机端六个页面消除页面级横向滚动，顶部操作区与表格改为容器内自适应
- SQLite 默认迁移到 `data/proxyguard.db`，由 Compose 的 data 挂载持久化
- 默认实验样本数统一为每类 800；生产依赖移除 pytest/httpx
- 移除未使用的 Tailwind CDN，静态资源使用版本化长缓存
- Chart.js 图表随主题即时更新；主题菜单支持单选语义、方向键、Escape 和焦点回归
- 首页训练时间在紧凑表格中保持单行，避免窄列逐字换行

### 安全
- Token 改用常量时间比较；422 与 500 响应不回显输入或内部异常类型
- CSP 移除 Tailwind 与内联脚本信任，增加 object/跨源隔离响应头
- CSV 按块读取并在超限时提前停止；预测拒绝 NaN/Inf

## [0.3.0] — 2026-07-15

### 新增
- 安全响应头中间件（CSP / XFO / nosniff）
- 统一日志配置（`app/logging_config.py`）
- `.env.example`、`requirements-dev.txt`、`docs/ARCHITECTURE.md`
- CI：先 ruff 再多版本 pytest，main 上 Docker 构建
- 训练取消接口；决策树 / 随机森林验证集轻量选参
- 数据页「论文参数」；实验页不用假图凑数

### 变更
- 版本号 0.3.0
- 设置仅保留实际生效字段
- 指标与导出使用相对路径
- Makefile 增加 lint/dev
- **公开文档统一为简体中文**（移除英文 README）

### 安全
- 可选 `PROXYGUARD_TOKEN` 保护写接口
- 上传大小/类型限制；拒绝 NaN/Inf 特征

## [0.2.4] — 2026-07-15

### 新增
- 演示向体验：取消训练、进度文案、RF 验证集选树数量
- `/api/predict/stats`、`/api/system`

## [0.2.0] — 2026-07-15

### 新增
- GitHub 包装：徽章、架构图、LICENSE、贡献与安全文档
- Docker / Compose、Issue 与 PR 模板
- pyproject.toml、editorconfig、CITATION.cff

## [0.1.0] — 2026-07-11

### 新增
- FastAPI 控制台：数据 / 训练 / 识别 / 实验 / 设置
- 合成 17 维特征、8 模型、pytest、离线实验脚本

[0.4.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.0...v0.2.4
[0.2.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ibi6/ProxyGuard-ML/releases/tag/v0.1.0
