# 贡献指南

感谢参与 ProxyGuard ML。

本仓库公开文档默认使用**简体中文**。

## 开发环境

```bash
git clone https://github.com/ibi6/ProxyGuard-ML.git
cd ProxyGuard-ML
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

代码检查：

```bash
ruff check app tests scripts
```

启动控制台：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 约定

| 方面 | 要求 |
|------|------|
| 分层 | `api` 薄适配 → `services` 编排 → `ml` 算法 |
| 特征 | 必须用 `FEATURE_COLUMNS` 校验 |
| 可复现 | 写明 seed / noise / n_per_class |
| 诚实 | 禁止把 mock 或合成指标说成真实 PCAP 结果 |
| 测试 | 行为变更请补 `tests/` |

## 提交 PR

1. Fork 后开功能分支  
2. 尽量一次只改一件事  
3. `pytest -q` 必须通过  
4. 填写 PR 模板  

## 请勿提交

- `.env`、令牌、本机绝对路径  
- 生成数据 `data/synthetic`、`models/*.joblib`、`*.db`  
- 含个人信息的论文/答辩二进制文件  

## 行为准则

见 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
