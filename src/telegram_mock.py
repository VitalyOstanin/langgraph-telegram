"""Mock Telegram client for testing."""

from datetime import datetime, timedelta
from typing import List, Dict, Any


class TelegramMockClient:
    """Mock client for testing without real Telegram connection."""
    
    def __init__(self):
        pass
    
    async def get_recent_messages(
        self, 
        chat_name: str = "BitKogan / Development",
        minutes_back: int = 10,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get mock recent messages."""
        
        print(f"[MOCK] Getting messages from {chat_name} for last {minutes_back} minutes")
        
        # Generate some mock messages
        now = datetime.now()
        messages = []
        
        for i in range(3):
            msg_time = now - timedelta(minutes=i*2)
            messages.append({
                "id": 1000 + i,
                "date": msg_time.isoformat(),
                "text": f"Mock message {i+1}: This is a test message about development work.",
                "from_user": {
                    "id": 100 + i,
                    "first_name": f"User{i+1}",
                    "username": f"user{i+1}"
                }
            })
        
        return messages
    
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
