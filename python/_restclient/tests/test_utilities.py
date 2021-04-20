#!/usr/bin/env python3

import pytest
from hydrotools._restclient import utilities


@pytest.fixture
def alias_fixture():
    return utilities.Alias("key", "value")


test_instance_args = [
    ("this", "that"),
    (1, 2),
    (1.0, 2.0),
    (lambda x: x, (1, 2)),
    ((1, 2), "key"),
]


@pytest.mark.parametrize("key,value", test_instance_args)
def test_instance_alias(key, value):
    """ Test inputs that can instantiate the class"""
    utilities.Alias(key, value)


def test_cannot_alter_alias_key(alias_fixture):
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        alias_fixture.key = "that"


def test_cannot_alter_alias_key(alias_fixture):
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        alias_fixture.value = "that"


def test_pass_mutable_as_key_then_try_to_change_implicitly_by_ref():
    mute = ["mutable"]
    inst = utilities.Alias(mute, "value")

    assert "mutable" in inst.key

    mute.pop()

    assert "mutable" in inst.key


def test_pass_mutable_as_value_then_try_to_change_implicitly_by_ref():
    mute = ["mutable"]
    inst = utilities.Alias("key", mute)

    assert "mutable" in inst

    mute.pop()

    assert "mutable" in inst


def test_get(alias_fixture):
    assert alias_fixture.key == alias_fixture.get("value")


def test__getitem__(alias_fixture):
    assert alias_fixture.key == alias_fixture["value"]
