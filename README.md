# Blood on the Clocktower - Trouble Brewing AI Simulation

This project provides a fully autonomous simulation of the "Trouble Brewing" edition of Blood on the Clocktower,
with 10 AI-driven players powered by multiple LLM providers and a WebSocket-based observer interface.

## Features

- **Multi-LLM Support**: Compatible with OpenAI GPT, Anthropic Claude, Google Gemini, and other providers
- **Flexible Configuration**: Easy switching between different LLM providers and models
- **Storyteller AI**: LLM-powered Storyteller enforces game rules, phases, and win conditions
- **AI Agents**: Players communicate publicly and privately with intelligent decision-making
- **Observer UI**: Real-time game events and AI chat monitoring
- **Detailed Rules**: Complete implementation of 'Trouble Brewing' roles and interactions

## Supported LLM Providers

- **OpenAI**: GPT-3.5-turbo, GPT-4, GPT-4-turbo, and other models
- **Anthropic**: Claude-3 Sonnet, Claude-3 Haiku, and other models  
- **Google**: Gemini 1.5 Flash, Gemini 1.5 Pro, and other models
- **LiteLLM**: Unified access to 100+ LLM providers (Cohere, Together AI, etc.)

## Prerequisites

- Python 3.10 or higher
- An API key for at least one supported LLM provider
- (Optional) Node.js 14+ to run the React frontend in `frontend/`

## Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ryankkien/AI-BOTC
   cd AI-BOTC/backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend/` directory. You can copy from `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Configure your LLM provider in the `.env` file:

   **For OpenAI (recommended for beginners):**
   ```dotenv
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-3.5-turbo
   LLM_MIN_INTERVAL=1.0
   ```

   **For Anthropic Claude:**
   ```dotenv
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ANTHROPIC_MODEL=claude-3-sonnet-20240229
   LLM_MIN_INTERVAL=1.0
   ```

   **For Google Gemini:**
   ```dotenv
   LLM_PROVIDER=google
   GOOGLE_API_KEY=your_google_api_key_here
   GOOGLE_MODEL=gemini-1.5-flash-latest
   LLM_MIN_INTERVAL=6.0
   ```

   **For Auto-detection (tries available providers):**
   ```dotenv
   LLM_PROVIDER=auto
   OPENAI_API_KEY=your_openai_api_key_here
   # Add other API keys as available
   LLM_MIN_INTERVAL=1.0
   ```

6. Start the backend server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

7. Open your browser at `http://localhost:8000` to observe the simulation.

## Configuration Options

### Environment Variables

- `LLM_PROVIDER`: Choose provider ("openai", "anthropic", "google", "litellm", "auto")
- `LLM_MODEL`: Override default model for the chosen provider
- `LLM_MIN_INTERVAL`: Seconds between LLM calls (respect rate limits)
- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key  
- `GOOGLE_API_KEY`: Your Google API key

### Model Recommendations

**For fast gameplay:**
- OpenAI: `gpt-3.5-turbo` (fast, cost-effective)
- Google: `gemini-1.5-flash-latest` (fast, free tier available)

**For higher quality:**
- OpenAI: `gpt-4` or `gpt-4-turbo` (slower, more expensive)
- Anthropic: `claude-3-sonnet-20240229` (excellent reasoning)

## Frontend Setup (Optional)

If you prefer to run the standalone React frontend:

1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Start the React development server:
   ```bash
   npm start
   ```

4. Open `http://localhost:3000` in your browser.

## Troubleshooting

### Common Issues

1. **"No API key found"**: Make sure you've set the correct API key in your `.env` file
2. **Rate limit errors**: Increase `LLM_MIN_INTERVAL` in your `.env` file
3. **Import errors**: Make sure all dependencies are installed with `pip install -r requirements.txt`

### Provider-Specific Notes

- **OpenAI**: Requires a paid account for API access
- **Anthropic**: Requires Claude API access (separate from ChatGPT)
- **Google**: Offers free tier with rate limits
- **LiteLLM**: Supports many providers but may require additional configuration

## API Cost Considerations

Different providers have different pricing models:
- OpenAI GPT-3.5-turbo: ~$0.002 per 1K tokens
- Anthropic Claude-3 Sonnet: ~$0.015 per 1K tokens  
- Google Gemini: Free tier available, then ~$0.001 per 1K tokens

A typical game generates 50K-100K tokens total across all players and the storyteller.

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests. 