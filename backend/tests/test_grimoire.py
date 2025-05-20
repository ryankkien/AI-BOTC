import pytest
from backend.storyteller.grimoire import Grimoire


def test_initial_state():
    g = Grimoire()
    assert g.game_state == {}
    assert g.players == []
    assert g.roles == {}
    assert g.alignments == {}
    assert g.statuses == {}
    assert g.game_log == []
    assert g.day_number == 0
    assert g.current_phase is None


def test_add_player_and_getters_and_log_event(capfd):
    g = Grimoire()
    # setup player names in game state for observer
    g.game_state['player_names'] = {'p1': 'Alice'}
    g.add_player('p1', 'Washerwoman', 'Good')
    # verify internal state
    assert 'p1' in g.players
    assert g.get_player_role('p1') == 'Washerwoman'
    assert g.get_player_alignment('p1') == 'Good'
    assert g.is_player_alive('p1') is True
    # default statuses include 'alive'
    assert g.get_player_status('p1', 'alive') is True
    # log_event should have been called
    logged = [e for e in g.game_log if e['event_type'] == 'PLAYER_ADDED']
    assert len(logged) == 1


def test_update_status_and_invalid_key(capfd):
    g = Grimoire()
    g.add_player('p1', 'Librarian', 'Good')
    # valid update
    g.update_status('p1', 'alive', False)
    assert g.get_player_status('p1', 'alive') is False
    statuses_updated = [e for e in g.game_log if e['event_type'] == 'STATUS_UPDATE']
    assert statuses_updated and statuses_updated[0]['data']['status'] == 'alive'
    # invalid update
    g.update_status('p1', 'nonexistent', True)
    # should append warning to storyteller_log
    assert any('could not update status' in msg.lower() for msg in g.storyteller_log)


def test_log_event_phase_change():
    g = Grimoire()
    # change phase and day number
    g.log_event('PHASE_CHANGE', {'new_phase': 'DAY_CHAT', 'day_number': 2})
    assert g.current_phase == 'DAY_CHAT'
    assert g.day_number == 2


def test_private_clues():
    g = Grimoire()
    g.add_player('p2', 'Empath', 'Good')
    clue = {'night': 1, 'text': 'No evil neighbors'}
    g.add_private_clue('p2', clue)
    assert g.get_private_clues('p2') == [clue]
    assert any(e['event_type'] == 'PRIVATE_INFO' for e in g.game_log)


def test_get_all_and_public_player_info():
    g = Grimoire()
    g.game_state['player_names'] = {'p3': 'Bob'}
    g.add_player('p3', 'Chef', 'Good')
    # change alive status
    g.update_status('p3', 'alive', False)
    observer_info = g.get_all_player_info_for_observer()
    assert isinstance(observer_info, list)
    info = observer_info[0]
    assert info['id'] == 'p3'
    assert info['name'] == 'Bob'
    assert info['role'] == 'Chef'
    assert info['alignment'] == 'Good'
    assert info['status']['alive'] is False

    public_info = g.get_public_player_info()
    assert public_info[0]['id'] == 'p3'
    assert public_info[0]['name'] == 'Bob'
    assert public_info[0]['isAlive'] is False


def test_player_queries():
    g = Grimoire()
    g.add_player('p4', 'Imp', 'Evil')
    g.add_player('p5', 'Washerwoman', 'Good')
    # by role
    assert 'p4' in g.get_player_ids_by_role('Imp')
    # by alignment
    assert 'p5' in g.get_player_ids_by_alignment('Good')
    # alive players
    assert 'p4' in g.get_alive_players()
    # after death
    g.update_status('p4', 'alive', False)
    assert 'p4' not in g.get_alive_players() 