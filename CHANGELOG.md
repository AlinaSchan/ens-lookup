# changelog

all notable changes to ens-lookup. the format follows [keep a changelog](https://keepachangelog.com/en/1.1.0/),
versions follow [semver](https://semver.org/) as far as a command line tool has an api.

## [unreleased]

- a pypi workflow: trusted publishing on a release, switched on by a repository variable

- avatar records resolved to an https url: ipfs and ipns gateways, erc721/erc1155 pointers through `tokenURI` / `uri`

## [0.1.0] - 2026-09-08

first cut: ens names to addresses and back, plus text records.

- forward and reverse lookups with the forward check, text records, batch files, json and csv
- keccak-256 in the package, tested against hashlib sha3 and the published vectors
