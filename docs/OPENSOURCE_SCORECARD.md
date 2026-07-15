# Open-source maturity scorecard (v0.3.0)

Scored against common “good public GitHub ML demo” expectations — **not** FAANG production SOC2.

| Dimension | Score | Notes |
|-----------|------:|-------|
| Architecture | 16/20 | Clear layered monolith; not distributed |
| Code quality | 15/20 | Services + tests; some USE_MOCK branching remains |
| Security | 12/20 | Token optional, headers, upload limits; no full auth |
| Maintainability | 15/20 | Config central, Makefile, ruff CI |
| Documentation | 17/20 | README + architecture + schema + security |
| OSS hygiene | 16/20 | License, CoC, templates, changelog, CI |
| **Total** | **91/100** | **Mature demo / research OSS** |

## Current grade

**A− / mature open-source demo project**

## Gap vs “excellent production OSS”

| Gap | Severity |
|-----|----------|
| No real multi-user auth / SSO | High for SaaS, OK for research demo |
| Synthetic data default | High for “detection product” claims |
| In-process training thread | Medium |
| CDN scripts (Tailwind/Chart) | Medium (CSP already documents this) |
| No release automation / PyPI | Low |

## Must-fix (if claiming enterprise product)

1. Real auth + audit  
2. Real traffic feature pipeline  
3. Process isolation for training  
4. Secrets management  

## Recommended next (still research-grade)

1. Self-host static assets (drop CDN)  
2. Pre-commit hooks  
3. Coverage badge + codecov  
4. GitHub Release workflow on tags  
