import streamlit as st
import sys
import os
import time
from decimal import Decimal, ROUND_DOWN
from binance.exceptions import BinanceAPIException 

# --- Path Fix to import from src/ ---
BASE = os.path.dirname(__file__)
SRC = os.path.join(BASE, "src")
ADV = os.path.join(SRC, "advanced")
if SRC not in sys.path:
    sys.path.append(SRC)
if ADV not in sys.path:
    sys.path.append(ADV)

# --- Import Bot Functions + utils ---
try:
    from utils import get_client  
    from market_orders import place_market_order
    from limit_orders import place_limit_order
    from oco import place_oco_conditional_orders
    from twap import execute_twap_strategy 
except ImportError as e:
    st.error(f"Failed to load backend functions. Ensure all files are in the 'src' directory and requirements are installed: {e}")
    sys.exit()


st.set_page_config(layout="wide", page_title="Binance Futures Bot — Streamlit UI")

# ----------------------
# Helper functions
# ----------------------
@st.cache_resource
def cached_client():
    """Return a cached Binance client (testnet configured in utils.get_client)."""
    try:
        return get_client()
    except Exception as e:
        st.error(f"🔴 Fatal Error: Cannot connect to Binance Testnet. Check API keys and network connection. Error: {e}")
        st.stop()


def get_price(symbol):
    client = cached_client()
    try:
        ticker = client.futures_symbol_ticker(symbol=symbol)
        return float(ticker["price"])
    except Exception as e:
        st.error(f"Failed to fetch price: {e}")
        return None

def get_exchange_info_symbol(symbol):
    """Fetch symbol info from exchangeInfo and return PRICE_FILTER tickSize and LOT_SIZE stepSize."""
    client = cached_client()
    try:
        info = client.futures_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                price_filter = next((f for f in s["filters"] if f["filterType"] == "PRICE_FILTER"), None)
                lot_filter = next((f for f in s["filters"] if f["filterType"] == "LOT_SIZE"), None)
                return {
                    "tickSize": float(price_filter["tickSize"]) if price_filter else None,
                    "minPrice": float(price_filter["minPrice"]) if price_filter else None,
                    "stepSize": float(lot_filter["stepSize"]) if lot_filter else None,
                    "minQty": float(lot_filter["minQty"]) if lot_filter else None
                }
        return None
    except Exception as e:
        st.warning(f"Failed to load exchange info for {symbol}: {e}")
        return None

def adjust_price_to_tick(price, tick_size):
    """Round price down to nearest tick_size (string safe with Decimal)."""
    if tick_size is None:
        return price
    p = Decimal(str(price))
    t = Decimal(str(tick_size))
    # floor to nearest tick: p - (p % t)
    factor = (p / t).quantize(0, rounding=ROUND_DOWN)
    valid = (factor * t).quantize(Decimal("0.00000001"))
    return float(valid)

def adjust_qty_to_step(qty, step_size):
    if step_size is None:
        return qty
    q = Decimal(str(qty))
    s = Decimal(str(step_size))
    factor = (q / s).quantize(0, rounding=ROUND_DOWN)
    valid = (factor * s).quantize(Decimal("0.00000001"))
    return float(valid)

def get_account_balances():
    client = cached_client()
    try:
        resp = client.futures_account_balance()
        return {r["asset"]: r["balance"] for r in resp}
    except Exception as e:
        st.warning(f"Could not fetch balances: {e}")
        return {}

def get_open_orders(symbol=None):
    client = cached_client()
    try:
        if symbol:
            return client.futures_get_open_orders(symbol=symbol)
        return client.futures_get_open_orders()
    except BinanceAPIException as e:
        if "No open orders" not in str(e):
             st.warning(f"API Error fetching orders: {e}")
        return []
    except Exception as e:
        st.warning(f"Could not fetch open orders: {e}")
        return []

# 🟢 MODIFIED FUNCTION: Returns both position list and total PNL
def get_positions():
    """Fetches non-zero open futures positions, simplifies data, and calculates total PNL."""
    client = cached_client()
    try:
        resp = client.futures_position_information()
        total_pnl = 0.0
        active_positions = []
        
        for p in resp:
            pnl_val = float(p.get('unRealizedProfit', '0.0'))
            pos_amt = float(p.get('positionAmt', '0.0'))
            
            if pos_amt != 0.0:
                total_pnl += pnl_val
                display_positions = {
                    'Symbol': p['symbol'],
                    'Side': 'LONG' if pos_amt > 0 else 'SHORT',
                    'Size': f"{pos_amt:.6f}",
                    'Entry Price': f"{float(p['entryPrice']):.2f}",
                    'Liq. Price': f"{float(p['liquidationPrice']):.2f}",
                    'Unrealized PNL': f"{pnl_val:.2f}"
                }
                active_positions.append(display_positions)
                
        # 🟢 RETURN: The list of positions and the total PNL
        return active_positions, total_pnl 
    except Exception as e:
        st.warning(f"Could not fetch positions: {e}")
        return [], 0.0 

# ----------------------
# UI: Top bar with live price and controls
# ----------------------
st.title("🤖 Binance Futures Testnet Bot")
# Allocate space for Market, Account, Open Orders, and Positions
col1, col2, col3, col4 = st.columns([2, 2, 1.5, 2.5]) 

with col1:
    st.subheader("Market Snapshot")
    symbol_global = st.text_input("Symbol", value="BTCUSDT", key="symbol_global")
    price_placeholder = st.empty()
    last_price = get_price(symbol_global.upper())
    price_placeholder.metric(label=f"{symbol_global.upper()} Price", value=f"{last_price:.2f}" if last_price else "N/A")

with col2:
    st.subheader("Account")
    if st.button("Refresh Balances"):
        st.cache_resource.clear() 
        st.rerun() 
        
    balances = get_account_balances()
    if balances:
        usdt = balances.get("USDT", "0")
        st.write(f"USDT Balance: **{float(usdt):.2f}**")
    else:
        st.write("No balance info (or failed to fetch).")

with col3:
    st.subheader("Open Orders")
    if st.button("Refresh Orders"): 
        st.rerun() 
    orders = get_open_orders(symbol_global.upper())
    st.write(f"Open orders: **{len(orders)}**")
    if orders:
        st.dataframe(orders, hide_index=True, width='stretch')

# 🟢 LIVE POSITIONS COLUMN (Modified to show PNL)
with col4:
    st.subheader("Live Positions & PNL")
    if st.button("Refresh Positions"):
        st.rerun()

    # 🟢 CAPTURE PNL
    active_positions, total_pnl = get_positions()

    # Determine PNL coloring using the required 'normal' value
    # We set a placeholder 'Value' (e.g., total equity) and use total_pnl as the 'delta'
    st.metric(
        label="Total Unrealized PNL", 
        # Display the actual PNL as the delta value
        value=f"${total_pnl:.2f}",
        delta=total_pnl, # Pass the float value to trigger color change based on sign
        delta_color='normal' # 'normal' = green for positive, red for negative
    )
    
    st.write(f"Active Positions: **{len(active_positions)}**")
    
    if active_positions:
        st.dataframe(active_positions, hide_index=True, width='stretch')
    else:
        st.info("No active open positions.")

st.markdown("---")

# ----------------------
# Tabs for order flows (Added Exit Position Tab)
# ----------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Market", "Limit", "OCO (Conditional)", "TWAP", "Exit Position"])

# ----------------------
# MARKET TAB
# ----------------------
with tab1:
    st.header("Market Order")
    with st.form("market_form"):
        m_symbol = st.text_input("Symbol", value=symbol_global.upper(), key="m_symbol")
        m_side = st.radio("Side", ("BUY", "SELL"), key="m_side")
        m_qty = st.number_input("Quantity", min_value=0.000001, format="%.6f", step=0.001, key="m_qty")
        preview = st.checkbox("Show validation preview", value=True)
        submit_market = st.form_submit_button("Place Market Order")
        
        if submit_market:
            info = get_exchange_info_symbol(m_symbol.upper())
            valid_qty = adjust_qty_to_step(m_qty, info["stepSize"] if info else None)
            
            if preview:
                st.info(f"Submitting: side={m_side}, adjusted quantity={valid_qty}")
            
            try:
                res = place_market_order(m_symbol.upper(), m_side.upper(), float(valid_qty))
                st.success("Market order placed and filled successfully.")
                st.json(res)
            except Exception as e:
                st.error(f"Market order failed: {e}")

# ----------------------
# LIMIT TAB
# ----------------------
with tab2:
    st.header("Limit Order")
    with st.form("limit_form"):
        l_symbol = st.text_input("Symbol", value=symbol_global.upper(), key="l_symbol")
        l_side = st.radio("Side", ("BUY", "SELL"), key="l_side")
        l_qty = st.number_input("Quantity", min_value=0.000001, format="%.6f", step=0.001, key="l_qty")
        l_price = st.number_input("Price", min_value=0.000001, format="%.2f", step=1.0, key="l_price")
        preview_limit = st.checkbox("Auto adjust price/qty to tick/lot step", value=True)
        submit_limit = st.form_submit_button("Place Limit Order")
        
        if submit_limit:
            info = get_exchange_info_symbol(l_symbol.upper())
            adj_price, adj_qty = l_price, l_qty
            
            if preview_limit and info:
                adj_price = adjust_price_to_tick(l_price, info["tickSize"])
                adj_qty = adjust_qty_to_step(l_qty, info["stepSize"])
                st.info(f"Adjusted Price -> {adj_price} (tickSize={info['tickSize']}), Adjusted Qty -> {adj_qty}")
            
            cur_price = get_price(l_symbol.upper())
            if (l_side.upper() == "SELL" and adj_price < cur_price) or \
               (l_side.upper() == "BUY" and adj_price > cur_price):
                try:
                    resp = place_limit_order(l_symbol.upper(), l_side.upper(), float(adj_qty), float(adj_price))
                    st.success("Limit order placed successfully.")
                    st.json(resp)
                except Exception as e:
                    st.error(f"Limit order failed: {e}")
            else:
                st.error(f"Limit price {adj_price} is likely to execute immediately ({cur_price}). Adjust price or use Market Order tab.")

# ----------------------
# OCO TAB
# ----------------------
with tab3:
    st.header("OCO (Take-Profit & Stop-Loss)")
    st.info("This places two conditional orders that attempt to close an existing position (reduceOnly).")
    with st.form("oco_form"):
        o_symbol = st.text_input("Symbol", value=symbol_global.upper(), key="o_symbol")
        o_side = st.radio("Closing Side (SELL if you are LONG)", ("SELL", "BUY"), key="o_side")
        o_qty = st.number_input("Quantity", min_value=0.000001, format="%.6f", step=0.001, key="o_qty")
        o_tp = st.number_input("Take Profit Trigger Price", min_value=0.000001, format="%.2f", step=1.0, key="o_tp")
        o_sl = st.number_input("Stop Loss Trigger Price", min_value=0.000001, format="%.2f", step=1.0, key="o_sl")
        submit_oco = st.form_submit_button("Place OCO (TP & SL)")
        
        if submit_oco:
            info = get_exchange_info_symbol(o_symbol.upper())
            o_tp_adj, o_sl_adj, o_qty_adj = o_tp, o_sl, o_qty
            
            if info:
                o_tp_adj = adjust_price_to_tick(o_tp, info["tickSize"])
                o_sl_adj = adjust_price_to_tick(o_sl, info["tickSize"])
                o_qty_adj = adjust_qty_to_step(o_qty, info["stepSize"])
                st.info(f"Adjusted: TP={o_tp_adj}, SL={o_sl_adj}, Qty={o_qty_adj}")
            
            try:
                resp = place_oco_conditional_orders(o_symbol.upper(), o_side.upper(), float(o_qty_adj), float(o_tp_adj), float(o_sl_adj))
                st.success("Placed OCO-like conditional orders (TP & SL)")
                st.json(resp)
            except Exception as e:
                st.error(f"OCO placement failed: {e}")

# ----------------------
# TWAP TAB
# ----------------------
with tab4:
    st.header("TWAP Strategy")
    with st.form("twap_form_ui"):
        t_symbol = st.text_input("Symbol", value=symbol_global.upper(), key="t_symbol")
        t_side = st.radio("Side", ("BUY", "SELL"), key="t_side")
        t_total_qty = st.number_input("Total Quantity", min_value=0.000001, format="%.6f", step=0.001, key="t_total_qty")
        t_duration = st.number_input("Duration (seconds)", min_value=10, max_value=3600, step=10, key="t_duration")
        t_chunks = st.number_input("Number of chunks", min_value=2, max_value=200, step=1, key="t_chunks", value=5)
        submit_twap = st.form_submit_button("Execute TWAP")
        
        if submit_twap:
            info = get_exchange_info_symbol(t_symbol.upper())
            
            if info:
                chunk_qty = (t_total_qty / float(t_chunks))
                chunk_qty_adj = adjust_qty_to_step(chunk_qty, info["stepSize"])
            else:
                chunk_qty_adj = t_total_qty / float(t_chunks)

            st.info(f"TWAP will place {t_chunks} market orders of {chunk_qty_adj} qty every {t_duration/float(t_chunks):.1f} seconds.")
            
            progress = st.progress(0)
            status_box = st.empty()
            results = []
            
            interval = t_duration / float(t_chunks)
            
            for i in range(int(t_chunks)):
                status_box.info(f"TWAP chunk {i+1}/{int(t_chunks)} — placing market order for {chunk_qty_adj}")
                try:
                    r = place_market_order(t_symbol.upper(), t_side.upper(), float(chunk_qty_adj))
                    results.append(r)
                    status_box.success(f"Chunk {i+1} placed. OrderID: {r.get('orderId') if isinstance(r, dict) else r}")
                except Exception as e:
                    status_box.error(f"Chunk {i+1} failed: {e}")
                    break
                
                progress.progress(int((i+1)/int(t_chunks)*100))
                
                if i < int(t_chunks)-1:
                    time.sleep(interval)
                    
            st.write("TWAP results:")
            st.json(results)
            st.success("TWAP completed (attempted all chunks).")

# ----------------------
# EXIT POSITION TAB (NEW)
# ----------------------
with tab5:
    st.header("Exit Active Position (Market Close)")
    st.warning("This function closes a selected open position immediately via a Market Order.")
    
    # Reload positions to ensure fresh data
    active_positions, _ = get_positions() # Ignore PNL here, we only need the list
    client = cached_client()
    
    if not active_positions:
        st.info("No active open positions to display or close.")
    else:
        # Create a dictionary mapping Symbol -> full position object for easy lookup
        position_map = {p['Symbol']: p for p in active_positions}
        position_symbols = list(position_map.keys())
        
        with st.form("exit_position_form"):
            exit_symbol = st.selectbox("Select Position to Exit:", position_symbols, key="exit_symbol")
            
            # Get details for the selected symbol
            selected_pos = position_map[exit_symbol]
            
            st.markdown(f"**Position Details:**")
            st.json(selected_pos)
            
            # Determine the side needed to close the position
            current_side = selected_pos['Side']
            exit_side = 'SELL' if current_side == 'LONG' else 'BUY'
            
            st.info(f"To close this **{current_side}** position, a **{exit_side} Market Order** will be placed.")
            
            submit_exit = st.form_submit_button(f"Execute {exit_side} Market Close")
            
            if submit_exit:
                # The quantity to close is the absolute size of the position
                exit_quantity = abs(float(selected_pos['Size']))
                
                try:
                    # Note: We use the direct client call here to ensure reduceOnly=True is set explicitly, 
                    # as place_market_order does not expose this parameter.
                    resp = client.futures_create_order(
                        symbol=exit_symbol,
                        side=exit_side,
                        type='MARKET',
                        quantity=exit_quantity,
                        reduceOnly=True 
                    )
                    
                    st.success(f"Position close order executed successfully: {exit_symbol}")
                    st.json(resp)
                    # Clear cache and rerun to reflect the closed position immediately
                    st.cache_resource.clear() 
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Position close failed for {exit_symbol}: {e}")

st.markdown("---")
st.caption("Note: This UI polls REST endpoints for price & account info. For production-grade real-time updates use authenticated WebSocket streams and background worker processes.")
