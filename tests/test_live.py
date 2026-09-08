"""talks to a public rpc. skipped unless ENSLOOKUP_LIVE=1 so ci stays deterministic."""
import os

import pytest

from enslookup import Ens

pytestmark = pytest.mark.skipif(os.environ.get("ENSLOOKUP_LIVE") != "1", reason="set ENSLOOKUP_LIVE=1")

NICK = "0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5"


def test_nick_eth_forward_and_back():
    e = Ens()
    assert e.addr("nick.eth") == NICK
    name, verified = e.reverse(NICK)
    assert name == "nick.eth" and verified is True


def test_unregistered_name_is_empty():
    assert Ens().addr("this-name-should-not-exist-9f3a1c.eth") is None
