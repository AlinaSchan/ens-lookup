"""ens the long way round: registry -> resolver -> record, nothing cached, nothing hidden.

forward:  namehash(name) -> registry.resolver(node) -> resolver.addr(node) / resolver.text(node, key)
reverse:  namehash("<hex>.addr.reverse") -> resolver.name(node), then the forward lookup
          has to land on the same address, otherwise the name is reported as unverified.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from . import abi
from .keccak import keccak256
from .rpc import Rpc, RpcError

REGISTRY = "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
ZERO_ADDRESS = "0x" + "0" * 40

SEL_RESOLVER = abi.selector("resolver(bytes32)")
SEL_ADDR = abi.selector("addr(bytes32)")
SEL_TEXT = abi.selector("text(bytes32,string)")
SEL_NAME = abi.selector("name(bytes32)")

TEXT_KEYS_DEFAULT = ("url", "com.twitter", "com.github")
TEXT_KEYS_ALL = (
    "avatar", "description", "url", "email", "com.twitter", "com.github", "com.discord",
    "org.telegram", "location", "keywords", "notice",
)


def normalize(name: str) -> str:
    """lowercase + nfc. good enough for ascii names; full ensip-15 is out of scope here."""
    name = unicodedata.normalize("NFC", (name or "").strip()).lower()
    return name.strip(".")


def namehash(name: str) -> bytes:
    """eip-137 namehash of an already normalized name ('' -> 32 zero bytes)."""
    node = bytes(32)
    if name:
        for label in reversed(name.split(".")):
            node = keccak256(node + keccak256(label.encode()))
    return node


@dataclass
class Lookup:
    query: str
    kind: str = "name"  # "name" when the query was a name, "address" when it was an address
    name: str | None = None
    address: str | None = None
    resolver: str | None = None
    verified: bool | None = None  # reverse lookups only: does the name point back?
    text: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    @property
    def resolved(self) -> bool:
        """a name query needs an address, an address query needs a name."""
        return bool(self.name) if self.kind == "address" else bool(self.address)

    def as_dict(self) -> dict:
        return {
            "query": self.query, "kind": self.kind, "name": self.name, "address": self.address,
            "resolver": self.resolver, "verified": self.verified, "text": dict(self.text), "error": self.error,
        }


class Ens:
    def __init__(self, rpc: Rpc | None = None):
        self.rpc = rpc or Rpc()

    def resolver_of(self, node: bytes) -> str | None:
        out = self.rpc.eth_call(REGISTRY, SEL_RESOLVER + node)
        if len(out) < 32:
            return None
        resolver = abi.dec_address(out)
        return None if resolver == ZERO_ADDRESS else resolver

    def addr(self, name: str, resolver: str | None = None) -> str | None:
        node = namehash(normalize(name))
        resolver = resolver or self.resolver_of(node)
        if not resolver:
            return None
        try:
            out = self.rpc.eth_call(resolver, SEL_ADDR + node)
        except RpcError:
            return None
        if len(out) < 32:
            return None
        address = abi.dec_address(out)
        return None if address == ZERO_ADDRESS else address

    def text(self, name: str, key: str, resolver: str | None = None) -> str | None:
        node = namehash(normalize(name))
        resolver = resolver or self.resolver_of(node)
        if not resolver:
            return None
        data = SEL_TEXT + node + abi.enc_uint(0x40) + abi.enc_string(key)
        try:
            out = self.rpc.eth_call(resolver, data)
        except RpcError:
            return None
        if len(out) < 64:
            return None
        value = abi.dec_string(out)
        return value or None

    def reverse(self, address: str) -> tuple[str | None, bool | None]:
        """(name, verified). verified is None when there is no reverse record at all."""
        node = namehash(f"{address[2:].lower()}.addr.reverse")
        resolver = self.resolver_of(node)
        if not resolver:
            return None, None
        try:
            out = self.rpc.eth_call(resolver, SEL_NAME + node)
        except RpcError:
            return None, None
        if len(out) < 64:
            return None, None
        name = normalize(abi.dec_string(out))
        if not name:
            return None, None
        forward = self.addr(name)
        return name, bool(forward and forward.lower() == address.lower())

    def lookup(self, query: str, keys: tuple[str, ...] = TEXT_KEYS_DEFAULT) -> Lookup:
        query = query.strip()
        if abi.is_address(query):
            result = Lookup(query=query, kind="address", address=abi.to_checksum(query))
            result.name, result.verified = self.reverse(query)
        else:
            result = Lookup(query=query, kind="name", name=normalize(query))
            result.address = self.addr(result.name)
        if result.name:
            node = namehash(result.name)
            result.resolver = self.resolver_of(node)
            for key in keys:
                value = self.text(result.name, key, resolver=result.resolver)
                if value:
                    result.text[key] = value
        return result
