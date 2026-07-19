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
  indigo: "#0f8f83",
  cyan: "#20b8bb",
  emerald: "#13865f",
  amber: "#d97706",
  rose: "#cf3f4d",
  blue: "#0e7490",
  violet: "#155e75",
  slate: "#82969e",
};

const CLASS_COLORS = {
  normal_https: "#0e7490",
  shadowsocks: "#0f8f83",
  trojan: "#f59e0b",
  vmess: "#13865f",
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
const MAX_PREDICT_BATCH = 500;

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
  el.setAttribute("role", type === "error" ? "alert" : "status");
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
  const palette = themePalette();
  Chart.defaults.color = palette.textMuted;
  Chart.defaults.borderColor = palette.grid;
  Chart.defaults.font.family = "Segoe UI, PingFang SC, Microsoft YaHei, system-ui, sans-serif";
  Chart.defaults.plugins.tooltip.backgroundColor = palette.tooltip;
  Chart.defaults.plugins.tooltip.titleColor = palette.text;
  Chart.defaults.plugins.tooltip.bodyColor = palette.textMuted;
  Chart.defaults.plugins.tooltip.borderColor = palette.border;
  Chart.defaults.plugins.tooltip.borderWidth = 1;
}

function cssVariable(name, fallback) {
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function themePalette() {
  return {
    text: cssVariable("--pg-text", "#102631"),
    textMuted: cssVariable("--pg-text-muted", "#56707a"),
    grid: cssVariable("--pg-chart-grid", "rgba(99,124,132,0.2)"),
    border: cssVariable("--pg-border", "rgba(99,124,132,0.22)"),
    surface: cssVariable("--pg-surface-solid", "#ffffff"),
    tooltip: cssVariable("--pg-chart-tooltip", "#102631"),
  };
}

function refreshChartTheme() {
  if (typeof Chart === "undefined") return;
  chartDefaults();
  const palette = themePalette();
  Object.entries(_charts).forEach(([key, chart]) => {
    if (!chart) return;
    chart.options.color = palette.textMuted;
    if (chart.options.plugins?.legend?.labels) {
      chart.options.plugins.legend.labels.color = palette.textMuted;
    }
    Object.values(chart.options.scales || {}).forEach((scale) => {
      scale.ticks = { ...(scale.ticks || {}), color: palette.textMuted };
      if (scale.grid?.display !== false) {
        scale.grid = { ...(scale.grid || {}), color: palette.grid };
      }
    });
    if (key === "data-dist" && chart.data.datasets?.[0]) {
      chart.data.datasets[0].borderColor = palette.surface;
    }
    chart.update("none");
  });
}

function initThemeControl() {
  const toggle = document.getElementById("pg-theme-toggle");
  const menu = document.getElementById("pg-theme-menu");
  const options = Array.from(menu?.querySelectorAll("[data-theme-option]") || []);
  if (!toggle || !menu || !options.length) return;

  const labels = {
    system: "跟随系统",
    light: "浅色模式",
    dark: "深色模式",
  };

  function currentPreference() {
    return window.pgTheme?.getPreference()
      || document.documentElement.dataset.themePreference
      || "system";
  }

  function syncThemeControl() {
    const preference = currentPreference();
    toggle.dataset.preference = preference;
    toggle.setAttribute("aria-label", `选择主题，当前${labels[preference] || labels.system}`);
    options.forEach((option) => {
      const selected = option.dataset.themeOption === preference;
      option.setAttribute("aria-checked", String(selected));
      option.tabIndex = selected ? 0 : -1;
    });
  }

  function positionMenu() {
    if (menu.classList.contains("pg-hidden")) return;
    const rect = toggle.getBoundingClientRect();
    const gutter = 10;
    const menuWidth = menu.offsetWidth;
    const menuHeight = menu.offsetHeight;
    const left = Math.min(
      Math.max(gutter, rect.right - menuWidth),
      window.innerWidth - menuWidth - gutter
    );
    const spaceBelow = window.innerHeight - rect.bottom;
    const top = spaceBelow >= menuHeight + gutter
      ? rect.bottom + 8
      : Math.max(gutter, rect.top - menuHeight - 8);
    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
  }

  function setMenuOpen(open, focusSelected = false) {
    menu.classList.toggle("pg-hidden", !open);
    toggle.setAttribute("aria-expanded", String(open));
    if (open) {
      syncThemeControl();
      positionMenu();
      if (focusSelected) {
        options.find((option) => option.getAttribute("aria-checked") === "true")?.focus();
      }
    }
  }

  toggle.addEventListener("click", () => {
    setMenuOpen(menu.classList.contains("pg-hidden"), false);
  });
  toggle.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setMenuOpen(true, true);
    }
  });

  options.forEach((option) => {
    option.addEventListener("click", () => {
      window.pgTheme?.setPreference(option.dataset.themeOption);
      syncThemeControl();
      setMenuOpen(false);
      toggle.focus();
    });
  });

  menu.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setMenuOpen(false);
      toggle.focus();
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const current = Math.max(0, options.indexOf(document.activeElement));
    let next = current;
    if (event.key === "ArrowDown") next = (current + 1) % options.length;
    if (event.key === "ArrowUp") next = (current - 1 + options.length) % options.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = options.length - 1;
    options[next].focus();
  });

  document.addEventListener("pointerdown", (event) => {
    if (!menu.classList.contains("pg-hidden")
      && !menu.contains(event.target)
      && !toggle.contains(event.target)) {
      setMenuOpen(false);
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !menu.classList.contains("pg-hidden")) {
      event.preventDefault();
      setMenuOpen(false);
      toggle.focus();
    }
  });
  window.addEventListener("resize", positionMenu);
  window.addEventListener("scroll", positionMenu, true);
  window.addEventListener("pg:themechange", () => {
    syncThemeControl();
    refreshChartTheme();
  });

  syncThemeControl();
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
  initThemeControl();
  const sidebar = document.getElementById("pg-sidebar");
  const overlay = document.getElementById("pg-overlay");
  const toggle = document.getElementById("pg-mobile-toggle");
  const mobileNavMedia = window.matchMedia("(max-width: 960px)");

  function syncSidebarAccessibility(open) {
    const hidden = mobileNavMedia.matches && !open;
    sidebar?.toggleAttribute("inert", hidden);
    sidebar?.setAttribute("aria-hidden", String(hidden));
  }

  function setSidebar(open) {
    sidebar?.classList.toggle("open", open);
    overlay?.classList.toggle("open", open);
    overlay?.setAttribute("aria-hidden", String(!open));
    toggle?.setAttribute("aria-expanded", String(open));
    toggle?.setAttribute("aria-label", open ? "关闭导航" : "打开导航");
    document.body.classList.toggle("pg-nav-open", open);
    syncSidebarAccessibility(open);
  }

  toggle?.addEventListener("click", () => {
    setSidebar(!sidebar?.classList.contains("open"));
  });
  overlay?.addEventListener("click", () => setSidebar(false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && sidebar?.classList.contains("open")) {
      setSidebar(false);
      toggle?.focus();
    }
  });
  mobileNavMedia.addEventListener("change", () => {
    setSidebar(false);
  });
  syncSidebarAccessibility(false);

  // One real health probe updates the consistent status component on every page.
  const healthPills = Array.from(document.querySelectorAll(".js-health-pill"));
  api("/api/health")
    .then((h) => {
      healthPills.forEach((pill) => {
        const healthText = pill.querySelector(".js-health-text");
        const healthDot = pill.querySelector(".js-health-dot");
        const bits = ["服务在线"];
        if (h.use_mock) bits.push("MOCK");
        if (h.auth_required) bits.push("需Token");
        if (healthText) healthText.textContent = bits.join(" · ");
        if (healthDot) healthDot.style.background = h.use_mock
          ? "#f59e0b"
          : h.auth_required
            ? "#0e7490"
            : "#1cad7b";
        pill.dataset.state = h.use_mock ? "warning" : "online";
        pill.setAttribute("aria-label", bits.join("，"));
      });
    })
    .catch(() => {
      healthPills.forEach((pill) => {
        const healthText = pill.querySelector(".js-health-text");
        const healthDot = pill.querySelector(".js-health-dot");
        if (healthText) healthText.textContent = "服务离线";
        if (healthDot) healthDot.style.background = "#dc3545";
        pill.dataset.state = "offline";
        pill.setAttribute("aria-label", "服务离线");
      });
    });
}

async function waitUntilDocumentVisible() {
  if (!document.hidden) return;
  await new Promise((resolve) => {
    const onVisibility = () => {
      if (document.hidden) return;
      document.removeEventListener("visibilitychange", onVisibility);
      resolve();
    };
    document.addEventListener("visibilitychange", onVisibility);
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
        if (typeof Chart === "undefined") {
          chartWrap.classList.add("pg-hidden");
          if (chartEmpty) {
            chartEmpty.classList.remove("pg-hidden");
            chartEmpty.innerHTML = emptyHtml(
              '<path d="M4 19V5"/><path d="M4 19h16"/>',
              "图表组件未加载",
              "模型指标仍可在训练和实验页面查看，请检查网络后刷新。"
            );
          }
        } else {
          chartEmpty?.classList.add("pg-hidden");
          chartWrap.classList.remove("pg-hidden");
        }
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
                  m.is_ensemble ? "rgba(19,134,95,0.72)" : "rgba(15,143,131,0.72)"
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
                <td class="pg-dim pg-nowrap">${escapeHtml((t.finished_at || t.created_at || "").replace("T", " ").replace("+00:00", " UTC"))}</td>
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
  const paperBtn = document.getElementById("btn-paper-params");
  const uploadInput = document.getElementById("data-upload");
  const summaryBadge = document.getElementById("data-summary-badge");
  const metaLine = document.getElementById("data-meta-line");
  const chartEmpty = document.getElementById("data-dist-empty");
  const chartWrap = document.getElementById("data-dist-wrap");
  const previewBody = document.getElementById("data-preview-body");
  const nInput = document.getElementById("gen-n");
  const seedInput = document.getElementById("gen-seed");
  const noiseInput = document.getElementById("gen-noise");

  const PAPER = { n_per_class: 800, seed: 42, noise: 0.85 };

  function fillPaperParams() {
    if (nInput) nInput.value = PAPER.n_per_class;
    if (seedInput) seedInput.value = PAPER.seed;
    if (noiseInput) noiseInput.value = PAPER.noise;
  }

  paperBtn?.addEventListener("click", () => {
    fillPaperParams();
    showToast("已填入论文参数：800 / 42 / 0.85", "success");
  });

  // 默认用论文参数；若设置页有值则覆盖（但 n 太小时提醒）
  fillPaperParams();
  try {
    const settings = await api("/api/settings");
    if (seedInput && settings.random_seed != null) seedInput.value = settings.random_seed;
    if (noiseInput && settings.noise_default != null) noiseInput.value = settings.noise_default;
    if (nInput && settings.n_per_class_default != null) {
      const n = Number(settings.n_per_class_default);
      // 设置里若是演示用的小 n，仍优先论文 800，避免训成玩具集
      nInput.value = n >= 500 ? n : PAPER.n_per_class;
    }
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
        if (typeof Chart === "undefined") {
          chartWrap?.classList.add("pg-hidden");
          if (chartEmpty) {
            chartEmpty.classList.remove("pg-hidden");
            chartEmpty.innerHTML = emptyHtml(
              '<circle cx="12" cy="12" r="8"/>',
              "图表组件未加载",
              "类别数据已就绪，请检查网络后刷新图表。"
            );
          }
        } else {
          chartEmpty?.classList.add("pg-hidden");
          chartWrap?.classList.remove("pg-hidden");
        }
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
                borderColor: themePalette().surface,
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
  const trainBtnBottom = document.getElementById("btn-train-bottom");
  const cancelBtn = document.getElementById("btn-cancel-train");
  const statusCard = document.getElementById("train-status-card");
  const metricsBody = document.getElementById("train-metrics-body");
  const selectDefaults = document.getElementById("btn-select-defaults");
  const selectAll = document.getElementById("btn-select-all");

  // 答辩推荐：快、够对比（不含 stacking）
  const defaultIds = ["random_forest", "xgboost", "voting"];
  let activeTaskId = null;

  if (modelGrid) {
    modelGrid.innerHTML = MODEL_CATALOG.map((m) => {
      const slow = m.id === "stacking" || m.id === "svm";
      return `
      <label class="pg-check-card">
        <input type="checkbox" name="model" value="${m.id}" ${defaultIds.includes(m.id) ? "checked" : ""} />
        <span class="pg-check-card-body">
          <span class="pg-check-card-title">${escapeHtml(m.label)}</span>
          <span class="pg-check-card-sub">${m.ensemble ? "集成" : "基学习器"}${slow ? " · 可能较慢" : ""}</span>
        </span>
        ${m.ensemble ? '<span class="pg-badge pg-badge-info">集成</span>' : '<span class="pg-badge pg-badge-neutral">基模型</span>'}
      </label>`;
    }).join("");
  }

  function selectedModels() {
    return Array.from(document.querySelectorAll('input[name="model"]:checked')).map((el) => el.value);
  }

  function setTrainBusy(busy) {
    [trainBtn, trainBtnBottom].forEach((b) => {
      if (!b) return;
      b.disabled = !!busy;
    });
    if (cancelBtn) cancelBtn.disabled = !busy && !activeTaskId;
  }

  selectDefaults?.addEventListener("click", () => {
    document.querySelectorAll('input[name="model"]').forEach((el) => {
      el.checked = defaultIds.includes(el.value);
    });
    showToast("已选答辩推荐：RF + XGBoost + Voting", "info");
  });
  selectAll?.addEventListener("click", () => {
    document.querySelectorAll('input[name="model"]').forEach((el) => {
      el.checked = true;
    });
    showToast("已全选（含 Stacking，可能较慢）", "warning");
  });

  cancelBtn?.addEventListener("click", async () => {
    if (!activeTaskId) {
      showToast("没有进行中的任务", "warning");
      return;
    }
    try {
      await api(`/api/train/${activeTaskId}/cancel`, { method: "POST", body: "{}" });
      showToast("已请求取消，当前模型结束后停止", "info");
      await renderTasks();
    } catch (err) {
      showToast(err.message || "取消失败", "error");
    }
  });

  async function renderTasks() {
    try {
      const [tasksResp, modelsResp] = await Promise.all([
        api("/api/train"),
        api("/api/models"),
      ]);
      const tasks = tasksResp.tasks || [];
      const latest = tasks[0];

      if (latest && latest.status === "running") {
        activeTaskId = latest.task_id;
        if (cancelBtn) cancelBtn.disabled = false;
      } else if (latest && latest.status !== "running") {
        if (activeTaskId === latest.task_id) activeTaskId = null;
        if (cancelBtn) cancelBtn.disabled = true;
      }

      if (statusCard) {
        if (!latest) {
          statusCard.innerHTML = emptyHtml(
            '<path d="M12 3v6"/><rect x="4" y="11" width="16" height="9" rx="2"/>',
            "尚无训练任务",
            "建议先确认数据约每类 800，再勾选模型开始训练。"
          );
        } else {
          const stMap = {
            success: '<span class="pg-badge pg-badge-success">成功</span>',
            running: '<span class="pg-badge pg-badge-info">运行中</span>',
            failed: '<span class="pg-badge pg-badge-danger">失败</span>',
            cancelled: '<span class="pg-badge pg-badge-warning">已取消</span>',
          };
          const st = stMap[latest.status]
            || `<span class="pg-badge pg-badge-neutral">${escapeHtml(latest.status)}</span>`;
          const progressVal = latest.progress == null
            ? (latest.status === "success" || latest.status === "cancelled" ? 1 : 0)
            : latest.progress;
          const modelCount = (latest.models || []).length;
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
              <div style="height:100%;width:${Math.max(2, Math.min(100, (progressVal || 0) * 100))}%;background:linear-gradient(90deg,#0f8f83,#20b8bb);transition:width .3s ease;"></div>
            </div>
            <p class="pg-dim" style="margin:0.9rem 0 0;font-size:0.8rem;">
              ${escapeHtml(latest.message || latest.error || "")}
              ${modelCount ? ` · 共 ${modelCount} 个模型` : ""}
              ${latest.finished_at ? ` · 结束于 ${String(latest.finished_at).replace("T", " ").replace("+00:00", "")}` : ""}
              ${latest.status === "running" ? " · 请稍候，Stacking 会慢一些" : ""}
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

  async function pollTrainTask(taskId, { intervalMs = 1200, timeoutMs = 600000 } = {}) {
    const started = Date.now();
    while (Date.now() - started < timeoutMs) {
      await waitUntilDocumentVisible();
      const task = await api(`/api/train/${taskId}`);
      await renderTasks();
      if (["success", "failed", "cancelled"].includes(task.status)) {
        return task;
      }
      await new Promise((r) => window.setTimeout(r, intervalMs));
    }
    throw new Error("训练等待超时，请稍后在本页查看任务状态");
  }

  async function startTrain() {
    const models = selectedModels();
    if (!models.length) {
      showToast("请至少选择一个模型", "warning");
      return;
    }
    if (models.includes("stacking") && models.length > 4) {
      showToast("含 Stacking 且模型较多，可能要几分钟", "warning");
    }
    setTrainBusy(true);
    setLoading(trainBtn, true);
    try {
      const summary = await api("/api/data/summary");
      if (!summary.total_samples) {
        await api("/api/data/generate", {
          method: "POST",
          body: JSON.stringify({ n_per_class: 800, seed: 42, noise: 0.85 }),
        });
        showToast("没有数据，已按论文参数生成 800/类", "info");
      } else if ((summary.n_per_class || 0) > 0 && summary.n_per_class < 500) {
        showToast(
          `当前每类约 ${summary.n_per_class} 条，论文建议 800。可先回数据页重新生成。`,
          "warning"
        );
      }
      const res = await api("/api/train", {
        method: "POST",
        body: JSON.stringify({ models }),
      });
      const taskId = res.task_id;
      activeTaskId = taskId;
      if (cancelBtn) cancelBtn.disabled = false;
      const initial = res.task || res;
      if (initial.status === "success") {
        showToast(`训练完成 · 最优 ${modelShort(initial.best_model || taskId)}`, "success");
        await renderTasks();
      } else if (initial.status === "failed") {
        showToast(initial.error || initial.message || "训练失败", "error");
        await renderTasks();
      } else {
        showToast(`训练已启动 · ${taskId}`, "info");
        await renderTasks();
        const task = await pollTrainTask(taskId);
        if (task.status === "success") {
          showToast(`训练完成 · 最优 ${modelShort(task.best_model)}`, "success");
        } else if (task.status === "cancelled") {
          showToast("训练已取消", "warning");
        } else {
          showToast(task.error || task.message || "训练失败", "error");
        }
        await renderTasks();
      }
    } catch (err) {
      showToast(err.message || "训练失败", "error");
    } finally {
      setTrainBusy(false);
      activeTaskId = null;
      if (cancelBtn) cancelBtn.disabled = true;
      setLoading(trainBtn, false);
      setLoading(trainBtnBottom, false);
    }
  }

  trainBtn?.addEventListener("click", startTrain);
  trainBtnBottom?.addEventListener("click", startTrain);

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
        <input class="pg-input" id="pf-${f.key}" name="${f.key}" type="number" step="${f.step}" value="${FEATURE_DEFAULTS[f.key]}" inputmode="decimal" required />
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
          <a href="/train" style="color:#08746c;text-decoration:underline;font-weight:600;">模型训练</a>
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

  function normalizeSample(sample, index) {
    if (!sample || typeof sample !== "object" || Array.isArray(sample)) {
      throw new Error(`第 ${index + 1} 条样本必须是对象`);
    }
    const row = { ...FEATURE_DEFAULTS, ...sample };
    FEATURE_COLUMNS.forEach((column) => {
      const rawValue = row[column];
      if (rawValue === null || typeof rawValue === "boolean") {
        throw new Error(`第 ${index + 1} 条的 ${column} 必须是数值`);
      }
      const value = Number(rawValue);
      if (!Number.isFinite(value)) {
        throw new Error(`第 ${index + 1} 条的 ${column} 必须是有限数值`);
      }
      row[column] = value;
    });
    return row;
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
      const probabilityPairs = Object.entries(p.probabilities || {})
        .filter(([, value]) => Number.isFinite(Number(value)));
      const probaEntries = probabilityPairs
        .sort((a, b) => b[1] - a[1])
        .map(([k, rawValue]) => {
          const v = Math.max(0, Math.min(1, Number(rawValue)));
          return `
          <div class="pg-proba-row">
            <span>${escapeHtml(LABEL_DISPLAY[k] || k)}</span>
            <div class="pg-proba-bar"><span style="width:${v * 100}%"></span></div>
            <span class="pg-dim">${formatPercent(v)}</span>
          </div>
        `;
        }).join("");
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
          ${probaEntries
            ? `<div class="pg-proba-list">${probaEntries}</div>`
            : '<p class="pg-dim pg-result-note">当前模型不提供类别概率。</p>'}
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
    if (samples.length > MAX_PREDICT_BATCH) {
      showToast(`单次最多提交 ${MAX_PREDICT_BATCH} 条样本`, "warning");
      return;
    }
    const normalizedSamples = samples.map(normalizeSample);
    const model = modelSelect?.value || undefined;
    const res = await api("/api/predict", {
      method: "POST",
      body: JSON.stringify({ samples: normalizedSamples, model }),
    });
    bumpPredictCount(normalizedSamples.length);
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
      if (samples.length > MAX_PREDICT_BATCH) {
        throw new Error(`单次最多提交 ${MAX_PREDICT_BATCH} 条样本`);
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
            "还没有实验结果",
            "请先在数据页生成约每类 800 条样本，再到训练页完成一次训练。这里会显示指标对比；混淆矩阵和特征重要性来自真实训练结果，不会用假图凑数。",
            '<a href="/data" class="pg-btn pg-btn-secondary pg-btn-sm">去数据页</a> <a href="/train" class="pg-btn pg-btn-primary pg-btn-sm">去训练</a>'
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

      if (cmBody) {
        if (Array.isArray(cmFromReport)) {
          const matrix = cmFromReport;
          const head = `<tr><th></th>${LABEL_ORDER.map((l) => `<th>${escapeHtml(LABEL_DISPLAY[l])}</th>`).join("")}</tr>`;
          const body = matrix.map((row, i) => {
            const cells = row.map((v) => {
              const intensity = v / (Math.max(...row, 1) || 1);
              const bg = `rgba(15,143,131,${0.06 + intensity * 0.42})`;
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
              行=真实 · 列=预测 · 模型 ${escapeHtml(modelShort(best?.model))}
            </p>
          `;
        } else {
          cmBody.innerHTML = emptyHtml(
            '<path d="M4 19V5"/><path d="M4 19h16"/>',
            "暂无混淆矩阵",
            "重新训练一次后，这里会显示最优模型的真实混淆矩阵（不再使用示意假图）。",
            '<a href="/train" class="pg-btn pg-btn-primary pg-btn-sm">去训练</a>'
          );
        }
      }

      const fiFromReport = best?.model && report.feature_importances
        ? report.feature_importances[best.model]
        : null;
      // 若最优模型没有重要性（如 SVM），尝试其它带 FI 的模型
      let fiSource = fiFromReport;
      if (!fiSource || !Object.keys(fiSource).length) {
        const allFi = report.feature_importances || {};
        for (const key of ["random_forest", "xgboost", "lightgbm", "decision_tree", "adaboost"]) {
          if (allFi[key] && Object.keys(allFi[key]).length) {
            fiSource = allFi[key];
            break;
          }
        }
      }

      if (fiSource && typeof fiSource === "object" && Object.keys(fiSource).length) {
        const fi = Object.entries(fiSource)
          .map(([feature, importance]) => ({ feature, importance: Number(importance) || 0 }))
          .sort((a, b) => b.importance - a.importance)
          .slice(0, 10);
        if (typeof Chart === "undefined") {
          fiWrap?.classList.add("pg-hidden");
          if (fiEmpty) {
            fiEmpty.classList.remove("pg-hidden");
            fiEmpty.innerHTML = emptyHtml(
              '<path d="M4 19V5"/><path d="M4 19h16"/>',
              "图表组件未加载",
              "特征重要性数据已就绪，请检查网络后刷新。"
            );
          }
        } else {
          fiEmpty?.classList.add("pg-hidden");
          fiWrap?.classList.remove("pg-hidden");
        }
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
                backgroundColor: "rgba(15,143,131,0.55)",
                borderColor: CHART_COLORS.blue,
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
      } else {
        fiWrap?.classList.add("pg-hidden");
        if (fiEmpty) {
          fiEmpty.classList.remove("pg-hidden");
          fiEmpty.innerHTML = emptyHtml(
            '<path d="M4 19V5"/><path d="M4 19h16"/>',
            "暂无特征重要性",
            "树模型（RF/XGB 等）训练后会有重要性；仅 SVM/集成时可能没有。",
            ""
          );
        }
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
    if (nPer) nPer.value = s.n_per_class_default ?? 800;
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
      n_per_class_default: Number(nPer?.value || 800),
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
