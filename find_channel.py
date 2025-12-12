#!/usr/bin/env python3
"""Find infotest channel ID."""

import asyncio
from src.telegram_mcp_client import TelegramMCPClient
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    client = TelegramMCPClient()
    
    async with stdio_client(client.server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get list of chats
            chats_result = await session.call_tool("list_chats", {"limit": 100})
            
            if chats_result.content and len(chats_result.content) > 0:
                content_text = chats_result.content[0].text
                print("All chats:")
                print(content_text)
                
                # Look for infotest
                for line in content_text.split('\n'):
                    if 'infotest' in line.lower():
                        print(f"\nFound infotest: {line}")

if __name__ == "__main__":
    asyncio.run(main())
