import os
import logging
import math
from dotenv import load_dotenv
from binance.client import Client, BinanceAPIException, BinanceRequestException

load_dotenv()

# --- Configuration ---
# Set the Binance Futures Testnet URL based on the documentation
TESTNET_FUTURES_URL = "https://testnet.binancefuture.com/fapi"

# Cache for exchange rules (to avoid spamming the API)
EXCHANGE_RULES = {}

# Logging setup
logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# --- Client and Setup ---

def get_client():
    """Return Binance Futures Testnet client."""
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("API_KEY or API_SECRET not found in .env file.")
        raise EnvironmentError("API credentials not configured.")

    # FIX: Removed the 'base_url' argument from the Client constructor.
    # We rely on setting client.FUTURES_URL after initialization.
    client = Client(api_key, api_secret)
    
    # This line correctly points all futures API calls to the Testnet URL.
    client.FUTURES_URL = TESTNET_FUTURES_URL 
    
    try:
        client.futures_ping()
        logger.info("Binance Futures Testnet client connected successfully.")
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"Failed to connect to Binance Futures Testnet: {e}")
        raise ConnectionError(f"API connection failed: {e}")
        
    return client

def _load_exchange_rules(client, symbol):
# ... (rest of the function is unchanged)
    global EXCHANGE_RULES
    if symbol in EXCHANGE_RULES:
        return EXCHANGE_RULES[symbol]

    try:
        # Fetch all symbols and filter for the target symbol
        info = client.futures_exchange_info()
        symbol_info = next(s for s in info['symbols'] if s['symbol'] == symbol)
        
        rules = {}
        for f in symbol_info['filters']:
            # Extract key filters: lot size and price filter
            if f['filterType'] == 'PRICE_FILTER':
                rules['price_precision'] = int(-math.log10(float(f['tickSize'])))
                rules['tickSize'] = float(f['tickSize'])
            elif f['filterType'] == 'LOT_SIZE':
                rules['quantity_precision'] = int(-math.log10(float(f['stepSize'])))
                rules['stepSize'] = float(f['stepSize'])
                rules['minQty'] = float(f['minQty'])

        EXCHANGE_RULES[symbol] = rules
        logger.info(f"Exchange rules loaded and cached for {symbol}.")
        return rules

    except Exception as e:
        logger.error(f"Failed to load exchange rules for {symbol}: {e}")
        raise

# --- Validation Logic ---

def validate_order(symbol, side, qty, price=None):
# ... (rest of the function is unchanged)
    """
    Robust validation using exchange rules:
    Checks symbol suffix, quantity/price positivity, and Binance precision rules.
    """
    # NOTE: Calling get_client() here will create a new client object 
    # for every validation call. In a production system, you'd pass a single client 
    # instance, but for this structure, it's fine for now.
    client = get_client() 
    
    # 1. Basic Sanity Checks (from your original code)
    if not symbol.endswith("USDT"):
        raise ValueError("Only USDT pairs allowed (e.g., BTCUSDT)")
    if side not in ['BUY', 'SELL']:
        raise ValueError("Order side must be 'BUY' or 'SELL'.")
    if qty <= 0:
        raise ValueError("Quantity must be > 0")
    if price is not None and price <= 0:
        raise ValueError("Price must be > 0 for Limit orders.")

    # 2. Advanced Binance Precision Checks
    rules = _load_exchange_rules(client, symbol)
    
    # Quantity Validation (LOT_SIZE filter)
    min_qty = rules.get('minQty', 0)
    step_size = rules.get('stepSize', 0)
    
    if qty < min_qty:
        raise ValueError(f"Quantity {qty} is less than minimum quantity {min_qty}.")
    
    # Check if quantity is a multiple of the step size (with tolerance for float)
    if step_size > 0 and abs((qty / step_size) - round(qty / step_size)) > 1e-6:
        raise ValueError(f"Quantity {qty} must be a multiple of the step size {step_size}.")

    # Price Validation (PRICE_FILTER) - only for Limit orders
    if price is not None:
        tick_size = rules.get('tickSize', 0)
        
        # Check if price is a multiple of the tick size (with tolerance)
        if tick_size > 0 and abs((price / tick_size) - round(price / tick_size)) > 1e-6:
            raise ValueError(f"Price {price} must be a multiple of the tick size {tick_size}.")
            
    # Success
    logger.info(f"Validation successful for {symbol} | QTY={qty} | PRICE={price if price else 'N/A'}")
    return True