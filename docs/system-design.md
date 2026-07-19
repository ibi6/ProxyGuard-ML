# 系统设计说明（论文第 3 章素材）

> 对应实现仓库：ProxyGuard ML（`app/` 单体 FastAPI 全栈）  
> 本文档描述**已实现系统**的需求、架构、模块、数据流与接口，可直接改写入毕业论文第 3 章。

---

## 3.1 系统需求分析

### 3.1.1 业务目标

在无法解密 TLS/代理载荷的前提下，利用加密流的侧信道统计特征，识别流量是否属于常见加密代理协议，并输出可复现的实验指标与图表，支撑毕业设计「系统设计与实现」答辩演示。

### 3.1.2 功能需求

| 编号 | 需求 | 实现要点 |
|------|------|----------|
| FR-1 | 数据集管理 | 合成特征生成、CSV 上传、摘要与预览 |
| FR-2 | 模型训练 | 多模型批量训练、任务状态查询、模型落盘 |
| FR-3 | 在线识别 | 单条/批量特征向量输入，输出类别与概率 |
| FR-4 | 实验对比 | Accuracy/F1 等指标、混淆矩阵、特征重要性、导出 |
| FR-5 | 系统配置 | 随机种子、划分比例等可持久化设置 |
| FR-6 | Web 控制台 | Dashboard / 数据 / 训练 / 识别 / 实验 / 设置页面 |

### 3.1.3 非功能需求

| 编号 | 需求 | 说明 |
|------|------|------|
| NFR-1 | 可运行 | Windows 下 venv + `uvicorn` 本地启动 |
| NFR-2 | 可复现 | 默认 `RANDOM_SEED=42`，合成数据与划分可控 |
| NFR-3 | 不解密 | 仅流级统计特征，不做明文还原 |
| NFR-4 | 可写论文 | 指标 JSON + 标准对比图与混淆矩阵 |
| NFR-5 | 边界诚实 | 明确合成数据与非在线抓包限制 |

### 3.1.4 识别任务定义

- **任务类型**：多分类监督学习  
- **标签集合（4 类）**：

| 内部标签 | 含义 |
|----------|------|
| `normal_https` | 普通 HTTPS / 正常加密 Web 流量 |
| `shadowsocks` | Shadowsocks 代理流量（特征画像） |
| `trojan` | Trojan 代理流量（特征画像） |
| `vmess` | VMess 代理流量（特征画像） |

配置见 `app/config.py` 中 `LABELS` / `LABEL_DISPLAY`。

### 3.1.5 范围边界

**在范围内：**

- 流级 17 维统计特征 schema  
- 合成数据 + CSV 导入  
- 经典 ML 与集成学习对比  
- Web 演示与实验导出  

**不在范围内（首期）：**

- 真实网卡抓包、PCAP 解析  
- TLS 解密 / DPI 设备部署  
- 用户注册登录与多租户  
- 大规模分布式 / GPU 深度学习主方案  

---

## 3.2 总体架构设计

### 3.2.1 技术选型

| 层次 | 技术 |
|------|------|
| Web / API | FastAPI + Uvicorn |
| 模板前端 | Jinja2 + 静态 CSS/JS（控制台风格） |
| ML | scikit-learn、XGBoost、LightGBM |
| 序列化 | joblib |
| 持久化 | 本地 CSV / JSON / PNG + SQLite（`data/proxyguard.db`） |
| 评估可视化 | matplotlib / seaborn |

### 3.2.2 逻辑分层

```
┌──────────────────────────────────────────────────┐
│  Web 层：Dashboard / 数据 / 训练 / 识别 / 实验 / 设置 │
├──────────────────────────────────────────────────┤
│  API 层：/api/data | train | models | predict | … │
├──────────────────────────────────────────────────┤
│  业务服务层：Dataset / Train / Predict / Experiment / Settings │
├──────────────────────────────────────────────────┤
│  ML 核心层：generator · features · models · train · evaluate · predict │
├──────────────────────────────────────────────────┤
│  存储层：data/ · models/ · reports/ · SQLite      │
└──────────────────────────────────────────────────┘
```

### 3.2.3 物理部署形态

单体进程部署：浏览器 → `127.0.0.1:8000` → Uvicorn 加载 `app.main:app`。  
训练任务在服务进程内后台执行（线程），通过任务 ID 轮询状态。  
可选：不启动 Web，使用 `scripts/run_experiments.py` 离线跑通训练与出图。

---

## 3.3 模块设计

### 3.3.1 目录与职责

| 路径 | 职责 |
|------|------|
| `app/main.py` | 应用入口、页面路由、`/api/health`、挂载 static/templates |
| `app/config.py` | 路径、标签、17 特征列、划分比例、随机种子 |
| `app/db.py` | SQLite 表初始化 |
| `app/api/*.py` | REST 路由适配层 |
| `app/services/*_service.py` | 业务编排（生成数据、启停训练、预测、导出） |
| `app/ml/data_generator.py` | 按类别均值+噪声生成合成特征 |
| `app/ml/features.py` | 特征框校验与标签规范化 |
| `app/ml/models.py` | 模型动物园 `build_model` / Voting / Stacking |
| `app/ml/train.py` | 划分、训练、落盘、汇总指标 |
| `app/ml/evaluate.py` | 指标计算与论文图导出 |
| `app/ml/predict.py` | 加载 joblib 推理 |
| `scripts/run_experiments.py` | 离线实验 runner |

### 3.3.2 特征模块

固定 **17** 维特征（`FEATURE_COLUMNS`）：

1. 包长：`pkt_len_mean`, `pkt_len_std`, `pkt_len_min`, `pkt_len_max`, `pkt_len_p25`, `pkt_len_p75`  
2. 到达间隔：`iat_mean`, `iat_std`, `iat_burstiness`  
3. 方向：`uplink_pkt_ratio`, `byte_up_down_ratio`  
4. 流规模：`duration`, `total_packets`, `total_bytes`, `packets_per_second`  
5. 复杂度：`pkt_size_entropy`, `iat_entropy`  

校验规则（`validate_feature_frame`）：

- 必须含 `label` 与全部 17 列  
- 特征可数值化且无 NaN  
- 标签经 `normalize_label` 映射到 4 类枚举  

### 3.3.3 模型模块

| 键名 | 显示名 | 角色 |
|------|--------|------|
| `decision_tree` | Decision Tree | 基线 |
| `svm` | SVM (RBF) | 基线（Pipeline + StandardScaler） |
| `random_forest` | Random Forest | Bagging 集成 |
| `adaboost` | AdaBoost | Boosting 集成 |
| `xgboost` | XGBoost | 梯度提升 |
| `lightgbm` | LightGBM | 梯度提升 |
| `voting` | Soft Voting Ensemble | 软投票（DT/RF/SVM/XGB/LGBM） |
| `stacking` | Stacking Ensemble | 同上 base + LogisticRegression meta |

XGBoost/LightGBM 通过 `LabeledClassifier` 包装，保证落盘后预测仍为字符串标签。

### 3.3.4 训练与评估模块

- 默认划分：`TRAIN_RATIO=0.70`，`VAL_RATIO=0.15`，`TEST_RATIO=0.15`  
- 默认种子：`RANDOM_SEED=42`  
- 测试集指标：Accuracy；Precision / Recall / F1 使用 **macro** 平均  
- 产出：  
  - `models/{name}.joblib`  
  - `reports/metrics.json`  
  - `reports/figures/model_accuracy_comparison.png`  
  - `reports/figures/model_f1_comparison.png`  
  - `reports/figures/confusion_matrix_{name}.png`  
  - `reports/figures/feature_importance.png`  

### 3.3.5 业务服务与存储

| 服务 | 职责 |
|------|------|
| DatasetService | 生成/上传、写 `data/synthetic` 或 uploaded、维护 `data/active.json` |
| TrainService | 创建任务、后台训练、写 SQLite 任务状态 |
| PredictService | 加载指定或最优模型推理，记录预测日志 |
| ExperimentService | 读取 metrics、打包导出 zip |
| SettingsService | 读写可配置项 |

SQLite 精简表：`train_tasks`、`predict_logs`、`settings`（实现以 `app/db.py` 为准）。

### 3.3.6 前端页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 总览 | `/` | 样本数、模型、最近任务等概览 |
| 数据管理 | `/data` | 合成、上传、分布、预览 |
| 模型训练 | `/train` | 勾选模型、启停、任务列表 |
| 在线识别 | `/predict` | 表单/JSON 输入、结果展示 |
| 实验结果 | `/experiments` | 对比表与图表、导出 |
| 系统设置 | `/settings` | 种子、划分等 |

---

## 3.4 核心流程设计

### 3.4.1 端到端主流程

1. 用户生成合成数据或上传 CSV  
2. 系统校验特征 schema 并设为 active 数据集  
3. 用户选择模型列表启动训练任务  
4. 服务划分 train/val/test，逐模型 `fit` → `evaluate` → `joblib.dump`  
5. 汇总 metrics、选 `best_model`、导出图表  
6. 用户在识别页提交特征向量，加载模型 `predict` / `predict_proba`  
7. 实验页展示对比并可导出论文材料包  

### 3.4.2 合成数据生成流程

1. 读取 4 类标签与各类特征均值画像（`data_generator` 内 `_CLASS_MEANS`）  
2. 按 `n_per_class`、`seed`、`noise` 采样  
3. 写出 `data/synthetic/features.csv` 与 `meta.json`  
4. 更新 active 数据指针  

### 3.4.3 训练任务状态机

`running` → `success` / `failed` / `cancelled`

失败时在任务记录中保留错误信息，便于 Web 展示。

### 3.4.4 预测流程

1. 校验样本字典是否含 17 维特征  
2. 拒绝 NaN/Inf，单次最多 500 条
3. 解析 `model` 参数；缺省时使用当前最优或默认可用模型
4. 加载 `models/{name}.joblib`
5. 输出 `label`、`proba`（若支持）、所用模型名

---

## 3.5 接口设计

错误体统一：`{"detail": "..."}`，配合合适 HTTP 状态码。

### 3.5.1 健康与页面

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | `{"status":"ok","service":"ProxyGuard ML"}` |
| GET | `/` `/data` `/train` `/predict` `/experiments` `/settings` | HTML 页面 |

### 3.5.2 数据 API（前缀 `/api/data`）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/data/generate` | Body: `n_per_class`, `seed`, `noise` |
| POST | `/api/data/upload` | `multipart/form-data` 文件字段 `file` |
| GET | `/api/data/summary` | 样本数、类别分布等 |
| GET | `/api/data/preview?limit=20` | 样本预览 |

### 3.5.3 训练与模型

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/train` | Body: `{"models":["random_forest","xgboost",...]}` |
| GET | `/api/train` | 任务列表 |
| GET | `/api/train/{task_id}` | 单任务详情 |
| GET | `/api/models` | 已训练模型列表 |

### 3.5.4 预测

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/predict` | Body: `{"samples":[{...17 features...}], "model": "optional"}`；单次最多 500 条 |

### 3.5.5 实验与设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/experiments` | 指标对比结果 |
| GET | `/api/report/export?download=true` | 导出 zip 或元信息 |
| GET | `/api/settings` | 读取配置 |
| PUT | `/api/settings` | 更新配置 |

### 3.5.6 可选 Mock

环境变量 `USE_MOCK=true` 时部分 API 走 `mock_store`（开发/展示用）。**默认 `false`，使用真实 ML 流水线。**

---

## 3.6 数据设计摘要

| 数据 | 路径 | 说明 |
|------|------|------|
| 合成特征 | `data/synthetic/features.csv` | 列 = 17 特征 + `label` |
| 合成元信息 | `data/synthetic/meta.json` | seed、noise、n_per_class 等 |
| Active 指针 | `data/active.json` | 当前训练使用的数据集 |
| 模型 | `models/*.joblib` | 可加载估计器 |
| 指标 | `reports/metrics.json` | 各模型指标与 best_model |
| 图表 | `reports/figures/*.png` | 论文插图 |
| 数据库 | `data/proxyguard.db` | 任务、设置与预测日志（gitignore / Compose 持久化） |

CSV 导入约定：必须含 `label`；特征列与 `FEATURE_COLUMNS` 对齐；未知列忽略策略以实现为准（缺失必要列报 400）。

---

## 3.7 安全与运行约束

- 本地演示系统，默认仅绑定 `127.0.0.1`  
- 上传限制为 CSV 解析路径，不执行用户代码  
- 不处理真实抓包权限与内核驱动  
- 论文表述中须区分「特征空间分类能力」与「真实网络对抗环境」  

---

## 3.8 小结

本系统采用单体 FastAPI 架构，将数据管理、集成学习训练、在线识别与实验导出整合为可演示闭环；以固定 4 类标签与 17 维流特征为契约，便于后续替换为真实 PCAP 特征管线而不改整体分层。
