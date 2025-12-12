#!/usr/bin/env python3
"""Test script for the Telegram summary bot."""

import asyncio
from src.workflow import run_summary_workflow


async def test_summary():
    """Test the summary generation workflow."""
    print("Testing Telegram Summary Bot...")
    print("Fetching messages and generating summary...")
    
    try:
        summary = await run_summary_workflow()
        print("\nGenerated Summary:")
        print("-" * 50)
        print(summary)
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_summary())
