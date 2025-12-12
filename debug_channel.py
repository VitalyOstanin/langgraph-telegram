#!/usr/bin/env python3
"""Debug infotest channel access."""

import asyncio
from src.telegram_mcp_client import TelegramMCPClient
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def main():
    client = TelegramMCPClient()
    
    async with stdio_client(client.server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Try to get chat info for infotest
            print("1. Trying to get chat info for infotest (ID: 2514401938)")
            try:
                chat_result = await session.call_tool("get_chat", {"chat_id": 2514401938})
                print(f"Chat info result: {chat_result.content[0].text}")
            except Exception as e:
                print(f"Failed to get chat info: {e}")
            
            # Try to get recent messages from the channel
            print("\n2. Trying to get recent messages from infotest")
            try:
                messages_result = await session.call_tool("list_messages", {
                    "chat_id": 2514401938,
                    "limit": 5
                })
                print(f"Messages result: {messages_result.content[0].text}")
            except Exception as e:
                print(f"Failed to get messages: {e}")
            
            # Try different ways to reference the channel
            print("\n3. Trying to send a test message")
            try:
                send_result = await session.call_tool("send_message", {
                    "chat_id": 2514401938,
                    "message": "Test message from bot"
                })
                print(f"Send result: {send_result.content[0].text}")
            except Exception as e:
                print(f"Failed to send message: {e}")

if __name__ == "__main__":
    asyncio.run(main())
