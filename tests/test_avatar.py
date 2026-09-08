"""offline: avatar records to urls, nft pointers through a fake node and a fake fetch."""
from enslookup import abi
from enslookup.avatar import SEL_TOKEN_URI, SEL_URI, http_url, nft_image, resolve

CONTRACT = "0x" + "ab" * 20


def test_http_url_shapes():
    assert http_url("https://euc.li/nick.eth") == "https://euc.li/nick.eth"
    assert http_url("ipfs://QmHash/1.png") == "https://ipfs.io/ipfs/QmHash/1.png"
    assert http_url("ipfs://ipfs/QmHash") == "https://ipfs.io/ipfs/QmHash"
    assert http_url("ipns://name.eth/a.png") == "https://ipfs.io/ipns/name.eth/a.png"
    assert http_url("/ipfs/QmHash") == "https://ipfs.io/ipfs/QmHash"
    assert http_url("data:image/svg+xml;base64,AAAA") == "data:image/svg+xml;base64,AAAA"
    assert http_url("") is None and http_url("ftp://x") is None


class FakeRpc:
    def __init__(self, uri):
        self.uri, self.calls = uri, []

    def eth_call(self, to, data):
        self.calls.append((to, data[:4], data[4:]))
        return abi.enc_uint(0x20) + abi.enc_string(self.uri)


def test_erc721_pointer_fetches_the_metadata_image():
    rpc = FakeRpc("ipfs://QmMeta/123.json")
    fetched = []

    def fetch(url):
        fetched.append(url)
        return {"name": "x", "image": "ipfs://QmImage/123.png"}

    assert nft_image(rpc, f"eip155:1/erc721:{CONTRACT}/123", fetch) == "https://ipfs.io/ipfs/QmImage/123.png"
    assert rpc.calls[0][1] == SEL_TOKEN_URI and abi.dec_uint(rpc.calls[0][2]) == 123
    assert fetched == ["https://ipfs.io/ipfs/QmMeta/123.json"]


def test_erc1155_pointer_substitutes_the_id():
    rpc = FakeRpc("https://api.example/{id}.json")
    seen = []
    assert nft_image(rpc, f"eip155:1/erc1155:{CONTRACT}/7", lambda url: seen.append(url) or {"image": "https://cdn/7.png"}) == "https://cdn/7.png"
    assert rpc.calls[0][1] == SEL_URI and seen == ["https://api.example/" + f"{7:064x}" + ".json"]


def test_other_chains_and_broken_metadata_give_none():
    assert nft_image(FakeRpc("ipfs://x"), f"eip155:137/erc721:{CONTRACT}/1") is None
    assert nft_image(FakeRpc("ipfs://x"), f"eip155:1/erc721:{CONTRACT}/1", lambda url: (_ for _ in ()).throw(OSError("down"))) is None
    assert nft_image(FakeRpc("ipfs://x"), f"eip155:1/erc721:{CONTRACT}/1", lambda url: {"no": "image"}) is None


def test_resolve_dispatches():
    assert resolve(FakeRpc(""), "ipfs://QmX") == "https://ipfs.io/ipfs/QmX"
    assert resolve(FakeRpc("ipfs://QmMeta"), f"eip155:1/erc721:{CONTRACT}/1", lambda url: {"image": "https://i/1.png"}) == "https://i/1.png"
    assert resolve(FakeRpc(""), None) is None
