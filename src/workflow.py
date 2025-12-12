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


async def fetch_messages_node(state: SummaryState) -> Dict[str, Any]:
    """Fetch recent messages from Telegram."""
    print("[DEBUG] Starting fetch_messages_node")
    try:
        # Use mock client for now since telegram-mcp has connection issues
        from .telegram_mock import TelegramMockClient
        telegram_client = TelegramMockClient()
        print("[DEBUG] Created TelegramMockClient")
        
        messages = await telegram_client.get_recent_messages(
            chat_name="BitKogan / Development",
            minutes_back=10
        )
        print(f"[DEBUG] Fetched {len(messages)} messages")
        
        formatted_messages = telegram_client.format_messages_for_summary(messages)
        print(f"[DEBUG] Formatted messages length: {len(formatted_messages)}")
        
        return {
            "messages": formatted_messages,
            "error": ""
        }
    except Exception as e:
        print(f"[DEBUG] Error in fetch_messages_node: {e}")
        import traceback
        traceback.print_exc()
        return {
            "messages": "",
            "error": f"Failed to fetch messages: {str(e)}"
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
    
    try:
        print("[DEBUG] Creating QwenChatModel")
        llm = QwenChatModel()
        
        system_prompt = """You are a helpful assistant that summarizes Telegram chat messages.
        
        Please provide a concise summary of the following messages from the last 10 minutes.
        Focus on:
        - Key topics discussed
        - Important decisions or announcements
        - Action items or tasks mentioned
        - Any urgent matters
        
        Keep the summary brief but informative."""
        
        chat_messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Messages to summarize:\n\n{messages}")
        ]
        
        print("[DEBUG] Calling LLM for summarization")
        result = await llm._agenerate(chat_messages)
        summary = result.generations[0].message.content
        print(f"[DEBUG] Generated summary: {len(summary)} characters")
        
        return {"summary": summary}
    
    except Exception as e:
        print(f"[DEBUG] Error in summarize_messages_node: {e}")
        import traceback
        traceback.print_exc()
        return {"summary": f"Failed to generate summary: {str(e)}"}


def create_summary_workflow():
    """Create the LangGraph workflow for message summarization."""
    
    # Create the state graph
    workflow = StateGraph(SummaryState)
    
    # Add nodes
    workflow.add_node("fetch_messages", fetch_messages_node)
    workflow.add_node("summarize", summarize_messages_node)
    
    # Define the flow
    workflow.set_entry_point("fetch_messages")
    workflow.add_edge("fetch_messages", "summarize")
    workflow.add_edge("summarize", END)
    
    # Compile the graph
    return workflow.compile()


async def run_summary_workflow() -> str:
    """Run the complete summarization workflow."""
    workflow = create_summary_workflow()
    
    # Initialize state
    initial_state: SummaryState = {
        "messages": "",
        "summary": "",
        "error": ""
    }
    
    # Run the workflow
    result = await workflow.ainvoke(initial_state)
    
    return result.get("summary", "No summary generated")
