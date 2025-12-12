"""Telegram MCP client for fetching messages."""

import subprocess
import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any


class TelegramMCPClient:
    """Client for interacting with Telegram MCP server."""
    
    def __init__(self):
        self.mcp_command = [
            "uv", "--directory", "/home/vyt/devel/telegram-mcp", "run", "main.py"
        ]
    
    async def _run_mcp_command(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Run MCP command and return result."""
        if params is None:
            params = {}
        
        print(f"[DEBUG] Running MCP command: {method} with params: {params}")
        
        # Create MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        try:
            print(f"[DEBUG] Starting MCP process: {' '.join(self.mcp_command)}")
            
            # Run the MCP server command
            process = await asyncio.create_subprocess_exec(
                *self.mcp_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            print(f"[DEBUG] Sending request: {json.dumps(request)}")
            
            # Send request and get response
            stdout, stderr = await process.communicate(
                input=json.dumps(request).encode()
            )
            
            print(f"[DEBUG] Process return code: {process.returncode}")
            print(f"[DEBUG] Stdout: {stdout.decode()[:500]}...")
            print(f"[DEBUG] Stderr: {stderr.decode()[:500]}...")
            
            if process.returncode != 0:
                raise RuntimeError(f"MCP command failed: {stderr.decode()}")
            
            response = json.loads(stdout.decode())
            
            if "error" in response:
                raise RuntimeError(f"MCP error: {response['error']}")
            
            return response.get("result", {})
        
        except Exception as e:
            print(f"[DEBUG] Exception in MCP command: {e}")
            raise RuntimeError(f"Failed to run MCP command: {e}")
    
    async def get_recent_messages(
        self, 
        chat_name: str = "BitKogan / Development",
        minutes_back: int = 10,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent messages from a Telegram chat."""
        
        # First, find the chat by name
        chats = await self._run_mcp_command("list_chats", {"limit": 100})
        
        target_chat = None
        for chat in chats.get("chats", []):
            if chat.get("title") == chat_name:
                target_chat = chat
                break
        
        if not target_chat:
            raise ValueError(f"Chat '{chat_name}' not found")
        
        chat_id = target_chat["id"]
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=minutes_back)
        
        # Get messages from the chat
        messages = await self._run_mcp_command(
            "list_messages",
            {
                "chat_id": chat_id,
                "limit": limit,
                "from_date": start_time.strftime("%Y-%m-%d"),
                "to_date": end_time.strftime("%Y-%m-%d")
            }
        )
        
        # Filter messages by time (more precise filtering)
        recent_messages = []
        for msg in messages.get("messages", []):
            if "date" in msg:
                msg_time = datetime.fromisoformat(msg["date"].replace("Z", "+00:00"))
                if msg_time >= start_time:
                    recent_messages.append(msg)
        
        return recent_messages
    
    def format_messages_for_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Format messages for LLM summarization."""
        if not messages:
            return "No messages found in the specified time period."
        
        formatted = []
        for msg in messages:
            author = msg.get("from_user", {}).get("first_name", "Unknown")
            content = msg.get("text", "")
            timestamp = msg.get("date", "")
            
            if content:  # Only include messages with text content
                formatted.append(f"[{timestamp}] {author}: {content}")
        
        if not formatted:
            return "No text messages found in the specified time period."
        
        return "\n".join(formatted)
