#!/usr/bin/env python3
"""Test script for MCP Telegram client."""

import asyncio
from src.telegram_mcp_client import TelegramMCPClient


async def test_mcp_client():
    """Test the MCP Telegram client."""
    print("Testing MCP Telegram client...")
    
    try:
        client = TelegramMCPClient()
        
        print("Calling MCP client...")
        messages = await client.get_recent_messages(
            chat_name="BitKogan / Development",
            minutes_back=10
        )
        
        print(f"Received {len(messages)} messages")
        
        formatted = client.format_messages_for_summary(messages)
        print(f"Formatted messages ({len(formatted)} chars):")
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
