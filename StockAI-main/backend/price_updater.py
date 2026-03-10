'''import pandas as pd
import yfinance as yf
import firebase_admin
from firebase_admin import credentials, firestore
import time
import re

# ---------------- FIREBASE ----------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- LOAD CSV (SAFE MODE) ----------------
df = pd.read_csv(
    "nse_symbols.csv",
    encoding="utf-8-sig",
    sep=None,
    engine="python",
    on_bad_lines="skip"
)

print("🔍 RAW COLUMNS FOUND:", df.columns.tolist())

# ---------------- CLEAN COLUMN NAMES ----------------
df.columns = (
    df.columns
    .astype(str)
    .str.replace('"', '', regex=False)
    .str.replace("\n", "", regex=False)
    .str.strip()
    .str.upper()
)

print("✅ CLEANED COLUMNS:", df.columns.tolist())

# ---------------- AUTO-DETECT SYMBOL COLUMN ----------------
symbol_col = None
for col in df.columns:
    if "SYMBOL" in col:
        symbol_col = col
        break

if symbol_col is None:
    raise Exception("❌ Could not find SYMBOL column in CSV")

print(f"✔ Using symbol column: {symbol_col}")

# ---------------- CLEAN SYMBOL VALUES ----------------
symbols = (
    df[symbol_col]
    .astype(str)
    .str.replace('"', '', regex=False)
    .str.strip()
)

# ❌ REMOVE INDEX / INVALID ROWS
symbols = symbols[
    symbols.str.match(r"^[A-Z&.-]+$", na=False)
]

# ❌ REMOVE EMPTY & DUPLICATES
symbols = symbols[symbols != ""].unique().tolist()

# ✅ ADD .NS ONLY ONCE
symbols = [s if s.endswith(".NS") else s + ".NS" for s in symbols]

print(f"📊 TOTAL VALID NSE STOCKS: {len(symbols)}")
print("Sample:", symbols[:10])

# ---------------- UPDATE PRICES ----------------
for symbol in symbols:
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")

        if hist.empty:
            print(f"⚠ No data for {symbol}")
            continue

        price = float(hist["Close"].iloc[-1])

        db.collection("stock_prices").document(symbol.replace(".NS", "")).set({
            "symbol": symbol.replace(".NS", ""),
            "price": price,
            "updated": firestore.SERVER_TIMESTAMP
        })

        print(f"✔ {symbol} → ₹{price}")
        time.sleep(0.6)

    except Exception as e:
        print(f"❌ Error {symbol}: {e}")

print("\n🎉 PRICE UPDATE COMPLETED SUCCESSFULLY")'''
import pandas as pd
import yfinance as yf
import firebase_admin
from firebase_admin import credentials, firestore
import time

# ---------------- FIREBASE ----------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# ---------------- LOAD SYMBOLS ----------------
df = pd.read_csv("nse_symbols.csv")

df.columns = df.columns.str.strip().str.upper()
symbol_col = [c for c in df.columns if "SYMBOL" in c][0]

symbols = (
    df[symbol_col]
    .astype(str)
    .str.strip()
    .str.upper()
    .unique()
)

# Add .NS
symbols = [s if s.endswith(".NS") else s + ".NS" for s in symbols]

print(f"📊 TOTAL SYMBOLS: {len(symbols)}")

# ---------------- UPDATE LIVE PRICES ----------------
for symbol in symbols:
    try:
        ticker = yf.Ticker(symbol)

        # ✅ LIVE PRICE (THIS IS THE KEY)
        price = ticker.info.get("regularMarketPrice")

        if price is None:
            print(f"⚠ No live price for {symbol}")
            continue

        db.collection("stock_prices").document(symbol.replace(".NS", "")).set({
            "symbol": symbol.replace(".NS", ""),
            "price": round(float(price), 2),
            "updated_at": firestore.SERVER_TIMESTAMP
        })

        print(f"✔ {symbol} → ₹{price}")
        time.sleep(0.5)

    except Exception as e:
        print(f"❌ {symbol}: {e}")

print("\n🎉 LIVE PRICE UPDATE COMPLETED")