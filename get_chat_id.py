#!/usr/bin/env python3
"""Get chat ID for BitKogan / Development group."""

import asyncio
from src.telegram_mcp_client import TelegramMCPClient

async def main():
    client = TelegramMCPClient()
    
    # Get recent messages to see the format and get chat ID
    messages = await client.get_recent_messages("BitKogan / Development", 10)
    print(f"Found {len(messages)} messages")
    
    if messages:
        print("Sample message:", messages[0])

if __name__ == "__main__":
    asyncio.run(main())
