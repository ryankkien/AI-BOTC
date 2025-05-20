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
    #prepare dummy grimoire with game_log
    class DummyGrimoire: pass
    dummy = DummyGrimoire()
    dummy.game_log = [{"timestamp":"2020","event_type":"TEST","data":{}}]
    monkeypatch.setattr(game_manager, 'grimoire', dummy)
    cwd = os.getcwd()
    os.chdir(tmp_path)
    response = client.get("/save_logs")
    os.chdir(cwd)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "logs saved successfully"
    filepath = data["filepath"]
    file = tmp_path / filepath
    assert file.exists()
    shutil.rmtree(tmp_path / "logs", ignore_errors=True) 