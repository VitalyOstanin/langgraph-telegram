#!/usr/bin/env python3
"""Test different channel ID formats."""

import asyncio
from src.telegram_mcp_client import TelegramMCPClient
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    client = TelegramMCPClient()
    
    async with stdio_client(client.server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Different formats to try for channel ID 2514401938
            formats_to_try = [
                2514401938,                    # Original ID
                -2514401938,                   # Negative ID
                f"-100{2514401938}",           # Supergroup format
                -1002514401938,                # Channel format (-100 prefix)
                "2514401938",                  # String format
                "-2514401938",                 # Negative string
                "-1002514401938",              # Channel string format
            ]
            
            for chat_id in formats_to_try:
                print(f"\nTrying format: {chat_id} (type: {type(chat_id)})")
                try:
                    result = await session.call_tool("get_chat", {"chat_id": chat_id})
                    print(f"SUCCESS! Chat info: {result.content[0].text[:200]}...")
                    break
                except Exception as e:
                    print(f"Failed: {str(e)[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
