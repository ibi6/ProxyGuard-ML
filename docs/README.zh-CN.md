# 文档中枢（中文）

欢迎阅读 ProxyGuard ML 文档。建议从本页进入，再按需深入。

[English docs hub](README.md) · [中文项目 README（默认）](../README.md) · [English README](../README.en.md)

## 指南一览

| 文档 | 读者 | 内容 |
|------|------|------|
| [系统设计](system-design.md) | 二次开发工程师 | 需求、架构、模块、数据流、接口 |
| [实验指南](experiment-guide.md) | 复现实验的研究者 | 数据 schema、模型、指标、Web / 离线流程 |
| [贡献指南](../CONTRIBUTING.md) | 贡献者 | 本地环境、约定、PR 清单 |
| [安全策略](../SECURITY.md) | 安全研究者 | 威胁模型、报告渠道 |

## 心智模型

```text
合成 / CSV 特征
        │
        ▼
  schema 校验  ──►  train/val/test 划分
        │
        ▼
   模型动物园 fit  ──►  joblib + 指标 + 图表
        │
        ▼
   在线预测  ──►  标签 + 置信度
```

## 设计原则

1. **不解密载荷** — 仅侧信道统计特征。  
2. **可复现** — 固定种子、可文档化噪声、离线脚本。  
3. **诚实评估** — 合成数据必须标明为合成。  
4. **薄分层** — API 不做业务；服务编排；`app/ml` 保持纯算法。

## 版本

文档对应软件版本 **0.2.0**。变更见 [CHANGELOG.md](../CHANGELOG.md)。

## 说明

`system-design.md` 与 `experiment-guide.md` 正文目前以中文撰写，可直接用于学习与二次开发。  
项目首页默认中文见 [README.md](../README.md)，英文版见 [README.en.md](../README.en.md)。
