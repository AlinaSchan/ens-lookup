"""turn an ens avatar record into something a browser can open.

records come in three shapes (ensip-12): a plain url, an ipfs/ipns uri, or an nft pointer such as
eip155:1/erc721:0x.../123 - for the last one the token's metadata is fetched and its image taken.
"""
from __future__ import annotations

import json
import re
import urllib.request

from . import abi
from .rpc import Rpc, RpcError

GATEWAY = "https://ipfs.io"
USER_AGENT = "enslookup/0.1 (+https://github.com/alinaschanz/ens-lookup)"
SEL_TOKEN_URI = abi.selector("tokenURI(uint256)")
SEL_URI = abi.selector("uri(uint256)")
_NFT = re.compile(r"^eip155:(?P<chain>\d+)/(?P<kind>erc721|erc1155):(?P<contract>0x[0-9a-fA-F]{40})/(?P<id>\d+)$")


def http_url(uri: str | None) -> str | None:
    """ipfs://, ipns:// and bare cids become gateway urls; http(s) and data: stay; the rest is None."""
    if not uri:
        return None
    uri = uri.strip()
    if uri.startswith(("http://", "https://", "data:")):
        return uri
    if uri.startswith("ipfs://"):
        path = uri[len("ipfs://"):]
        path = path[len("ipfs/"):] if path.startswith("ipfs/") else path
        return f"{GATEWAY}/ipfs/{path}"
    if uri.startswith("ipns://"):
        return f"{GATEWAY}/ipns/{uri[len('ipns://'):]}"
    if uri.startswith("/ipfs/"):
        return GATEWAY + uri
    return None


def fetch_json(url: str, timeout: float = 15.0) -> dict:
    if url.startswith("data:application/json;base64,"):
        import base64

        return json.loads(base64.b64decode(url.split(",", 1)[1]))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read(1_000_000))


def nft_image(rpc: Rpc, record: str, fetch=fetch_json) -> str | None:
    """eip155:1/erc721:<contract>/<id> -> tokenURI(id) -> metadata -> image, as an https url."""
    m = _NFT.match(record.strip())
    if not m or m.group("chain") != "1":
        return None
    token_id = int(m.group("id"))
    selector = SEL_TOKEN_URI if m.group("kind") == "erc721" else SEL_URI
    try:
        out = rpc.eth_call(m.group("contract"), selector + abi.enc_uint(token_id))
    except RpcError:
        return None
    if len(out) < 64:
        return None
    uri = abi.dec_string(out)
    if m.group("kind") == "erc1155":
        uri = uri.replace("{id}", f"{token_id:064x}")
    url = http_url(uri)
    if not url:
        return None
    try:
        meta = fetch(url)
    except Exception:
        return None
    image = meta.get("image") or meta.get("image_url") or meta.get("image_data")
    return http_url(image) if isinstance(image, str) else None


def resolve(rpc: Rpc, record: str | None, fetch=fetch_json) -> str | None:
    if not record:
        return None
    if record.startswith("eip155:"):
        return nft_image(rpc, record, fetch)
    return http_url(record)
