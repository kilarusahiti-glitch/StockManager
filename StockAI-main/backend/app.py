from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
# ------------------ FLASK ------------------
app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)
# ------------------ FIREBASE ------------------
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
# ------------------ UTIL ------------------
def normalize_symbol(sym):
    if not sym:
        return None
    return sym.replace(".NS", "").strip().upper()
def get_current_price(symbol, fallback):
    doc = db.collection("stock_prices").document(symbol).get()
    if not doc.exists:
        return fallback
    return round(doc.to_dict().get("price", fallback), 2)
# ------------------ SIGNUP ------------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    confirm_password = data.get("confirm_password", "").strip()
    if not username or not password or not confirm_password:
        return jsonify({"message": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters"}), 400
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400
    user_ref = db.collection("users").document(username)
    if user_ref.get().exists:
        return jsonify({"message": "User already exists"}), 409
    user_ref.set({
        "username": username,
        "password": password,  # ⚠ plain text for now (learning phase)
        "created_at": datetime.utcnow()
    })
    return jsonify({"message": "Signup successful"})
# ------------------ LOGIN ------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400
    user_ref = db.collection("users").document(username)
    doc = user_ref.get()
    if not doc.exists:
        return jsonify({"message": "User not found"}), 404
    if doc.to_dict().get("password") != password:
        return jsonify({"message": "Incorrect password"}), 401
    return jsonify({"message": "Login successful"})
# ------------------ BUY STOCK ------------------
@app.route("/buy-stock", methods=["POST"])
def buy_stock():
    d = request.json
    user = d.get("user_id")
    symbol = normalize_symbol(d.get("symbol"))
    qty = int(d.get("quantity", 1))
    buy_price = round(float(d.get("price", 0)), 2)
    if not user or not symbol or buy_price <= 0 or qty <= 0:
        return jsonify({"message": "Invalid data"}), 400
    ref = db.collection("users").document(user)\
        .collection("portfolio").document(symbol)
    now = datetime.utcnow()
    doc = ref.get()
    if doc.exists:
        old = doc.to_dict()
        old_qty = old.get("quantity", 0)
        old_price = old.get("buy_price", buy_price)
        new_qty = old_qty + qty
        avg_price = round(
            ((old_qty * old_price) + (qty * buy_price)) / new_qty, 2
        )
        ref.set({
            "symbol": symbol,
            "quantity": new_qty,
            "buy_price": avg_price,
            "updated_at": now
        }, merge=True)
    else:
        ref.set({
            "symbol": symbol,
            "quantity": qty,
            "buy_price": buy_price,
            "created_at": now,
            "updated_at": now
        })
    return jsonify({"message": "Stock bought successfully"})
# ------------------ SELL STOCK ------------------
@app.route("/sell-stock", methods=["POST"])
def sell_stock():
    d = request.json
    user = d.get("user_id")
    symbol = normalize_symbol(d.get("symbol"))
    sell_qty = int(d.get("quantity", 0))
    if not user or not symbol or sell_qty <= 0:
        return jsonify({"message": "Invalid data"}), 400
    ref = db.collection("users").document(user)\
        .collection("portfolio").document(symbol)
    doc = ref.get()
    if not doc.exists:
        return jsonify({"message": "Stock not found"}), 404
    data = doc.to_dict()
    qty = data.get("quantity", 0)
    if sell_qty >= qty:
        ref.delete()
    else:
        ref.update({
            "quantity": qty - sell_qty,
            "updated_at": datetime.utcnow()
        })
    return jsonify({"message": "Sell successful"})
# ------------------ BUY SUGGESTIONS ------------------
@app.route("/buy-suggestions", methods=["POST"])
def buy_suggestions():
    data = request.json
    amount = float(data.get("amount", 0))
    clean = {}
    for doc in db.collection("stock_prices").stream():
        stock = doc.to_dict()
        price = round(stock.get("price", 0), 2)
        symbol = normalize_symbol(doc.id)
        if price <= 0 or price > amount:
            continue
        if symbol not in clean or price < clean[symbol]["price"]:
            clean[symbol] = {
                "symbol": symbol,
                "price": price,
                "qty": int(amount // price)
            }
    results = list(clean.values())
    results.sort(key=lambda x: x["qty"]* x["price"], reverse=True)
    return jsonify(results[:20])
# ----------------- SELL SUGGESTIONS ------------------
@app.route("/sell-suggestions/<user>", methods=["GET"])
def sell_suggestions(user):
    suggestions = []
    portfolio_ref = db.collection("users").document(user).collection("portfolio")
    for doc in portfolio_ref.stream():
        stock = doc.to_dict()
        symbol = normalize_symbol(doc.id)
        qty = stock.get("quantity", 0)
        buy_price = round(stock.get("buy_price", 0), 2)
        if qty <= 0 or buy_price <= 0:
            continue
        curr_price = get_current_price(symbol, buy_price)
        profit = round((curr_price - buy_price) * qty, 2)
        profit_percent = round(((curr_price - buy_price) / buy_price) * 100, 2)
        suggestions.append({
            "symbol": symbol,
            "quantity": qty,
            "buy_price": buy_price,
            "current_price": curr_price,
            "profit": profit,
            "profit_percent": profit_percent,
            "suggested_sell_qty": qty
        })
    suggestions.sort(key=lambda x: x["profit"], reverse=True)
    return jsonify(suggestions)
# ------------------ PORTFOLIO ------------------
@app.route("/portfolio/<user>")
def portfolio(user):
    total_invested = 0
    current_value = 0
    stocks = []
    for doc in db.collection("users").document(user).collection("portfolio").stream():
        s = doc.to_dict()
        symbol = normalize_symbol(doc.id)
        qty = s.get("quantity", 0)
        buy_price = round(s.get("buy_price", 0), 2)
        if qty <= 0 or buy_price <= 0:
            continue
        curr_price = get_current_price(symbol, buy_price)
        invested = round(buy_price * qty, 2)
        current = round(curr_price * qty, 2)
        total_invested += invested
        current_value += current
        stocks.append({
            "symbol": symbol,
            "quantity": qty,
            "buy_price": buy_price,
            "current_price": curr_price,
            "invested": invested,
            "current_value": current,
            "profit": round(current - invested, 2),
            "profit_percent": round(((current - invested) / invested) * 100, 2)
        })
    profit = round(current_value - total_invested, 2)
    return jsonify({
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "profit": profit,
        "direction": "UP" if profit >= 0 else "DOWN",
        "stocks": stocks
    })
# ------------------ FRONTEND ------------------
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_frontend(path):
    frontend_folder = os.path.join(os.path.dirname(__file__), "../frontend")
    return send_from_directory(frontend_folder, path)
# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(debug=True)