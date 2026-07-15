/**
 * ProxyGuard ML — shared frontend utilities + page controllers
 */

const FEATURE_COLUMNS = [
  "pkt_len_mean", "pkt_len_std", "pkt_len_min", "pkt_len_max", "pkt_len_p25", "pkt_len_p75",
  "iat_mean", "iat_std", "iat_burstiness",
  "uplink_pkt_ratio", "byte_up_down_ratio",
  "duration", "total_packets", "total_bytes", "packets_per_second",
  "pkt_size_entropy", "iat_entropy",
];

const LABEL_DISPLAY = {
  normal_https: "Normal HTTPS",
  shadowsocks: "Shadowsocks",
  trojan: "Trojan",
  vmess: "VMess",
};

const LABEL_ORDER = ["normal_https", "shadowsocks", "trojan", "vmess"];

const MODEL_CATALOG = [
  { id: "decision_tree", label: "决策树 (DT)", short: "DT" },
  { id: "svm", label: "支持向量机 (SVM)", short: "SVM" },
  { id: "random_forest", label: "随机森林 (RF)", short: "RF" },
  { id: "adaboost", label: "AdaBoost", short: "Ada" },
  { id: "xgboost", label: "XGBoost", short: "XGB" },
  { id: "lightgbm", label: "LightGBM", short: "LGBM" },
  { id: "voting", label: "Voting 软投票", short: "Voting", ensemble: true },
  { id: "stacking", label: "Stacking 堆叠", short: "Stacking", ensemble: true },
];

const CHART_COLORS = {
  indigo: "#2563eb",
  cyan: "#0ea5e9",
  emerald: "#059669",
  amber: "#d97706",
  rose: "#dc2626",
  blue: "#3b82f6",
  violet: "#1d4ed8",
  slate: "#94a3b8",
};

const CLASS_COLORS = {
  normal_https: "#3b82f6",
  shadowsocks: "#2563eb",
  trojan: "#f59e0b",
  vmess: "#10b981",
};

const FEATURE_DEFAULTS = {
  pkt_len_mean: 620,
  pkt_len_std: 140,
  pkt_len_min: 54,
  pkt_len_max: 1460,
  pkt_len_p25: 480,
  pkt_len_p75: 780,
  iat_mean: 0.035,
  iat_std: 0.018,
  iat_burstiness: 0.85,
  uplink_pkt_ratio: 0.48,
  byte_up_down_ratio: 0.92,
  duration: 12.5,
  total_packets: 186,
  total_bytes: 98500,
  packets_per_second: 28,
  pkt_size_entropy: 3.4,
  iat_entropy: 2.9,
};

const PREDICT_KEY_FIELDS = [
  { key: "pkt_len_mean", label: "包长均值", step: "0.1" },
  { key: "iat_mean", label: "包间隔均值", step: "0.001" },
  { key: "packets_per_second", label: "包速率 (pps)", step: "0.1" },
  { key: "pkt_size_entropy", label: "包长熵", step: "0.01" },
  { key: "byte_up_down_ratio", label: "上下行字节比", step: "0.01" },
  { key: "duration", label: "流持续时间 (s)", step: "0.1" },
  { key: "total_packets", label: "总包数", step: "1" },
  { key: "iat_burstiness", label: "突发度", step: "0.01" },
];

const PREDICT_COUNT_KEY = "pg_predict_count";

let _charts = {};

function getApiToken() {
  try {
    return (window.localStorage.getItem("pg_api_token") || "").trim();
  } catch (_) {
    return "";
  }
}

async function api(path, options = {}) {
  const opts = { ...options };
  const headers = { ...(options.headers || {}) };
  // Don't force JSON content-type for FormData
  if (!(opts.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }
  const token = getApiToken();
  if (token) headers["X-API-Token"] = token;
  const res = await fetch(path, { ...opts, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
      if (Array.isArray(detail)) {
        detail = detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      }
    } catch (_) {
      /* keep statusText */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.blob();
}

function showToast(msg, type = "info") {
  const root = document.getElementById("pg-toast-root");
  if (!root) return;

  const el = document.createElement("div");
  el.className = `pg-toast ${type}`;
  el.innerHTML = `
    <span class="pg-toast-dot" aria-hidden="true"></span>
    <p class="pg-toast-msg"></p>
  `;
  el.querySelector(".pg-toast-msg").textContent = String(msg ?? "");
  root.appendChild(el);

  const ttl = type === "error" ? 4200 : 2800;
  window.setTimeout(() => {
    el.classList.add("hiding");
    window.setTimeout(() => el.remove(), 220);
  }, ttl);
}

function setLoading(el, on) {
  if (!el) return;
  if (on) {
    el.classList.add("pg-loading");
    if ("disabled" in el) el.disabled = true;
    el.setAttribute("aria-busy", "true");
  } else {
    el.classList.remove("pg-loading");
    if ("disabled" in el) el.disabled = false;
    el.removeAttribute("aria-busy");
  }
}

function formatPercent(x, digits = 1) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  const n = Number(x);
  const pct = Math.abs(n) <= 1 ? n * 100 : n;
  return `${pct.toFixed(digits)}%`;
}

function formatNumber(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("zh-CN");
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function modelLabel(id) {
  const m = MODEL_CATALOG.find((x) => x.id === id);
  return m ? m.label : String(id || "").replace(/_/g, " ");
}

function modelShort(id) {
  const m = MODEL_CATALOG.find((x) => x.id === id);
  return m ? m.short : id;
}

function labelBadgeHtml(label, display) {
  const text = display || LABEL_DISPLAY[label] || label;
  const cls = {
    normal_https: "pg-badge-info",
    shadowsocks: "pg-badge-primary",
    trojan: "pg-badge-warning",
    vmess: "pg-badge-success",
  }[label] || "pg-badge-neutral";
  return `<span class="pg-badge ${cls}">${escapeHtml(text)}</span>`;
}

function getPredictCount() {
  try {
    return Number(localStorage.getItem(PREDICT_COUNT_KEY) || 0) || 0;
  } catch (_) {
    return 0;
  }
}

function bumpPredictCount(n = 1) {
  const next = getPredictCount() + n;
  try {
    localStorage.setItem(PREDICT_COUNT_KEY, String(next));
  } catch (_) {
    /* ignore */
  }
  return next;
}

function destroyChart(key) {
  if (_charts[key]) {
    try {
      _charts[key].destroy();
    } catch (_) {
      /* ignore */
    }
    delete _charts[key];
  }
}

function chartDefaults() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.color = "#64748b";
  Chart.defaults.borderColor = "rgba(148,163,184,0.22)";
  Chart.defaults.font.family = "Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif";
}

function emptyHtml(iconPath, title, desc, actionHtml = "") {
  return `
    <div class="pg-empty">
      <div class="pg-empty-icon">
        <svg viewBox="0 0 24 24">${iconPath}</svg>
      </div>
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(desc)}</p>
      ${actionHtml ? `<div class="pg-mt-4">${actionHtml}</div>` : ""}
    </div>
  `;
}

function initShell() {
  const sidebar = document.getElementById("pg-sidebar");
  const overlay = document.getElementById("pg-overlay");
  const toggle = document.getElementById("pg-mobile-toggle");

  function closeSidebar() {
    sidebar?.classList.remove("open");
    overlay?.classList.remove("open");
  }

  function openSidebar() {
    sidebar?.classList.add("open");
    overlay?.classList.add("open");
  }

  toggle?.addEventListener("click", () => {
    if (sidebar?.classList.contains("open")) closeSidebar();
    else openSidebar();
  });
  overlay?.addEventListener("click", closeSidebar);

  // Real health probe (template no longer hardcodes "online")
  const healthText = document.getElementById("pg-health-text");
  const healthDot = document.getElementById("pg-health-dot");
  api("/api/health")
    .then((h) => {
      if (healthText) {
        const bits = ["服务在线"];
        if (h.use_mock) bits.push("MOCK");
        if (h.auth_required) bits.push("需Token");
        healthText.textContent = bits.join(" · ");
      }
      if (healthDot) {
        healthDot.style.background = h.use_mock
          ? "#f59e0b"
          : h.auth_required
            ? "#3b82f6"
            : "#10b981";
      }
    })
    .catch(() => {
      if (healthText) healthText.textContent = "服务离线";
      if (healthDot) healthDot.style.background = "#f43f5e";
    });
}

/* ===================== Dashboard ===================== */
async function initDashboard() {
  const kpiSamples = document.getElementById("kpi-samples");
  const kpiModels = document.getElementById("kpi-models");
  const kpiF1 = document.getElementById("kpi-f1");
  const kpiPredict = document.getElementById("kpi-predict");
  const kpiSamplesTrend = document.getElementById("kpi-samples-trend");
  const kpiModelsTrend = document.getElementById("kpi-models-trend");
  const kpiF1Trend = document.getElementById("kpi-f1-trend");
  const chartWrap = document.getElementById("dash-chart-wrap");
  const chartEmpty = document.getElementById("dash-chart-empty");
  const tasksBody = document.getElementById("dash-tasks-body");
  const refreshBtn = document.getElementById("btn-dash-refresh");

  async function load() {
    try {
      const [summary, modelsResp, tasksResp] = await Promise.all([
        api("/api/data/summary"),
        api("/api/models"),
        api("/api/train"),
      ]);

      const total = summary.total_samples || 0;
      const models = modelsResp.models || [];
      const tasks = tasksResp.tasks || [];
      const bestF1 = models.reduce((m, x) => Math.max(m, x.metrics?.f1 || 0), 0);

      if (kpiSamples) kpiSamples.textContent = formatNumber(total);
      if (kpiModels) kpiModels.textContent = formatNumber(models.length);
      if (kpiF1) kpiF1.textContent = bestF1 ? formatPercent(bestF1) : "—";
      // Prefer server-side predict_logs count; fall back to local demo counter.
      let predictCount = getPredictCount();
      try {
        const stats = await api("/api/predict/stats");
        if (stats && typeof stats.count === "number") predictCount = stats.count;
      } catch (_) {
        /* keep localStorage fallback */
      }
      if (kpiPredict) kpiPredict.textContent = formatNumber(predictCount);

      if (kpiSamplesTrend) {
        kpiSamplesTrend.textContent = total
          ? `来源：${summary.source === "synthetic" ? "合成数据" : summary.source || "—"} · ${summary.n_per_class || 0}/类`
          : "尚未生成数据";
        kpiSamplesTrend.classList.toggle("up", total > 0);
      }
      if (kpiModelsTrend) {
        kpiModelsTrend.textContent = models.length
          ? `最优：${modelShort(models[0]?.name)} · F1 ${formatPercent(models[0]?.metrics?.f1)}`
          : "完成训练后展示";
      }
      if (kpiF1Trend) {
        kpiF1Trend.textContent = bestF1
          ? `基于 ${models.length} 个已训练模型`
          : "完成训练后展示";
        kpiF1Trend.classList.toggle("up", !!bestF1);
      }

      // Accuracy bar chart
      if (models.length && chartWrap) {
        chartEmpty?.classList.add("pg-hidden");
        chartWrap.classList.remove("pg-hidden");
        const canvas = document.getElementById("dash-acc-chart");
        if (canvas && typeof Chart !== "undefined") {
          destroyChart("dash-acc");
          _charts["dash-acc"] = new Chart(canvas, {
            type: "bar",
            data: {
              labels: models.map((m) => modelShort(m.name)),
              datasets: [{
                label: "Accuracy",
                data: models.map((m) => Number(((m.metrics?.accuracy || 0) * 100).toFixed(2))),
                backgroundColor: models.map((m) =>
                  m.is_ensemble ? "rgba(5,150,105,0.72)" : "rgba(37,99,235,0.72)"
                ),
                borderColor: models.map((m) =>
                  m.is_ensemble ? CHART_COLORS.emerald : CHART_COLORS.blue
                ),
                borderWidth: 1,
                borderRadius: 8,
                maxBarThickness: 42,
              }],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false },
                tooltip: {
                  callbacks: {
                    label: (ctx) => `准确率 ${ctx.parsed.y.toFixed(1)}%`,
                  },
                },
              },
              scales: {
                x: { grid: { display: false } },
                y: {
                  beginAtZero: true,
                  min: 0,
                  max: 100,
                  ticks: { callback: (v) => `${v}%` },
                },
              },
            },
          });
        }
      } else {
        chartWrap?.classList.add("pg-hidden");
        if (chartEmpty) {
          chartEmpty.classList.remove("pg-hidden");
          chartEmpty.innerHTML = emptyHtml(
            '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5"/><path d="M12 16V8"/><path d="M16 16v-3"/>',
            total ? "暂无模型准确率" : "尚未生成数据",
            total
              ? "请前往模型训练页启动训练，完成后此处展示柱状对比。"
              : "请先在数据管理页生成合成流特征数据集。",
            total
              ? '<a href="/train" class="pg-btn pg-btn-primary pg-btn-sm">去训练</a>'
              : '<a href="/data" class="pg-btn pg-btn-primary pg-btn-sm">去生成数据</a>'
          );
        }
      }

      // Recent tasks
      if (tasksBody) {
        if (!tasks.length) {
          tasksBody.innerHTML = emptyHtml(
            '<path d="M12 3v6"/><rect x="4" y="11" width="16" height="9" rx="2"/>',
            "暂无训练记录",
            "生成数据集并启动训练后，这里会显示任务状态与关键指标。",
            '<a href="/train" class="pg-btn pg-btn-ghost pg-btn-sm">去训练</a>'
          );
        } else {
          const rows = tasks.slice(0, 6).map((t) => {
            const statusCls =
              t.status === "success"
                ? "pg-badge-success"
                : t.status === "running"
                  ? "pg-badge-info"
                  : t.status === "failed"
                    ? "pg-badge-danger"
                    : "pg-badge-neutral";
            const statusText =
              t.status === "success"
                ? "成功"
                : t.status === "running"
                  ? "运行中"
                  : t.status === "failed"
                    ? "失败"
                    : t.status;
            const best = t.best_model ? modelShort(t.best_model) : "—";
            const f1 = t.best_model && t.metrics?.[t.best_model]
              ? formatPercent(t.metrics[t.best_model].f1)
              : "—";
            return `
              <tr>
                <td><code class="pg-code">${escapeHtml(t.task_id)}</code></td>
                <td><span class="pg-badge ${statusCls}">${escapeHtml(statusText)}</span></td>
                <td>${escapeHtml((t.models || []).map(modelShort).join(" · ") || "—")}</td>
                <td>${escapeHtml(best)}</td>
                <td>${escapeHtml(f1)}</td>
                <td class="pg-dim">${escapeHtml((t.finished_at || t.created_at || "").replace("T", " ").replace("+00:00", " UTC"))}</td>
              </tr>
            `;
          }).join("");
          tasksBody.innerHTML = `
            <div class="pg-table-wrap">
              <table class="pg-table">
                <thead>
                  <tr>
                    <th>任务 ID</th>
                    <th>状态</th>
                    <th>模型</th>
                    <th>最优</th>
                    <th>F1</th>
                    <th>时间</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          `;
        }
      }
    } catch (err) {
      showToast(err.message || "看板加载失败", "error");
    }
  }

  refreshBtn?.addEventListener("click", async () => {
    setLoading(refreshBtn, true);
    await load();
    setLoading(refreshBtn, false);
    showToast("看板已刷新", "success");
  });

  await load();
}

/* ===================== Data ===================== */
async function initDataPage() {
  const form = document.getElementById("data-generate-form");
  const genBtn = document.getElementById("btn-generate");
  const uploadInput = document.getElementById("data-upload");
  const summaryBadge = document.getElementById("data-summary-badge");
  const metaLine = document.getElementById("data-meta-line");
  const chartEmpty = document.getElementById("data-dist-empty");
  const chartWrap = document.getElementById("data-dist-wrap");
  const previewBody = document.getElementById("data-preview-body");
  const nInput = document.getElementById("gen-n");
  const seedInput = document.getElementById("gen-seed");
  const noiseInput = document.getElementById("gen-noise");

  // Prefill from settings
  try {
    const settings = await api("/api/settings");
    if (nInput && settings.n_per_class_default != null) nInput.value = settings.n_per_class_default;
    if (seedInput && settings.random_seed != null) seedInput.value = settings.random_seed;
    if (noiseInput && settings.noise_default != null) noiseInput.value = settings.noise_default;
  } catch (_) {
    /* ignore */
  }

  async function refresh() {
    try {
      const [summary, preview] = await Promise.all([
        api("/api/data/summary"),
        api("/api/data/preview?limit=12"),
      ]);

      const total = summary.total_samples || 0;
      if (summaryBadge) {
        summaryBadge.textContent = total ? `${formatNumber(total)} 条样本` : "空数据集";
        summaryBadge.className = `pg-badge ${total ? "pg-badge-success" : "pg-badge-neutral"}`;
      }
      if (metaLine) {
        metaLine.textContent = total
          ? `特征 ${summary.n_features} 维 · 每类 ${summary.n_per_class} · seed=${summary.seed ?? "—"} · noise=${summary.noise ?? "—"} · ${summary.generated_at ? summary.generated_at.replace("T", " ").replace("+00:00", "") : ""}`
          : "尚未生成或上传数据。可使用下方表单生成合成流级特征。";
      }

      const dist = summary.class_distribution || {};
      if (total) {
        chartEmpty?.classList.add("pg-hidden");
        chartWrap?.classList.remove("pg-hidden");
        const canvas = document.getElementById("data-dist-chart");
        if (canvas && typeof Chart !== "undefined") {
          destroyChart("data-dist");
          const labels = LABEL_ORDER.map((l) => LABEL_DISPLAY[l] || l);
          const values = LABEL_ORDER.map((l) => dist[l] || 0);
          _charts["data-dist"] = new Chart(canvas, {
            type: "doughnut",
            data: {
              labels,
              datasets: [{
                data: values,
                backgroundColor: LABEL_ORDER.map((l) => CLASS_COLORS[l]),
                borderColor: "#ffffff",
                borderWidth: 2,
                hoverOffset: 6,
              }],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  position: "bottom",
                  labels: { boxWidth: 12, padding: 14 },
                },
              },
              cutout: "62%",
            },
          });
        }
      } else {
        chartWrap?.classList.add("pg-hidden");
        if (chartEmpty) {
          chartEmpty.classList.remove("pg-hidden");
          chartEmpty.innerHTML = emptyHtml(
            '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>',
            "暂无类别分布",
            "生成数据后将展示四类协议的样本占比。"
          );
        }
      }

      if (previewBody) {
        if (!preview.rows?.length) {
          previewBody.innerHTML = emptyHtml(
            '<path d="M4 6h16M4 12h16M4 18h10"/>',
            "暂无预览行",
            "生成合成数据后，这里会展示前若干条流级特征。"
          );
        } else {
          const cols = ["label", "pkt_len_mean", "iat_mean", "packets_per_second", "pkt_size_entropy", "byte_up_down_ratio", "duration", "total_packets"];
          const head = cols.map((c) => `<th>${escapeHtml(c === "label" ? "标签" : c)}</th>`).join("");
          const body = preview.rows.map((row) => {
            const tds = cols.map((c) => {
              if (c === "label") return `<td>${labelBadgeHtml(row.label, LABEL_DISPLAY[row.label])}</td>`;
              const v = row[c];
              const text = typeof v === "number" ? (Number.isInteger(v) ? v : Number(v).toFixed(3)) : (v ?? "—");
              return `<td>${escapeHtml(text)}</td>`;
            }).join("");
            return `<tr>${tds}</tr>`;
          }).join("");
          previewBody.innerHTML = `
            <div class="pg-table-wrap">
              <table class="pg-table">
                <thead><tr>${head}</tr></thead>
                <tbody>${body}</tbody>
              </table>
            </div>
            <p class="pg-dim pg-mt-4" style="margin:0.75rem 0 0;font-size:0.8rem;">
              预览 ${preview.rows.length} / 共 ${formatNumber(preview.total)} 条 · 完整 ${FEATURE_COLUMNS.length} 维特征已写入内存
            </p>
          `;
        }
      }
    } catch (err) {
      showToast(err.message || "数据概览加载失败", "error");
    }
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const n_per_class = Number(nInput?.value || 800);
    const seed = Number(seedInput?.value || 42);
    const noise = Number(noiseInput?.value || 0.85);
    setLoading(genBtn, true);
    try {
      const res = await api("/api/data/generate", {
        method: "POST",
        body: JSON.stringify({ n_per_class, seed, noise }),
      });
      showToast(`已生成 ${formatNumber(res.total_samples || n_per_class * 4)} 条样本`, "success");
      await refresh();
    } catch (err) {
      showToast(err.message || "生成失败", "error");
    } finally {
      setLoading(genBtn, false);
    }
  });

  uploadInput?.addEventListener("change", async () => {
    const file = uploadInput.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await api("/api/data/upload", { method: "POST", body: fd });
      showToast(res.message || `上传成功，共 ${formatNumber(res.total_samples || 0)} 条`, "success");
      await refresh();
    } catch (err) {
      showToast(err.message || "上传失败", "error");
    } finally {
      uploadInput.value = "";
    }
  });

  await refresh();
}

/* ===================== Train ===================== */
async function initTrainPage() {
  const modelGrid = document.getElementById("train-model-grid");
  const trainBtn = document.getElementById("btn-train");
  const statusCard = document.getElementById("train-status-card");
  const metricsBody = document.getElementById("train-metrics-body");
  const selectDefaults = document.getElementById("btn-select-defaults");
  const selectAll = document.getElementById("btn-select-all");

  const defaultIds = ["random_forest", "xgboost", "lightgbm", "voting", "stacking"];

  if (modelGrid) {
    modelGrid.innerHTML = MODEL_CATALOG.map((m) => `
      <label class="pg-check-card">
        <input type="checkbox" name="model" value="${m.id}" ${defaultIds.includes(m.id) ? "checked" : ""} />
        <span class="pg-check-card-body">
          <span class="pg-check-card-title">${escapeHtml(m.label)}</span>
          <span class="pg-check-card-sub">${m.ensemble ? "集成学习" : "基学习器"}</span>
        </span>
        ${m.ensemble ? '<span class="pg-badge pg-badge-info">Ensemble</span>' : '<span class="pg-badge pg-badge-neutral">Base</span>'}
      </label>
    `).join("");
  }

  function selectedModels() {
    return Array.from(document.querySelectorAll('input[name="model"]:checked')).map((el) => el.value);
  }

  selectDefaults?.addEventListener("click", () => {
    document.querySelectorAll('input[name="model"]').forEach((el) => {
      el.checked = defaultIds.includes(el.value);
    });
  });
  selectAll?.addEventListener("click", () => {
    document.querySelectorAll('input[name="model"]').forEach((el) => {
      el.checked = true;
    });
  });

  async function renderTasks() {
    try {
      const [tasksResp, modelsResp] = await Promise.all([
        api("/api/train"),
        api("/api/models"),
      ]);
      const tasks = tasksResp.tasks || [];
      const latest = tasks[0];

      if (statusCard) {
        if (!latest) {
          statusCard.innerHTML = emptyHtml(
            '<path d="M12 3v6"/><rect x="4" y="11" width="16" height="9" rx="2"/>',
            "尚无训练任务",
            "勾选模型后点击「开始训练」。训练在后台线程执行，页面会轮询任务状态。"
          );
        } else {
          const st =
            latest.status === "success"
              ? '<span class="pg-badge pg-badge-success">训练成功</span>'
              : latest.status === "running"
                ? '<span class="pg-badge pg-badge-info">运行中</span>'
                : latest.status === "failed"
                  ? '<span class="pg-badge pg-badge-danger">失败</span>'
                  : `<span class="pg-badge pg-badge-neutral">${escapeHtml(latest.status)}</span>`;
          const progressVal = latest.progress == null ? (latest.status === "success" ? 1 : 0) : latest.progress;
          statusCard.innerHTML = `
            <div class="pg-status-grid">
              <div>
                <div class="pg-metric-label">任务 ID</div>
                <div class="pg-status-value"><code class="pg-code">${escapeHtml(latest.task_id)}</code></div>
              </div>
              <div>
                <div class="pg-metric-label">状态</div>
                <div class="pg-status-value">${st}</div>
              </div>
              <div>
                <div class="pg-metric-label">最优模型</div>
                <div class="pg-status-value">${escapeHtml(latest.best_model ? modelLabel(latest.best_model) : "—")}</div>
              </div>
              <div>
                <div class="pg-metric-label">进度</div>
                <div class="pg-status-value">${formatPercent(progressVal, 0)}</div>
              </div>
            </div>
            <div class="pg-mt-4" style="height:8px;background:rgba(148,163,184,0.2);border-radius:999px;overflow:hidden;">
              <div style="height:100%;width:${Math.max(2, Math.min(100, (progressVal || 0) * 100))}%;background:linear-gradient(90deg,#2563eb,#0ea5e9);transition:width .3s ease;"></div>
            </div>
            <p class="pg-dim" style="margin:0.9rem 0 0;font-size:0.8rem;">
              ${escapeHtml(latest.message || latest.error || "")}${latest.finished_at ? ` · 完成于 ${String(latest.finished_at).replace("T", " ").replace("+00:00", " UTC")}` : latest.status === "running" ? " · 后台训练中，请稍候…" : ""}
            </p>
          `;
        }
      }

      const models = modelsResp.models || [];
      if (metricsBody) {
        if (!models.length) {
          metricsBody.innerHTML = emptyHtml(
            '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5"/><path d="M12 16V8"/><path d="M16 16v-3"/>',
            "暂无指标",
            "训练完成后将展示 Accuracy / Precision / Recall / F1。"
          );
        } else {
          const rows = models.map((m) => `
            <tr>
              <td>
                <strong>${escapeHtml(modelLabel(m.name))}</strong>
                ${m.is_ensemble ? ' <span class="pg-badge pg-badge-info">集成</span>' : ""}
              </td>
              <td>${formatPercent(m.metrics?.accuracy)}</td>
              <td>${formatPercent(m.metrics?.precision)}</td>
              <td>${formatPercent(m.metrics?.recall)}</td>
              <td><strong>${formatPercent(m.metrics?.f1)}</strong></td>
              <td><span class="pg-badge pg-badge-success">${escapeHtml(m.status || "ready")}</span></td>
            </tr>
          `).join("");
          metricsBody.innerHTML = `
            <div class="pg-table-wrap">
              <table class="pg-table">
                <thead>
                  <tr>
                    <th>模型</th>
                    <th>Accuracy</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>状态</th>
                  </tr>
                </thead>
                <tbody>${rows}</tbody>
              </table>
            </div>
          `;
        }
      }
    } catch (err) {
      showToast(err.message || "训练状态加载失败", "error");
    }
  }

  async function pollTrainTask(taskId, { intervalMs = 1500, timeoutMs = 180000 } = {}) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      const task = await api(`/api/train/${taskId}`);
      await renderTasks();
      if (task.status === "success" || task.status === "failed") {
        return task;
      }
      await new Promise((r) => window.setTimeout(r, intervalMs));
    }
    throw new Error("训练超时（已超过 180s），请稍后在任务列表查看状态");
  }

  trainBtn?.addEventListener("click", async () => {
    const models = selectedModels();
    if (!models.length) {
      showToast("请至少选择一个模型", "warning");
      return;
    }
    setLoading(trainBtn, true);
    try {
      // Ensure data exists for nicer demo
      const summary = await api("/api/data/summary");
      if (!summary.total_samples) {
        await api("/api/data/generate", {
          method: "POST",
          body: JSON.stringify({ n_per_class: 200, seed: 42, noise: 0.85 }),
        });
        showToast("未检测到数据，已自动生成 200/类 样本", "info");
      }
      const res = await api("/api/train", {
        method: "POST",
        body: JSON.stringify({ models }),
      });
      const taskId = res.task_id;
      const initial = res.task || res;
      if (initial.status === "success") {
        showToast(`训练完成 · 最优 ${modelShort(initial.best_model || taskId)}`, "success");
        await renderTasks();
      } else if (initial.status === "failed") {
        showToast(initial.error || initial.message || "训练失败", "error");
        await renderTasks();
      } else {
        showToast(`训练已启动 · ${taskId}，后台运行中…`, "info");
        await renderTasks();
        const task = await pollTrainTask(taskId);
        if (task.status === "success") {
          showToast(`训练完成 · 最优 ${modelShort(task.best_model)}`, "success");
        } else {
          showToast(task.error || task.message || "训练失败", "error");
        }
        await renderTasks();
      }
    } catch (err) {
      showToast(err.message || "训练失败", "error");
    } finally {
      setLoading(trainBtn, false);
    }
  });

  await renderTasks();
}

/* ===================== Predict ===================== */
async function initPredictPage() {
  const form = document.getElementById("predict-single-form");
  const fieldsWrap = document.getElementById("predict-fields");
  const batchInput = document.getElementById("predict-batch");
  const singleBtn = document.getElementById("btn-predict-single");
  const batchBtn = document.getElementById("btn-predict-batch");
  const resultBody = document.getElementById("predict-result-body");
  const modelSelect = document.getElementById("predict-model");
  const warnBox = document.getElementById("predict-warn");

  // Build key fields
  if (fieldsWrap) {
    fieldsWrap.innerHTML = PREDICT_KEY_FIELDS.map((f) => `
      <div class="pg-field">
        <label class="pg-label" for="pf-${f.key}">${escapeHtml(f.label)}</label>
        <input class="pg-input" id="pf-${f.key}" name="${f.key}" type="number" step="${f.step}" value="${FEATURE_DEFAULTS[f.key]}" />
      </div>
    `).join("");
  }

  // Models select
  try {
    const modelsResp = await api("/api/models");
    const trained = modelsResp.models || [];
    const available = modelsResp.available || [];
    if (modelSelect) {
      if (trained.length) {
        modelSelect.innerHTML = trained
          .map((m) => `<option value="${escapeHtml(m.name)}">${escapeHtml(modelLabel(m.name))}</option>`)
          .join("");
      } else {
        modelSelect.innerHTML = available
          .map((m) => `<option value="${escapeHtml(m.name)}">${escapeHtml(modelLabel(m.name))}（未训练）</option>`)
          .join("");
      }
    }
    if (warnBox) {
      if (!trained.length) {
        warnBox.classList.remove("pg-hidden");
        warnBox.innerHTML = `
          <strong>尚未完成训练。</strong>
          请先到
          <a href="/train" style="color:#2563eb;text-decoration:underline;font-weight:600;">模型训练</a>
          页完成至少一次训练，再进行真实模型推理。
        `;
      } else {
        warnBox.classList.add("pg-hidden");
      }
    }
  } catch (err) {
    showToast(err.message || "模型列表加载失败", "error");
  }

  function buildSampleFromForm() {
    const sample = { ...FEATURE_DEFAULTS };
    PREDICT_KEY_FIELDS.forEach((f) => {
      const el = document.getElementById(`pf-${f.key}`);
      if (el && el.value !== "") sample[f.key] = Number(el.value);
    });
    return sample;
  }

  function renderPredictions(payload) {
    const preds = payload.predictions || [];
    if (!resultBody) return;
    if (!preds.length) {
      resultBody.innerHTML = emptyHtml(
        '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
        "暂无识别结果",
        "提交单条或批量样本后，将显示协议标签与置信度。"
      );
      return;
    }
    const cards = preds.map((p) => {
      const conf = p.confidence == null ? "不适用" : formatPercent(p.confidence);
      const probaEntries = Object.entries(p.probabilities || {})
        .sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `
          <div class="pg-proba-row">
            <span>${escapeHtml(LABEL_DISPLAY[k] || k)}</span>
            <div class="pg-proba-bar"><span style="width:${Math.max(4, (v || 0) * 100)}%"></span></div>
            <span class="pg-dim">${formatPercent(v)}</span>
          </div>
        `).join("");
      return `
        <div class="pg-result-card">
          <div class="pg-flex-between" style="gap:0.75rem;flex-wrap:wrap;">
            <div class="pg-flex pg-gap-2" style="align-items:center;">
              <span class="pg-dim" style="font-size:0.8rem;">#${p.index}</span>
              ${labelBadgeHtml(p.label, p.display_label)}
            </div>
            <div class="pg-flex pg-gap-2" style="align-items:center;">
              <span class="pg-badge pg-badge-neutral">置信度 ${escapeHtml(conf)}</span>
              <span class="pg-badge pg-badge-primary">${escapeHtml(modelShort(p.model || payload.model))}</span>
            </div>
          </div>
          <div class="pg-proba-list">${probaEntries}</div>
        </div>
      `;
    }).join("");
    resultBody.innerHTML = `
      <div class="pg-stack" style="gap:0.75rem;">
        <p class="pg-muted" style="margin:0;font-size:0.85rem;">
          共 ${preds.length} 条 · 模型 <strong>${escapeHtml(modelLabel(payload.model))}</strong>
          ${payload.mode === "mock" ? ' · <span class="pg-badge pg-badge-warning">Mock 推理</span>' : ""}
        </p>
        ${cards}
      </div>
    `;
  }

  async function runPredict(samples) {
    if (!samples.length) {
      showToast("样本不能为空", "warning");
      return;
    }
    const model = modelSelect?.value || undefined;
    const res = await api("/api/predict", {
      method: "POST",
      body: JSON.stringify({ samples, model }),
    });
    bumpPredictCount(samples.length);
    renderPredictions(res);
    showToast(`识别完成 · ${res.count} 条`, "success");
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    setLoading(singleBtn, true);
    try {
      await runPredict([buildSampleFromForm()]);
    } catch (err) {
      showToast(err.message || "识别失败", "error");
    } finally {
      setLoading(singleBtn, false);
    }
  });

  batchBtn?.addEventListener("click", async () => {
    const raw = (batchInput?.value || "").trim();
    if (!raw) {
      showToast("请粘贴 JSON 数组或 CSV 行", "warning");
      return;
    }
    setLoading(batchBtn, true);
    try {
      let samples = [];
      if (raw.startsWith("[")) {
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) throw new Error("JSON 须为对象数组");
        samples = parsed.map((row) => ({ ...FEATURE_DEFAULTS, ...row }));
      } else {
        // CSV: header optional; if no header, map key fields in order
        const lines = raw.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
        if (!lines.length) throw new Error("CSV 内容为空");
        const first = lines[0].split(",").map((s) => s.trim());
        const hasHeader = first.some((h) => FEATURE_COLUMNS.includes(h) || h === "label");
        if (hasHeader) {
          const headers = first;
          samples = lines.slice(1).map((line) => {
            const cells = line.split(",").map((s) => s.trim());
            const row = { ...FEATURE_DEFAULTS };
            headers.forEach((h, i) => {
              if (h === "label") return;
              const v = cells[i];
              if (v !== undefined && v !== "") row[h] = Number(v);
            });
            return row;
          });
        } else {
          samples = lines.map((line) => {
            const cells = line.split(",").map((s) => s.trim());
            const row = { ...FEATURE_DEFAULTS };
            PREDICT_KEY_FIELDS.forEach((f, i) => {
              if (cells[i] !== undefined && cells[i] !== "") row[f.key] = Number(cells[i]);
            });
            return row;
          });
        }
      }
      await runPredict(samples);
    } catch (err) {
      showToast(err.message || "批量解析/识别失败", "error");
    } finally {
      setLoading(batchBtn, false);
    }
  });

  // Initial empty result
  if (resultBody) {
    resultBody.innerHTML = emptyHtml(
      '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
      "等待识别",
      "填写关键流特征或粘贴批量样本，系统将返回协议类别与置信度。"
    );
  }
}

/* ===================== Experiments ===================== */
function syntheticConfusion(bestF1 = 0.92) {
  // 4x4 soft diagonal matrix that looks realistic
  const n = 100;
  const diag = Math.round(n * Math.min(0.97, Math.max(0.75, bestF1)));
  const off = n - diag;
  const matrix = LABEL_ORDER.map((rowLabel, i) =>
    LABEL_ORDER.map((colLabel, j) => {
      if (i === j) return diag;
      // distribute off-diagonal
      const share = Math.floor(off / 3);
      const rem = off - share * 3;
      const order = [0, 1, 2].filter((x) => x !== i);
      // map j to off-diag slot
      const offs = LABEL_ORDER.map((_, k) => k).filter((k) => k !== i);
      const idx = offs.indexOf(j);
      return idx === 0 ? share + rem : share;
    })
  );
  return matrix;
}

function syntheticFeatureImportance() {
  // Stable-ish ranking for demo charts
  const weights = {
    pkt_size_entropy: 0.14,
    packets_per_second: 0.12,
    iat_mean: 0.11,
    iat_burstiness: 0.1,
    byte_up_down_ratio: 0.09,
    pkt_len_mean: 0.08,
    iat_std: 0.07,
    duration: 0.06,
    uplink_pkt_ratio: 0.05,
    total_packets: 0.05,
    pkt_len_std: 0.04,
    iat_entropy: 0.03,
    pkt_len_max: 0.02,
    total_bytes: 0.02,
    pkt_len_p75: 0.01,
    pkt_len_p25: 0.005,
    pkt_len_min: 0.005,
  };
  return FEATURE_COLUMNS
    .map((f) => ({ feature: f, importance: weights[f] ?? 0.01 }))
    .sort((a, b) => b.importance - a.importance);
}

async function initExperimentsPage() {
  const tableBody = document.getElementById("exp-table-body");
  const cmBody = document.getElementById("exp-cm-body");
  const fiWrap = document.getElementById("exp-fi-wrap");
  const fiEmpty = document.getElementById("exp-fi-empty");
  const exportBtn = document.getElementById("btn-export-report");
  const emptyAll = document.getElementById("exp-empty");
  const content = document.getElementById("exp-content");

  async function load() {
    try {
      const data = await api("/api/experiments");
      const comparison = data.comparison || [];
      const experiments = data.experiments || [];

      if (!comparison.length) {
        content?.classList.add("pg-hidden");
        if (emptyAll) {
          emptyAll.classList.remove("pg-hidden");
          emptyAll.innerHTML = emptyHtml(
            '<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5"/><path d="M12 16V8"/><path d="M16 16v-3"/>',
            "暂无实验数据",
            "完成至少一次模型训练后，这里将展示对比表、混淆矩阵与特征重要性。",
            '<a href="/train" class="pg-btn pg-btn-primary pg-btn-sm">去训练</a>'
          );
        }
        return;
      }

      emptyAll?.classList.add("pg-hidden");
      content?.classList.remove("pg-hidden");

      if (tableBody) {
        const rows = comparison.map((row) => `
          <tr class="${row.is_best ? "pg-row-best" : ""}">
            <td>
              <strong>${escapeHtml(modelLabel(row.model))}</strong>
              ${row.is_best ? ' <span class="pg-badge pg-badge-success">最优</span>' : ""}
            </td>
            <td>${formatPercent(row.accuracy)}</td>
            <td>${formatPercent(row.precision)}</td>
            <td>${formatPercent(row.recall)}</td>
            <td><strong>${formatPercent(row.f1)}</strong></td>
          </tr>
        `).join("");
        tableBody.innerHTML = `
          <div class="pg-table-wrap">
            <table class="pg-table">
              <thead>
                <tr>
                  <th>模型</th>
                  <th>Accuracy</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
          <p class="pg-dim" style="margin:0.75rem 0 0;font-size:0.8rem;">
            基于最近一次实验（共 ${experiments.length} 次记录）· 真实训练指标
          </p>
        `;
      }

      const best = comparison.find((c) => c.is_best) || comparison[0];
      const report = data.report || {};
      const cmFromReport = best?.model && report.confusion_matrices
        ? report.confusion_matrices[best.model]
        : null;
      const matrix = Array.isArray(cmFromReport) ? cmFromReport : syntheticConfusion(best?.f1 || 0.92);
      const cmIsReal = Array.isArray(cmFromReport);
      if (cmBody) {
        const head = `<tr><th></th>${LABEL_ORDER.map((l) => `<th>${escapeHtml(LABEL_DISPLAY[l])}</th>`).join("")}</tr>`;
        const body = matrix.map((row, i) => {
          const cells = row.map((v) => {
            const intensity = v / (Math.max(...row, 1) || 1);
            const bg = `rgba(37,99,235,${0.06 + intensity * 0.42})`;
            return `<td class="pg-cm-cell" style="background:${bg}">${v}</td>`;
          }).join("");
          return `<tr><th>${escapeHtml(LABEL_DISPLAY[LABEL_ORDER[i]])}</th>${cells}</tr>`;
        }).join("");
        cmBody.innerHTML = `
          <div class="pg-table-wrap">
            <table class="pg-table pg-cm-table">
              <thead>${head}</thead>
              <tbody>${body}</tbody>
            </table>
          </div>
          <p class="pg-dim" style="margin:0.75rem 0 0;font-size:0.8rem;">
            行 = 真实标签 · 列 = 预测标签 · 基于最优模型 ${escapeHtml(modelShort(best?.model))}${cmIsReal ? " 的真实混淆矩阵" : " 的示意热力"}
          </p>
        `;
      }

      const fiFromReport = best?.model && report.feature_importances
        ? report.feature_importances[best.model]
        : null;
      let fi;
      if (fiFromReport && typeof fiFromReport === "object" && Object.keys(fiFromReport).length) {
        fi = Object.entries(fiFromReport)
          .map(([feature, importance]) => ({ feature, importance: Number(importance) || 0 }))
          .sort((a, b) => b.importance - a.importance)
          .slice(0, 10);
      } else {
        fi = syntheticFeatureImportance().slice(0, 10);
      }
      fiEmpty?.classList.add("pg-hidden");
      fiWrap?.classList.remove("pg-hidden");
      const canvas = document.getElementById("exp-fi-chart");
      if (canvas && typeof Chart !== "undefined") {
        destroyChart("exp-fi");
        _charts["exp-fi"] = new Chart(canvas, {
          type: "bar",
          data: {
            labels: fi.map((x) => x.feature),
            datasets: [{
              label: "重要性",
              data: fi.map((x) => Number((x.importance * 100).toFixed(2))),
              backgroundColor: "rgba(37,99,235,0.55)",
              borderColor: CHART_COLORS.violet,
              borderWidth: 1,
              borderRadius: 6,
              maxBarThickness: 22,
            }],
          },
          options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                callbacks: {
                  label: (ctx) => `重要性 ${ctx.parsed.x.toFixed(2)}%`,
                },
              },
            },
            scales: {
              x: {
                beginAtZero: true,
                ticks: { callback: (v) => `${v}%` },
              },
              y: { grid: { display: false } },
            },
          },
        });
      }
    } catch (err) {
      showToast(err.message || "实验数据加载失败", "error");
    }
  }

  exportBtn?.addEventListener("click", async () => {
    setLoading(exportBtn, true);
    try {
      const [meta, exp] = await Promise.all([
        api("/api/report/export"),
        api("/api/experiments"),
      ]);
      const report = {
        exported_at: new Date().toISOString(),
        meta,
        experiments: exp,
        note: "真实训练指标 + 报告清单（含 zip 路径）",
      };
      const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `proxyguard-report-${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      const zipNote = meta?.bundle?.zip_path ? " · 服务端已生成 zip" : "";
      showToast(`报告已下载（JSON）${zipNote}`, "success");
    } catch (err) {
      showToast(err.message || "导出失败", "error");
    } finally {
      setLoading(exportBtn, false);
    }
  });

  await load();
}

/* ===================== Settings ===================== */
async function initSettingsPage() {
  const form = document.getElementById("settings-form");
  const saveBtn = document.getElementById("btn-settings-save");
  const seed = document.getElementById("set-seed");
  const trainR = document.getElementById("set-train");
  const valR = document.getElementById("set-val");
  const testR = document.getElementById("set-test");
  const nPer = document.getElementById("set-n");
  const noise = document.getElementById("set-noise");
  const ratioHint = document.getElementById("set-ratio-hint");

  function updateRatioHint() {
    if (!ratioHint) return;
    const t = Number(trainR?.value || 0);
    const v = Number(valR?.value || 0);
    const te = Number(testR?.value || 0);
    const sum = t + v + te;
    const ok = Math.abs(sum - 1) < 0.001;
    ratioHint.textContent = `当前合计 ${sum.toFixed(2)}${ok ? " · 合法" : " · 建议合计为 1.00"}`;
    ratioHint.className = ok ? "pg-hint ok" : "pg-hint warn";
  }

  [trainR, valR, testR].forEach((el) => el?.addEventListener("input", updateRatioHint));

  try {
    const s = await api("/api/settings");
    if (seed) seed.value = s.random_seed ?? 42;
    if (trainR) trainR.value = s.train_ratio ?? 0.7;
    if (valR) valR.value = s.val_ratio ?? 0.15;
    if (testR) testR.value = s.test_ratio ?? 0.15;
    if (nPer) nPer.value = s.n_per_class_default ?? 1000;
    if (noise) noise.value = s.noise_default ?? 0.85;
    updateRatioHint();
  } catch (err) {
    showToast(err.message || "设置加载失败", "error");
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      random_seed: Number(seed?.value || 42),
      train_ratio: Number(trainR?.value || 0.7),
      val_ratio: Number(valR?.value || 0.15),
      test_ratio: Number(testR?.value || 0.15),
      n_per_class_default: Number(nPer?.value || 1000),
      noise_default: Number(noise?.value || 0.85),
    };
    const sum = payload.train_ratio + payload.val_ratio + payload.test_ratio;
    if (Math.abs(sum - 1) > 0.02) {
      showToast("划分比例合计应接近 1.0", "warning");
      return;
    }
    setLoading(saveBtn, true);
    try {
      await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showToast("设置已保存", "success");
      updateRatioHint();
    } catch (err) {
      showToast(err.message || "保存失败", "error");
    } finally {
      setLoading(saveBtn, false);
    }
  });
}

/* ===================== Boot ===================== */
function initPages() {
  chartDefaults();
  const page = document.querySelector("[data-page]")?.getAttribute("data-page");
  switch (page) {
    case "dashboard":
      return initDashboard();
    case "data":
      return initDataPage();
    case "train":
      return initTrainPage();
    case "predict":
      return initPredictPage();
    case "experiments":
      return initExperimentsPage();
    case "settings":
      return initSettingsPage();
    default:
      return undefined;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initShell();
  Promise.resolve(initPages()).catch((err) => {
    console.error(err);
    showToast(err.message || "页面初始化失败", "error");
  });
});

// Expose for inline page scripts / console debugging
window.api = api;
window.showToast = showToast;
window.setLoading = setLoading;
window.formatPercent = formatPercent;
window.formatNumber = formatNumber;
window.FEATURE_COLUMNS = FEATURE_COLUMNS;
window.MODEL_CATALOG = MODEL_CATALOG;
