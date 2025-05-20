import pytest
from backend.storyteller.roles import get_role_details, get_roles_by_type, get_all_roles, RoleType, RoleAlignment


def test_get_role_details_valid():
    details = get_role_details("Washerwoman")
    assert isinstance(details, dict)
    assert details["alignment"] == RoleAlignment.GOOD
    assert details["type"] == RoleType.TOWNSFOLK


def test_get_role_details_invalid():
    assert get_role_details("Nonexistent") is None


def test_get_roles_by_type():
    townsfolk = get_roles_by_type(RoleType.TOWNSFOLK)
    assert isinstance(townsfolk, dict)
    assert "Washerwoman" in townsfolk
    for name, data in townsfolk.items():
        assert data["type"] == RoleType.TOWNSFOLK


def test_get_all_roles():
    roles = get_all_roles()
    assert isinstance(roles, list)
    assert "Imp" in roles 