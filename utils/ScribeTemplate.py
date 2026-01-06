from jinja2 import Template

html_template = Template(r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>🦋 MetaMorph Report — {{ dataset_id }}</title>
  <style>
    :root{
      --bg:#0b1020;
      --panel:#0f1733;
      --panel2:#0c132b;
      --text:#e9ecf5;
      --muted:#aab3cf;
      --border:rgba(255,255,255,.10);
      --good:#23c55e;
      --bad:#ef4444;
      --warn:#f59e0b;
      --chip:#101a3a;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji";
      --shadow: 0 10px 30px rgba(0,0,0,.35);

      /* metamorph vibe accents */
      --glow1: rgba(124,58,237,.18);
      --glow2: rgba(59,130,246,.14);
      --glow3: rgba(34,197,94,.12);
    }
    *{ box-sizing:border-box; }
    body{
      margin:0;
      font-family:var(--sans);
      background:
        radial-gradient(1000px 800px at 20% -10%, var(--glow2), transparent 60%),
        radial-gradient(900px 700px at 90% 10%, var(--glow1), transparent 55%),
        radial-gradient(800px 650px at 60% 120%, var(--glow3), transparent 55%),
        var(--bg);
      color:var(--text);
      line-height:1.4;
    }
    a{ color:#93c5fd; text-decoration:none; }
    a:hover{ text-decoration:underline; }

    .wrap{ max-width:1100px; margin:0 auto; padding:28px 18px 60px; }

    .header{
      position: sticky;
      top:0;
      z-index:10;
      backdrop-filter: blur(10px);
      background: linear-gradient(to bottom, rgba(11,16,32,.92), rgba(11,16,32,.65));
      border-bottom:1px solid var(--border);
      margin:0 -18px 18px;
      padding:18px 18px 16px;
    }
    .titlebar{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:12px;
    }
    .title{
      display:flex;
      flex-wrap:wrap;
      align-items:baseline;
      gap:10px;
      margin:0 0 8px;
    }
    h1{
      margin:0;
      font-size:20px;
      letter-spacing:.2px;
      font-weight:800;
    }
    .sub{
      font-size:12px;
      color:var(--muted);
      font-family:var(--mono);
    }

    /* toggle for timestamps */
    .toggles{
      display:flex;
      align-items:center;
      gap:10px;
      margin-top:2px;
      color:var(--muted);
      font-size:12px;
      font-family:var(--mono);
      white-space:nowrap;
    }
    .switch{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:6px 10px;
      border:1px solid var(--border);
      border-radius:999px;
      background:rgba(255,255,255,.04);
      cursor:pointer;
      user-select:none;
    }
    .switch input{ display:none; }
    .knob{
      width:34px;
      height:18px;
      border-radius:999px;
      border:1px solid var(--border);
      background:rgba(255,255,255,.06);
      position:relative;
      box-shadow: inset 0 1px 0 rgba(255,255,255,.04);
    }
    .knob:after{
      content:"";
      position:absolute;
      top:2px;
      left:2px;
      width:14px;
      height:14px;
      border-radius:50%;
      background:rgba(255,255,255,.70);
      transition:transform .18s ease;
    }
    .switch input:checked + .knob:after{
      transform: translateX(16px);
    }

    .summary{
      display:grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap:10px;
      margin-top:10px;
    }
    @media (max-width: 820px){
      .summary{ grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    .kpi{
      background:rgba(255,255,255,.04);
      border:1px solid var(--border);
      border-radius:14px;
      padding:10px 12px;
      box-shadow: 0 1px 0 rgba(255,255,255,.03) inset;
    }
    .kpi .label{ font-size:11px; color:var(--muted); }
    .kpi .value{ font-size:14px; margin-top:4px; font-family:var(--mono); }

    .chips{
      display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;
    }
    .chip{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:6px 10px;
      background:var(--chip);
      border:1px solid var(--border);
      border-radius:999px;
      font-size:12px;
      color:var(--muted);
      font-family:var(--mono);
    }
    .dot{ width:8px; height:8px; border-radius:50%; background:var(--muted); }
    .dot.good{ background:var(--good); }
    .dot.bad{ background:var(--bad); }

    .grid{
      display:grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap:14px;
      margin-top:18px;
    }
    @media (max-width: 920px){
      .grid{ grid-template-columns: 1fr; }
    }

    .card{
      background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02));
      border:1px solid var(--border);
      border-radius:18px;
      padding:14px 14px 12px;
      box-shadow:var(--shadow);
      overflow:hidden;
      position:relative;
    }
    /* subtle "cocoon thread" accent */
    .card:before{
      content:"";
      position:absolute;
      inset:0;
      pointer-events:none;
      background:
        linear-gradient(135deg, rgba(255,255,255,.06), transparent 40%),
        repeating-linear-gradient(90deg, rgba(255,255,255,.03), rgba(255,255,255,.03) 1px, transparent 1px, transparent 18px);
      opacity:.12;
      mask-image: radial-gradient(500px 240px at 20% 0%, black, transparent 70%);
    }

    .cardhead{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:12px;
      margin-bottom:10px;
      position:relative;
    }
    .colname{
      font-size:15px;
      font-weight:800;
      margin:0;
      word-break:break-word;
    }
    .badge{
      display:inline-flex;
      align-items:center;
      gap:8px;
      padding:6px 10px;
      border-radius:999px;
      border:1px solid var(--border);
      background:rgba(255,255,255,.04);
      font-size:12px;
      font-family:var(--mono);
      white-space:nowrap;
      color:var(--muted);
    }
    .badge.good{ color: #bbf7d0; border-color: rgba(34,197,94,.35); background: rgba(34,197,94,.08); }
    .badge.bad{ color: #fecaca; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.08); }

    .meta{
      display:flex;
      flex-wrap:wrap;
      gap:10px;
      margin: 8px 0 12px;
      color:var(--muted);
      font-size:12px;
      font-family:var(--mono);
      position:relative;
    }
    .meta b{ color:var(--text); font-weight:700; }

    details{
      border-top:1px dashed rgba(255,255,255,.12);
      padding-top:10px;
      margin-top:10px;
    }
    summary{
      cursor:pointer;
      list-style:none;
      user-select:none;
      font-size:12px;
      color:var(--muted);
      font-family:var(--mono);
      display:flex;
      align-items:center;
      gap:10px;
    }
    summary::-webkit-details-marker{ display:none; }
    summary:before{
      content:"▸";
      display:inline-block;
      transform: translateY(-1px);
      opacity:.9;
    }
    details[open] summary:before{ content:"▾"; }

    .row{
      display:grid;
      grid-template-columns: 160px 1fr;
      gap:10px;
      margin-top:10px;
      align-items:start;
      position:relative;
    }
    @media (max-width: 560px){
      .row{ grid-template-columns: 1fr; }
    }

    table{
      width:100%;
      border-collapse:collapse;
      overflow:hidden;
      border-radius:14px;
      border:1px solid var(--border);
      background:rgba(0,0,0,.12);
      font-size:12px;
    }
    th, td{
      padding:8px 10px;
      border-bottom:1px solid rgba(255,255,255,.08);
      vertical-align:top;
      word-break:break-word;
    }
    th{
      text-align:left;
      color:var(--muted);
      font-family:var(--mono);
      font-weight:700;
      background:rgba(255,255,255,.03);
    }
    tr:last-child td{ border-bottom:none; }

    .code{
      font-family:var(--mono);
      background: rgba(0,0,0,.20);
      border:1px solid rgba(255,255,255,.10);
      border-radius:14px;
      padding:10px 12px;
      overflow:auto;
      white-space:pre-wrap;
      word-break:break-word;
      font-size:12px;
      color:#f3f4f6;
      line-height:1.45;
    }

    .muted{ color:var(--muted); }
    .small{ font-size:12px; }
    .preview{
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      margin-top:6px;
    }
    .pill{
      font-family:var(--mono);
      font-size:12px;
      padding:4px 8px;
      border-radius:999px;
      border:1px solid rgba(255,255,255,.12);
      background:rgba(255,255,255,.04);
      color:var(--text);
      max-width:100%;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }

    /* agents breadcrumb tokens */
    .agents-line{
      display:flex;
      flex-wrap:wrap;
      align-items:center;
      gap:6px;
      font-family:var(--mono);
      font-size:12px;
    }
    .agent{
      display:inline-flex;
      align-items:center;
      gap:6px;
      padding:4px 8px;
      border-radius:999px;
      border:1px solid rgba(255,255,255,.10);
      background: rgba(0,0,0,.18);
      color:#e9ecf5;
      max-width:100%;
      overflow:hidden;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .arrow{
      color:rgba(255,255,255,.22);
      font-family:var(--mono);
      padding:0 2px;
    }

    .footer{
      margin-top:20px;
      color:var(--muted);
      font-size:12px;
      font-family:var(--mono);
      text-align:center;
      opacity:.9;
    }
  </style>
</head>

<body>
  <div class="wrap">

    <div class="header">
      <div class="titlebar">
        <div>
          <div class="title">
            <h1>🦋 MetaMorph Report</h1>
            <div class="sub">dataset_id={{ dataset_id }}</div>
          </div>
          <div class="sub">🐛 → 🧵🕸️ → 🦋 &nbsp;&nbsp;|&nbsp;&nbsp; “From raw columns to transformed structure”</div>
        </div>

        <div class="toggles">
          <label class="switch" title="Toggle timestamps in the Agents breadcrumb (node@timestamp)">
            <input id="toggle-ts" type="checkbox" />
            <span class="knob"></span>
            <span>show timestamps</span>
          </label>
        </div>
      </div>

      <div class="summary">
        <div class="kpi">
          <div class="label">🥚 Started (UTC)</div>
          <div class="value">{{ started_at }}</div>
        </div>
        <div class="kpi">
          <div class="label">🦋 Finished (UTC)</div>
          <div class="value">{{ finished_at }}</div>
        </div>
        <div class="kpi">
          <div class="label">✅ Success</div>
          <div class="value">{{ n_success }}</div>
        </div>
        <div class="kpi">
          <div class="label">⚠️ Failed</div>
          <div class="value">{{ n_failed }}</div>
        </div>
      </div>

      <div class="chips">
        <span class="chip"><span class="dot good"></span>✅ SUCCESS</span>
        <span class="chip"><span class="dot bad"></span>❌ FAILED</span>
        <span class="chip">🧬 columns={{ colData|length }}</span>
      </div>
    </div>

    <div class="grid">
    {% for col, d in colData.items() %}
      {% set ok = (not d.error) %}
      {% set conf = (d.confidence if d.confidence is not none else 0) %}
      {% set node_dict = d.trackerInfo.node_path.get(col, {}) if d.trackerInfo and d.trackerInfo.node_path else {} %}
      {% set names = d.ColNames.get(col, []) if d.ColNames else [] %}
      {% set tv = d.TransformedValues or [] %}
      {% set n_cols = tv|length %}
      {% set n_rows = (tv[0]|length) if n_cols > 0 else 0 %}

      <section class="card">
        <div class="cardhead">
          <h2 class="colname">🌱 {{ col }}</h2>
          <span class="badge {{ 'good' if ok else 'bad' }}">
            <span class="dot {{ 'good' if ok else 'bad' }}"></span>
            {{ "✅ SUCCESS" if ok else "❌ FAILED" }}
          </span>
        </div>

        <div class="meta">
          <div><b>confidence</b>={{ "%.2f"|format(conf) }}</div>
          <div><b>shape</b>={{ n_rows }}×{{ n_cols }}</div>
          <div><b>mapped_cols</b>={{ names|length }}</div>
        </div>

        <div class="row">
          <div class="muted small"><b>🧵 Agents</b></div>
          <div class="small">
            {% if d.trackerInfo and d.trackerInfo.events_path %}
              <div class="agents-line">
                {% for e in d.trackerInfo.events_path %}
                  {% set parts = e.split('@', 1) %}
                  {% set node_name = parts[0] %}
                  {% set ts = parts[1] if parts|length > 1 else "" %}
                  <span class="agent"
                        data-node="{{ node_name }}"
                        data-ts="{{ ts }}"
                        title="{{ e }}">{{ node_name }}</span>
                  {% if not loop.last %}<span class="arrow">→</span>{% endif %}
                {% endfor %}
              </div>
              <div class="muted small" style="margin-top:6px;">Tip: toggle “show timestamps” ↗</div>
            {% else %}
              <span class="muted">—</span>
            {% endif %}
          </div>
        </div>

        <div class="row">
          <div class="muted small"><b>🧬 Output columns</b></div>
          <div class="small">
            {% if names %}
              <span class="code" style="padding:8px 10px; border-radius:12px;">{{ names|join(", ") }}</span>
            {% else %}
              <span class="muted">—</span>
            {% endif %}
          </div>
        </div>

        <div class="row">
          <div class="muted small"><b>🔎 Preview</b></div>
          <div>
            {% if n_cols > 0 and n_rows > 0 %}
              <div class="preview">
                {% for v in tv[0][:8] %}
                  <span class="pill">{{ v }}</span>
                {% endfor %}
              </div>
            {% else %}
              <span class="muted small">—</span>
            {% endif %}
          </div>
        </div>

        {% if d.error %}
          <details open>
            <summary>❌ Error</summary>
            <div class="code" style="margin-top:10px; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.06);">
{{ d.error }}
            </div>
          </details>
        {% endif %}

        <details>
          <summary>🕸️ Node summaries ({{ node_dict|length }})</summary>
          <div style="margin-top:10px;">
            <table>
              <thead>
                <tr>
                  <th style="width:22%;">Node</th>
                  <th style="width:24%;">Time</th>
                  <th>Notes</th>
                </tr>
              </thead>

              {# -------- sorted node summaries by timestamp -------- #}
              {% set summaries = [] %}
              {% for raw_key, note in node_dict.items() %}
                {% set parts = raw_key.split('@', 1) %}
                {% set node_name = parts[0] %}
                {% set ts = parts[1] if parts|length > 1 else "" %}
                {% set _ = summaries.append({'node': node_name, 'ts': ts, 'note': note, 'raw': raw_key}) %}
              {% endfor %}
              {% set summaries = summaries|sort(attribute='ts') %}

              <tbody>
                {% for s in summaries %}
                  <tr>
                    <td><span class="code" style="padding:6px 8px; border-radius:10px;">{{ s.node }}</span></td>
                    <td><span class="code" style="padding:6px 8px; border-radius:10px;">{{ s.ts if s.ts else "—" }}</span></td>
                    <td>{{ s.note }}</td>
                  </tr>
                {% endfor %}
                {% if summaries|length == 0 %}
                  <tr><td colspan="3" class="muted"><i>No node summaries available</i></td></tr>
                {% endif %}
              </tbody>
              {# --------------------------------------------------- #}
            </table>
          </div>
        </details>

      </section>
    {% endfor %}
    </div>

    <div class="footer">
      🦋 MetaMorph • generated {{ finished_at }}
    </div>

  </div>

  <script>
    // Toggle timestamp visibility in the Agents breadcrumb.
    // Each .agent span has: data-node="SupervisorNode" data-ts="2026-01-05T..."
    (function () {
      const toggle = document.getElementById("toggle-ts");
      if (!toggle) return;

      function renderAgents(showTs) {
        document.querySelectorAll(".agent").forEach((el) => {
          const node = el.getAttribute("data-node") || "";
          const ts = el.getAttribute("data-ts") || "";
          if (showTs && ts) {
            el.textContent = node + " @" + ts;
          } else {
            el.textContent = node;
          }
        });
      }

      // default: off
      renderAgents(false);

      toggle.addEventListener("change", () => {
        renderAgents(toggle.checked);
      });
    })();
  </script>
</body>
</html>
""")
