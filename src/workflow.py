"""LangGraph workflow for Telegram message processing."""

from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from .qwen_langchain import QwenChatModel
from .telegram_mcp import TelegramMCPClient


class ProcessingState(TypedDict):
    """State for the message processing workflow."""
    source_channels: List[str]  # List of channel names/IDs to fetch from
    time_period_minutes: int    # How many minutes back to fetch
    target_channel: str         # Channel to send results to
    raw_messages: List[Dict]    # Raw messages from Telegram
    processed_messages: List[Dict]  # Messages after AI analysis
    error: str
    mcp_session: Any           # Store MCP session for reuse
    custom_filter_rules: List[str]  # Custom filtering rules


async def fetch_messages_from_channels_node(state: ProcessingState) -> Dict[str, Any]:
    """Fetch messages from specified Telegram channels for given time period."""
    print("[DEBUG] Starting fetch_messages_from_channels_node")
    
    try:
        from .telegram_mcp_client import TelegramMCPClient
        telegram_client = TelegramMCPClient()
        
        all_messages = []
        source_channels = state.get("source_channels", ["BitKogan / Development"])
        time_period = state.get("time_period_minutes", 10)
        
        for channel in source_channels:
            print(f"[DEBUG] Fetching from channel: {channel}")
            messages = await telegram_client.get_recent_messages(
                chat_name=channel,
                minutes_back=time_period
            )
            all_messages.extend(messages)
        
        print(f"[DEBUG] Total messages fetched: {len(all_messages)}")
        
        return {
            "raw_messages": all_messages,
            "error": "",
            "mcp_session": telegram_client
        }
        
    except Exception as e:
        print(f"[DEBUG] Error fetching messages: {e}")
        return {
            "raw_messages": [],
            "error": f"Failed to fetch messages: {str(e)}",
            "mcp_session": None
        }


async def analyze_messages_node(state: ProcessingState) -> Dict[str, Any]:
    """Analyze each message individually: rephrase or filter out."""
    print("[DEBUG] Starting analyze_messages_node")
    
    raw_messages = state.get("raw_messages", [])
    if not raw_messages:
        return {"processed_messages": []}
    
    print(f"[DEBUG] First message structure: {raw_messages[0] if raw_messages else 'No messages'}")
    
    try:
        # Get current user info for mention detection
        mcp_session = state.get("mcp_session")
        user_mentions = []
        if mcp_session:
            try:
                user_info = await mcp_session.get_current_user()
                if user_info.get('username'):
                    user_mentions.append(f"@{user_info['username']}")
                if user_info.get('first_name'):
                    user_mentions.append(user_info['first_name'])
                if user_info.get('name'):
                    user_mentions.append(user_info['name'])
                user_mentions = [m for m in user_mentions if m and m != '@']
                print(f"[DEBUG] User mentions to check: {user_mentions}")
            except Exception as e:
                print(f"[DEBUG] Could not get user info: {e}")
        
        llm = QwenChatModel()
        processed_messages = []
        
        mentions_text = ", ".join(user_mentions) if user_mentions else "не указаны"
        
        # Build custom filter rules text
        custom_rules_text = ""
        custom_filter_rules = state.get("custom_filter_rules", [])
        if custom_filter_rules:
            custom_rules_text = "\n\nДОПОЛНИТЕЛЬНЫЕ ПРАВИЛА ФИЛЬТРАЦИИ:\n" + "\n".join(f"- {rule}" for rule in custom_filter_rules)
        
        system_prompt = f"""Ты анализируешь сообщения из IT-чата разработчиков. Для каждого сообщения выполни одно из действий:

1. ПЕРЕФРАЗИРОВАТЬ - если сообщение содержит полезную информацию (включая реакции на важные темы, планы, решения)
2. ОТФИЛЬТРОВАТЬ - только если сообщение явно бесполезное (спам, одиночные эмодзи, "ок", "да", "+1")

ВАЖНО: 
- Реакции на важные темы, обещания изучить что-то, планы встреч - это полезная информация, НЕ фильтруй их
- "прод" = "продакшн" (production), не "продажа"
- Сохраняй IT-терминологию: релиз, хотфикс, бэкенд, эндпоинт, аппрув и т.д.
- Используй ТОЛЬКО русский язык, английский допустим только для устоявшихся IT-терминов (API, backend, frontend, deploy и т.д.)
- Сохраняй английские слова из оригинального сообщения, но не добавляй новые английские слова
- При перефразировании используй только русские слова: "впечатляющий" вместо "impressive", "отзыв" вместо "feedback"
- ОБЯЗАТЕЛЬНО сохраняй все упоминания пользователей (@username) из оригинального сообщения
- НЕ используй квадратные скобки [ ] в тексте - они мешают Markdown ссылкам{custom_rules_text}

ДОПОЛНИТЕЛЬНО: Определи, упомянут ли ТОЧНО текущий пользователь в сообщении.
Текущий пользователь может быть упомянут как: {mentions_text}
ВНИМАНИЕ: Ставь mentioned=true ТОЛЬКО если в тексте есть ТОЧНОЕ совпадение с одним из вариантов выше.

Отвечай ТОЛЬКО в формате JSON:
{{"action": "rephrase", "text": "исправленный текст", "mentioned": true/false}}
или
{{"action": "filter", "reason": "причина фильтрации", "mentioned": false}}

Перефразируй на правильном русском языке, сохраняя смысл и IT-контекст."""
        
        for msg in raw_messages:
            try:
                message_text = msg.get('text', '')
                context = msg.get('context', '')
                
                # Prepare full context for analysis
                full_context = f"Сообщение: {message_text}"
                if context:
                    full_context += f"\nКонтекст (на что отвечает): {context}"
                
                chat_messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=full_context)
                ]
                
                result = await llm._agenerate(chat_messages)
                response = result.generations[0].message.content
                
                import json
                analysis = json.loads(response)
                
                print(f"[DEBUG] Message from {msg.get('author')}: {msg.get('text')[:50]}...")
                print(f"[DEBUG] AI decision: {analysis}")
                
                if analysis.get("action") == "rephrase":
                    processed_msg = msg.copy()
                    processed_msg["text"] = analysis["text"]
                    processed_msg["mentioned"] = analysis.get("mentioned", False)
                    processed_messages.append(processed_msg)
                else:
                    print(f"[DEBUG] Filtered out: {analysis.get('reason', 'No reason')}")
                    
            except Exception as e:
                print(f"[DEBUG] Error analyzing message: {e}")
                # Keep original message if analysis fails
                processed_messages.append(msg)
        
        print(f"[DEBUG] Processed {len(processed_messages)} out of {len(raw_messages)} messages")
        
        return {"processed_messages": processed_messages}
        
    except Exception as e:
        print(f"[DEBUG] Error in analyze_messages_node: {e}")
        return {"processed_messages": raw_messages}  # Fallback to original messages


async def send_results_node(state: ProcessingState) -> Dict[str, Any]:
    """Send processed messages to target Telegram channel."""
    print("[DEBUG] Starting send_results_node")
    
    processed_messages = state.get("processed_messages", [])
    target_channel = state.get("target_channel", "infotest")
    mcp_session = state.get("mcp_session")
    
    if not processed_messages:
        print("[DEBUG] No processed messages to send")
        return {"error": "No messages to send"}
    
    if not mcp_session:
        print("[DEBUG] No MCP session available")
        return {"error": "No MCP session available"}
    
    try:
        # Calculate time period info
        from datetime import datetime, timezone, timedelta
        now_msk = datetime.now(timezone(timedelta(hours=3)))
        
        # Always show period as "from X to Y" format
        if state.get("time_period_minutes"):
            # Custom period
            start_time = now_msk - timedelta(minutes=state["time_period_minutes"])
            period_text = f"с {start_time.strftime('%H:%M')} до {now_msk.strftime('%H:%M')} MSK"
        else:
            # Default: from 8 AM MSK today
            today_8am = now_msk.replace(hour=8, minute=0, second=0, microsecond=0)
            if now_msk < today_8am:
                # If it's before 8 AM, use yesterday 8 AM
                today_8am -= timedelta(days=1)
            period_text = f"с {today_8am.strftime('%H:%M')} до {now_msk.strftime('%H:%M')} MSK"
        
        # Get source channel name
        source_channels = state.get("source_channels", ["BitKogan / Development"])
        channel_text = ", ".join(source_channels)
        
        # Format messages for sending
        formatted_text = f"Сводка сообщений из {channel_text} {period_text}\n\n"
        
        chat_id = 2083014011  # BitKogan / Development group ID for links
        
        message_parts = []
        current_part = formatted_text
        
        for i, msg in enumerate(processed_messages, 1):
            author = msg.get("author", "Unknown")
            text = msg.get("text", "")
            date_str = msg.get("date", "")
            msg_id = msg.get("id", "")
            is_mentioned = msg.get("mentioned", False)  # Use AI-determined mention flag
            
            mention_prefix = "🔔 " if is_mentioned else ""
            
            print(f"[DEBUG] Message {msg_id}: mentioned={is_mentioned} (AI-determined)")
            
            # Convert UTC to MSK and format
            if date_str:
                from datetime import datetime, timezone, timedelta
                try:
                    # Parse UTC datetime
                    utc_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # Convert to MSK (UTC+3)
                    msk_dt = utc_dt.astimezone(timezone(timedelta(hours=3)))
                    date_formatted = msk_dt.strftime("%Y-%m-%d %H:%M MSK")
                except:
                    date_formatted = date_str[:16].replace('T', ' ') + " MSK"
            else:
                date_formatted = "Unknown MSK"
            
            # Create Telegram link
            link = f"https://t.me/c/{chat_id}/{msg_id}" if msg_id else ""
            link_text = f" [Ссылка]({link})" if link else ""
            
            message_entry = f"{mention_prefix}{i}. **{author}** ({date_formatted}):\n{text}{link_text}\n\n"
            
            # Check if adding this message would exceed Telegram's limit (4096 chars)
            if len(current_part + message_entry) > 4000:  # Leave some margin
                message_parts.append(current_part.strip())
                current_part = f"Сводка сообщений из {channel_text} {period_text} (продолжение)\n\n" + message_entry
            else:
                current_part += message_entry
        
        # Add the last part
        if current_part.strip():
            message_parts.append(current_part.strip())
        
        # Send all parts
        target_chat_id = 2514401938 if target_channel == "infotest" else target_channel
        success_count = 0
        
        for part_num, part_text in enumerate(message_parts, 1):
            if len(message_parts) > 1:
                part_header = f"Часть {part_num}/{len(message_parts)}\n\n"
                part_text = part_header + part_text
            
            success = await mcp_session.send_message_to_channel(target_chat_id, part_text)
            if success:
                success_count += 1
                print(f"[DEBUG] Successfully sent part {part_num}/{len(message_parts)}")
            else:
                print(f"[DEBUG] Failed to send part {part_num}/{len(message_parts)}")
        
        if success_count == len(message_parts):
            print(f"[DEBUG] Successfully sent all {len(message_parts)} parts with {len(processed_messages)} messages to {target_channel}")
            return {"error": ""}
        else:
            return {"error": f"Failed to send {len(message_parts) - success_count} out of {len(message_parts)} parts"}
            
    except Exception as e:
        print(f"[DEBUG] Error in send_results_node: {e}")
        return {"error": f"Failed to send results: {str(e)}"}


def create_processing_workflow():
    """Create the LangGraph workflow for message processing."""
    
    workflow = StateGraph(ProcessingState)
    
    # Add nodes
    workflow.add_node("fetch_messages", fetch_messages_from_channels_node)
    workflow.add_node("analyze_messages", analyze_messages_node)
    workflow.add_node("send_results", send_results_node)
    
    # Define the flow
    workflow.set_entry_point("fetch_messages")
    workflow.add_edge("fetch_messages", "analyze_messages")
    workflow.add_edge("analyze_messages", "send_results")
    workflow.add_edge("send_results", END)
    
    return workflow.compile()


async def run_processing_workflow(
    source_channels: List[str] = None,
    time_period_minutes: int = None,  # None = from 8 AM MSK today
    target_channel: str = "infotest",
    custom_filter_rules: List[str] = None
) -> str:
    """Run the complete message processing workflow."""
    
    if source_channels is None:
        source_channels = ["BitKogan / Development"]
    
    # Calculate default period (from 8 AM MSK today)
    if time_period_minutes is None:
        from datetime import datetime, timezone, timedelta
        now_msk = datetime.now(timezone(timedelta(hours=3)))
        today_8am = now_msk.replace(hour=8, minute=0, second=0, microsecond=0)
        if now_msk < today_8am:
            today_8am -= timedelta(days=1)
        time_period_minutes = int((now_msk - today_8am).total_seconds() / 60)
    
    workflow = create_processing_workflow()
    
    initial_state: ProcessingState = {
        "source_channels": source_channels,
        "time_period_minutes": time_period_minutes,
        "target_channel": target_channel,
        "raw_messages": [],
        "processed_messages": [],
        "error": "",
        "mcp_session": None,
        "custom_filter_rules": custom_filter_rules or []
    }
    
    result = await workflow.ainvoke(initial_state)
    
    if result.get("error"):
        return f"Error: {result['error']}"
    
    processed_count = len(result.get("processed_messages", []))
    return f"Successfully processed and sent {processed_count} messages"
