# ─────────────────────────────────────────────────────────────
# db_init.py  建立資料庫與預設產品資料
# ─────────────────────────────────────────────────────────────
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# ----------------------------------------------------------------
# 建立 SQLAlchemy 的基礎類別
# ----------------------------------------------------------------
Base = declarative_base()

# ----------------------------------------------------------------
# 產品資料表模型
# ----------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"  # 資料表名稱

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    price = Column(Float, nullable=False)

    def __init__(self, name, unit, price):
        self.name = name
        self.unit = unit
        self.price = price

# ----------------------------------------------------------------
# 建立資料庫路徑
# ----------------------------------------------------------------
APP_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "products.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# ----------------------------------------------------------------
# 建立資料庫引擎與 Session
# ----------------------------------------------------------------
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ----------------------------------------------------------------
# 初始化資料：預設產品
# ----------------------------------------------------------------
if __name__ == "__main__":
    session = Session()

    if not session.query(Product).first():
        items = [
            Product(name="五花肉", unit="斤", price=145),
            Product(name="夾心肉", unit="斤", price=110),
            Product(name="絞肉", unit="斤", price=120),
            Product(name="後腿肉", unit="斤", price=120),
            Product(name="赤肉絲", unit="斤", price=130),
            Product(name="肉片", unit="斤", price=130),
        ]
        session.add_all(items)
        session.commit()
        print("✅ 已建立預設產品資料")
    else:
        print("✅ 資料庫已存在，略過初始化")
    session.close()
