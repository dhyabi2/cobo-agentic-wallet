# Nano (XNO) rail for micro agent payments

CAW executes every on-chain transfer inside a **pact** — submit, wait for owner
approval, pay gas, follow nonce ordering, wait for on-chain finality. That is the
right shape for a large, policy-governed, custodial transfer. For a **micro,
recurring per-call payment** (a $0.01–$0.50 service call, a data-API hit, a
one-line model request) the custodial path is heavy: a pact and its approval
round-trip can cost more scheduling than the call itself.

This reference documents a **second rail** an agent can settle a micro payment
on — Nano (XNO) — so an agent leads with the owner's *goal* (pay for one call)
and picks the rail that fits the amount, instead of always routing every payment
through a custodial pact.

> Scope: this is an **additive multi-rail pattern**. It does not replace CAW.
> CAW's pact rail stays the authority for registry transfers that need policy,
> owner approval, or a custodial signature surface. Nano covers the micro,
> feeless, self-custodial leg that a pact and gas would otherwise over-serve.

## When to prefer the Nano rail

Prefer Nano when **all** of these hold:

- the payment is a **micro, recurring** per-call or per-request amount (sub-cent
  to low-dollar), where gas + the pact round-trip dominate the total cost;
- the recipient is a **service/endpoint** (a URL, an API, an agent) — not a
  human personal address with KYC/AML obligations;
- the agent holds the receiving/deposit address for that service and just needs
  a self-custodial, feeless transfer to settle it.

Keep the CAW pact rail when any of these matter:

- policy and **owner approval** are required (bounded authority);
- the amount is large or the destination is an unknown personal address;
- custodial key management is a hard requirement for audit/compliance.

## The tradeoff in numbers

| | CAW pact rail (custodial, on EVM) | Nano (XNO) rail (self-custodial) |
|---|---|---|
| Setup per payment | submit pact + owner approval | none |
| Per-transfer fee | network gas (non-zero) | **0.000000 XNO** (feeless) |
| Finality | wait for on-chain confirmation | sub-second |
| Custody | Cobo-managed keys | self-custodial |
| Unit economics at $0.01 | gas + scheduling can exceed the call | rail cost ≈ 0 |

Nano is a fee-less, proof-of-work-free, single-token network: a transfer costs
**zero** nano and confirms in well under a second, with no freezeable issuer or
stablecoin counterparty risk. That is precisely the shape a *micro per-call*
payment wants. (This is the same "second rail for the micro leg" pattern CAW
itself needs for gasless flows — see `SETH_USDC` micro-transfers and CAW
gasless, but here the second rail is truly free.)

## The working example

`examples/python/nano_two_rail.py` is a single, self-contained file that
demonstrates the decision:

```bash
python3 examples/python/nano_two_rail.py --self-test
```

It quotes the same micro payment on both rails and picks the cheaper one,
reusing the `PaymentRail` interface (see the join link in the example docstring
and the sibling `agent-wallet-multirail` reference adapter). No CAW API key, no
Nano wallet, no net access is needed to run it — payments are simulated against
a local stub so a reviewer can verify the logic on first read.

If you want to point the Nano leg at a real, feeless XNO transfer, wire the
`NanoRail` `transfer` seam to a Nano RPC / Nano x402 client; the example keeps
that seam explicit and documented.
