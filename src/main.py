"""Main script for Telegram summary bot."""

import asyncio
import schedule
import time
from datetime import datetime
from .workflow import run_summary_workflow


async def generate_and_print_summary():
    """Generate and print a summary of recent Telegram messages."""
    print(f"\n{'='*60}")
    print(f"Telegram Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        summary = await run_summary_workflow()
        print(summary)
    except Exception as e:
        print(f"Error generating summary: {e}")
    
    print(f"{'='*60}\n")


def run_scheduled_summary():
    """Run the summary generation in async context."""
    asyncio.run(generate_and_print_summary())


def main():
    """Main function to set up scheduling and run the bot."""
    print("Starting Telegram Summary Bot...")
    print("Will generate summaries every 5 minutes")
    print("Press Ctrl+C to stop")
    
    # Schedule the task to run every 5 minutes
    schedule.every(5).minutes.do(run_scheduled_summary)
    
    # Run once immediately
    run_scheduled_summary()
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Telegram Summary Bot...")


if __name__ == "__main__":
    main()
