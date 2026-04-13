# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Calabi, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email us at: **security@calabi.dev**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 5 business days
- **Resolution**: Dependent on severity, typically within 30 days

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Security Best Practices

When deploying Calabi:

- Change all default passwords in `.env` before production use
- Use a strong `SUPERSET_SECRET_KEY`
- Restrict network access to ports 8080 and 8088
- Keep Docker and all images up to date
- Review the [deployment documentation](https://calabi.bifrost.examroom.ai/docs/platform/deployment) for production hardening
