"""Main script for Telegram message processing bot."""

import asyncio
import schedule
import time
from datetime import datetime
from .workflow import run_processing_workflow


async def process_and_send_messages():
    """Process messages from Telegram channels and send results."""
    print(f"\n{'='*60}")
    print(f"Telegram Processing - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    try:
        result = await run_processing_workflow(
            source_channels=["BitKogan / Development"],
            time_period_minutes=10,
            target_channel="infotest"
        )
        print(result)
    except Exception as e:
        print(f"Error processing messages: {e}")
    
    print(f"{'='*60}\n")


def run_scheduled_processing():
    """Run the message processing in async context."""
    asyncio.run(process_and_send_messages())


def main():
    """Main function to set up scheduling and run the bot."""
    print("Starting Telegram Message Processing Bot...")
    print("Will process messages every 5 minutes")
    print("Press Ctrl+C to stop")
    
    # Schedule the task to run every 5 minutes
    schedule.every(5).minutes.do(run_scheduled_processing)
    
    # Run once immediately
    run_scheduled_processing()
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping Telegram Message Processing Bot...")


if __name__ == "__main__":
    main()
