# 更新日志

本文件记录项目重要变更。  
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

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

[0.3.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.0...v0.2.4
[0.2.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ibi6/ProxyGuard-ML/releases/tag/v0.1.0
