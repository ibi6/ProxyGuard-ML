# 系统架构

## 概述

ProxyGuard ML 是一个**单体 FastAPI 应用**，包含：

1. **机器学习流程**（合成/CSV 特征 → 训练 → 评估 → joblib）
2. **Web 控制台**（Jinja2 + 静态 JS）便于演示
3. **SQLite** 保存训练任务、预测日志与设置

定位为单机、本地优先。默认数据为**合成特征**。

## 分层

```text
┌─────────────────────────────────────────────┐
│ 表现层   templates/ + static/css|js         │
├─────────────────────────────────────────────┤
│ 接口层   app/api/*   （薄适配）             │
├─────────────────────────────────────────────┤
│ 服务层   app/services/* （编排业务）        │
├─────────────────────────────────────────────┤
│ ML 核心  app/ml/*    （特征/模型/训练预测） │
├─────────────────────────────────────────────┤
│ 持久化   CSV / joblib / JSON + SQLite       │
└─────────────────────────────────────────────┘
```

| 目录 | 职责 |
|------|------|
| `app/api` | 参数校验、状态码、USE_MOCK 分支 |
| `app/services` | 业务流程、后台线程、数据库行 |
| `app/ml` | 特征 schema、模型、训练评估预测 |
| `app/db.py` | SQLite 建表与连接 |
| `app/security.py` | 写接口可选 Token |
| `app/middleware.py` | 访问日志 + 安全响应头 |

## 训练请求流程

1. `POST /api/train` 校验模型名  
2. `TrainService.start` 保证同时只有一个任务  
3. 后台线程执行 `train_all`，回调进度  
4. 产物：`models/*.joblib`、`reports/metrics.json`、图表  
5. 前端轮询 `GET /api/train/{task_id}`  

## 数据约定

- 特征：`app/config.py` 中 `FEATURE_COLUMNS`（17 维）  
- 标签：`normal_https` | `shadowsocks` | `trojan` | `vmess`  
- 上传 CSV 必须含 `label` 与全部特征列  

## 明确不做的事

- 实时抓包 / PCAP 解析  
- 多租户权限体系  
- 分布式训练 / GPU 在线服务  

## 扩展点

| 目标 | 接入位置 |
|------|----------|
| 真实 PCAP 特征 | 导出 17 维 CSV 上传，或在 `app/ml/` 增加提取器 |
| 登录鉴权 | 扩展 `app/security.py` |
| 任务队列 | 后续可用 Celery/RQ 替换线程 |
