from jinja2 import Template

html_template = Template("""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MetaMorph Report — {{ dataset_id }}</title>
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
    }
    *{ box-sizing:border-box; }
    body{
      margin:0;
      font-family:var(--sans);
      background: radial-gradient(1000px 800px at 20% -10%, #1a2a6a33, transparent 60%),
                  radial-gradient(900px 700px at 90% 10%, #7c3aed22, transparent 55%),
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
      font-weight:700;
    }
    .sub{
      font-size:12px;
      color:var(--muted);
      font-family:var(--mono);
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
    }
    .cardhead{
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:12px;
      margin-bottom:10px;
    }
    .colname{
      font-size:15px;
      font-weight:700;
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
    }
    .meta b{ color:var(--text); font-weight:600; }

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
      font-weight:600;
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
      <div class="title">
        <h1>MetaMorph Report</h1>
        <div class="sub">dataset_id={{ dataset_id }}</div>
      </div>

      <div class="summary">
        <div class="kpi">
          <div class="label">Started (UTC)</div>
          <div class="value">{{ started_at }}</div>
        </div>
        <div class="kpi">
          <div class="label">Finished (UTC)</div>
          <div class="value">{{ finished_at }}</div>
        </div>
        <div class="kpi">
          <div class="label">Success</div>
          <div class="value">{{ n_success }}</div>
        </div>
        <div class="kpi">
          <div class="label">Failed</div>
          <div class="value">{{ n_failed }}</div>
        </div>
      </div>

      <div class="chips">
        <span class="chip"><span class="dot good"></span>SUCCESS</span>
        <span class="chip"><span class="dot bad"></span>FAILED</span>
        <span class="chip">columns={{ colData|length }}</span>
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
          <h2 class="colname">{{ col }}</h2>
          <span class="badge {{ 'good' if ok else 'bad' }}">
            <span class="dot {{ 'good' if ok else 'bad' }}"></span>
            {{ "SUCCESS" if ok else "FAILED" }}
          </span>
        </div>

        <div class="meta">
          <div><b>confidence</b>={{ "%.2f"|format(conf) }}</div>
          <div><b>shape</b>={{ n_rows }}×{{ n_cols }}</div>
          <div><b>mapped_cols</b>={{ names|length }}</div>
        </div>

        <div class="row">
          <div class="muted small"><b>Agents</b></div>
          <div class="small">
            {% if d.trackerInfo and d.trackerInfo.events_path %}
              <span class="code" style="padding:8px 10px; border-radius:12px;">
              {% for e in d.trackerInfo.events_path %}
                {{ e.split('@')[0] }}{% if not loop.last %} → {% endif %}
              {% endfor %}
              </span>
            {% else %}
              <span class="muted">—</span>
            {% endif %}
          </div>
        </div>

        <div class="row">
          <div class="muted small"><b>Output columns</b></div>
          <div class="small">
            {% if names %}
              <span class="code" style="padding:8px 10px; border-radius:12px;">{{ names|join(", ") }}</span>
            {% else %}
              <span class="muted">—</span>
            {% endif %}
          </div>
        </div>

        <div class="row">
          <div class="muted small"><b>Preview</b></div>
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
            <summary>Error</summary>
            <div class="code" style="margin-top:10px; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.06);">
{{ d.error }}
            </div>
          </details>
        {% endif %}

        <details>
          <summary>Node summaries ({{ node_dict|length }})</summary>
          <div style="margin-top:10px;">
            <table>
              <thead>
                <tr><th style="width:32%;">Node</th><th>Notes</th></tr>
              </thead>
              <tbody>
                {% for node, note in node_dict.items() %}
                  <tr><td><span class="code" style="padding:6px 8px; border-radius:10px;">{{ node }}</span></td><td>{{ note }}</td></tr>
                {% endfor %}
                {% if node_dict|length == 0 %}
                  <tr><td colspan="2" class="muted"><i>No node summaries available</i></td></tr>
                {% endif %}
              </tbody>
            </table>
          </div>
        </details>

      </section>
    {% endfor %}
    </div>

    <div class="footer">
      MetaMorph • generated {{ finished_at }}
    </div>

  </div>
</body>
</html>
""")
