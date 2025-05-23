import os
import shutil
import pytest
from fastapi.testclient import TestClient
from backend.main import app, game_manager

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "<html>" in response.text


def test_save_logs_no_game(monkeypatch):
    #simulate no game in progress by setting grimoire to none
    monkeypatch.setattr(game_manager, 'grimoire', None)
    response = client.get("/save_logs")
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert data["error"] == "no game in progress to save logs"


def test_save_logs_creates_file(tmp_path, monkeypatch):
    #prepare dummy grimoire with comprehensive game data
    class DummyGrimoire: 
        def __init__(self):
            self.game_log = [{"timestamp":"2020","event_type":"TEST","data":{}}]
            self.storyteller_log = ["Test storyteller message"]
            self.current_phase = "DAY_CHAT"
            self.day_number = 1
            self.players = ["player1", "player2"]
            self.roles = {"player1": "Villager", "player2": "Demon"}
            self.alignments = {"player1": "Good", "player2": "Evil"}
            self.statuses = {"player1": {"alive": True}, "player2": {"alive": True}}
            self.demon_bluffs = []
            self.fortune_teller_red_herring_player_id = None
            self.current_demon_player_id = "player2"
            self.baron_added_outsiders = []
            self.private_clues = {}
            self.game_state = {}
    
    class DummyGameManager:
        def __init__(self):
            self.grimoire = DummyGrimoire()
            self._daily_chat_log = [{"sender": "player1", "text": "Hello"}]
            self.agents = {}
            self.storyteller_agent = type('obj', (object,), {})()
            self._game_started_event = type('obj', (object,), {'is_set': lambda: True})()
            self._current_nominating_player_index = 0
            self._nomination_order = []
    
    dummy_manager = DummyGameManager()
    monkeypatch.setattr('backend.main.game_manager', dummy_manager)
    
    cwd = os.getcwd()
    os.chdir(tmp_path)
    response = client.get("/save_logs")
    os.chdir(cwd)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "comprehensive logs saved successfully"
    filepath = data["filepath"]
    file = tmp_path / filepath
    assert file.exists()
    
    # Verify the comprehensive log structure
    import json
    with open(file, 'r') as f:
        saved_data = json.load(f)
    
    assert "metadata" in saved_data
    assert "game_log" in saved_data
    assert "storyteller_log" in saved_data
    assert "daily_chat_log" in saved_data
    assert "game_state" in saved_data
    assert "agent_memories" in saved_data
    assert saved_data["metadata"]["game_phase"] == "DAY_CHAT"
    assert saved_data["metadata"]["day_number"] == 1
    
    shutil.rmtree(tmp_path / "logs", ignore_errors=True) 