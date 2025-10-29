# src/advanced/oco.py (FINAL)
import sys
import os 
import logging
from binance.exceptions import BinanceAPIException

# 🟢 FIX 1: Add the parent directory ('src') to the system path to find utils.py
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# 🟢 FIX 2: Import the functions *after* the path fix
try:
    from utils import get_client, validate_order 
except ImportError as e:
    # Fail gracefully if utils is still not found
    print(f"FATAL ERROR: Could not import utility functions: {e}")
    sys.exit(1)

logger = logging.getLogger(__name__)

def place_oco_conditional_orders(symbol, side, quantity, take_profit_trigger, stop_loss_trigger):
    # ... (function body is the same, but remove the print statements inside the try blocks) ...
    client = get_client()
    
    # 1. Validate inputs (The trigger prices must meet precision rules)
    validate_order(symbol, side, quantity, price=take_profit_trigger)
    validate_order(symbol, side, quantity, price=stop_loss_trigger)
    
    orders = []

    # --- Order 1: Take Profit (Closes the position for profit) ---
    try:
        tp_order = client.futures_create_order(
            symbol=symbol, side=side, type='TAKE_PROFIT_MARKET', quantity=quantity, stopPrice=take_profit_trigger, reduceOnly=True
        )
        orders.append(tp_order)
        logging.info(f"OCO_TP_SUCCESS: Trigger={take_profit_trigger}, ID={tp_order.get('orderId')}")
        # REMOVED: print("✅ Take Profit Market Order placed...")
    except BinanceAPIException as e:
        logging.error(f"OCO_TP_ERROR: Failed to place Take Profit: {e}")
        raise # Re-raise for Streamlit
        
    # --- Order 2: Stop Loss (Closes the position to limit loss) ---
    try:
        sl_order = client.futures_create_order(
            symbol=symbol, side=side, type='STOP_MARKET', quantity=quantity, stopPrice=stop_loss_trigger, reduceOnly=True
        )
        orders.append(sl_order)
        logging.info(f"OCO_SL_SUCCESS: Trigger={stop_loss_trigger}, ID={sl_order.get('orderId')}")
        # REMOVED: print("✅ Stop Loss Market Order placed...")
    except BinanceAPIException as e:
        logging.error(f"OCO_SL_ERROR: Failed to place Stop Loss: {e}")
        raise # Re-raise for Streamlit
        
    # 🟢 FIX: Return the list of orders
    return orders

if __name__ == "__main__":
    # ... (CLI parsing code is here) ...
    if len(sys.argv) != 6:
        # ... print usage ...
        sys.exit(1)
    
    # ... (symbol, side, qty parsing) ...
    try:
        result = place_oco_conditional_orders(symbol, side, quantity, tp_price, sl_price)
        print("✅ OCO-like conditional orders placed successfully.")
        print(result)
    except Exception as e:
        print(f"❌ Error: {e}")