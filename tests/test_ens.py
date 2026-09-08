"""offline: namehash, checksums, abi, and the registry -> resolver -> record dance with a fake node."""
from enslookup import abi, ens
from enslookup.ens import Ens, namehash, normalize

NICK = "0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5"  # nick.eth
RESOLVER = "0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41"


def test_namehash_vectors_from_eip_137():
    assert namehash("") == bytes(32)
    assert namehash("eth").hex() == "93cdeb708b7545dc668eb9280176169d1c33cfd8ed6f04690a0bcc88a93fc4ae"
    assert namehash("vitalik.eth").hex() == "ee6c4522aab0003e8d14cd40a6af439055fd2577951148c14b6cea9a53475835"


def test_namehash_is_hierarchical():
    assert namehash("vitalik.eth") != namehash("eth")
    assert namehash("a.b.eth") != namehash("b.a.eth")


def test_normalize():
    assert normalize("  Vitalik.ETH. ") == "vitalik.eth"
    assert normalize("") == ""


def test_eip55_checksum_vectors():
    for good in (
        "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
        "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
        "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB",
        "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb",
        NICK,
        RESOLVER,
        "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e",  # the ens registry
    ):
        assert abi.to_checksum(good.lower()) == good
        assert abi.to_checksum(good.upper().replace("0X", "0x")) == good


def test_is_address():
    assert abi.is_address(NICK)
    assert not abi.is_address("nick.eth")
    assert not abi.is_address("0x1234")


def test_string_roundtrip():
    payload = abi.enc_uint(0x20) + abi.enc_string("hello ens")
    assert abi.dec_string(payload) == "hello ens"
    assert abi.dec_string(abi.enc_uint(0x20) + abi.enc_string("")) == ""


class FakeRpc:
    """answers eth_call by (to, selector) and records what was asked."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def eth_call(self, to, data):
        self.calls.append((to.lower(), data))
        return self.answers[(to.lower(), data[:4])](data)


def _word_address(address):
    return abi.enc_address(address)


def _string(value):
    return abi.enc_uint(0x20) + abi.enc_string(value)


def make_fake(texts=None, reverse_name="nick.eth"):
    texts = texts if texts is not None else {"url": "https://ens.domains/", "com.twitter": "nicksdjohnson"}
    reverse_node = namehash(f"{NICK[2:].lower()}.addr.reverse")

    def text_answer(data):
        key = abi.dec_string(data[4:], word=1)
        return _string(texts.get(key, ""))

    def name_answer(data):
        node = data[4:36]
        return _string(reverse_name if node == reverse_node else "")

    def addr_answer(data):  # only nick.eth has an address record in this fake
        node = data[4:36]
        return _word_address(NICK if node == namehash("nick.eth") else ens.ZERO_ADDRESS)

    return FakeRpc({
        (ens.REGISTRY.lower(), ens.SEL_RESOLVER): lambda data: _word_address(RESOLVER),
        (RESOLVER.lower(), ens.SEL_ADDR): addr_answer,
        (RESOLVER.lower(), ens.SEL_TEXT): text_answer,
        (RESOLVER.lower(), ens.SEL_NAME): name_answer,
    })


def test_forward_lookup_walks_registry_then_resolver():
    rpc = make_fake()
    result = Ens(rpc).lookup("Nick.eth")
    assert result.name == "nick.eth"
    assert result.address == NICK
    assert result.resolver == RESOLVER
    assert result.text == {"url": "https://ens.domains/", "com.twitter": "nicksdjohnson"}
    first_to, first_data = rpc.calls[0]
    assert first_to == ens.REGISTRY.lower()
    assert first_data == ens.SEL_RESOLVER + namehash("nick.eth")


def test_text_call_is_abi_encoded_with_dynamic_string():
    rpc = make_fake()
    Ens(rpc).text("nick.eth", "url")
    to, data = rpc.calls[-1]
    assert to == RESOLVER.lower()
    assert data[:4] == ens.SEL_TEXT
    assert data[4:36] == namehash("nick.eth")
    assert abi.dec_uint(data[4:], 1) == 0x40  # offset of the string
    assert abi.dec_string(data[4:], 1) == "url"


def test_reverse_lookup_verifies_forward_record():
    result = Ens(make_fake()).lookup(NICK.lower(), keys=())
    assert result.name == "nick.eth"
    assert result.address == NICK  # checksummed on the way out
    assert result.verified is True


def test_reverse_lookup_flags_names_that_do_not_point_back():
    other = "0x" + "ab" * 20
    result = Ens(make_fake()).lookup(other, keys=())
    assert result.name is None  # no reverse record for that address in the fake
    rpc = make_fake(reverse_name="someone-else.eth")
    result = Ens(rpc).lookup(NICK, keys=())
    assert result.name == "someone-else.eth"
    assert result.verified is False


def test_lookup_resolves_the_avatar_record(monkeypatch):
    rpc = make_fake(texts={"avatar": "ipfs://QmPic/a.png"})
    result = Ens(rpc).lookup("nick.eth", keys=("avatar",))
    assert result.text["avatar"] == "ipfs://QmPic/a.png" and result.avatar_url == "https://ipfs.io/ipfs/QmPic/a.png"
    assert result.as_dict()["avatar_url"] == "https://ipfs.io/ipfs/QmPic/a.png"


def test_no_resolver_means_nothing_found():
    rpc = FakeRpc({(ens.REGISTRY.lower(), ens.SEL_RESOLVER): lambda data: _word_address(ens.ZERO_ADDRESS)})
    result = Ens(rpc).lookup("definitely-not-registered-123456.eth")
    assert not result.resolved
    assert result.address is None and result.resolver is None


def test_resolved_depends_on_what_was_asked():
    assert ens.Lookup(query="a.eth", kind="name", name="a.eth").resolved is False
    assert ens.Lookup(query="a.eth", kind="name", name="a.eth", address=NICK).resolved is True
    assert ens.Lookup(query=NICK, kind="address", address=NICK).resolved is False
    assert ens.Lookup(query=NICK, kind="address", address=NICK, name="nick.eth").resolved is True
