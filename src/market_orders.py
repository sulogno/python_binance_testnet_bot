import sys
import logging
from utils import get_client, validate_order
from binance.exceptions import BinanceAPIException # Ensure this is imported

# Configure logging for standalone use (if not configured elsewhere)
try:
    logger = logging.getLogger(__name__)
except NameError:
    logging.basicConfig(filename="bot.log", level=logging.INFO, format="%(asctime)s %(message)s")
    logger = logging.getLogger(__name__)


def place_market_order(symbol, side, quantity):
    client = get_client()
    try:
        # Validate order parameters
        validate_order(symbol, side, quantity) 
        
        order = client.futures_create_order(
            symbol=symbol,
            side=side.upper(),
            type="MARKET",
            quantity=quantity
        )
        
        logging.info(f"Market Order SUCCESS: {order}")
        
        # 🟢 FIX for Streamlit: Return the order object
        return order
        
    except Exception as e:
        logging.error(f"Market Order Failed: {str(e)}")
        # 🟢 FIX for Streamlit: Re-raise the exception for the UI wrapper to catch
        raise 

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python src/market_orders.py SYMBOL SIDE QTY")
        sys.exit(1)

    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    try:
        qty = float(sys.argv[3])
    except ValueError:
        print("Error: Quantity must be a valid number.")
        sys.exit(1)

    try:
        # Run function and get result
        result = place_market_order(symbol, side, qty)
        print("✅ Market order placed successfully.")
        print(result)
    except Exception as e:
        # Print error which was already logged
        print(f"❌ Error: {e}")