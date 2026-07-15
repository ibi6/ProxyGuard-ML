# 实验说明（论文第 4 章素材）

> 本文档描述 ProxyGuard ML 的实验数据、特征、模型、评价指标与可复现步骤。  
> 请在论文中明确：**默认实验使用可复现合成流特征，而非真实 PCAP 抓包。**

---

## 4.1 实验目的

1. 验证基于流级统计特征的四分类加密代理流量识别流程可完整运行。  
2. 对比基线模型与集成学习模型（Bagging / Boosting / Voting / Stacking）的分类性能。  
3. 输出可写入论文的指标表与图表（准确率、F1、混淆矩阵、特征重要性）。  
4. 评估系统在 Web 与离线脚本两种入口下的可复现性。

---

## 4.2 实验环境

| 项 | 建议配置 |
|----|----------|
| OS | Windows 10/11 |
| Python | 3.10+ |
| 依赖 | 见项目根目录 `requirements.txt` |
| 启动 | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 离线实验 | `python scripts/run_experiments.py` |
| 硬件 | 普通笔记本 CPU 即可（万级样本内） |

关键第三方库版本（以 `requirements.txt` 锁定为准）：

- `scikit-learn==1.5.2`
- `xgboost==2.1.3`
- `lightgbm==4.5.0`
- `pandas` / `numpy` / `matplotlib` / `seaborn` / `joblib`

---

## 4.3 数据集

### 4.3.1 合成数据集（默认）

- **生成模块**：`app/ml/data_generator.py`  
- **输出路径**：  
  - `data/synthetic/features.csv`  
  - `data/synthetic/meta.json`  
- **生成参数**（Web API 与脚本一致思想）：  
  - `n_per_class`：每类样本数（演示建议 1000；冒烟可用 200）  
  - `seed`：随机种子（默认 42）  
  - `noise`：噪声尺度（默认 0.85，可调）  
- **类别数**：4（见下表）  
- **总样本数**：`4 × n_per_class`  

| 标签 | 含义 |
|------|------|
| `normal_https` | 正常 HTTPS 加密 Web 流量画像 |
| `shadowsocks` | Shadowsocks 代理流量画像 |
| `trojan` | Trojan 代理流量画像 |
| `vmess` | VMess 代理流量画像 |

**生成机理（论文可简述）：**  
为每个类别预置 17 维特征的均值画像，在给定 `seed` 下按高斯分布采样，并用 `noise` 控制类内离散与类间重叠程度，使任务可学习但非完全线性可分玩具问题。

### 4.3.2 CSV 导入数据集

- 接口：`POST /api/data/upload`  
- 要求：  
  - 含列 `label`  
  - 含全部 17 个特征列（名称与 `app/config.py` 中 `FEATURE_COLUMNS` 一致）  
  - 特征值可数值化  
- 标签别名会经 `normalize_label` 规范化（如 `https` → `normal_https`）

### 4.3.3 数据使用声明（务必写入论文）

本实验主结果基于**合成特征**。该设定保证：

- 流程与接口与真实特征 CSV 一致；  
- 实验可复现；  

但**不能**直接等同于真实网络环境下对 Shadowsocks/Trojan/VMess 的检测率。真实场景需补充 PCAP 流聚合与域差异分析。

---

## 4.4 特征设计

共 **17** 维流级侧信道统计特征（无载荷明文）：

| 分组 | 特征名 | 直观含义 |
|------|--------|----------|
| 包长 | `pkt_len_mean`, `pkt_len_std`, `pkt_len_min`, `pkt_len_max`, `pkt_len_p25`, `pkt_len_p75` | 包长分布 |
| 间隔 | `iat_mean`, `iat_std`, `iat_burstiness` | 到达间隔与突发性 |
| 方向 | `uplink_pkt_ratio`, `byte_up_down_ratio` | 上下行比例 |
| 流 | `duration`, `total_packets`, `total_bytes`, `packets_per_second` | 流规模与速率 |
| 复杂度 | `pkt_size_entropy`, `iat_entropy` | 包长/间隔熵 |

**设计原则：**

1. 不依赖解密内容，符合加密流量分析常见设定。  
2. 列名固定，便于论文表格与 CSV 契约。  
3. 与后续「PCAP → 流特征」管线字段一一对应，降低迁移成本。

---

## 4.5 模型与对比方案

实现见 `app/ml/models.py` 中 `MODEL_ZOO`：

| 模型键 | 类型 | 说明 |
|--------|------|------|
| `decision_tree` | 基线 | 单棵决策树 |
| `svm` | 基线 | RBF 核 SVM（含标准化 Pipeline） |
| `random_forest` | Bagging | 随机森林 |
| `adaboost` | Boosting | AdaBoost + 浅层树 |
| `xgboost` | Boosting | XGBoost 多分类 softprob |
| `lightgbm` | Boosting | LightGBM |
| `voting` | 集成 | Soft Voting：DT/RF/SVM/XGB/LGBM |
| `stacking` | 集成 | 同上 base + Logistic Regression 元学习器 |

**对比逻辑：**

- 基线：DT、SVM  
- 单一集成族：RF、AdaBoost、XGB、LGBM  
- 多模型融合：Voting、Stacking  

**假设（可在论文中作为待验证命题）：**  
在合成可分设定下，Voting/Stacking 的 macro-F1 不低于多数单一基学习器。

---

## 4.6 实验设置

| 项 | 默认值 | 配置位置 |
|----|--------|----------|
| 随机种子 | 42 | `RANDOM_SEED` |
| 训练集比例 | 0.70 | `TRAIN_RATIO` |
| 验证集比例 | 0.15 | `VAL_RATIO` |
| 测试集比例 | 0.15 | `TEST_RATIO` |
| 划分方式 | 分层随机划分（实现见 `train_all`） | `app/ml/train.py` |
| 评价指标计算子集 | **测试集** | `evaluate_model` |

说明：验证集预留用于扩展调参；当前主报告指标以测试集为准。

---

## 4.7 评价指标

实现：`app/ml/evaluate.py` → `evaluate_model`

| 指标 | 计算 | 备注 |
|------|------|------|
| Accuracy | `accuracy_score` | 整体正确率 |
| Precision | macro | 各类 precision 宏平均 |
| Recall | macro | 各类 recall 宏平均 |
| F1 | macro | 各类 F1 宏平均 |
| Confusion Matrix | `labels=LABELS` 顺序 | 4×4 |

最优模型选择：训练汇总时按 **F1（macro）** 取 `best_model`（见 `train_all` / `metrics.json`）。

---

## 4.8 实验步骤

### 方案 A：Web 控制台（答辩演示推荐）

1. 创建 venv 并安装依赖（见 README）。  
2. 启动：

```powershell
cd ProxyGuard-ML
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

3. 打开 http://127.0.0.1:8000  
4. **数据管理**：生成合成数据（记录 `n_per_class`、`seed`、`noise`）。  
5. **模型训练**：选择全部 8 个模型或论文对比子集，启动并等待 `success`。  
6. **实验结果**：记录 Accuracy/F1 表，保存 `reports/figures` 中图片。  
7. **在线识别**：用预览样本或手工特征做定性演示。  
8. 导出实验包：`GET /api/report/export?download=true`。

### 方案 B：离线脚本（论文批量复现推荐）

```powershell
cd ProxyGuard-ML
.\.venv\Scripts\Activate.ps1

# 正式规模示例
python scripts/run_experiments.py --n-per-class 1000 --seed 42 --noise 0.15

# 指定模型子集
python scripts/run_experiments.py --n-per-class 1000 --seed 42 --models decision_tree,svm,random_forest,adaboost,xgboost,lightgbm,voting,stacking
```

脚本行为：

1. 生成合成数据  
2. 调用 `train_all` 训练并写 `models/`、`reports/metrics.json`  
3. 导出对比图与混淆矩阵  
4. 写 `reports/experiment_summary.json`  
5. 终端打印指标表与 `best_model`

### 方案 C：自动化测试

```powershell
pytest -q
```

用于回归验证模块正确性，不替代论文主实验规模。

---

## 4.9 结果产物清单

| 产物 | 路径 |
|------|------|
| 指标 JSON | `reports/metrics.json` |
| 实验摘要 | `reports/experiment_summary.json` |
| 准确率对比图 | `reports/figures/model_accuracy_comparison.png` |
| F1 对比图 | `reports/figures/model_f1_comparison.png` |
| 混淆矩阵 | `reports/figures/confusion_matrix_{model}.png` |
| 特征重要性 | `reports/figures/feature_importance.png` |
| 模型文件 | `models/{model}.joblib` |

将数值填入论文表格时，建议同时记录：

- `n_per_class`、`seed`、`noise`  
- Python 与关键库版本  
- 划分比例  
- 参与对比的模型列表  

---

## 4.10 实验注意事项

1. **样本量**：每类过少（如 <100）时测试集很小，指标方差大且易出现接近 1.0 的虚高。  
2. **合成可分性**：若 `noise` 过小，类间分离过强，集成优势可能不明显。可做 `noise` 敏感性实验。  
3. **随机性**：固定 seed 后结果应稳定在合理波动内；换 seed 应报告波动。  
4. **真实性边界**：不得将合成数据结果表述为「真实代理协议检测准确率」。  
5. **依赖安装**：XGBoost/LightGBM 若安装失败，需在论文中说明降级模型集合。  
6. **路径**：训练与脚本均需在项目根目录运行，保证相对路径与 `app.config` 一致。

---

## 4.11 建议的论文实验小节结构

1. 实验环境与参数表  
2. 数据集说明（合成机理 + 规模 + 伦理/边界）  
3. 特征表（17 维）  
4. 对比模型表（8 个）  
5. 评价指标定义  
6. 主实验结果表 + 图  
7. 混淆矩阵与错误类型讨论  
8. 特征重要性讨论  
9. 消融/敏感性（可选：noise、样本量、模型子集）  
10. 局限性与真实数据展望  

结果文字可套用 `docs/result-analysis-template.md` 中的段落模板。
