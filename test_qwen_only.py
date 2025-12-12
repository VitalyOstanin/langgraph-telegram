#!/usr/bin/env python3
"""Test script for Qwen API only."""

import asyncio
from src.qwen_client import QwenClient


async def test_qwen_api():
    """Test the Qwen API directly."""
    print("Testing Qwen API...")
    
    try:
        client = QwenClient()
        
        messages = [
            {"role": "user", "content": "Hello! Can you tell me what 2+2 equals?"}
        ]
        
        print("Calling Qwen API...")
        response = await client.chat_completion(messages=messages)
        
        print("Response received:")
        print(response)
        
        if "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0]["message"]["content"]
            print(f"\nGenerated response: {content}")
        else:
            print("No content in response")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_qwen_api())
