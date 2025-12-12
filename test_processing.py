#!/usr/bin/env python3
"""Test script for the new message processing workflow."""

import asyncio
from src.workflow import run_processing_workflow


async def main():
    """Test the message processing workflow."""
    print("Testing message processing workflow...")
    
    # Test with default parameters (from 8 AM MSK today)
    result = await run_processing_workflow(
        source_channels=["BitKogan / Development"],
        target_channel="infotest"
    )
    
    print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(main())
