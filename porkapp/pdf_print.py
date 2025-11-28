# pdf_print.py
from weasyprint import HTML, CSS
from flask import render_template_string
from datetime import datetime

def _money(v):
    try:
        n = float(v)
        return f"{n:,.0f}" if n.is_integer() else f"{n:,.2f}"
    except Exception:
        return str(v)

def make_b4_pdf(rows, company="理皓肉品有限公司", vendor="", ship_date="", print_time=None):
    """
    rows: list of [編號, 產品, 數量, 單位, 單價, 總計]（直接用你 CSV 讀出的列）
    """
    page_css = "@page { size: B4; margin: 12mm; }"
    if not print_time:
        print_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = render_template_string("""
<!doctype html>
<html lang="zh-Hant">
<head><meta charset="utf-8">
<style>
  {{page_css}}
  body { font-family:-apple-system,BlinkMacSystemFont,"Noto Sans CJK TC","Microsoft JhengHei",sans-serif; }
  .title{ text-align:center; font-size:20pt; font-weight:700; margin: 2mm 0 6mm; }
  .meta{ display:grid; grid-template-columns:1fr 1fr 1fr; column-gap:6mm; margin-bottom:6mm; font-size:11pt; }
  .cell{ border-bottom:1px solid #000; padding:2mm 0 1mm; }
  .label{ color:#333; margin-right:2mm; }
  table{ width:100%; border-collapse:collapse; table-layout:fixed; font-size:11pt; }
  thead th{ border-bottom:2px solid #000; padding:6pt 2pt; }
  tbody td{ border-bottom:1px solid #ccc; padding:6pt 2pt; }
  th,td{ text-align:right; }
  th.name,td.name{ text-align:left; }
  th.idx,td.idx{ width:12mm; text-align:center; }
  th.qty,td.qty{ width:22mm; }
  th.unit,td.unit{ width:18mm; text-align:center; }
  th.price,td.price{ width:24mm; }
  th.sub,td.sub{ width:28mm; }
  .tot{ margin-top:8mm; font-size:14pt; font-weight:700; text-align:right; }
  .small{ font-size:9pt; color:#666; }
</style>
</head>
<body>
  <div class="title">{{company}}</div>
  <div class="meta">
    <div class="cell"><span class="label">出貨廠商(可輸入)：</span>{{vendor}}</div>
    <div class="cell"><span class="label">出貨日期(可輸入)：</span>{{ship_date}}</div>
    <div class="cell"><span class="label">列印時間(當下時間)：</span>{{print_time}}</div>
  </div>

  <table>
    <thead>
      <tr>
        <th class="idx">編號</th>
        <th class="name">產品名稱</th>
        <th class="qty">數量</th>
        <th class="unit">單位</th>
        <th class="price">單價</th>
        <th class="sub">總計</th>
      </tr>
    </thead>
    <tbody>
    {% set grand = 0 %}
    {% for r in rows %}
      {% set sub = (r[5] | float(default=0.0)) %}
      {% set grand = grand + sub %}
      <tr>
        <td class="idx">{{ r[0] }}</td>
        <td class="name">{{ r[1] }}</td>
        <td class="qty">{{ r[2] }}</td>
        <td class="unit">{{ r[3] }}</td>
        <td class="price">{{ money(r[4]) }}</td>
        <td class="sub">{{ money(r[5]) }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>

  <div class="tot">總金額：{{ money(grand) }}</div>
</body>
</html>
    """, rows=rows, company=company, vendor=vendor or "", ship_date=ship_date or "",
       print_time=print_time, page_css=page_css, money=_money)

    return HTML(string=html).write_pdf(stylesheets=[CSS(string=page_css)])
