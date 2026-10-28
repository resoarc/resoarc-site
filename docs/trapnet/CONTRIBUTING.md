# TrapNet Zero-Trust design reviews

The project is pre-alpha. No publicly installable Sensor or Guardian exists yet.

Please comment on https://github.com/resoarc/resoarc-site/issues/31 with:
- your threat model and realistic failure/abuse cases,
- data minimization and user-consent concerns,
- alternatives to centralized auto-blocking,
- independent verification and signed update/recovery suggestions,
- safe lab test designs (no third-party targets).

**Please do not open ports at home or test against systems you do not own/operate.**
Avoid posting IP addresses, passwords, captured payloads, or exploit details in public issues. Use the repository security disclosure instructions for vulnerabilities.

Code contributions should have unit tests, minimal dependencies, no remote execution/telemetry by default, and a clear statement of what has actually been tested.
