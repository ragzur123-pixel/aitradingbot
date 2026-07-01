import asyncio
import sys
import os
import time
from utils import setup_logging

logger = setup_logging("pipeline")

# The list of scripts to run for the CLOCKWORK Trading Operation
scripts = [
    "market_snapshot.py",
    "5_trading_bot.py"
]

async def run_script_async(script, ticker):
    """Run a python script asynchronously and return the exit code."""
    logger.info(f" >>> Executing {script}...")
    cmd = [sys.executable, script, ticker]
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        logger.info(f"SUCCESS: Completed {script}")
    elif process.returncode == 2:
        logger.info(f"STRATEGIC SKIP: {script} signaled no high-probability setup.")
    else:
        logger.error(f"[CRITICAL ERROR] {script} failed with exit code {process.returncode}.")
        if stderr:
            logger.error(f"Error Output: {stderr.decode(errors='replace').strip()}")
            
    return process.returncode

async def run_operation(ticker="EURUSD=X"):
    print("="*60)
    print(f"AITradingBot: CLOCKWORK OPERATION - {ticker}")
    print("Strategy: Local-First (Phase 1) + Strategic Alpha")
    print("="*60 + "\n")

    start_time = time.time()

    for script in scripts:
        exit_code = await run_script_async(script, ticker)
        if exit_code == 2:
            print(f"Cycle Halted: Local Math Gate blocked trade (Cost Saved).")
            return # Graceful exit
        if exit_code != 0:
            print(f"Operation halted due to error in {script}.")
            sys.exit(1)

    duration = time.time() - start_time
    print("!"*60)
    print(f"OPERATION COMPLETE in {duration:.2f} seconds.")
    print("Check 'trade_journal.json' for the CRO's decision.")
    print("="*60)

if __name__ == "__main__":
    ticker_arg = sys.argv[1] if len(sys.argv) > 1 else "EURUSD=X"
    asyncio.run(run_operation(ticker_arg))
