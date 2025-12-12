"""LangGraph workflow for Telegram message summarization."""

from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from .qwen_langchain import QwenChatModel
from .telegram_mcp import TelegramMCPClient


class SummaryState(TypedDict):
    """State for the summarization workflow."""
    messages: str
    summary: str
    error: str
    mcp_session: Any  # Store MCP session for reuse


async def fetch_messages_node(state: SummaryState) -> Dict[str, Any]:
    """Fetch recent messages from Telegram."""
    print("[DEBUG] Starting fetch_messages_node")
    try:
        # Try MCP client first, fallback to mock if it fails
        try:
            from .telegram_mcp_client import TelegramMCPClient
            telegram_client = TelegramMCPClient()
            print("[DEBUG] Created TelegramMCPClient")
            
            messages = await telegram_client.get_recent_messages(
                chat_name="BitKogan / Development",
                minutes_back=10
            )
            print(f"[DEBUG] Fetched {len(messages)} messages via MCP")
            
            formatted_messages = telegram_client.format_messages_for_summary(messages)
            print(f"[DEBUG] Formatted messages length: {len(formatted_messages)}")
            
            return {
                "messages": formatted_messages,
                "error": "",
                "mcp_session": telegram_client  # Store for reuse in send node
            }
            
        except Exception as mcp_error:
            print(f"[DEBUG] MCP client failed: {mcp_error}, falling back to mock")
            
            # Fallback to mock client
            from .telegram_mock import TelegramMockClient
            telegram_client = TelegramMockClient()
            print("[DEBUG] Created TelegramMockClient as fallback")
            
            messages = await telegram_client.get_recent_messages(
                chat_name="BitKogan / Development",
                minutes_back=10
            )
            print(f"[DEBUG] Fetched {len(messages)} messages via mock")
            
            formatted_messages = telegram_client.format_messages_for_summary(messages)
            print(f"[DEBUG] Formatted messages length: {len(formatted_messages)}")
            
            return {
                "messages": formatted_messages,
                "error": "",
                "mcp_session": None  # No MCP session available
            }
        
    except Exception as e:
        print(f"[DEBUG] Error in fetch_messages_node: {e}")
        import traceback
        traceback.print_exc()
        return {
            "messages": "",
            "error": f"Failed to fetch messages: {str(e)}",
            "mcp_session": None
        }


async def summarize_messages_node(state: SummaryState) -> Dict[str, Any]:
    """Summarize the fetched messages using Qwen."""
    print("[DEBUG] Starting summarize_messages_node")
    
    if state.get("error"):
        print(f"[DEBUG] Found error in state: {state['error']}")
        return {"summary": f"Error: {state['error']}"}
    
    messages = state.get("messages", "")
    print(f"[DEBUG] Messages to summarize: {len(messages)} characters")
    
    if not messages or messages.startswith("No"):
        print("[DEBUG] No messages to summarize")
        return {"summary": "No messages to summarize."}
    
    # Extract message data for links and dates
    message_data = []
    if "[MESSAGE_DATA:" in messages:
        import json
        data_part = messages.split("[MESSAGE_DATA:")[1].split("]")[0]
        try:
            message_data = json.loads(data_part)
        except:
            pass
        # Remove the MESSAGE_DATA part from messages for LLM
        messages = messages.split("[MESSAGE_DATA:")[0].strip()
    
    try:
        print("[DEBUG] Creating QwenChatModel")
        llm = QwenChatModel()
        
        system_prompt = """Ты полезный помощник, который создает сводки сообщений из Telegram чата.
        
        Пожалуйста, предоставь краткую сводку следующих сообщений за последние 10 минут НА РУССКОМ ЯЗЫКЕ.
        Сосредоточься на:
        - Ключевых обсуждаемых темах
        - Важных решениях или объявлениях  
        - Пунктах действий или упомянутых задачах
        - Любых срочных вопросах
        
        КРИТИЧЕСКИ ВАЖНО: В конце каждого пункта сводки добавляй ссылку ТОЛЬКО из списка "Доступные ссылки на сообщения". 
        Формат: [Ссылка](точный_URL_из_списка)
        Пример: [Ссылка](https://t.me/c/2083014011/12094)
        
        НЕ создавай свои ссылки! Используй ТОЛЬКО те, что указаны в списке доступных ссылок.
        Сводка должна быть краткой, но информативной. ОБЯЗАТЕЛЬНО отвечай на русском языке."""
        
        # Prepare messages with links for LLM
        messages_with_links = messages
        if message_data:
            chat_id = 2083014011  # BitKogan / Development group ID
            # Add available links info to the prompt
            links_info = "\n\nДоступные ссылки на сообщения:\n"
            for msg in message_data:
                links_info += f"ID {msg['id']} ({msg['date']}): https://t.me/c/{chat_id}/{msg['id']}\n"
            messages_with_links += links_info
        
        chat_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Messages to summarize:\n\n{messages_with_links}")
        ]
        
        print("[DEBUG] Calling LLM for summarization")
        result = await llm._agenerate(chat_messages)
        summary = result.generations[0].message.content
        print(f"[DEBUG] Generated summary: {len(summary)} characters")
        
        # Add dates to summary points if we have message data
        if message_data:
            # Create a mapping of message IDs to dates for post-processing
            id_to_date = {msg['id']: msg['date'][:16].replace('T', ' ') for msg in message_data}  # Format: YYYY-MM-DD HH:MM
            
            # Add date info to summary (this is a simple approach - could be enhanced)
            summary += f"\n\n**Временные метки сообщений:**\n"
            for msg in message_data:
                date_formatted = msg['date'][:16].replace('T', ' ')  # YYYY-MM-DD HH:MM
                summary += f"• {date_formatted} - {msg['author']}: {msg['text'][:50]}...\n"
        
        return {"summary": summary}
    
    except Exception as e:
        print(f"[DEBUG] Error in summarize_messages_node: {e}")
        import traceback
        traceback.print_exc()
        return {"summary": f"Failed to generate summary: {str(e)}"}


async def send_to_telegram_node(state: SummaryState) -> Dict[str, Any]:
    """Send summary to Telegram channel."""
    print("[DEBUG] Starting send_to_telegram_node")
    
    summary = state.get("summary", "")
    if not summary or summary.startswith("Error:") or summary.startswith("Failed"):
        print("[DEBUG] No valid summary to send")
        return {"error": "No valid summary to send"}
    
    # Get the MCP session from state
    mcp_session = state.get("mcp_session")
    if not mcp_session:
        print("[DEBUG] No MCP session available, skipping send")
        return {"error": "No MCP session available"}
    
    try:
        chat_id = 2514401938  # infotest channel
        
        # Use the stored MCP client to send message
        success = await mcp_session.send_message_to_channel(chat_id, summary)
        
        if success:
            print(f"[DEBUG] Message sent successfully to channel {chat_id}")
            return {"error": ""}
        else:
            print(f"[DEBUG] Failed to send message to channel {chat_id}")
            return {"error": "Failed to send message to channel"}
        
    except Exception as e:
        print(f"[DEBUG] Error in send_to_telegram_node: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to send to Telegram: {str(e)}"}


def create_summary_workflow():
    """Create the LangGraph workflow for message summarization."""
    
    # Create the state graph
    workflow = StateGraph(SummaryState)
    
    # Add nodes
    workflow.add_node("fetch_messages", fetch_messages_node)
    workflow.add_node("summarize", summarize_messages_node)
    workflow.add_node("send_to_telegram", send_to_telegram_node)
    
    # Define the flow
    workflow.set_entry_point("fetch_messages")
    workflow.add_edge("fetch_messages", "summarize")
    workflow.add_edge("summarize", "send_to_telegram")
    workflow.add_edge("send_to_telegram", END)
    
    # Compile the graph
    return workflow.compile()


async def run_summary_workflow() -> str:
    """Run the complete summarization workflow."""
    workflow = create_summary_workflow()
    
    # Initialize state
    initial_state: SummaryState = {
        "messages": "",
        "summary": "",
        "error": "",
        "mcp_session": None
    }
    
    # Run the workflow
    result = await workflow.ainvoke(initial_state)
    
    return result.get("summary", "No summary generated")
