"""Two-rail micro-payment example for Cobo Agentic Wallet (additive, self-contained).

Demonstrates the "second rail" decision documented in
``skills/cobo-agentic-wallet/references/nano-rail.md``: for a micro, recurring,
per-call payment, an agent settles on a feeless self-custodial rail (Nano/XNO)
instead of routing every payment through a custodial pact + gas.

    * CAW pact rail  — custodial EVM transfer inside a pact: owner approval,
      network gas, nonce ordering, on-chain finality. Best for large or
      policy-governed transfers.
    * Nano (XNO) rail — feeless (0.000000 XNO per transfer), sub-second
      finality, self-custodial, no pact. Best for micro per-call amounts.

The example is **fully offline**: payments are simulated against a local stub,
so it runs with no CAW API key, no Nano wallet, and no network. A reviewer can
verify the decision logic on first read.

This mirrors the ``PaymentRail`` interface shape (see the join note in the
docstring of agent-wallet-multirail — the reference multi-rail adapter this
example adapts). The ``NanoRail.transfer`` seam below is where a real,
self-custodial XNO transfer would be wired to a Nano RPC / Nano x402 client.

Run:

    python3 examples/python/nano_two_rail.py --self-test   # asserts, exit 0 on pass
    python3 examples/python/nano_two_rail.py 0.03          # print the chosen rail
"""

from __future__ import annotations

import dataclasses
import sys
from abc import ABC, abstractmethod
from typing import Dict, Optional


# ─── Rail abstraction (adapted from agent-wallet-multirail) ──────────────────


@dataclasses.dataclass
class Quote:
    rail: str
    amount_usd: float
    fee_usd: float
    finality_s: float
    needs_owner_pact: bool

    def total(self) -> float:
        return self.amount_usd + self.fee_usd


class PaymentRail(ABC):
    name: str = "abstract"

    @abstractmethod
    def quote(self, amount_usd: float) -> Quote:
        """Cost and finality to settle `amount_usd` on this rail."""


class CoboPactRail(PaymentRail):
    """Custodial EVM transfer inside a CAW pact: gas + owner-approval overhead."""

    name = "caw-pact-evm"

    def __init__(self, gas_usd: float = 0.15) -> None:
        # Average EVM transfer gas in USD-equivalent; kept as a stub for offline run.
        self.gas_usd = gas_usd

    def quote(self, amount_usd: float) -> Quote:
        return Quote(
            rail=self.name,
            amount_usd=amount_usd,
            fee_usd=self.gas_usd,  # every transfer burns network gas
            finality_s=12.0,       # on-chain confirmation
            needs_owner_pact=True,
        )


class NanoRail(PaymentRail):
    """Feeless self-custodial micro-settlement rail: 0 fee, sub-second finality.

    ``transfer`` is a stub so the example runs offline; a real integration
    points it at a Nano RPC / Nano x402 client to settle an actual XNO transfer.
    """

    name = "nano-xno"

    def __init__(self) -> None:
        self._calls: list[float] = []

    def quote(self, amount_usd: float) -> Quote:
        return Quote(
            rail=self.name,
            amount_usd=amount_usd,
            fee_usd=0.0,     # Nano is feeless per transfer
            finality_s=0.5,  # sub-second
            needs_owner_pact=False,
        )

    def transfer(self, amount_usd: float) -> str:
        """Dummy settlement; returns a fake tx reference (offline)."""
        self._calls.append(amount_usd)
        return f"xno-{len(self._calls)}-simulated"


def pick_cheaper_rail(amount_usd: float) -> str:
    """Return the rail name with the lowest total cost for a micro payment."""
    cobo = CoboPactRail().quote(amount_usd)
    nano = NanoRail().quote(amount_usd)
    if nano.total() < cobo.total():
        return nano.rail
    return cobo.rail


# ─── Self-test (no network, no keys) ─────────────────────────────────────────


def _self_test() -> None:
    # 1. Micro amount: Nano wins because the CAW pact + gas exceeds the call value.
    nano = NanoRail()
    cobo = CoboPactRail()
    assert pick_cheaper_rail(0.01) == "nano-xno", "micro per-call should settle feeless"
    # 2. Nano quote is feeless and sub-second.
    q = nano.quote(0.01)
    assert q.fee_usd == 0.0 and q.finality_s < 1.0 and q.needs_owner_pact is False
    # 3. The custodial rail carries gas and needs a pact (its real authority model).
    cq = cobo.quote(0.01)
    assert cq.fee_usd > 0.0 and cq.needs_owner_pact is True
    # 4. A large amount is still worth the custodial rail's policy control if it
    #    fits the pact; Nano stays the micro leg. (Here gas is small vs amount,
    #    so both are acceptable — we assert both rails quote the same amount.)
    assert nano.quote(500.0).amount_usd == cobo.quote(500.0).amount_usd == 500.0
    # 5. The Nano transfer stub records a settlement ref.
    ref = nano.transfer(0.01)
    assert ref.startswith("xno-") and nano._calls == [0.01]
    print("PASS: nano_two_rail self-test (5 checks)")


def main() -> None:
    args = sys.argv[1:]
    if "--self-test" in args:
        _self_test()
        return
    amount = float(args[0]) if args else 0.03
    rail = pick_cheaper_rail(amount)
    print(
        f"${amount:.4f} micro payment -> rail={rail} "
        f"(fee {NanoRail().quote(amount).fee_usd if rail=='nano-xno' else CoboPactRail().quote(amount).fee_usd})"
    )


if __name__ == "__main__":
    main()
