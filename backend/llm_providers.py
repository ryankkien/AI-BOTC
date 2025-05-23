"""
LLM Provider Abstraction Layer
Supports OpenAI, Anthropic, Google Gemini, and other providers through a unified interface.
"""

import os
import asyncio
import time
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from datetime import datetime
import json

# Import different provider libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

load_dotenv()

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self._last_call_time: Optional[float] = None
        self.rate_limit_interval = float(os.getenv("LLM_MIN_INTERVAL", "1.0"))
    
    @abstractmethod
    async def generate_async(self, prompt: str, **kwargs) -> str:
        """Generate text asynchronously"""
        pass
    
    async def _rate_limit(self):
        """Apply rate limiting between calls"""
        if self._last_call_time is not None:
            elapsed = time.monotonic() - self._last_call_time
            if elapsed < self.rate_limit_interval:
                await asyncio.sleep(self.rate_limit_interval - elapsed)
        self._last_call_time = time.monotonic()


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-3.5, GPT-4, etc.)"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        self.client = openai.AsyncOpenAI(api_key=self.api_key)
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        await self._rate_limit()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-sonnet-20240229"):
        super().__init__(api_key, model)
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key not provided")
        
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        await self._rate_limit()
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")


class GoogleProvider(LLMProvider):
    """Google Gemini API provider (existing implementation)"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-1.5-flash-latest"):
        super().__init__(api_key, model)
        if not GOOGLE_AVAILABLE:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided")
        
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        await self._rate_limit()
        
        try:
            response = await self.client.generate_content_async(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Google API error: {e}")


class LiteLLMProvider(LLMProvider):
    """LiteLLM provider for unified access to multiple LLM APIs"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)
        if not LITELLM_AVAILABLE:
            raise ImportError("litellm package not installed. Run: pip install litellm")
        
        # Set API keys for litellm
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
        
        # Set other API keys from environment
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "COHERE_API_KEY"]:
            if os.getenv(key):
                os.environ[key] = os.getenv(key)
    
    async def generate_async(self, prompt: str, **kwargs) -> str:
        await self._rate_limit()
        
        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                **{k: v for k, v in kwargs.items() if k not in ["max_tokens", "temperature"]}
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LiteLLM API error: {e}")


class LLMFactory:
    """Factory class to create LLM providers based on configuration"""
    
    @staticmethod
    def create_provider(provider_type: str = None, api_key: str = None, model: str = None) -> LLMProvider:
        """
        Create an LLM provider based on type and configuration.
        
        Args:
            provider_type: Type of provider ("openai", "anthropic", "google", "litellm")
            api_key: API key for the provider
            model: Model name to use
        
        Returns:
            LLMProvider instance
        """
        # Auto-detect provider type if not specified
        if not provider_type:
            provider_type = os.getenv("LLM_PROVIDER", "auto")
        
        if provider_type == "auto":
            # Auto-detect based on available API keys
            if os.getenv("OPENAI_API_KEY") or api_key:
                provider_type = "openai"
            elif os.getenv("ANTHROPIC_API_KEY"):
                provider_type = "anthropic"
            elif os.getenv("GOOGLE_API_KEY"):
                provider_type = "google"
            else:
                provider_type = "litellm"  # Fallback to litellm
        
        # Set default models based on provider
        if not model:
            model_defaults = {
                "openai": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                "google": os.getenv("GOOGLE_MODEL", "gemini-1.5-flash-latest"),
                "litellm": os.getenv("LITELLM_MODEL", "gpt-3.5-turbo")
            }
            model = model_defaults.get(provider_type, "gpt-3.5-turbo")
        
        # Create provider instance
        if provider_type == "openai":
            return OpenAIProvider(api_key=api_key, model=model)
        elif provider_type == "anthropic":
            return AnthropicProvider(api_key=api_key, model=model)
        elif provider_type == "google":
            return GoogleProvider(api_key=api_key, model=model)
        elif provider_type == "litellm":
            return LiteLLMProvider(api_key=api_key, model=model)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")


# Global rate limiting for all providers
_global_rate_limit_lock = asyncio.Lock()
_last_global_call_time: Optional[float] = None

async def global_rate_limit():
    """Global rate limiting across all LLM providers"""
    global _last_global_call_time
    min_interval = float(os.getenv("LLM_MIN_INTERVAL", "1.0"))
    
    async with _global_rate_limit_lock:
        now = time.monotonic()
        if _last_global_call_time is not None:
            elapsed = now - _last_global_call_time
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
        _last_global_call_time = time.monotonic()


class UnifiedLLMClient:
    """Unified client that wraps any LLM provider with consistent interface"""
    
    def __init__(self, provider: LLMProvider, game_manager=None):
        self.provider = provider
        self.game_manager = game_manager
    
    async def generate_content_async(self, prompt: str, **kwargs) -> 'MockResponse':
        """Generate content with unified interface matching the original Gemini interface"""
        await global_rate_limit()
        
        timestamp = datetime.utcnow().isoformat()
        agent_id = getattr(self, '_agent_id', 'unknown')
        
        # Debug logging for prompt
        if self.game_manager:
            try:
                await self.game_manager.broadcast_message("LLM_DEBUG", {
                    "agent": agent_id,
                    "type": "prompt",
                    "content": prompt,
                    "provider": type(self.provider).__name__,
                    "timestamp": timestamp,
                    "prompt_length": len(prompt),
                    "kwargs": kwargs
                })
            except Exception as e:
                print(f"Debug logging error (prompt): {e}")
        
        try:
            start_time = time.time()
            response_text = await self.provider.generate_async(prompt, **kwargs)
            end_time = time.time()
            
            # Debug logging for response
            if self.game_manager:
                try:
                    await self.game_manager.broadcast_message("LLM_DEBUG", {
                        "agent": agent_id,
                        "type": "response",
                        "content": response_text,
                        "provider": type(self.provider).__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                        "response_length": len(response_text),
                        "generation_time_seconds": round(end_time - start_time, 2),
                        "prompt_hash": hash(prompt) % 10000  # Simple hash for correlation
                    })
                except Exception as e:
                    print(f"Debug logging error (response): {e}")
            
            return MockResponse(response_text)
        except Exception as e:
            # Debug logging for errors
            if self.game_manager:
                try:
                    await self.game_manager.broadcast_message("LLM_DEBUG", {
                        "agent": agent_id,
                        "type": "error",
                        "content": str(e),
                        "provider": type(self.provider).__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                        "prompt_hash": hash(prompt) % 10000
                    })
                except Exception:
                    pass
            print(f"LLM generation error: {e}")
            raise
    
    def set_agent_id(self, agent_id: str):
        """Set agent ID for debugging purposes"""
        self._agent_id = agent_id


class MockResponse:
    """Mock response object to match Gemini's response interface"""
    
    def __init__(self, text: str):
        self.text = text 