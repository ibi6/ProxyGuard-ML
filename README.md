<div align="center">

<img src="assets/logo.svg" width="72" alt="ProxyGuard ML" />

# ProxyGuard ML

### 加密代理流量识别 · 不解密任何一个字节

侧信道集成学习 · FastAPI 控制台 · 可复现实验演示

[架构说明](docs/ARCHITECTURE.md) · [系统设计](docs/system-design.md) · [实验指南](docs/experiment-guide.md)

<br/>

![Stars](https://img.shields.io/github/stars/ibi6/ProxyGuard-ML?style=for-the-badge&label=STARS&logo=github&color=0969da)
![Forks](https://img.shields.io/github/forks/ibi6/ProxyGuard-ML?style=for-the-badge&label=FORKS&logo=github&color=1f883d)
![Last Commit](https://img.shields.io/github/last-commit/ibi6/ProxyGuard-ML?style=for-the-badge&label=LAST%20COMMIT&color=238636)
![CI](https://img.shields.io/github/actions/workflow/status/ibi6/ProxyGuard-ML/ci.yml?branch=main&style=for-the-badge&label=CI)
![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-2ea44f?style=for-the-badge)
![Version](https://img.shields.io/badge/version-0.3.0-111827?style=for-the-badge)

</div>

<p align="center">
  <img src="assets/banner.svg" alt="banner" width="100%" />
</p>

---

## 项目简介

TLS 与现代代理会隐藏载荷内容。**ProxyGuard ML 不做任何载荷解密**，仅使用 **17 维流级统计特征**，完成四分类：

`normal_https` · `shadowsocks` · `trojan` · `vmess`

| 层次 | 选型 |
|------|------|
| 接口 / 页面 | FastAPI + Jinja2 控制台 |
| 机器学习 | scikit-learn · XGBoost · LightGBM |
| 存储 | CSV / joblib / SQLite 任务日志 |
| 工程 | Docker Compose · GitHub Actions · 可选 API Token |

> **数据说明（必读）**  
> 默认样本为**可复现合成特征**（按类别均值加噪声），**不包含**网卡抓包 / PCAP 解析。  
> 发表或答辩时请明确标注数据性质；指标反映实验设定下的可分性，不能直接当作公网检出率。

---

## 功能亮点

- **8 模型对比**：决策树、SVM、随机森林、AdaBoost、XGBoost、LightGBM、软投票、堆叠  
- **完整控制台**：生成/上传数据 → 训练（可取消）→ 识别 → 导出实验  
- **可复现实验**：种子、噪声、划分比例写入 SQLite，训练时生效  
- **工程护栏**：上传限制、Inf 校验、训练互斥、安全响应头  
- **CI**：ruff 检查 + pytest（3.11/3.12）+ main 分支 Docker 构建  

<p align="center">
  <img src="assets/architecture.svg" width="100%" alt="架构图" />
</p>

```text
浏览器  →  FastAPI（页面 + /api/*）
        →  服务层（数据 / 训练 / 预测 / 实验 / 设置）
        →  ML 核心（生成 · 模型 · 训练 · 评估 · 预测）
        →  data/ · models/ · reports/ · SQLite
```

更多说明：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/schema.sql](docs/schema.sql)

---

## 快速开始

### 环境要求

- Python **3.10+**
- 约 2 GB 磁盘（依赖 + 模型）

### 安装与启动

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML

python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -U pip
pip install -r requirements.txt

# 可选：本地环境变量
cp .env.example .env

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

| 地址 | 说明 |
|------|------|
| http://127.0.0.1:8000 | Web 控制台 |
| http://127.0.0.1:8000/docs | OpenAPI 文档 |
| http://127.0.0.1:8000/api/health | 健康检查 |

### Make 命令

```bash
make install      # 运行依赖
make dev          # 含 ruff
make test         # pytest
make lint         # ruff + compileall
make run          # 启动服务
make experiment   # 离线 n=800 实验
make docker-up    # Compose 启动
```

### 离线实验

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
pytest -q
```

---

## 界面说明

<p align="center">
  <img src="assets/console-mock.svg" width="100%" alt="控制台示意" />
</p>

| 路径 | 页面 |
|------|------|
| `/` | 首页总览 |
| `/data` | 合成数据生成 / CSV 上传 |
| `/train` | 多模型训练（可取消） |
| `/predict` | 在线识别 |
| `/experiments` | 指标对比与导出 |
| `/settings` | 种子与划分比例 |

---

## 接口一览

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/health` | 存活检查 |
| GET | `/api/system` | 运行快照 |
| POST | `/api/data/generate` | 生成合成数据 |
| POST | `/api/data/upload` | 上传 CSV（≤20MB） |
| POST | `/api/train` | 启动训练 |
| POST | `/api/train/{id}/cancel` | 取消训练 |
| GET | `/api/train` · `/train/{id}` | 任务列表 / 详情 |
| GET | `/api/models` | 模型与指标 |
| POST | `/api/predict` | 预测 |
| GET | `/api/predict/stats` | 预测日志计数 |
| GET | `/api/experiments` | 实验对比 |
| GET | `/api/report/export` | 导出报告 |
| GET/PUT | `/api/settings` | 持久化配置 |

**可选鉴权：** 设置环境变量 `PROXYGUARD_TOKEN` 后，写接口需请求头 `X-API-Token`。  
浏览器可执行：`localStorage.setItem('pg_api_token', '你的令牌')`。

服务启动后可访问 `/docs` 查看交互式文档。

---

## 实验结果（合成数据）

<p align="center">
  <img src="assets/leaderboard.svg" width="100%" alt="排行榜" />
</p>

设定：每类 800 样本，`seed=42`，`noise=0.85`，划分 `0.70 / 0.15 / 0.15`。

| 名次 | 模型 | Accuracy | Macro-F1 |
|:----:|------|---------:|---------:|
| 1 | **Soft Voting** | **0.752** | **0.752** |
| 2 | SVM (RBF) | 0.750 | 0.748 |
| 3 | Stacking | 0.746 | 0.744 |
| 4 | Random Forest | 0.740 | 0.735 |
| 5 | XGBoost | 0.727 | 0.725 |
| 6 | LightGBM | 0.725 | 0.723 |
| 7 | AdaBoost | 0.690 | 0.694 |
| 8 | Decision Tree | 0.600 | 0.604 |

决策树 `max_depth`、随机森林 `n_estimators` 在**验证集**上做了小范围选择；**对外报告的准确率 / F1 一律以测试集为准**。

---

## Docker 部署

```bash
docker compose up --build
# 浏览器打开 http://127.0.0.1:8000
```

---

## 配置项

| 环境变量 | 默认 | 含义 |
|----------|------|------|
| `USE_MOCK` | `false` | 模拟指标路径，正式运行请保持 false |
| `PROXYGUARD_TOKEN` | 空 | 非空则保护写接口 |
| `PROXYGUARD_MAX_UPLOAD_BYTES` | 20MB | CSV 大小上限 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

可将 [`.env.example`](.env.example) 复制为 `.env` 后本地修改。

---

## 目录结构

```text
ProxyGuard-ML/
├── app/                 # FastAPI、服务、ML、页面
├── tests/               # pytest
├── scripts/             # 离线实验脚本
├── docs/                # 架构、建表、设计说明
├── assets/              # README 配图
├── data/ models/ reports/
├── Dockerfile · docker-compose.yml
├── requirements.txt · requirements-dev.txt
├── pyproject.toml · Makefile
└── .github/workflows/ci.yml
```

---

## 路线图

- [ ] PCAP → 流聚合 → 对齐 `FEATURE_COLUMNS`  
- [ ] 静态资源本地化（减少 CDN 依赖）  
- [ ] 可选多用户登录方案  
- [ ] 更完整的交叉验证与调参报告  
- [ ] 打 tag 自动发 Release  

---

## 贡献与安全

- [贡献指南](CONTRIBUTING.md)  
- [安全策略](SECURITY.md)  
- [行为准则](CODE_OF_CONDUCT.md)  
- [更新日志](CHANGELOG.md)  
- [开源评分卡](docs/OPENSOURCE_SCORECARD.md)  

---

## 许可证

[MIT](LICENSE) © ProxyGuard ML 贡献者  

请勿用于未授权网络监控。发表结果时请注明数据为合成或真实。

<p align="center">
  <img src="assets/social.svg" width="100%" alt="社交卡片" />
  <br/>
  <a href="https://github.com/ibi6/ProxyGuard-ML"><b>github.com/ibi6/ProxyGuard-ML</b></a>
</p>
