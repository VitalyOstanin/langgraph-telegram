"""MCP client for telegram-mcp server."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class TelegramMCPClient:
    """MCP client for interacting with telegram-mcp server."""
    
    def __init__(self, server_path: str = "/home/vyt/devel/telegram-mcp"):
        self.server_path = server_path
        self.server_params = StdioServerParameters(
            command="uv",
            args=["--directory", server_path, "run", "main.py"]
        )
    
    async def get_recent_messages(
        self, 
        chat_name: str = "BitKogan / Development",
        minutes_back: int = 10,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a Telegram chat."""
        
        print(f"[MCP] Getting messages from {chat_name} for last {minutes_back} minutes")
        
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # List available tools
                tools = await session.list_tools()
                print(f"[MCP] Available tools: {[tool.name for tool in tools.tools]}")
                
                # First, get list of chats to find the target chat
                try:
                    chats_result = await session.call_tool("list_chats", {"limit": 100})
                    print(f"[MCP] Chats result type: {type(chats_result)}")
                    
                    # Handle text response format from telegram-mcp
                    if chats_result.content and len(chats_result.content) > 0:
                        content_text = chats_result.content[0].text
                        print(f"[MCP] Raw content: {content_text[:200]}...")
                        
                        # Parse text format: "Chat ID: 123, Title: Name, Type: group"
                        target_chat_id = None
                        for line in content_text.split('\n'):
                            if f"Title: {chat_name}" in line and "Type: group" in line:
                                # Extract chat ID from line like "Chat ID: 2083014011, Title: BitKogan / Development, Type: group"
                                parts = line.split(', ')
                                for part in parts:
                                    if part.startswith('Chat ID: '):
                                        target_chat_id = int(part.replace('Chat ID: ', ''))
                                        break
                                break
                        
                        if not target_chat_id:
                            print(f"[MCP] Chat '{chat_name}' not found in response")
                            raise ValueError(f"Chat '{chat_name}' not found")
                        
                        print(f"[MCP] Found chat ID: {target_chat_id}")
                        
                        # Calculate time range
                        end_time = datetime.now()
                        start_time = end_time - timedelta(minutes=minutes_back)
                        
                        # Get messages from the chat
                        messages_result = await session.call_tool(
                            "list_messages",
                            {
                                "chat_id": target_chat_id,
                                "limit": limit,
                                "from_date": start_time.strftime("%Y-%m-%d"),
                                "to_date": end_time.strftime("%Y-%m-%d")
                            }
                        )
                        
                        print(f"[MCP] Messages result type: {type(messages_result)}")
                        
                        # Parse messages from text format
                        messages = []
                        if messages_result.content and len(messages_result.content) > 0:
                            messages_text = messages_result.content[0].text
                            print(f"[MCP] Raw messages: {messages_text[:200]}...")
                            
                            # Parse format: "ID: 12094 | Егор Тютюрин | Date: 2025-12-12 08:03:16+00:00 | Message: текст"
                            for line in messages_text.split('\n'):
                                line = line.strip()
                                if line and line.startswith('ID:') and '|' in line:
                                    messages.append({
                                        "date": datetime.now().isoformat(),
                                        "from_user": {"first_name": "Telegram"},
                                        "text": line  # Store the full line for parsing later
                                    })
                        
                        print(f"[MCP] Parsed {len(messages)} messages")
                        return messages
                    
                    else:
                        print("[MCP] No content in chats_result")
                        return []
                    
                except Exception as e:
                    print(f"[MCP] Error calling tools: {e}")
                    raise RuntimeError(f"Failed to get messages via MCP: {e}")
    
    def format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for LLM summarization."""
        if not messages:
            return "No messages found in the specified time period."
        
        formatted = []
        message_data = []  # Store both text and metadata
        
        for msg in messages:
            content = msg.get("text", "")
            
            if content and "ID:" in content and "|" in content:
                # Parse format: "ID: 12094 | Егор Тютюрин | Date: 2025-12-12 08:03:16+00:00 | Message: текст"
                parts = content.split(" | ")
                if len(parts) >= 4:
                    msg_id = parts[0].replace("ID: ", "").strip()
                    author = parts[1].strip()
                    date_str = parts[2].replace("Date: ", "").strip()
                    message_text = " | ".join(parts[3:]).replace("Message: ", "").strip()
                    
                    if message_text:  # Only include messages with actual text content
                        formatted.append(f"[{date_str}] {author}: {message_text}")
                        message_data.append({
                            "id": msg_id,
                            "author": author,
                            "date": date_str,
                            "text": message_text
                        })
        
        if not formatted:
            return "No text messages found in the specified time period."
        
        # Add message data for link generation
        result = "\n".join(formatted)
        if message_data:
            # Store message data as JSON for later parsing
            import json
            result += f"\n\n[MESSAGE_DATA: {json.dumps(message_data)}]"
        
        return result
    
    async def send_message_to_channel(self, chat_id: int, message: str) -> bool:
        """Send message to a Telegram channel using the same session."""
        print(f"[MCP] Sending message to channel {chat_id}")
        
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                try:
                    # First, "discover" the channel by listing chats to populate entity cache
                    print(f"[MCP] Discovering channel {chat_id} first...")
                    chats_result = await session.call_tool("list_chats", {"limit": 200})
                    
                    # Check if our target channel is in the list
                    channel_found = False
                    if chats_result.content and len(chats_result.content) > 0:
                        content_text = chats_result.content[0].text
                        if f"Chat ID: {chat_id}" in content_text:
                            channel_found = True
                            print(f"[MCP] Channel {chat_id} found in chat list")
                    
                    if not channel_found:
                        print(f"[MCP] Channel {chat_id} not found in chat list")
                        return False
                    
                    # Now try to send the message
                    result = await session.call_tool("send_message", {
                        "chat_id": chat_id,
                        "message": message
                    })
                    
                    print(f"[MCP] Send result: {result.content[0].text}")
                    
                    # Check if message was sent successfully
                    if "successfully" in result.content[0].text.lower():
                        print(f"[MCP] Message sent successfully to channel {chat_id}")
                        return True
                    else:
                        print(f"[MCP] Send failed: {result.content[0].text}")
                        return False
                        
                except Exception as e:
                    print(f"[MCP] Error sending message: {e}")
                    return False
