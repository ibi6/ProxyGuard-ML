# ProxyGuard ML

基于集成学习的**加密代理流量识别系统**（本科毕业设计可运行演示版）。

系统在**不解密载荷**的前提下，使用流级统计特征，对 4 类加密相关流量做多分类识别，并提供 Web 控制台完成「生成数据 → 训练 → 识别 → 查看实验」闭环。

| 项 | 说明 |
|----|------|
| 任务 | 四分类监督学习 |
| 类别 | `normal_https` / `shadowsocks` / `trojan` / `vmess` |
| 特征 | 17 维流级统计特征 |
| 模型 | Decision Tree、SVM、Random Forest、AdaBoost、XGBoost、LightGBM、Soft Voting、Stacking |
| 形态 | FastAPI 单体全栈 + Jinja2 控制台 |
| 数据 | 默认可复现**合成特征数据**；支持上传对齐 schema 的 CSV |

> **重要说明**：当前实现使用合成流特征或用户上传的特征 CSV，**不包含真实网卡抓包 / PCAP 解析**。论文与答辩中请如实表述数据来源。

---

## 环境要求

- Windows 10/11（PowerShell）
- Python **3.10+**（推荐 3.11/3.12）
- 约 2 GB 可用磁盘（含依赖与模型）
- 可选：浏览器 Chrome / Edge

---

## 安装与启动（Windows PowerShell）

在**项目根目录**（克隆后的 `ProxyGuard-ML` 目录）执行：

```powershell
# 1) 进入项目目录（按你的实际路径修改）
cd ProxyGuard-ML

# 2) 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3) 安装依赖
python -m pip install -U pip
pip install -r requirements.txt

# 4) 启动 Web 服务（项目根目录）
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

若 PowerShell 禁止执行脚本，可先运行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

或使用：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 访问地址

- Web 控制台：http://127.0.0.1:8000
- 健康检查：http://127.0.0.1:8000/api/health

页面路由：

| 路径 | 页面 |
|------|------|
| `/` | 总览 Dashboard |
| `/data` | 数据管理 |
| `/train` | 模型训练 |
| `/predict` | 在线识别 |
| `/experiments` | 实验结果 |
| `/settings` | 系统设置 |

---

## 演示操作（5 步）

1. **打开总览**  
   浏览器访问 http://127.0.0.1:8000 ，确认页面可打开。

2. **生成合成数据**  
   进入「数据管理」→ 设置每类样本数（建议演示 `1000`）→ 生成。  
   产物：`data/synthetic/features.csv`、`data/synthetic/meta.json`。

3. **训练模型**  
   进入「模型训练」→ 勾选模型（至少含 `random_forest`、`xgboost`、`voting` 等）→ 启动训练 → 等待任务状态变为成功。  
   产物：`models/*.joblib`、`reports/metrics.json`、`reports/figures/*`。

4. **在线识别**  
   进入「在线识别」→ 使用页面默认样例或粘贴 17 维特征 JSON → 选择已训练模型 → 查看预测标签与置信度。

5. **查看实验与导出**  
   进入「实验结果」→ 对比 Accuracy / F1、混淆矩阵、特征重要性 → 导出实验包（zip）。

### 离线一键实验（可选，不启动 Web）

```powershell
cd ProxyGuard-ML
.\.venv\Scripts\Activate.ps1
python scripts/run_experiments.py --n-per-class 1000 --seed 42
```

小样本冒烟：

```powershell
python scripts/run_experiments.py --n-per-class 200 --seed 42 --models decision_tree,random_forest
```

---

## 目录结构

```
ProxyGuard-ML/
├── README.md
├── requirements.txt
├── app/
│   ├── main.py              # FastAPI 入口与页面路由
│   ├── config.py            # 路径、标签、17 维特征、划分比例
│   ├── db.py                # SQLite 初始化
│   ├── api/                 # REST：data / train / predict / experiments / settings
│   ├── services/            # 业务服务
│   ├── ml/                  # 数据生成、特征、模型、训练、评估、预测
│   ├── templates/           # Jinja2 页面
│   └── static/              # CSS / JS
├── data/                    # 数据集与 active 指针
├── models/                  # *.joblib 训练产物
├── reports/                 # metrics.json、figures、实验导出
├── scripts/
│   ├── run_experiments.py   # 离线实验脚本
│   └── run_ablation.py      # 消融实验脚本
├── docs/
│   ├── system-design.md     # 系统设计说明
│   └── experiment-guide.md  # 实验说明
└── tests/                   # pytest
```

---

## 功能完成度

### 已完成

- Web 控制台全流程：数据 / 训练 / 识别 / 实验 / 设置
- 4 类标签 + 17 维流级特征 schema（固定列名）
- 合成数据集生成（可复现 seed / noise）
- CSV 上传（需含 `label` 与全部特征列）
- 8 个模型训练、评估、joblib 持久化
- Soft Voting / Stacking 集成对比
- 指标：Accuracy、Precision、Recall、F1（macro）
- 对比图：准确率、F1、混淆矩阵、特征重要性
- SQLite 任务与设置；实验报告导出
- 离线脚本 `scripts/run_experiments.py` / `scripts/run_ablation.py`

### 已知限制

- **合成数据**：默认数据由高斯分布按类别均值生成，**不是**真实 Shadowsocks/Trojan/VMess 抓包结果；指标仅反映该可复现设定下的可分性。
- **无在线抓包**：不读取网卡、不解析 PCAP、不解密 TLS。
- **无用户体系**：本地演示，无登录/多租户。
- **小样本易过拟合**：每类样本过少时测试集 F1 可能虚高（接近 1.0），建议每类 ≥1000 并固定 seed。
- 训练在后台线程执行，大规模全模型训练时 Web 可能短暂变慢。

---

## 后续优化方向

1. 真实 PCAP → 流聚合 → 与 `FEATURE_COLUMNS` 对齐的特征提取管线  
2. 扩展协议/代理类（如 OpenVPN、WireGuard 等）  
3. 交叉验证、网格搜索与更严谨的调参报告  
4. 类别不平衡处理与域自适应（合成 → 真实）  
5. 可选实时检测流水线（旁路镜像流量特征）  
6. 容器化部署与只读演示模式  

---

## 文档

| 文档 | 用途 |
|------|------|
| [docs/system-design.md](docs/system-design.md) | 需求、架构、模块、流程、接口 |
| [docs/experiment-guide.md](docs/experiment-guide.md) | 数据集、特征、模型、指标、实验步骤 |

---

## 运行测试

```powershell
cd ProxyGuard-ML
.\.venv\Scripts\Activate.ps1
pytest -q
```

---

## 许可证与声明

本项目用于学习与演示。请勿将识别能力用于未授权监控；使用合成数据时请明确标注数据性质。
