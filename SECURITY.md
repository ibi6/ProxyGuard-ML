# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` (latest) | ✅ |
| Older commits | ❌ Best-effort only |

## Scope

ProxyGuard ML is a **local demonstration / research** system. It is **not** hardened for multi-tenant internet exposure.

Default threat model assumptions:

- Single trusted local user
- No authentication layer
- No production secrets store
- Synthetic or user-supplied feature CSVs only

## Reporting a vulnerability

If you discover a security issue (e.g. path traversal on upload, unsafe deserialization, command injection):

1. **Do not** open a public GitHub issue with exploit details.
2. Email the maintainer via the contact method on the GitHub profile, or open a private security advisory on GitHub if available.
3. Include:
   - Affected path / version (commit SHA)
   - Impact
   - Minimal reproduction steps
   - Suggested fix (optional)

Please allow reasonable time for a fix before public disclosure.

## Known non-goals / residual risks

- **No authn/authz** — anyone who can reach the server can train/predict
- **joblib model load** — only load models you trust
- **File upload** — CSV is validated for schema, but treat untrusted files carefully
- **Local bind recommended** — default docs use `127.0.0.1`

## Responsible use

Do not use this project for unauthorized network monitoring or interception. Classification of encrypted traffic has legal and ethical constraints depending on jurisdiction and deployment context.
