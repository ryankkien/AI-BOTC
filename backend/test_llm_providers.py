#!/usr/bin/env python3
"""
Test script for the LLM abstraction system.
This script tests the LLM provider system without requiring actual API keys.
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_providers import LLMFactory, UnifiedLLMClient

def test_llm_factory():
    """Test the LLM factory without actual API calls."""
    print("Testing LLM Factory...")
    
    # Test auto detection (should default to Google since no API keys are set)
    try:
        provider = LLMFactory.create_provider("auto", "fake-api-key", "test-model")
        print(f"✓ Auto detection works: {type(provider).__name__}")
    except Exception as e:
        print(f"✗ Auto detection failed: {e}")
    
    # Test specific providers
    providers = ["openai", "anthropic", "google", "litellm"]
    for provider_type in providers:
        try:
            provider = LLMFactory.create_provider(provider_type, "fake-api-key", "test-model")
            print(f"✓ {provider_type.capitalize()} provider created: {type(provider).__name__}")
        except Exception as e:
            print(f"✗ {provider_type.capitalize()} provider failed: {e}")

def test_unified_client():
    """Test the unified client interface."""
    print("\nTesting Unified Client...")
    
    try:
        # Create a provider first
        provider = LLMFactory.create_provider("google", "fake-api-key", "gemini-1.5-flash")
        # Then create the unified client with the provider
        client = UnifiedLLMClient(provider)
        print(f"✓ Unified client created with Google provider")
        
        # Test that the client has the expected methods
        assert hasattr(client, 'generate_content_async'), "Missing generate_content_async method"
        assert hasattr(client, 'provider'), "Missing provider attribute"
        print("✓ Unified client has required methods")
        
    except Exception as e:
        print(f"✗ Unified client test failed: {e}")

def test_environment_loading():
    """Test environment variable loading."""
    print("\nTesting Environment Configuration...")
    
    # Load environment variables
    load_dotenv()
    
    # Test default values
    provider = os.getenv('LLM_PROVIDER', 'auto')
    model = os.getenv('LLM_MODEL', 'gemini-1.5-flash')
    min_interval = float(os.getenv('LLM_MIN_INTERVAL', '1.0'))
    
    print(f"✓ LLM_PROVIDER: {provider}")
    print(f"✓ LLM_MODEL: {model}")
    print(f"✓ LLM_MIN_INTERVAL: {min_interval}")
    
    # Test API key detection
    api_keys = {
        'OpenAI': os.getenv('OPENAI_API_KEY'),
        'Anthropic': os.getenv('ANTHROPIC_API_KEY'),
        'Google': os.getenv('GOOGLE_API_KEY'),
        'LiteLLM': os.getenv('LITELLM_API_KEY')
    }
    
    print("\nAPI Key Status:")
    for provider, key in api_keys.items():
        status = "✓ Set" if key else "✗ Not set"
        print(f"  {provider}: {status}")

if __name__ == "__main__":
    print("=== LLM Provider System Test ===\n")
    
    test_llm_factory()
    test_unified_client()
    test_environment_loading()
    
    print("\n=== Test Complete ===")
    print("\nTo use the system with real API keys:")
    print("1. Copy backend/.env.example to backend/.env")
    print("2. Add your API keys to the .env file")
    print("3. Set LLM_PROVIDER to your preferred provider")
    print("4. Run the main application") 