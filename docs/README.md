# Documentation Hub

Welcome to the ProxyGuard ML docs. Start here and drill down as needed.

## Guides

| Document | Audience | Contents |
|----------|----------|----------|
| [System Design](system-design.md) | Engineers writing / extending the stack | Requirements, architecture, modules, data flows, API surface |
| [Experiment Guide](experiment-guide.md) | Researchers reproducing metrics | Dataset schema, models, metrics, Web + offline runners |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Contributors | Local setup, conventions, PR checklist |
| [../SECURITY.md](../SECURITY.md) | Security researchers | Threat model, reporting channel |

## Mental model

```text
Synthetic / CSV features
        │
        ▼
  schema validation  ──►  train/val/test split
        │
        ▼
   model zoo fit  ──►  joblib + metrics + figures
        │
        ▼
   online predict  ──►  label + confidence
```

## Design principles

1. **No payload decrypt** — classification is side-channel only.
2. **Reproducibility** — fixed seeds, documented noise, offline scripts.
3. **Honest evaluation** — synthetic data is labeled as synthetic.
4. **Thin layers** — API adapters never own business logic; services orchestrate; `app/ml` stays pure.

## Version

Docs track software version **0.2.0**. See [CHANGELOG.md](../CHANGELOG.md).
