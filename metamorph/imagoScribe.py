import sys
from pathlib import Path

from datetime import datetime
import json
from jinja2 import Template
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))

from utils.llm import get_llm
from utils.prompts import get_prompt
from utils.MetaMorphState import ImagoState


def parse_iso(ts: str) -> datetime:

    return datetime.fromisoformat(ts.replace('Z', '+00:00'))

def summarizeTransformations(Res):
    lines = []
    lines.append(f"🐛 MetaMorph Transformation Report for {Res['dataset_id']}\n")

    StartTime, EndTime = Res['started_at'], Res['finished_at']

    dur = (parse_iso(EndTime) - parse_iso(StartTime)).total_seconds()

    lines.append(f"**Started:** {StartTime}  \n**Finished:** {EndTime}  \n**Duration:** {dur:.2f}s  \n")

    lines.append(f"✅ Success: {Res['n_success']} | ❌ Failed: {Res['n_failed']}\n")


    for col, data in Res['colData'].items():
        lines.append(f"---\n## Column: `{col}`")
        lines.append(f"**Confidence:** {data.get('confidence', 0):.2f}")
        lines.append(f"**Status:** {'FAILED' if data.get('error') else 'SUCCESS'}")
        lines.append("\n### Transformation Path")
        events = " → ".join([e.split('@')[0] for e in data['trackerInfo']['events_path']])
        lines.append(f"`{events}`")

        lines.append("\n### Node Summaries")
        for node, note in data['trackerInfo']['node_path'].get(col, {}).items():
            lines.append(f"- **{node}:** {note}")

        lines.append("\n### Output Summary")
        colnames = list(data['ColNames'].get(col, []))
        lines.append(f"**Output Columns:** {', '.join(colnames) or '—'}")
        tv = data.get("TransformedValues", [])
        n_cols = len(tv)
        n_rows = len(tv[0]) if tv and isinstance(tv[0], list) else 0
        lines.append(f"**Shape:** {n_rows} rows × {n_cols} col(s)")
        if n_rows > 0:
            preview = [str(v) for v in tv[0][:5]]
            lines.append(f"**Preview:** {', '.join(preview)}...")
        if data.get("error"):
            lines.append(f"\n❗ **Error:** {data['error']}")

    return "\n".join(lines)

html_template = Template("""
<h1>MetaMorph Report — {{ dataset_id }}</h1>
<p><b>Start:</b> {{ started_at }}<br>
<b>End:</b> {{ finished_at }}<br>
<b>Success:</b> {{ n_success }} &nbsp; <b>Failed:</b> {{ n_failed }}</p>

{% for col, d in colData.items() %}
<hr>
<h2>{{ col }}</h2>

<p>
<b>Confidence:</b> {{ "%.2f"|format(d.confidence or 0) }}
&nbsp;|&nbsp;
<b>Status:</b> {{ "FAILED" if d.error else "SUCCESS" }}
</p>

<p><b>Agents:</b>
{% if d.trackerInfo and d.trackerInfo.events_path %}
  {% for e in d.trackerInfo.events_path %}
    {{ e.split('@')[0] }}{% if not loop.last %} → {% endif %}
  {% endfor %}
{% else %}
  —
{% endif %}
</p>

<table border="1" cellspacing="0" cellpadding="4">
  <tr><th>Node</th><th>Notes</th></tr>
  {% set node_dict = d.trackerInfo.node_path.get(col, {}) if d.trackerInfo and d.trackerInfo.node_path else {} %}
  {% for node, note in node_dict.items() %}
    <tr><td>{{ node }}</td><td>{{ note }}</td></tr>
  {% endfor %}
  {% if node_dict|length == 0 %}
    <tr><td colspan="2"><i>No node summaries available</i></td></tr>
  {% endif %}
</table>

<p>
<b>Columns:</b>
{% set names = d.ColNames.get(col, []) if d.ColNames else [] %}
{{ names|join(", ") if names else "—" }}<br>

{% set tv = d.TransformedValues or [] %}
{% set n_cols = tv|length %}
{% set n_rows = (tv[0]|length) if n_cols > 0 else 0 %}
<b>Shape:</b> {{ n_rows }} rows × {{ n_cols }} col(s)<br>

<b>Preview:</b>
{% if n_cols > 0 and n_rows > 0 %}
  {% for v in tv[0][:5] %}
    {{ v }}{% if not loop.last %}, {% endif %}
  {% endfor %}
{% else %}
  —
{% endif %}
</p>

{% if d.error %}
  <p style="color:#b00020;"><b>Error:</b> {{ d.error }}</p>
{% endif %}

{% endfor %}
""")
