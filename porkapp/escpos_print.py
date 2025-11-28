from escpos.printer import Network
import re, datetime

def only_number(s):
    m = re.findall(r"[0-9.]+", str(s))
    return float(m[0]) if m else 0.0

def print_receipt(ip: str, order: dict, width: int = 32, port: int = 9100):
    p = Network(ip, port=port, timeout=3)
    p.set(align='center', text_type='B')
    p.text("銷售明細 / SALES RECEIPT\n")
    p.set(align='left')
    p.text(f"單號:{order['id']}  日期:{order.get('date')}\n")
    p.text('-'*width + '\n')

    name_w = max(8, width - (6+5+6+3))
    total = 0
    for it in order["items"]:
        qty = only_number(it["qty"])
        price = float(it["price"])
        sub = round(qty * price)
        total += sub
        name = str(it["name"])[:name_w]
        line = f"{name:<{name_w}} {str(it['qty']):>6} {int(price):>5} {int(sub):>6}\n"
        p.text(line)

    p.text('-'*width + '\n')
    p.set(text_type='B'); p.text(f"{'合計:':>{width-8}} {int(total):>8}\n\n")
    p.cut(); p.close()
