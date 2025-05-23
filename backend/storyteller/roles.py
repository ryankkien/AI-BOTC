#backend/storyteller/roles.py
from enum import Enum

class RoleAlignment(Enum):
    GOOD = "Good"
    EVIL = "Evil"

class RoleType(Enum):
    TOWNSFOLK = "Townsfolk"
    OUTSIDER = "Outsider"
    MINION = "Minion"
    DEMON = "Demon"

#this could be a list of dicts, or a dict of dicts, or a list of Role objects
#for now, a simple dictionary structure

ROLES_DATA = {
    #Townsfolk
    "Washerwoman": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "You start knowing that one of two players is a particular Townsfolk.",
        "first_night_ability": True,
        "detailed_first_night_info": True,
        "other_night_ability": False,
        "day_ability": False,
        "affects_setup": True #e.g. for fortune teller red herring selection
    },
    "Librarian": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "You start knowing that one of two players is a particular Outsider.",
        "first_night_ability": True,
        "detailed_first_night_info": True,
        "other_night_ability": False,
        "day_ability": False,
        "affects_setup": True
    },
    "Investigator": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "You start knowing that one of two players is a particular Minion.",
        "first_night_ability": True,
        "detailed_first_night_info": True,
        "other_night_ability": False,
        "day_ability": False,
        "affects_setup": True
    },
    "Chef": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "You start knowing if any two evil players are sitting next to each other.",
        "first_night_ability": True,
        "detailed_first_night_info": True,
        "other_night_ability": False,
        "day_ability": False
    },
    "Empath": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "Each night, you learn how many of your alive neighbors are evil.",
        "first_night_ability": True, #gets a 0, 1, or 2
        "detailed_first_night_info": True,
        "other_night_ability": True
    },
    "Fortune Teller": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "Each night, choose two players: you learn if either is a Demon. One of the two players you choose is the Demon, is a 'yes'. If one of the two players you choose is the Recluse, you may learn a 'no'. You have a red herring.",
        "first_night_ability": True,
        "other_night_ability": True,
        "has_red_herring": True
    },
    "Undertaker": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "Each night*, if a player was executed today, you learn their role.",
        "other_night_ability": True #* signifies not first night
    },
    "Monk": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "Each night*, choose a player (not yourself): they are safe from the Demon tonight.",
        "other_night_ability": True
    },
    "Ravenkeeper": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "If you die at night, you are woken to choose a player: you learn their role.",
        "on_death_night_ability": True
    },
    "Virgin": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "The first time you are nominated by a Townsfolk, they are executed immediately.",
        "day_ability": True, #triggered on nomination
        "once_per_game": True
    },
    "Slayer": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "Once per game, during the day, publicly choose a player. If they are the Demon, they die.",
        "day_ability": True,
        "once_per_game": True
    },
    "Soldier": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "You are safe from the Demon."
    },
    "Mayor": {
        "type": RoleType.TOWNSFOLK,
        "alignment": RoleAlignment.GOOD,
        "description": "If only 3 players live and no execution occurs, your team wins. If you die at night, another player might die instead.",
        "end_game_modifier": True,
        "on_death_night_ability_passive": True #not an action, but a consequence
    },

    #Outsiders
    "Butler": {
        "type": RoleType.OUTSIDER,
        "alignment": RoleAlignment.GOOD,
        "description": "Each night, choose a player (not yourself): tomorrow, you may only vote if they vote.",
        "other_night_ability": True
    },
    "Drunk": {
        "type": RoleType.OUTSIDER,
        "alignment": RoleAlignment.GOOD,
        "description": "You do not know you are the Drunk. You think you are a Townsfolk, but you are not. You have no ability.",
        "thinks_is_role": None, # Storyteller will assign a false Townsfolk identity
        "affects_setup": True
        #special handling: storyteller gives false info
    },
    "Recluse": {
        "type": RoleType.OUTSIDER,
        "alignment": RoleAlignment.GOOD,
        "description": "You might register as evil, or as a Minion or Demon, even if dead.",
        "can_misregister_as_evil": True, # ST LLM pre-determines a 'false persona'
        "affects_setup": True
        #special handling: can confuse Investigator, Fortune Teller, Empath, Undertaker, Ravenkeeper, Slayer
    },
    "Saint": {
        "type": RoleType.OUTSIDER,
        "alignment": RoleAlignment.GOOD,
        "description": "If you die by execution, your team loses.",
        "on_execution_modifier": True
    },

    #Minions
    "Poisoner": {
        "type": RoleType.MINION,
        "alignment": RoleAlignment.EVIL,
        "description": "Each night, choose a player: they are poisoned tonight and tomorrow day. Their ability malfunctions.",
        "other_night_ability": True,
        "knows_demon": True
    },
    "Spy": {
        "type": RoleType.MINION,
        "alignment": RoleAlignment.EVIL,
        "description": "Each night, you see the Grimoire. You might register as good, or as a Townsfolk or Outsider, even if dead.",
        "other_night_ability": True,
        "knows_demon": True
        #special handling: can confuse Investigator, Fortune Teller, Empath, Undertaker, Ravenkeeper, Slayer
    },
    "Scarlet Woman": {
        "type": RoleType.MINION,
        "alignment": RoleAlignment.EVIL,
        "description": "If the Demon dies and there are 5 or more players alive, you become the Demon.",
        "knows_demon": True,
        "promotion_ability": True
    },
    "Baron": {
        "type": RoleType.MINION,
        "alignment": RoleAlignment.EVIL,
        "description": "Setup: Add two Outsiders to the game.",
        "affects_setup": True,
        "knows_demon": True
    },

    #Demons
    "Imp": {
        "type": RoleType.DEMON,
        "alignment": RoleAlignment.EVIL,
        "description": "Each night*, choose a player: they die. If you kill yourself, a Minion becomes the Imp.",
        "other_night_ability": True,
        "demon_kill": True,
        "suicide_promotion": True #if self-target, new Imp (Scarlet Woman if in play and conditions met)
    }
}

def get_role_details(role_name: str):
    return ROLES_DATA.get(role_name)

def get_roles_by_type(role_type: RoleType):
    return {name: data for name, data in ROLES_DATA.items() if data["type"] == role_type}

def get_all_roles():
    return list(ROLES_DATA.keys()) 