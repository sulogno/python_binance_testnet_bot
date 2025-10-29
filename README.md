# 🧠 Binance Testnet Trading Bot  
_A Modular Algorithmic Trading Framework built with Python and Streamlit_

---

## 🚀 Overview

This project is a **fully functional Binance Futures Testnet trading bot** that supports **Market**, **Limit**, **OCO**, and **TWAP** orders — all accessible via both **CLI commands** and a **Streamlit web dashboard**.

It’s designed with a **modular Python architecture**, robust **validation**, and **structured logging**, making it ideal for both learning and extending to real-world trading automation.

---

## 🏗️ Project Structure

## ✅ Features Implemented

| Feature | Description |
| :--- | :--- |
| **Market Orders** | Executes instant buy/sell orders using `client.futures_create_order`. |
| **Limit Orders** | Places price-specific orders with proper precision validation. |
| **TWAP Strategy** | Splits orders into timed intervals to minimize slippage. |
| **Synthetic OCO Logic** | Emulates One-Cancels-the-Other orders for risk management. |
| **Streamlit UI** | Provides an interactive dashboard with real-time PnL, positions, and control. |
| **Error Logging** | Every order, validation, and exception logged in `bot.log`. |

---

## 💡 Advanced Capabilities

### 🕒 TWAP (Time-Weighted Average Price)
_File: `src/advanced/twap.py`_

* Divides a total quantity into smaller trades executed at fixed time intervals.
* Reduces market impact of large trades.

### 🔁 OCO (One-Cancels-the-Other)
_File: `src/advanced/oco.py`_

* Simulates Futures OCO using dual conditional orders (`TAKE_PROFIT_MARKET`, `STOP_MARKET`).
* Uses `reduceOnly=True` to prevent overexposure.

### 🖥️ Streamlit Web UI
_File: `app.py`_

| Component | Function |
| :--- | :--- |
| **Live PnL Tracking** | Real-time Unrealized PnL with green/red color codes. |
| **Active Position Monitor** | Lists all open positions with size, entry, and PnL. |
| **Position Exit Tab** | Safely closes any open trade using a market order. |

---

## ⚙️ Setup & Installation

### 1️⃣ Clone the repository


```bash
git clone https://github.com/sulogno/python_binance_testnet_bot.git
cd python_binance_testnet_bot
```
### 2️⃣ Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
# or
source venv/bin/activate   # On Mac/Linux
```
###3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

###4️⃣ Configure Binance Testnet keys
```bash
API_KEY=your_testnet_api_key
API_SECRET=your_secret_key_here

```

###💻 Execution Modes
Order Type,Command Example
Market Order,python src/market_orders.py BTCUSDT BUY 0.001
Limit Order,python src/limit_orders.py ETHUSDT SELL 0.05 3500.00
OCO (Simulated),python src/advanced/oco.py BNBUSDT SELL 1.0 250.0 240.0
TWAP Strategy,python src/advanced/twap.py BTCUSDT BUY 0.005 60


⚠️ For OCO, the SIDE must close your position (SELL if you’re LONG, BUY if you’re SHORT).

🔹 Streamlit Dashboard (UI Mode)
Launch the full trading interface:
```bash
streamlit run app.py
```
###🏁 Conclusion
This project is a perfect foundation for real-world algo trading systems, showcasing:

Strong grasp of Python architecture & modular design

Deep understanding of Binance Futures API

Implementation of algorithmic execution strategies (TWAP, OCO)

Real-time, user-friendly frontend integration
