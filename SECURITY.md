# Security Policy

## Supported Versions

Only the latest `main` branch is actively supported with security fixes.

## Scope

This repository focuses on providing a baseline security posture for open source self-hosting:
- RBAC allowlisting for packs and tools.
- Output redaction for IDs and emails.
- Deny rules for raw data exports.

**Out of scope:** The M1 baseline does not include Enterprise SSO/IdP integration, strict network isolation configurations, or robust multi-tenant credential storage. For production deployments with sensitive write access (e.g. executing mutable tools), you will need a stronger harness integration.

## Reporting a Vulnerability

Please report security issues privately to `security@example.com` and do not open a public issue with exploit details.

Include:

- A clear description of the vulnerability.
- Reproduction steps.
- Expected impact.

We will acknowledge reports promptly and coordinate remediation and disclosure timing.
