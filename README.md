# ens-lookup

[![ci](https://github.com/AlinaSchan/ens-lookup/actions/workflows/ci.yml/badge.svg)](https://github.com/AlinaSchan/ens-lookup/actions/workflows/ci.yml)
![python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab)
![license mit](https://img.shields.io/badge/license-MIT-2b7a74)
[![release](https://img.shields.io/github/v/release/AlinaSchan/ens-lookup?color=2b7a74)](https://github.com/AlinaSchan/ens-lookup/releases)
[![openssf scorecard](https://api.scorecard.dev/projects/github.com/AlinaSchan/ens-lookup/badge)](https://scorecard.dev/viewer/?uri=github.com/AlinaSchan/ens-lookup)

ens names to addresses and back, plus the text records (twitter, github, url, ...).
pure python, nothing to install, a public rpc, no keys. keccak-256 is implemented in
the package because the standard library only ships nist sha3, which pads differently.

i wrote this because i kept pasting names into a block explorer to check who an
address was. now it is one command, and it works in a loop over a file.

```
$ enslookup vitalik.eth --all-text
vitalik.eth
  address   0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
  resolver  0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63
  avatar    https://euc.li/vitalik.eth
  description mi pinxe lo crino tcati
  url       https://vitalik.ca
  com.twitter VitalikButerin
  com.github vbuterin

$ enslookup 0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5
0xb8c2C29ee19D8307cb7255e1Cd9CbDE883A267d5
  name      nick.eth
  resolver  0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41
  url       https://ens.domains/
  com.twitter nicksdjohnson
  com.github arachnid
```

## install

```
pipx install git+https://github.com/AlinaSchan/ens-lookup
```

or clone it and run `python -m enslookup ...` from the folder. python 3.10 or newer,
no dependencies.

## use

```
enslookup vitalik.eth nick.eth                  # forward
enslookup 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045   # reverse, checked against the forward record
enslookup ens.eth --text url,com.twitter,email  # pick the text records
enslookup --batch names.txt --csv > out.csv     # one query per line, - for stdin
enslookup --batch names.txt --json              # json lines
enslookup vitalik.eth --rpc https://your.node   # your own endpoint first
```

`--all-text` asks for avatar, description, url, email, com.twitter, com.github,
com.discord, org.telegram, location, keywords and notice. `--no-text` is faster.
an `avatar` record is also printed as an `avatar url` you can open: `ipfs://` becomes a
gateway link and `eip155:1/erc721:<contract>/<id>` is followed through `tokenURI` to the
token's image ([ensip-12](https://docs.ens.domains/ensip/12)).
batches run four lookups at a time (`--workers`).

exit code is 0 when at least one query resolved, 1 when none did, 2 when no rpc answered.

## how it works

the long way round, on purpose, so the steps are visible:

1. `namehash(name)` per [eip-137](https://eips.ethereum.org/EIPS/eip-137)
2. `registry.resolver(node)` on the [ens registry](https://etherscan.io/address/0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e)
3. `resolver.addr(node)` for the address, `resolver.text(node, key)` for the records
   ([ensip-5](https://docs.ens.domains/ensip/5) keys)
4. reverse: `namehash("<hex>.addr.reverse")` -> `resolver.name(node)`, then step 1-3 on the
   result. if that does not land on the same address the name is printed as unverified,
   the way [eip-181](https://eips.ethereum.org/EIPS/eip-181) asks for.

every call is a plain `eth_call` over json-rpc via `urllib`. the default endpoints are
publicnode, drpc, mevblocker, tenderly and blastapi, tried in that order; the first one
that answers is remembered.

what it does not do: offchain and wildcard names ([ensip-10](https://docs.ens.domains/ensip/10),
the `*.cb.id` and `*.base.eth` kind) show up as "nothing found", and normalization is
lowercase + nfc rather than full [ensip-15](https://docs.ens.domains/ensip/15), so emoji
names may hash differently than in a wallet.

## tests

```
python -m pytest -q                       # offline: keccak vectors, namehash, checksums, a fake node
ENSLOOKUP_LIVE=1 python -m pytest -q      # plus two lookups against mainnet
```

the sponge is checked against `hashlib.sha3_256` for a few hundred input lengths (same
permutation, different padding byte), and the padding against the published keccak-256
vectors, so a wrong bit anywhere in `keccak.py` fails loudly.

## see also

- [onchain-notes](https://github.com/AlinaSchan/onchain-notes): the daily card and gas scripts
- [bigmoves](https://github.com/AlinaSchan/bigmoves): large transfers, which can use this package to name addresses
- [gasweek](https://github.com/AlinaSchan/gasweek), [stablepeg](https://github.com/AlinaSchan/stablepeg)
- the notes behind the numbers: [alinaschanz.life](https://alinaschanz.life), the short version on [x](https://x.com/alinaschanz)

## verify a release

from the next release on, every release carries the sdist and the wheel, a `SHA256SUMS` file, an
opentimestamps proof of that file, and a build provenance attestation made in github's own signing
flow. with the files downloaded into one folder:

    sha256sum -c SHA256SUMS
    gh attestation verify ./*.whl --owner AlinaSchan
    ots verify SHA256SUMS.ots

the attestation names the commit and the workflow run that produced the file; the timestamp proves
the checksums existed before a certain bitcoin block; the commit itself is
[signed](https://alinaschanz.life/verify/#commits).

## license

[mit](LICENSE)
