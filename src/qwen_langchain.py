"""LangChain integration for Qwen API."""

from typing import Any, Dict, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field
from .qwen_client import QwenClient


class QwenChatModel(BaseChatModel):
    """LangChain chat model for Qwen API."""
    
    qwen_client: QwenClient = Field(default_factory=QwenClient)
    model_name: str = Field(default="qwen3-coder-plus")
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def _llm_type(self) -> str:
        return "qwen"
    
    def _convert_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """Convert LangChain messages to Qwen API format."""
        converted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, SystemMessage):
                role = "system"
            else:
                role = "user"
            
            converted.append({"role": role, "content": msg.content})
        return converted
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate chat response asynchronously."""
        converted_messages = self._convert_messages(messages)
        
        response = await self.qwen_client.chat_completion(
            messages=converted_messages,
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        
        content = response["choices"][0]["message"]["content"]
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        
        return ChatResult(generations=[generation])
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation (not implemented for async-only client)."""
        raise NotImplementedError("Use async methods only")
