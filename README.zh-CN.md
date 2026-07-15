<p align="center">
  <img src="assets/logo.svg" width="96" alt="ProxyGuard ML logo" />
</p>

<h1 align="center">ProxyGuard ML</h1>

<p align="center">
  <b>加密代理流量识别 — 不解密任何一个字节。</b><br/>
  侧信道集成学习 · FastAPI 运维控制台 · 可复现研究演示
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <b>简体中文</b>
</p>

<p align="center">
  <a href="https://github.com/ibi6/ProxyGuard-ML/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/ibi6/ProxyGuard-ML/actions/workflows/ci.yml/badge.svg" /></a>
  <a href="https://www.python.org/downloads/"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white" /></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" /></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e" /></a>
  <a href="https://github.com/ibi6/ProxyGuard-ML/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=social" /></a>
  <img alt="Models" src="https://img.shields.io/badge/模型-8_集成动物园-14b8a6" />
  <img alt="Decrypt" src="https://img.shields.io/badge/载荷解密-永不-0ea5e9" />
  <img alt="Version" src="https://img.shields.io/badge/version-0.2.0-111827" />
</p>

<p align="center">
  <a href="#-为什么需要它">为什么</a> ·
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-系统架构">架构</a> ·
  <a href="#-基准结果快照">基准</a> ·
  <a href="#-api-一览">API</a> ·
  <a href="#-docker">Docker</a> ·
  <a href="docs/README.zh-CN.md">文档</a>
</p>

<p align="center">
  <img src="assets/banner.svg" alt="ProxyGuard ML banner" width="100%" />
</p>

---

## 为什么需要它

TLS 与现代代理隧道在没有密钥时，使**载荷检测几乎失效**——且在未授权场景下往往不合法。  
ProxyGuard ML 走另一条路：把每条双向流当作**统计指纹**。

```text
加密字节流  ──►  17 维流级特征  ──►  集成分类器  ──►  类别 + 置信度
                    （不做 DPI 解密）
```

| 维度 | 规格 |
|------|------|
| **任务** | 四分类监督学习 |
| **标签** | `normal_https` · `shadowsocks` · `trojan` · `vmess` |
| **特征** | 固定 **17 维**流统计（包长 / 到达间隔 / 方向 / 规模 / 熵） |
| **模型** | DT · SVM · RF · AdaBoost · XGBoost · LightGBM · **Soft Voting** · **Stacking** |
| **运行时** | FastAPI 单体 + Jinja2 控制台 + SQLite 任务库 |
| **数据** | 可复现合成生成器 **或** 对齐 schema 的 CSV 上传 |

> **研究诚实声明。** 默认数据为带**故意类重叠**的合成特征。  
> 本仓库**不包含**网卡抓包或 PCAP 解析。指标只反映可控实验设定下的可分性，**不能**等同于公网真实 DPI 准确率。

---

## 控制台预览

<p align="center">
  <img src="assets/console-mock.svg" alt="ProxyGuard 控制台示意" width="100%" />
</p>

| 路由 | 工作台 |
|------|--------|
| `/` | 运营总览 Dashboard |
| `/data` | 生成 / 上传 / 预览数据集 |
| `/train` | 多模型训练任务 |
| `/predict` | 在线 17 维推理 |
| `/experiments` | 指标、图表、zip 导出 |
| `/settings` | 随机种子、划分比例等 |

---

## 能力矩阵

<table>
<tr>
<td width="50%">

### 产品能力
- 端到端 Web 控制台（不是 notebook 堆砌）
- 后台训练 + 任务进度
- Soft Voting / Stacking 对比强基线
- 论文级图表（准确率、F1、混淆矩阵、特征重要性）
- 离线脚本，适配 CI / 批量实验

</td>
<td width="50%">

### 工程质量
- 分层架构（API → 服务 → ML）
- 固定特征 schema + 标签规范化
- 默认可复现种子（`42`）
- pytest 套件 + GitHub Actions 矩阵
- Docker / Compose 一键演示

</td>
</tr>
</table>

---

## 系统架构

<p align="center">
  <img src="assets/architecture.svg" alt="架构图" width="100%" />
</p>

<p align="center">
  <img src="assets/pipeline.svg" alt="识别流水线" width="100%" />
</p>

```text
浏览器（Jinja2 + Chart.js）
        │
        ▼
FastAPI  ── /api/data | train | predict | experiments | settings
        │
        ▼
服务层  ── Dataset · Train · Predict · Experiment · Settings
        │
        ▼
ML 核心  ── generator · features · models · train · evaluate · predict
        │
        ▼
存储层  ── data/ · models/*.joblib · reports/ · SQLite
```

---

## 快速开始

### 环境要求

- Python **3.10+**（推荐 3.11 / 3.12）
- 约 2 GB 可用磁盘
- Windows · macOS · Linux

### 安装与启动

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML

python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Unix:    source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

打开 **http://127.0.0.1:8000**  
健康检查 **http://127.0.0.1:8000/api/health**  
OpenAPI **http://127.0.0.1:8000/docs**

<details>
<summary><b>Make 常用命令</b></summary>

```bash
make install      # 安装依赖
make test         # 跑 pytest
make run          # 启动 :8000
make experiment   # 离线 n=1000 全模型
make smoke        # 小样本冒烟
make docker-up    # Compose 启动
```

</details>

### 五分钟演示闭环

1. **数据** → 每类生成约 1000 条样本  
2. **训练** → 勾选 `random_forest`、`xgboost`、`voting`（或全部 8 个）  
3. **识别** → 使用默认 17 维样例向量推理  
4. **实验** → 对比 F1 / 导出 zip  

### 无界面离线实验

```bash
python scripts/run_experiments.py --n-per-class 1000 --seed 42
python scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest
```

---

## 基准结果快照

<p align="center">
  <img src="assets/leaderboard.svg" alt="模型排行榜" width="100%" />
</p>

可控合成设定（`n_per_class=800`，`seed=42`，`noise=0.85`）：

| 名次 | 模型 | Accuracy | Macro F1 |
|:----:|------|---------:|---------:|
| 1 | **Soft Voting** | **0.752** | **0.752** |
| 2 | SVM (RBF) | 0.750 | 0.748 |
| 3 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

**噪声消融**（每类 500）：最优 F1 约 **0.86**（`noise=0.55`）→ 约 **0.74**（`noise=0.85`）。  
随着类重叠增大，集成模型仍具竞争力。完整表见 `reports/ablation_results.json`。

---

## 模型动物园

| 键名 | 角色 | 说明 |
|------|------|------|
| `decision_tree` | 基线 | 可解释，方差较大 |
| `svm` | 核方法基线 | `StandardScaler` + RBF |
| `random_forest` | Bagging | 表格数据强默认 |
| `adaboost` | Boosting | 经典自适应提升 |
| `xgboost` | GBDT | 字符串标签兼容包装 |
| `lightgbm` | GBDT | 直方图加速提升 |
| `voting` | 软投票集成 | 强基学习器概率平均 |
| `stacking` | 堆叠集成 | 基概率 + 逻辑回归元学习器 |

默认划分 **70 / 15 / 15** · 指标采用 **macro** 平均。

### 17 维特征 schema

| 分组 | 列名 |
|------|------|
| 包长 | `pkt_len_mean` `pkt_len_std` `pkt_len_min` `pkt_len_max` `pkt_len_p25` `pkt_len_p75` |
| 到达间隔 | `iat_mean` `iat_std` `iat_burstiness` |
| 方向 | `uplink_pkt_ratio` `byte_up_down_ratio` |
| 流规模 | `duration` `total_packets` `total_bytes` `packets_per_second` |
| 复杂度 | `pkt_size_entropy` `iat_entropy` |

---

## API 一览

| 方法 | 路径 | 作用 |
|------|------|------|
| `GET` | `/api/health` | 存活检查 |
| `POST` | `/api/data/generate` | 生成合成数据 |
| `POST` | `/api/data/upload` | 上传 CSV |
| `GET` | `/api/data/summary` · `/preview` | 数据摘要 / 预览 |
| `POST` | `/api/train` | 启动训练 |
| `GET` | `/api/train` · `/train/{id}` | 任务列表 / 详情 |
| `GET` | `/api/models` | 模型注册表 |
| `POST` | `/api/predict` | 推理 |
| `GET` | `/api/experiments` | 实验指标 |
| `GET` | `/api/report/export` | 导出 zip |
| `GET`/`PUT` | `/api/settings` | 运行时配置 |

交互文档：`/docs` · ReDoc：`/redoc`

---

## Docker

```bash
docker compose up --build
# → http://127.0.0.1:8000
```

```bash
docker build -t proxyguard-ml .
docker run --rm -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/models:/app/models" \
  -v "$(pwd)/reports:/app/reports" \
  proxyguard-ml
```

`data/`、`models/`、`reports/` 通过卷挂载，重启后实验产物仍在。

---

## 仓库结构

```text
ProxyGuard-ML/
├── app/                 # FastAPI · 服务 · ML 核心 · 模板 · 静态资源
├── tests/               # API + ML 单测
├── scripts/             # 离线实验与消融
├── docs/                # 设计说明与实验指南
├── assets/              # Logo、架构图、社交卡片
├── data/ models/ reports/
├── Dockerfile · docker-compose.yml
├── pyproject.toml · Makefile · CITATION.cff
└── .github/workflows/ci.yml
```

---

## 测试与质量门禁

```bash
pytest -q
# 或
make test
```

每次 push / PR 到 `main` 触发 CI：

| 任务 | 内容 |
|------|------|
| **test** | Python **3.11** + **3.12** 矩阵，完整 pytest |
| **lint-light** | 对 `app` / `scripts` / `tests` 做 `compileall` |
| **docker** | main 分支推送时构建镜像 |

---

## 已知限制

| 约束 | 含义 |
|------|------|
| 默认同数据 | **不是**真实 Shadowsocks / Trojan / VMess 抓包 |
| 无 PCAP 管线 | 需自备特征或扩展提取器 |
| 无登录鉴权 | 演示请绑定 `127.0.0.1` |
| 线程内训练 | 全模型重训可能拖慢 Web 进程 |

---

## 路线图

- [ ] PCAP → 流聚合 → 对齐 `FEATURE_COLUMNS` 的特征管线  
- [ ] 更多协议（OpenVPN、WireGuard 等）  
- [ ] 嵌套交叉验证 + 结构化超参搜索  
- [ ] 类别不平衡与 合成→真实 域偏移研究  
- [ ] 可选流式 / 镜像旁路检测  
- [ ] 加固的多用户部署模式  

---

## 文档与社区

| 资源 | 链接 |
|------|------|
| 中文文档中枢 | [docs/README.zh-CN.md](docs/README.zh-CN.md) |
| 系统设计 | [docs/system-design.md](docs/system-design.md) |
| 实验指南 | [docs/experiment-guide.md](docs/experiment-guide.md) |
| 贡献指南 | [CONTRIBUTING.md](CONTRIBUTING.md) |
| 安全策略 | [SECURITY.md](SECURITY.md) |
| 行为准则 | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| 变更日志 | [CHANGELOG.md](CHANGELOG.md) |
| 引用本软件 | [CITATION.cff](CITATION.cff) |
| English README | [README.md](README.md) |

---

## 许可证与伦理

**MIT** — 详见 [LICENSE](LICENSE)。

ProxyGuard ML 用于**教学、研究与防御性分析演示**。  
**请勿**用于未授权监控。发表指标时，请**明确标注数据来源**（合成 / 真实）。

---

<p align="center">
  <img src="assets/social.svg" width="100%" alt="ProxyGuard 社交卡片" />
</p>

<p align="center">
  <sub>FastAPI · scikit-learn · XGBoost · LightGBM · 集成学习</sub><br/>
  <a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>
</p>
