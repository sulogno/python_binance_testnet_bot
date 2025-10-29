# src/limit_orders.py (FINAL)
import sys
import logging
from utils import get_client, validate_order 
from binance.exceptions import BinanceAPIException # Ensure imported for better error catching

logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

def place_limit_order(symbol, side, quantity, price):
    client = get_client()
    try:
        # Call validation function
        validate_order(symbol, side, quantity, price) 
        
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            timeInForce="GTC",
            quantity=quantity,
            price=price
        )
        # Use a more consistent log format
        logging.info(f"LIMIT_ORDER_SUCCESS: Symbol={symbol}, Side={side}, OrderID={order.get('orderId')}") 
        # 🟢 FIX: Return the order object
        return order
        
    except Exception as e:
        # Log the error, but re-raise for Streamlit
        logging.error(f"LIMIT_ORDER_ERROR: {e}")
        # 🟢 FIX: Re-raise the exception
        raise 

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python src/limit_orders.py <symbol> <BUY/SELL> <quantity> <price>")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    try:
        quantity = float(sys.argv[3])
        price = float(sys.argv[4])
    except ValueError:
        print("Error: Quantity and Price must be valid numbers.")
        sys.exit(1)

    try:
        result = place_limit_order(symbol, side, quantity, price)
        print("✅ Limit order placed successfully.")
        print(result)
    except Exception as e:
        print(f"❌ Error: {e}")