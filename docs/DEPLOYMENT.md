# 部署、备份与回滚

## 1. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `USE_MOCK` | `false` | 仅演示时启用模拟路径 |
| `PROXYGUARD_TOKEN` | 空 | 非空时保护写接口 |
| `PROXYGUARD_MAX_UPLOAD_BYTES` | `20971520` | CSV 上限，范围 1KiB–1GiB |
| `PROXYGUARD_DB_PATH` | `data/proxyguard.db` | SQLite 路径 |
| `LOG_LEVEL` | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `PROXYGUARD_BIND_HOST` | `127.0.0.1` | Compose 宿主机绑定地址 |
| `PROXYGUARD_PORT` | `8000` | Compose 宿主机端口 |

复制 `.env.example` 为 `.env`；应用启动时自动加载该文件，但真实系统环境变量优先。真实 Token 只保存在部署环境，不提交到 Git。

## 2. 本地进程

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

开发时可添加 `--reload`；生产进程不要使用 reload，也不要启动多个 worker，因为训练互斥是单进程内锁。

## 3. Docker Compose

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs -f proxyguard
```

默认打开 `http://127.0.0.1:8000`。健康状态应变为 `healthy`。

持久化：

- `./data:/app/data`：CSV、active 指针、SQLite。
- `./models:/app/models`：joblib 模型。
- `./reports:/app/reports`：指标、图表和 ZIP。

## 4. Nginx 反向代理

仓库提供 `deploy/nginx.conf`。先启动 Compose，再将 Nginx 加入固定的 `proxyguard-ml_default` 网络：

```bash
docker run -d --name proxyguard-nginx \
  --restart unless-stopped \
  --network proxyguard-ml_default \
  -p 127.0.0.1:8080:80 \
  -v "$PWD/deploy/nginx.conf:/etc/nginx/nginx.conf:ro" \
  nginx:1.27-alpine
```

访问 `http://127.0.0.1:8080`。公网部署应在 Nginx 前配置 TLS、域名、防火墙和可信代理；不要直接把无 Token 的写接口暴露到互联网。

Nginx 配置包含：20MiB 请求上限、API 速率限制、连接复用、代理超时和独立健康端点 `/nginx-health`。

## 5. 生产检查

```bash
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/system
docker compose ps
docker compose logs --tail=200 proxyguard
```

检查磁盘容量，尤其是 `data/`、`models/`、`reports/`。训练期间 CPU 高属于预期；持续 5xx、任务长期无进度或磁盘逼近 90% 需要告警。

## 6. 备份

备份前停止新训练；SQLite 使用 WAL 以外的默认日志模式，推荐短暂停服获得一致快照。

```bash
docker compose stop proxyguard
tar -czf proxyguard-backup-$(date +%Y%m%d-%H%M%S).tar.gz data models reports .env
docker compose start proxyguard
```

Windows PowerShell：

```powershell
docker compose stop proxyguard
Compress-Archive -Path data,models,reports,.env -DestinationPath "proxyguard-backup-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
docker compose start proxyguard
```

备份文件含 Token，必须加密并限制访问。恢复时先停止服务，把三个目录恢复到同一版本，再启动并检查 `/api/health` 和 `/api/system`。

## 7. 回滚

发布前为镜像打不可变版本标签：

```bash
docker build -t proxyguard-ml:0.4.0 .
```

回滚步骤：

1. `docker compose stop proxyguard`。
2. 备份当前 `data/ models/ reports/`。
3. 恢复与目标版本对应的数据备份（本版本只移动 SQLite 路径，表结构兼容）。
4. 将 Compose 的 image 临时改为上一标签，或重新 tag 为 `proxyguard-ml:local`。
5. `docker compose up -d --no-build`。
6. 验证健康、页面、数据摘要、模型列表和一次预测。

## 8. 故障排查

| 现象 | 检查 |
|------|------|
| Compose 提示项目名为空 | 使用仓库的 v0.4 `name: proxyguard-ml` 配置 |
| 页面无图表 | 检查 jsDelivr 网络；数据表仍可用 |
| 写接口 401 | 检查 `.env` Token 与浏览器 `pg_api_token` |
| 数据存在但任务历史为空 | 检查 `PROXYGUARD_DB_PATH` 和 `data/proxyguard.db` 权限 |
| 训练一直 running | 重启后应自动标记中断；查看日志和 SQLite |
| 报告下载失败 | 检查 `reports/` 可写、磁盘空间和 ZIP 文件权限 |
