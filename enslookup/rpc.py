"""a tiny json-rpc client over urllib with fallback across public endpoints."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

DEFAULT_RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://eth.drpc.org",
    "https://rpc.mevblocker.io",
    "https://gateway.tenderly.co/public/mainnet",
    "https://eth-mainnet.public.blastapi.io",
)
USER_AGENT = "enslookup/0.1 (+https://github.com/alinaschanz/ens-lookup)"


class RpcError(Exception):
    """the call itself failed on chain (revert, bad params) - same answer from every node."""


class RpcUnavailable(Exception):
    """no endpoint gave a usable answer."""


def _is_revert(error: dict) -> bool:
    message = str(error.get("message", "")).lower()
    return error.get("code") == 3 or "revert" in message or "invalid opcode" in message


class Rpc:
    def __init__(self, urls: tuple[str, ...] | list[str] | None = None, timeout: float = 15.0):
        self.urls = list(urls or DEFAULT_RPCS)
        self.timeout = timeout
        self._id = 0

    def call(self, method: str, params: list):
        self._id += 1
        payload = json.dumps({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}).encode()
        last_problem: str | None = None
        for i, url in enumerate(self.urls):
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json", "User-Agent": USER_AGENT}
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = json.loads(resp.read())
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
                last_problem = f"{url}: {exc}"
                continue
            error = body.get("error") if isinstance(body, dict) else {"message": "malformed response"}
            if error:
                if _is_revert(error):
                    raise RpcError(error.get("message", "execution reverted"))
                # rate limits and "internal error" answers: try the next endpoint
                last_problem = f"{url}: {error.get('message', error)}"
                continue
            if i:  # remember the endpoint that worked, try it first next time
                self.urls.insert(0, self.urls.pop(i))
            return body.get("result")
        raise RpcUnavailable(f"no rpc endpoint gave a usable answer ({last_problem})")

    def eth_call(self, to: str, data: bytes) -> bytes:
        result = self.call("eth_call", [{"to": to, "data": "0x" + data.hex()}, "latest"])
        return bytes.fromhex((result or "0x")[2:])
