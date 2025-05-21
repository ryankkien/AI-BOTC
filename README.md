# Blood on the Clocktower - Trouble Brewing AI Simulation

This project provides a fully autonomous simulation of the "Trouble Brewing" edition of Blood on the Clocktower,
with 10 AI-driven players powered by Google Gemini and a WebSocket-based observer interface.

## Features

- Storyteller enforces game rules, phases, and win conditions
- AI Agents communicate publicly and privately with rate limiting
- Observer UI to watch game events and AI chat in real time
- Detailed rule implementation for various 'Trouble Brewing' roles, including complex interactions like Poisoner effects, Imp promotions, Mayor saves, specific first-night information, and nuanced victory conditions.

## Prerequisites

- Python 3.10 or higher
- A Google Cloud API key with access to Gemini (set in `.env`)
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
   # windows
env\Scripts\activate
   # macos/linux
source venv/bin/activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend/` directory containing:
   ```dotenv
   GOOGLE_API_KEY=your_google_gemini_api_key_here
   LLM_MIN_INTERVAL=6.0  # seconds between LLM calls (10 RPM limit)
   ```

5. Start the backend server:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Open your browser at `http://localhost:8000` to observe the simulation.

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

## .gitignore

This project ignores Python venvs, `.env` files, Node modules, IDE configs, and other common artifacts.

## License

MIT License 