# Security Policy

## Supported Versions

We release security updates and patches for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Sovereign AI is built with an air-gapped, zero-trust mindset designed for sovereign enterprise environments where data leakage is strictly unacceptable.

If you discover a potential security vulnerability (e.g., secret leakage, unauthorized proxy access, container privilege escalation, or vector injection flaws), please **DO NOT** create a public GitHub issue.

Instead, please report security issues privately:
- Contact the maintainers directly via email: `mahdijm.bb@gmail.com`
- Include a detailed technical description of the vulnerability, reproduction steps, and potential impact.

### Our Commitment

- We will acknowledge receipt of your vulnerability report within 48 hours.
- We will provide an estimated timeframe for a patch or mitigation.
- Once fixed, we will publicly credit your responsible disclosure (unless you prefer to remain anonymous).

## Air-Gap & Zero-Trust Best Practices

When operating in production:
1. Never expose raw container ports (e.g., PostgreSQL `:5432` or Weaviate `:8080`) to public networks.
2. Route all remote worker traffic through encrypted WireGuard / Tailscale tunnels.
3. Keep `LITELLM_MASTER_KEY` and database credentials strictly managed via encrypted environment injection.
