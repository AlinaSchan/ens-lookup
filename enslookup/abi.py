"""just enough abi encoding and decoding for the handful of ens calls in here."""
from __future__ import annotations

import re

from .keccak import keccak256

_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def selector(signature: str) -> bytes:
    """first four bytes of keccak256 of the canonical signature, e.g. addr(bytes32)."""
    return keccak256(signature.encode())[:4]


def enc_uint(value: int) -> bytes:
    return value.to_bytes(32, "big")


def enc_address(address: str) -> bytes:
    return bytes(12) + bytes.fromhex(address[2:])


def enc_string(text: str) -> bytes:
    """dynamic string tail: length word, then the utf-8 bytes padded to 32."""
    raw = text.encode()
    return enc_uint(len(raw)) + raw + bytes(-len(raw) % 32)


def dec_uint(data: bytes, word: int = 0) -> int:
    return int.from_bytes(data[32 * word:32 * word + 32], "big")


def dec_address(data: bytes, word: int = 0) -> str:
    return to_checksum("0x" + data[32 * word + 12:32 * word + 32].hex())


def dec_string(data: bytes, word: int = 0) -> str:
    offset = dec_uint(data, word)
    length = int.from_bytes(data[offset:offset + 32], "big")
    return data[offset + 32:offset + 32 + length].decode("utf-8", errors="replace")


def is_address(text: str) -> bool:
    return bool(_ADDR_RE.match(text or ""))


def to_checksum(address: str) -> str:
    """eip-55 mixed-case checksum."""
    low = address[2:].lower()
    digest = keccak256(low.encode()).hex()
    out = "".join(ch.upper() if ch in "abcdef" and int(digest[i], 16) >= 8 else ch for i, ch in enumerate(low))
    return "0x" + out
