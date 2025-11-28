# pdf_print.py
from weasyprint import HTML
from flask import render_template_string
from datetime import datetime


def make_b4_pdf(rows, company="理皓肉品有限公司", vendor="", ship_date="", print_time=None):
    """
    rows: list of [編號, 產品, 數量, 單位, 單價, 總計]
    這份模板的版面、欄位寬度、對齊方式，都盡量跟 print_preview.html 一模一樣。
    """
    if not print_time:
        print_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 在 Python 這邊先把總金額算好，避免 Jinja 裡面 set 累加的問題
    grand = 0.0
    for r in rows:
        try:
            grand += float(r[5] or 0)
        except Exception:
            pass

    html = render_template_string(
        """
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <title>出貨單</title>
  <style>
    /* PDF 用 B4 紙，邊界 12mm */
    @page { size: B4; margin: 12mm; }

    :root{
      --fg:#111; --muted:#555; --line:#000; --line-weak:#ccc;
      --font:-apple-system,BlinkMacSystemFont,"Noto Sans CJK TC","Microsoft JhengHei",sans-serif;
    }
    html,body{
      margin:0;padding:0;background:#fff;color:var(--fg);font-family:var(--font);
    }
    .wrap{max-width:980px;margin:20px auto 40px;padding:0 16px;}

    .title{
      text-align:center;font-size:20pt;font-weight:700;
      letter-spacing:.5pt;margin:6px 0 12px;
    }

    .meta{
      display:grid;grid-template-columns:1fr 1fr 1fr;
      column-gap:12mm;margin:0 0 12mm;font-size:11pt;
    }
    .cell{border-bottom:1px solid var(--line);padding:6px 0 4px;}
    .label{color:var(--muted);margin-right:6px;}

    table{
      width:100%;border-collapse:collapse;table-layout:fixed;font-size:11pt;
    }
    thead th{border-bottom:2px solid var(--line);padding:6pt 2pt;}
    tbody td{border-bottom:1px solid var(--line-weak);padding:6pt 2pt;}
    th,td{text-align:right;}
    th.name,td.name{text-align:left;}
    th.idx, td.idx { width:12mm;text-align:center; }
    th.qty, td.qty { width:22mm; }
    th.unit,td.unit{ width:18mm;text-align:center; }
    th.price,td.price{width:24mm;}
    th.sub,  td.sub  {width:28mm;}

    .tot{
      margin-top:12mm;font-size:16pt;font-weight:800;text-align:right;
    }
  </style>
</head>
<body>
  <div class="wrap">

    <div class="title">{{ company or '理皓肉品有限公司' }}</div>

    <div class="meta">
      <div class="cell"><span class="label">出貨廠商：</span>{{ vendor or '' }}</div>
      <div class="cell"><span class="label">出貨日期：</span>{{ ship_date or '' }}</div>
      <div class="cell"><span class="label">列印時間：</span>{{ print_time or '' }}</div>
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
        {% for r in rows %}
          {% set price = (r[4] | float(default=0.0)) %}
          {% set sub   = (r[5] | float(default=0.0)) %}
          <tr>
            <td class="idx">{{ r[0] }}</td>
            <td class="name">{{ r[1] }}</td>
            <!-- 數量顯示原本的文字（例如：20斤10兩、20KG） -->
            <td class="qty">{{ r[2] }}</td>
            <td class="unit">{{ r[3] }}</td>
            <td class="price">
              {{ '%.0f' % price if price==price|round(0) else '%.2f' % price }}
            </td>
            <td class="sub">
              {{ '%.0f' % sub   if sub  ==sub  |round(0) else '%.2f' % sub   }}
            </td>
          </tr>
        {% endfor %}
      </tbody>
    </table>

    <div class="tot">
      總金額：{{ '%.0f' % grand if grand==grand|round(0) else '%.2f' % grand }}
    </div>
  </div>
</body>
</html>
        """,
        rows=rows,
        company=company,
        vendor=vendor,
        ship_date=ship_date,
        print_time=print_time,
        grand=grand,
    )

    # WeasyPrint 產生 PDF
    return HTML(string=html).write_pdf()
