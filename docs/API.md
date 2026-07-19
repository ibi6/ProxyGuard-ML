# API 文档

## 1. 通用约定

- Base URL：`http://127.0.0.1:8000`
- 数据格式：除文件上传和 ZIP 下载外均为 JSON。
- OpenAPI：`GET /openapi.json`；交互文档：`GET /docs`。
- 写接口鉴权：配置 `PROXYGUARD_TOKEN` 后，请求头必须包含 `X-API-Token: <token>`。
- 错误体：`{"detail":"message"}` 或 422 的结构化错误数组。422 不回显原始输入。

| 状态码 | 含义 |
|--------|------|
| 200 | 请求成功 |
| 400 | 业务条件不满足、CSV/模型无效 |
| 401 | Token 缺失或错误 |
| 404 | 训练任务不存在 |
| 413 | 上传超过大小限制 |
| 422 | 请求字段、类型、范围或枚举不符合契约 |
| 500 | 未处理的服务端错误；详细信息仅写日志 |

## 2. 健康与系统

### GET `/api/health`

返回进程状态、版本、Mock/鉴权模式和数据边界。

```bash
curl http://127.0.0.1:8000/api/health
```

```json
{
  "status": "ok",
  "service": "ProxyGuard ML",
  "version": "0.4.0",
  "use_mock": false,
  "auth_required": false,
  "data_mode": "synthetic_or_csv",
  "payload_decrypt": false
}
```

### GET `/api/system`

返回数据集、模型数、最优模型、预测日志数和划分设置的运行快照。

## 3. 数据接口

### POST `/api/data/generate`

生成四类均衡合成特征。

```json
{
  "n_per_class": 800,
  "seed": 42,
  "noise": 0.85
}
```

约束：`n_per_class` 1–50000，`seed` 0–4294967295，`noise` 0–5；未知字段返回 422。

```bash
curl -X POST http://127.0.0.1:8000/api/data/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Token: $PROXYGUARD_TOKEN" \
  -d '{"n_per_class":800,"seed":42,"noise":0.85}'
```

成功响应包含 `total_samples`、`class_distribution`、`feature_columns`、`source`、`seed` 和 `noise`。

### POST `/api/data/upload`

字段名为 `file` 的 multipart CSV。文件必须以 `.csv` 结尾，包含 17 个特征列和 `label`，默认上限 20MiB。系统按块读取，超限立即返回 413。

```bash
curl -X POST http://127.0.0.1:8000/api/data/upload \
  -H "X-API-Token: $PROXYGUARD_TOKEN" \
  -F "file=@features.csv;type=text/csv"
```

### GET `/api/data/summary`

返回当前 active 数据集摘要、类别分布和生成元信息。

### GET `/api/data/preview?limit=20`

返回前 `limit` 行，`limit` 范围为 1–200。

## 4. 训练与模型

### POST `/api/train`

```json
{
  "models": ["random_forest", "xgboost", "voting"]
}
```

模型枚举：`decision_tree`、`svm`、`random_forest`、`adaboost`、`xgboost`、`lightgbm`、`voting`、`stacking`。至少选择一个，重复项按首次出现顺序去重；同一进程同时只允许一个训练任务。

成功响应：

```json
{
  "task_id": "task_123456789abc",
  "status": "running",
  "task": {"status": "running", "progress": 0.0}
}
```

### GET `/api/train`

按创建时间倒序返回任务数组。

### GET `/api/train/{task_id}`

返回单个任务的状态、模型、配置、进度、指标、最优模型、错误和时间。

### POST `/api/train/{task_id}/cancel`

请求取消运行中的训练。取消点位于模型之间，因此当前模型会先完成。

### GET `/api/models`

返回已训练模型、指标、可用模型清单和最优模型。

## 5. 预测

### POST `/api/predict`

请求必须包含 1–500 个完整 17 维样本，所有值必须是有限数。`model` 可省略，省略时使用报告中的最优模型或首个可用模型。

```json
{
  "model": "random_forest",
  "samples": [
    {
      "pkt_len_mean": 620,
      "pkt_len_std": 140,
      "pkt_len_min": 54,
      "pkt_len_max": 1460,
      "pkt_len_p25": 480,
      "pkt_len_p75": 780,
      "iat_mean": 0.035,
      "iat_std": 0.018,
      "iat_burstiness": 0.85,
      "uplink_pkt_ratio": 0.48,
      "byte_up_down_ratio": 0.92,
      "duration": 12.5,
      "total_packets": 186,
      "total_bytes": 98500,
      "packets_per_second": 28,
      "pkt_size_entropy": 3.4,
      "iat_entropy": 2.9
    }
  ]
}
```

成功响应包含每条样本的 `label`、`display_label`、`confidence`、`probabilities`、`proba_supported` 和模型名。不支持概率的模型返回 `confidence: null`，不会伪造置信度。

### GET `/api/predict/stats`

返回 SQLite 中累计预测日志数。

## 6. 实验与报告

### GET `/api/experiments`

返回成功训练记录、最新指标对比、混淆矩阵和特征重要性报告。

### GET `/api/report/export`

生成报告 ZIP 并返回元信息。它会写入 `reports/`，因此配置 Token 后同样要求 `X-API-Token`。添加 `?download=true` 时返回 `application/zip` 文件。

```bash
curl -OJ -H "X-API-Token: $PROXYGUARD_TOKEN" \
  "http://127.0.0.1:8000/api/report/export?download=true"
```

## 7. 设置

### GET `/api/settings`

返回 `random_seed`、三段比例、`n_per_class_default` 和 `noise_default`。

### PUT `/api/settings`

支持部分更新，未知字段返回 422；三段比例在与现有值合并后必须接近 1.0。

```json
{
  "random_seed": 42,
  "train_ratio": 0.7,
  "val_ratio": 0.15,
  "test_ratio": 0.15,
  "n_per_class_default": 800,
  "noise_default": 0.85
}
```

## 8. 页面路由

`/`、`/data`、`/train`、`/predict`、`/experiments`、`/settings` 返回 Jinja2 HTML。页面只通过同源 `/api/*` 读取业务数据。
