document.addEventListener("DOMContentLoaded", () => {
  const user = localStorage.getItem("loggedInUser");
  if (!user) {
    window.location.href = "login.html"; // optional safety
    return;
  }
  document.getElementById("user").textContent = user;
});

// ---------------- NAVIGATION ----------------
function navigate(page) {
  window.location.href = page + ".html";
}

// ---------------- BUY SUGGESTIONS ----------------
function getBuySuggestions() {
  const amount = parseFloat(document.getElementById("amount").value);
  if (!amount || amount <= 0) {
    alert("Please enter a valid amount");
    return;
  }
  fetch("http://127.0.0.1:5000/buy-suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount })
  })
    .then(res => res.json())
    /*.then(data => {
      data.forEach(s => s.qty = Math.floor(amount / s.price));
      data.sort((a, b) => b.qty - a.qty);
      document.getElementById("top-picks").innerHTML =
        data.slice(0, 2).map(stockCard).join("");
      document.getElementById("suggestions").innerHTML =
        data.slice(2).map(stockCard).join("");
    });*/
    .then(data => {
    document.getElementById("topHeading").classList.remove("hidden");
    document.getElementById("otherHeading").classList.remove("hidden");
    data.forEach(s => s.qty = Math.floor(amount / s.price));
    data.sort((a, b) => b.qty - a.qty);
    document.getElementById("top-picks").innerHTML =
    data.slice(0, 2).map(stockCard).join("");
    document.getElementById("suggestions").innerHTML =
    data.slice(2).map(stockCard).join("");
    });
}

function stockCard(s) {
  return `
    <div class="card">
      <p><b>${s.symbol}</b></p>
      <p>Price: ₹${s.price}</p>
      <p>Qty: ${s.qty}</p>
      <button onclick="buyStock('${s.symbol}', ${s.price})">Buy</button>
    </div>
  `;
}

function buyStock(symbol, price) {
  fetch("http://127.0.0.1:5000/buy-stock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: localStorage.getItem("loggedInUser"),
      symbol,
      price,
      quantity: 1
    })
  })
    .then(res => res.json())
    .then(d => alert(d.message));
}

// ---------------- SELL PAGE (FIXED) ----------------
function loadSellSuggestions() {
  const user = localStorage.getItem("loggedInUser");
  fetch(`http://127.0.0.1:5000/portfolio/${user}`)
    .then(res => res.json())
    /*.then(data => {
      if (!data.stocks || data.stocks.length === 0) {
        document.getElementById("top-picks").innerHTML =
          "<p>No stocks to sell</p>";
        document.getElementById("portfolio").innerHTML = "";
        return;
      }
      Compute profit per stock
      data.stocks.forEach(s => {
        s.profit = s.current_value - s.invested;
      });

      Sort by profit DESC
      const sorted = [...data.stocks].sort(
        (a, b) => b.profit - a.profit
      );

      document.getElementById("top-picks").innerHTML =
        sorted.slice(0, 2).map(sellCard).join("");

      document.getElementById("portfolio").innerHTML =
        sorted.slice(2).map(sellCard).join("");
    });*/
    .then(data => {
      renderSellPage(data);
    });
}

function sellCard(s) {
  return `
    <div class="card">
      <p><b>${s.symbol}</b></p>
      <p>Qty Owned: ${s.quantity}</p>
      <p>Buy Price: ₹${s.buy_price}</p>
      <p>Current Price: ₹${(s.current_value / s.quantity).toFixed(2)}</p>
      <p>Profit: ₹${s.profit.toFixed(2)}</p>

      <input
        type="number"
        min="1"
        max="${s.quantity}"
        value="1"
        id="sell-${s.symbol}"
      />

      <button onclick="sellStock(
        '${s.symbol}',
        document.getElementById('sell-${s.symbol}').value
      )">
        Sell
      </button>
    </div>
  `;
}

function sellStock(symbol, quantity) {
  fetch("http://127.0.0.1:5000/sell-stock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: localStorage.getItem("loggedInUser"),
      symbol,
      quantity: parseInt(quantity)
    })
  })
    .then(res => res.json())
    .then(d => {
      alert(d.message);
      loadSellSuggestions();
    });
}

// ---------------- PORTFOLIO (READ ONLY) ----------------
function loadPortfolioReadOnly() {
  const user = localStorage.getItem("loggedInUser");
  fetch(`http://127.0.0.1:5000/portfolio/${user}`)
    .then(res => res.json())
    .then(renderPortfolio);
}

function renderPortfolio(data) {
  let invested = 0;
  let current = 0;
  data.stocks.forEach(s => {
    invested += s.invested;
    current += s.current_value;
  });
  const profit = current - invested;
  document.getElementById("total-invested").innerText = invested.toFixed(2);
  document.getElementById("current-value").innerText = current.toFixed(2);
  document.getElementById("profit-loss").innerText = profit.toFixed(2);
  document.getElementById("direction").innerText = profit >= 0 ? "↑" : "↓";
  document.getElementById("portfolio").innerHTML =
    data.stocks.map(s => `
      <div class="card">
        <p><b>${s.symbol}</b></p>
        <p>Qty: ${s.quantity}</p>
        <p>Invested: ₹${s.invested.toFixed(2)}</p>
        <p>Current: ₹${s.current_value.toFixed(2)}</p>
        <p>Profit: ₹${(s.current_value - s.invested).toFixed(2)}</p>
      </div>
    `).join("");
}

// ---------------- PAGE LOAD (SINGLE & FIXED) ----------------
window.onload = () => {
  const p = window.location.pathname;
  if (p.includes("sell.html")) loadSellSuggestions();
  if (p.includes("profile.html")) loadPortfolioReadOnly();
};