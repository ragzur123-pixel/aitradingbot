## 2026-08-05 - [Unauthenticated API Endpoint Risk]
**Vulnerability:** The Deadman's Switch server exposed an unauthenticated `/heartbeat` POST endpoint, intended to monitor the bot's health.
**Learning:** Due to the lack of authentication, a malicious actor or network scanner could spoof heartbeat requests to the VPS, thereby neutralizing the emergency shutdown safeguard even if the home PC crashed.
**Prevention:** Implementing an `Authorization: Bearer <token>` check on such administrative/health endpoints ensures that only trusted senders can suppress the deadman switch trigger. Always validate the source of critical operational signals.
## 2026-08-05 - [Predictable Randomness in Financial Jitter]
**Vulnerability:** The `ibkr_bridge.py` script used the standard `random` module to apply jitter to limit orders.
**Learning:** Standard `random` generates pseudo-random numbers which can be predicted by algorithmic sniffers, making the "tactical offset" ineffective and potentially predictable for high-stakes financial operations.
**Prevention:** Use `secrets.SystemRandom()` for cryptographically secure randomness when applying tactical offsets or jitter to limit orders.
