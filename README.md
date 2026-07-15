# ProxyGuard ML

本科毕业设计项目：**基于集成学习的加密代理流量识别**。

不解密 TLS 载荷，只用流级统计特征（17 维），对下面 4 类做分类：

- `normal_https`
- `shadowsocks`
- `trojan`
- `vmess`

技术：Python + FastAPI + scikit-learn / XGBoost / LightGBM + SQLite + 简单网页控制台。

[English](README.en.md)

---

## 说明（很重要）

默认数据是**自己生成的合成特征**（按类别设均值再加噪声），方便复现实验。  
**不是**网卡抓包，也**没有**解析 PCAP。论文和答辩里要按合成数据来讲。

正式实验参数（和仓库里报告一致）：

| 参数 | 值 |
|------|-----|
| 每类样本 | 800 |
| 总数 | 3200 |
| seed | 42 |
| noise | 0.85 |
| 划分 | 0.7 / 0.15 / 0.15 |
| 较好结果 | Soft Voting，macro-F1 约 0.75 |

---

## 环境

- Python 3.10 及以上
- Windows / macOS / Linux 都行

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML

python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

---

## 启动

在项目根目录：

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

浏览器打开：http://127.0.0.1:8000  

接口文档：http://127.0.0.1:8000/docs  

健康检查：http://127.0.0.1:8000/api/health

### 页面

| 地址 | 干什么 |
|------|--------|
| `/` | 总览 |
| `/data` | 生成/上传数据 |
| `/train` | 训练模型 |
| `/predict` | 输入特征做识别 |
| `/experiments` | 看指标和导出 |
| `/settings` | 种子、划分比例等 |

### 建议演示顺序

1. 数据页：每类生成 800，seed=42，noise=0.85  
2. 训练页：至少勾选 random_forest、xgboost、voting  
3. 等任务成功  
4. 实验页看对比  
5. 识别页用默认特征试一条  

也可以不启动网页，直接跑脚本：

```bash
python scripts/run_experiments.py --n-per-class 800 --seed 42 --noise 0.85
```

---

## 模型

| 名称 | 备注 |
|------|------|
| decision_tree | 基线；验证集上会试几个 max_depth |
| svm | RBF，前面有标准化 |
| random_forest | Bagging |
| adaboost | Boosting |
| xgboost / lightgbm | 梯度提升 |
| voting | 软投票 |
| stacking | 堆叠，元模型用逻辑回归 |

特征列名在 `app/config.py` 的 `FEATURE_COLUMNS` 里，上传 CSV 必须带 `label` 和这 17 列。

---

## 目录

```text
app/          # 后端 + 页面
  api/        # 接口
  services/   # 业务
  ml/         # 生成数据、训练、预测
  templates/  # 页面
  static/     # css/js
tests/        # pytest
scripts/      # 离线实验
data/         # 生成的数据（本地）
models/       # joblib（本地）
reports/      # 指标和图
docs/         # 说明和 schema
```

---

## 测试

```bash
pytest -q
```

---

## Docker（可选）

```bash
docker compose up --build
```

---

## 配置

| 环境变量 | 作用 |
|----------|------|
| `USE_MOCK=true` | 走假数据/假指标，**答辩不要开** |
| `PROXYGUARD_TOKEN=xxx` | 写接口要带头 `X-API-Token`；网页可在控制台 `localStorage.setItem('pg_api_token','xxx')` |

设置页改的种子和 train/val/test 比例会存 SQLite，**下次训练会用到**。

---

## 已知限制

1. 合成数据，不能当真实代理检测率  
2. 没有登录系统（本地用）；需要可设 Token  
3. 训练在进程里开线程，一次只跑一个任务  
4. 没有 PCAP 解析，真流量要自己提成 17 维 CSV 再上传  

---

## 许可证

MIT，见 [LICENSE](LICENSE)。

别拿去未授权监听别人网络。写论文请写清楚数据是合成还是真实。
