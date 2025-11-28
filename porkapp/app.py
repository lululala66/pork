import os, re, csv, glob
from datetime import datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Flask, request, jsonify, render_template, session
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session

# ───────────────── 基本設定 ─────────────────
app = Flask(__name__, template_folder="templates")

# ✅ Flask session 加密用（請保持長且隨機的字串）
app.secret_key = "zK2t7!@#L9$gPq8uFm5b&0wT!rQvN9jR"

# ✅ 管理員登入密碼（/products 頁按「管理登入」要輸入的這組）
ADMIN_PASSWORD = "0933112968"

DATA_DIR = "data"
ORDERS_ROOT = os.path.join(DATA_DIR, "orders")
PROD_DB_PATH = os.path.join(DATA_DIR, "products.db")
os.makedirs(ORDERS_ROOT, exist_ok=True)

# ───────────────── DB & Model ─────────────────
Base = declarative_base()
engine = create_engine(f"sqlite:///{PROD_DB_PATH}", echo=False, future=True)
Session = scoped_session(sessionmaker(bind=engine))

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    unit = Column(String)     # 斤 / 個 / 只 …
    price = Column(Float)

# ───────────────── 共用工具 ─────────────────
def _safe_vendor(v: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", (v or "").strip())[:80]

def vendor_from_filename(filename: str) -> str:
    if not filename or filename.startswith("newfile_"): return ""
    m = re.match(r"^\d{4}-\d{2}-\d{2}__(.+)\.csv$", filename)
    return m.group(1) if m else ""

def order_path(date: str, vendor: str = "", filename: str = "") -> str:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    ym = date[:7]
    base = os.path.join(ORDERS_ROOT, ym)
    os.makedirs(base, exist_ok=True)
    if filename:
        return os.path.join(base, filename)
    return os.path.join(base, f"{date}__{_safe_vendor(vendor)}.csv")

def ensure_header(path: str):
    if not os.path.exists(path):
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["編號", "產品", "數量", "單位", "單價", "總計"])

def read_rows(path: str):
    rows, total = [], Decimal("0")
    if not os.path.exists(path):
        return rows, "0"
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.reader(f)
        _ = next(r, None)
        for row in r:
            if not row: continue
            rows.append(row)
            try:
                total += Decimal(str(row[5])) if row[5] else 0
            except InvalidOperation:
                pass
    return rows, f"{total:.2f}"

def write_rows(path: str, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["編號", "產品", "數量", "單位", "單價", "總計"])
        w.writerows(rows)

def parse_qty(text: str, unit: str):
    """僅『斤』需要換算；其他單位（個、只…）直接取數字"""
    s = (text or "").strip().lower().replace("台斤", "斤")
    if unit != "斤":
        m = re.findall(r"\d+(?:\.\d+)?", s)
        return Decimal(m[0]) if m else Decimal("0")

    # 公斤 → 斤（1 公斤 / 0.6 = 台斤）
    if "公斤" in s or "kg" in s:
        m = re.findall(r"\d+(?:\.\d+)?", s)
        return (Decimal(m[0]) / Decimal("0.6")) if m else Decimal("0")

    # 2斤12兩
    m = re.match(r"(\d+)\s*斤\s*(\d+)\s*兩", s)
    if m:
        return Decimal(m.group(1)) + Decimal(m.group(2)) / Decimal("16")

    # 12兩
    m = re.match(r"(\d+)\s*兩", s)
    if m:
        return Decimal(m.group(1)) / Decimal("16")

    # 直接數字（斤）
    m = re.findall(r"\d+(?:\.\d+)?", s)
    return Decimal(m[0]) if m else Decimal("0")

def recalc_row(pid: str, qty_text: str):
    s = Session()
    name = unit = ""
    price = Decimal("0")
    try:
        p = s.get(Product, int(pid)) if str(pid).isdigit() else None
        if p:
            name, unit, price = p.name, p.unit, Decimal(str(p.price))
    finally:
        s.close()

    qty_calc = parse_qty(qty_text, unit)
    amount = qty_calc * price
    return [pid, name, qty_text, unit, f"{price}", f"{amount:.2f}"]

# ───────────────── Auth（管理員模式） ─────────────────
def is_admin() -> bool:
    return bool(session.get("is_admin"))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not is_admin():
            return jsonify(ok=False, error="forbidden"), 403
        return fn(*args, **kwargs)
    return wrapper

@app.post("/api/auth/login")
def api_login():
    j = request.get_json(silent=True) or {}
    pwd = (j.get("password") or "").strip()
    if pwd and ADMIN_PASSWORD and pwd == ADMIN_PASSWORD:
        session["is_admin"] = True
        return jsonify(ok=True)
    return jsonify(ok=False, error="bad password"), 401

@app.post("/api/auth/logout")
def api_logout():
    session.pop("is_admin", None)
    return jsonify(ok=True)

@app.get("/api/auth/status")
def api_status():
    return jsonify(ok=True, admin=is_admin())

# ───────────────── 頁面 ─────────────────
@app.get("/")
def index():
    # URL 上帶進來的 date（上方輸入框顯示的日期）
    date = (request.args.get("date") or datetime.now().strftime("%Y-%m-%d")).strip()
    vendor = (request.args.get("vendor") or "").strip()
    filename = (request.args.get("file") or "").strip()

    # 從檔名回推廠商
    if filename and not vendor:
        vendor = vendor_from_filename(filename)

    path = order_path(date, vendor, filename)
    ensure_header(path)
    rows, total = read_rows(path)

    # 🆕 從檔名抓出「檔案的日期」，例如 2025-11-11__大象.csv → 2025-11-11
    file_date = date
    m = re.match(r"^(\d{4}-\d{2}-\d{2})__", filename)
    if m:
        file_date = m.group(1)

    return render_template(
        "index.html",
        date=date,
        vendor=vendor,
        rows=rows,
        total_sum=total,
        file_date=file_date,   # 🆕 多丟一個變數給 template
    )

@app.get("/products")
def products_page():
    # 不傳 products，由前端呼叫 /api/products 載入
    return render_template("products.html")

# ───────────────── 產品查詢／維護 API ─────────────────
@app.get("/api/products")
def api_products():
    q = (request.args.get("query") or "").strip()
    s = Session()
    try:
        items = []
        if q.isdigit():
            p = s.get(Product, int(q))
            if p: items = [p]
        if not items:
            items = (s.query(Product)
                       .filter(Product.name.like(f"%{q}%"))
                       .order_by(Product.id.asc())
                       .limit(50).all())
        return jsonify([{"id": p.id, "name": p.name, "unit": p.unit, "price": p.price} for p in items])
    finally:
        s.close()

@app.post("/api/products/add")
@admin_required
def api_products_add():
    j = request.get_json(silent=True) or {}
    name = (j.get("name") or "").strip()
    unit = (j.get("unit") or "").strip()
    price = j.get("price")
    if not name:
        return jsonify(ok=False, error="name required"), 400
    try:
        price = float(price or 0)
    except:
        return jsonify(ok=False, error="bad price"), 400

    s = Session()
    try:
        p = Product(name=name, unit=unit, price=price)
        s.add(p); s.commit()
        return jsonify(ok=True, id=p.id)
    finally:
        s.close()

@app.post("/api/products/update")
@admin_required
def api_products_update():
    j = request.get_json(silent=True) or {}
    pid = j.get("id")
    if not pid:
        return jsonify(ok=False, error="id required"), 400
    s = Session()
    try:
        p = s.get(Product, int(pid))
        if not p:
            return jsonify(ok=False, error="not found"), 404
        if "name" in j:  p.name  = (j.get("name") or "").strip()
        if "unit" in j:  p.unit  = (j.get("unit") or "").strip()
        if "price" in j:
            try:
                p.price = float(j.get("price") or 0)
            except:
                return jsonify(ok=False, error="bad price"), 400
        s.commit()
        return jsonify(ok=True)
    finally:
        s.close()

@app.post("/api/products/delete")
@admin_required
def api_products_delete():
    j = request.get_json(silent=True) or {}
    pid = j.get("id")
    if not pid:
        return jsonify(ok=False, error="id required"), 400
    s = Session()
    try:
        p = s.get(Product, int(pid))
        if not p:
            return jsonify(ok=False, error="not found"), 404
        s.delete(p); s.commit()
        return jsonify(ok=True)
    finally:
        s.close()

# ───────────────── 訂單（CSV） API ─────────────────
@app.post("/api_add_row")
def api_add_row():
    j = request.get_json(silent=True) or {}
    date = (j.get("date") or "").strip()
    vendor = (j.get("vendor") or "").strip()
    filename = (j.get("filename") or "").strip()
    pid = (j.get("product_id") or "").strip()
    qty = (j.get("quantity") or "").strip()

    if not date or not pid:
        return jsonify(ok=False, error="missing required fields"), 400

    path = order_path(date, vendor, filename)
    ensure_header(path)
    new_row = recalc_row(pid, qty)
    rows, _ = read_rows(path)
    rows.append(new_row)
    write_rows(path, rows)
    _, total_sum = read_rows(path)
    return jsonify(ok=True, row=new_row, total_sum=total_sum)

@app.post("/api_update_cell")
def api_update_cell():
    j = request.get_json(silent=True) or {}
    date = j.get("date","")
    vendor = j.get("vendor","")
    filename = j.get("filename","")
    idx = int(j.get("row_index",0))
    field = j.get("field")
    value = j.get("value","")

    path = order_path(date,vendor,filename)
    rows,_ = read_rows(path)
    if not rows or idx < 0 or idx >= len(rows):
        return jsonify(ok=False, error="bad index"), 400

    pid,_,qty,_,_,_ = rows[idx]
    if field == "編號": pid=value
    elif field == "數量": qty=value

    rows[idx] = recalc_row(pid, qty)
    write_rows(path, rows)
    _, total_sum = read_rows(path)
    return jsonify(ok=True, row=rows[idx], total_sum=total_sum)

@app.post("/api_delete_row")
def api_delete_row():
    j = request.get_json(silent=True) or {}
    date = j.get("date","")
    vendor = j.get("vendor","")
    filename = j.get("filename","")
    idx = int(j.get("row_index",0))

    path = order_path(date,vendor,filename)
    rows,_ = read_rows(path)
    if 0 <= idx < len(rows):
        del rows[idx]
        write_rows(path, rows)
    _, total_sum = read_rows(path)
    return jsonify(ok=True, total_sum=total_sum)

@app.post("/api/orders/new")
def api_new():
    j = request.get_json(silent=True) or {}
    date = (j.get("date") or datetime.now().strftime("%Y-%m-%d"))
    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    fn = f"newfile_{ts}.csv"
    path = order_path(date, filename=fn)
    ensure_header(path)
    return jsonify(ok=True, filename=fn)

@app.post("/api/orders/rename")
def api_rename():
    j = request.get_json(silent=True) or {}
    date = j.get("date","")
    nv = j.get("new_vendor","")
    fn = j.get("filename","")
    if not nv or not fn:
        return jsonify(ok=False,error="缺少參數")
    src = order_path(date, filename=fn)
    dst = order_path(date, vendor=nv)
    if not os.path.exists(src):
        return jsonify(ok=False, error="檔案不存在")
    os.replace(src, dst)
    return jsonify(ok=True, new_name=os.path.basename(dst))

@app.get("/api/orders/list")
def api_list():
    ym = request.args.get("ym","")
    base = os.path.join(ORDERS_ROOT, ym) if ym else ORDERS_ROOT
    arr = []
    for p in sorted(glob.glob(os.path.join(base,"**/*.csv"),recursive=True), key=os.path.getmtime, reverse=True):
        arr.append({"filename":os.path.basename(p),"display":os.path.relpath(p,ORDERS_ROOT)})
    return jsonify(arr)

# ───────────────── 列印預覽頁面 ─────────────────
@app.get("/print_preview")
def print_preview():
    # 從網址取得參數 ?date=...&vendor=...&file=...
    ship_date = (request.args.get("date") or "").strip()
    vendor = (request.args.get("vendor") or "").strip()
    filename = (request.args.get("file") or "").strip()

    if not filename:
        return "缺少 file 參數", 404

    # 使用原本的 order_path + read_rows
    path = order_path(ship_date, vendor, filename)
    rows, total_sum = read_rows(path)

    return render_template(
        "print_preview.html",
        vendor=vendor,
        ship_date=ship_date,
        rows=rows,
        print_time=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

# ───────────────── Main ─────────────────
if __name__ == "__main__":
    app.run(debug=True)
