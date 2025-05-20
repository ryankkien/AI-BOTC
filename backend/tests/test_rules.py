import pytest
from backend.storyteller.rules import RuleEnforcer
from backend.storyteller.grimoire import Grimoire
from backend.storyteller.roles import RoleAlignment

@pytest.fixture
def grimoire():
    return Grimoire()

@pytest.fixture
def rule_enforcer(grimoire):
    return RuleEnforcer(grimoire)


def test_execute_player_and_events(rule_enforcer):
    g = rule_enforcer.grimoire
    g.add_player('p1', 'Washerwoman', 'Good')
    rule_enforcer._execute_player('p1', 'executed by majority vote')
    assert not g.is_player_alive('p1')
    death_events = [e for e in g.game_log if e['event_type'] == 'DEATH']
    assert death_events
    data = death_events[0]['data']
    assert data['player_id'] == 'p1'
    assert data['role_at_death'] == 'Washerwoman'
    assert data['reason'] == 'executed by majority vote'
    rule_enforcer._execute_player('p1', 'executed again')
    assert any('attempted to execute already dead player p1' in msg.lower() for msg in g.storyteller_log)


def test_victory_no_players(rule_enforcer):
    victor, winner = rule_enforcer.check_victory_conditions()
    assert victor is True
    assert winner == 'No one (Draw)'


def test_victory_two_players_evil_wins(rule_enforcer):
    g = rule_enforcer.grimoire
    g.add_player('d1', 'Imp', 'Evil')
    g.add_player('p1', 'Washerwoman', 'Good')
    victor, winner = rule_enforcer.check_victory_conditions()
    assert victor is True
    assert winner == RoleAlignment.EVIL.value


def test_victory_two_good_players_no_victory(rule_enforcer):
    g = rule_enforcer.grimoire
    g.add_player('p1', 'Washerwoman', 'Good')
    g.add_player('p2', 'Librarian', 'Good')
    victor, winner = rule_enforcer.check_victory_conditions()
    assert victor is False
    assert winner is None


def test_victory_good_wins_after_demon_killed(rule_enforcer):
    g = rule_enforcer.grimoire
    g.add_player('d1', 'Imp', 'Evil')
    g.update_status('d1', 'alive', False)
    victor, winner = rule_enforcer.check_victory_conditions()
    assert victor is True
    assert winner == RoleAlignment.GOOD.value


def test_victory_saint_executed(rule_enforcer):
    g = rule_enforcer.grimoire
    g.add_player('s1', 'Saint', 'Good')
    g.add_player('d1', 'Imp', 'Evil')
    g.log_event('DEATH', {'player_id': 's1', 'reason': 'Executed by majority vote'})
    victor, winner = rule_enforcer.check_victory_conditions()
    assert victor is True
    assert winner == RoleAlignment.EVIL.value 