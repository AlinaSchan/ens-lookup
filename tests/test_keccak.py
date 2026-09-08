"""the sponge is checked against hashlib's sha3 (same permutation, different pad byte),
the pad byte against published keccak-256 vectors."""
import hashlib
import os

from enslookup import abi
from enslookup.keccak import keccak256, sha3_256


def test_sponge_matches_hashlib_sha3_for_many_lengths():
    for n in list(range(0, 300)) + [1000, 4096]:  # crosses the 136 byte block boundary a few times
        data = os.urandom(n)
        assert sha3_256(data) == hashlib.sha3_256(data).digest(), n


def test_keccak256_known_vectors():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert keccak256(b"abc").hex() == "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45"
    assert keccak256(b"Transfer(address,address,uint256)").hex() == (
        "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
    )


def test_keccak_differs_from_sha3_on_purpose():
    assert keccak256(b"abc") != hashlib.sha3_256(b"abc").digest()


def test_selectors():
    assert abi.selector("transfer(address,uint256)").hex() == "a9059cbb"
    assert abi.selector("balanceOf(address)").hex() == "70a08231"
    assert abi.selector("resolver(bytes32)").hex() == "0178b8bf"
    assert abi.selector("addr(bytes32)").hex() == "3b3b57de"
    assert abi.selector("text(bytes32,string)").hex() == "59d1d43c"
    assert abi.selector("name(bytes32)").hex() == "691f3431"
