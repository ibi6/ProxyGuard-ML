# 测试与验收

## 1. 本地测试

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check app tests scripts
python -m compileall -q app scripts tests
python -m pytest -q
```

测试按职责拆分：

| 文件 | 覆盖范围 |
|------|----------|
| `test_api_mock.py` | Mock 端到端链路 |
| `test_api_real.py` | 隔离目录中的真实 API/训练/导出 |
| `test_api_contracts.py` | 严格 Schema、上限、非有限数、流式上传、报告路径 |
| `test_runtime_hardening.py` | SQLite、环境变量、Token、重启恢复、响应头、依赖分层 |
| `test_ui_contracts.py` | 六页模板、健康状态、ARIA、批量提示和默认参数 |
| `test_models_train.py` | 模型构建、训练与指标 |
| `test_dataset_service.py` | 数据集持久化与恢复 |
| `test_evaluate.py` | 评估 JSON 与图表 |

## 2. 集成用例

| 编号 | 前置 | 操作 | 预期 |
|------|------|------|------|
| IT-01 | 空数据目录 | 生成 40/类合成数据 | 160 行，四类均衡，摘要持久化 |
| IT-02 | IT-01 | 训练决策树 | 任务进入 success，joblib 与 metrics 存在 |
| IT-03 | 已训练模型 | 提交完整单条样本 | 返回合法标签并写一条预测日志 |
| IT-04 | 已有指标 | 导出 ZIP | ZIP 含 manifest、metrics 和已有图表 |
| IT-05 | running 任务行 | 重启服务 | 旧任务标记 failed，说明为重启中断 |
| IT-06 | 设置已有值 | 部分更新比例 | 合并校验后持久化，合计为 1 |

## 3. UI/响应式验收

宽度：375×812、768×1024、1440×1000。页面：总览、数据、训练、识别、实验、设置。

必须满足：

- `document.documentElement.scrollWidth <= window.innerWidth`。
- 375px 标题不逐字换行，顶部操作区不挤压标题。
- 表格和混淆矩阵只在自身容器横向滚动。
- 移动侧栏关闭时 `inert` 且 `aria-hidden=true`；打开后 Escape 可关闭并把焦点还给菜单按钮。
- 键盘 Tab 可看到清晰焦点；触控按钮不小于 44px。
- 加载、空、失败、成功状态都有文字，不只依赖颜色。
- Chart.js 不可用时显示降级说明。

## 4. 压力与容量测试

应用定位为单进程本地实验控制台，压力测试重点是验证边界而非宣称高并发生产吞吐。

### 只读接口

安装 `hey` 后：

```bash
hey -n 2000 -c 20 http://127.0.0.1:8000/api/health
hey -n 1000 -c 10 http://127.0.0.1:8000/api/data/summary
```

验收：0 个 5xx；健康接口 P95 < 200ms（普通开发机、无训练负载）。

### 边界用例

| 用例 | 输入 | 预期 |
|------|------|------|
| ST-01 | 500 条完整预测 | 200；内存可回收，日志数增加 500 |
| ST-02 | 501 条预测 | 422；服务不调用模型 |
| ST-03 | 20MiB 合法 CSV | 在配置允许时处理或给出明确格式错误 |
| ST-04 | 上限 +1 字节 | 读取到超限即 413 |
| ST-05 | 并发启动两个训练 | 一个启动，另一个 400 提示已有任务 |

训练会占用 CPU，压测时必须把“空闲”和“训练中”结果分开记录。

## 5. 安全测试

- SQL 注入：设置、任务 ID 和日志查询均走参数绑定；提交引号/SQL 片段不改变表结构。
- XSS：上传标签、任务错误和 API 文本经过 `textContent` 或 `escapeHtml`；注入 `<script>` 只显示文本。
- CSRF：系统不使用 Cookie 会话；配置 Token 后写操作要求非简单自定义请求头。
- 权限绕过：逐一验证所有 POST/PUT/取消接口在无 Token、错 Token、正确 Token 下的 401/200。
- 暴力尝试：公网部署必须在 Nginx/防火墙限制速率；应用本身默认只绑定本地回环。
- Token 伪造：错误 Token 使用常量时间比较，响应不区分缺失与错误。
- 文件上传：扩展名、大小、必需列、标签、NaN/Inf 均验证。
- 响应头：断言 CSP、XFO、nosniff、COOP、CORP、Permissions-Policy 和 Cache-Control。

## 6. 用户验收

1. 新用户按 README 在 15 分钟内启动页面。
2. 使用 800/42/0.85 一键生成数据。
3. 选择 RF/XGBoost/Voting 启动训练，可看到进度并能取消。
4. 单条识别返回标签、概率和模型；批量超过 500 条在浏览器直接提示。
5. 实验页能解释 Accuracy、Macro-F1、混淆矩阵与特征重要性。
6. 能下载报告并明确数据是合成而非公网抓包。
7. 重启容器后设置、任务记录、数据、模型和报告仍存在。
