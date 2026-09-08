"""keccak-256 in plain python.

ethereum hashes with the original keccak padding byte (0x01). the standard
library only ships nist sha3, which pads with 0x06, so ``hashlib.sha3_256``
gives a different digest for the same input. everything else (the sponge,
the permutation) is identical, which is what the tests lean on.

this is slow compared to a c implementation, but a name lookup needs a
handful of hashes and the point of this repo is to have nothing to install.
"""
from __future__ import annotations

_MASK = (1 << 64) - 1

_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)

# rotation offsets, indexed [x][y]
_ROT = (
    (0, 36, 3, 41, 18),
    (1, 44, 10, 45, 2),
    (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56),
    (27, 20, 39, 8, 14),
)


def _rol(v: int, n: int) -> int:
    return ((v << n) | (v >> (64 - n))) & _MASK if n else v


def _keccak_f(a: list[int]) -> None:
    """keccak-f[1600] on 25 lanes, lane index = x + 5 * y, in place."""
    for rc in _RC:
        # theta
        c = [a[x] ^ a[x + 5] ^ a[x + 10] ^ a[x + 15] ^ a[x + 20] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a[:] = [a[i] ^ d[i % 5] for i in range(25)]
        # rho + pi
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rol(a[x + 5 * y], _ROT[x][y])
        # chi
        for y in range(0, 25, 5):
            for x in range(5):
                a[y + x] = b[y + x] ^ ((~b[y + (x + 1) % 5]) & b[y + (x + 2) % 5])
        # iota
        a[0] ^= rc


def _sponge(data: bytes, pad: int, rate: int = 136, out_len: int = 32) -> bytes:
    buf = bytearray(data)
    buf.append(pad)
    buf.extend(b"\x00" * (-len(buf) % rate))
    buf[-1] |= 0x80
    a = [0] * 25
    lanes = rate // 8
    for off in range(0, len(buf), rate):
        block = buf[off:off + rate]
        for i in range(lanes):
            a[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        _keccak_f(a)
    return b"".join(lane.to_bytes(8, "little") for lane in a)[:out_len]


def keccak256(data: bytes) -> bytes:
    """keccak-256 digest (the ethereum one), 32 bytes."""
    return _sponge(data, 0x01)


def keccak256_hex(data: bytes) -> str:
    return "0x" + keccak256(data).hex()


def sha3_256(data: bytes) -> bytes:
    """nist sha3-256, only here so the tests can compare against hashlib."""
    return _sponge(data, 0x06)
