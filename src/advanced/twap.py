# src/advanced/twap.py
import sys
import time
import logging
# We need to import the function from market_orders.py to reuse its logic
sys.path.append('src') # Temporarily add src to path if market_orders is not visible
from market_orders import place_market_order 

logger = logging.getLogger(__name__)

def execute_twap_strategy(symbol, side, total_quantity, duration_seconds, num_chunks=10):
    """
    Splits a large order into smaller market orders executed over time.
    """
    if duration_seconds < num_chunks * 2: # Ensure reasonable interval (min 2 seconds)
        print("Duration is too short for the number of chunks.")
        logger.error("TWAP_ERROR: Duration constraint failed.")
        return

    chunk_quantity = total_quantity / num_chunks
    interval_seconds = duration_seconds / num_chunks
    
    print(f"Starting TWAP: {total_quantity} over {duration_seconds}s in {num_chunks} chunks ({interval_seconds:.1f}s interval).")
    logger.info(f"TWAP_START: Symbol={symbol}, Total Qty={total_quantity}, Duration={duration_seconds}s")
    
    for i in range(num_chunks):
        chunk_num = i + 1
        print(f"Chunk {chunk_num}/{num_chunks}: Placing {chunk_quantity:.6f} {side} order...")
        
        # Reuse the existing market order function
        # Note: You MUST ensure chunk_quantity passes the minQty/stepSize validation!
        try:
            place_market_order(symbol, side, chunk_quantity) 
        except Exception as e:
            logger.error(f"TWAP_CHUNK_ERROR: Chunk {chunk_num} failed: {e}")
            print(f"❌ TWAP execution interrupted due to error in chunk {chunk_num}: {e}")
            break # Stop the TWAP if one chunk fails
        
        if chunk_num < num_chunks:
            print(f"Waiting {interval_seconds:.1f} seconds...")
            time.sleep(interval_seconds)
            
    print("✅ TWAP strategy complete.")
    logger.info("TWAP_COMPLETE: All chunks attempted.")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python src/advanced/twap.py <symbol> <BUY/SELL> <total_quantity> <duration_seconds>")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    side = sys.argv[2].upper()
    try:
        total_quantity = float(sys.argv[3])
        duration = int(sys.argv[4])
    except ValueError:
        print("Error: Quantity must be a number, duration must be an integer.")
        sys.exit(1)

    # Use a fixed number of chunks (e.g., 5) for a short test, or 10 for standard
    execute_twap_strategy(symbol, side, total_quantity, duration, num_chunks=5)