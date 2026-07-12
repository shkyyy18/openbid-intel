# Security Policy

## Reporting a vulnerability

Do not post credentials, private procurement files, customer information, exploit details, or sensitive system data in a public issue. If GitHub private vulnerability reporting is enabled for the repository, use it. Otherwise, contact the repository owner through a private channel and provide only the minimum information needed to reproduce the problem.

## Credential handling

- Keep Feishu webhooks and signing secrets in `.env` only.
- Never commit `.env`, SQLite databases, exported reports, cookies, authorization headers, or private attachments.
- Revoke and replace a credential immediately if it appears in a commit, issue, log, screenshot, or report.
- Treat sample URLs containing `...` as placeholders; do not replace them with a live webhook in documentation.

## Collector security boundary

A connector must not disable TLS verification, bypass authentication or CAPTCHA, execute downloaded content, or follow a workflow that grants broader access than an ordinary public visitor. Parse remote content as untrusted input and keep CI tests offline.

## Sensitive-industry boundary

This project may be used around universities, research institutes, aerospace, electronics, or defense-adjacent procurement. The public repository must contain only public tender information and synthetic or explicitly public fixtures. Do not add classified, controlled, export-restricted, internal, customer-confidential, or personally sensitive information.
