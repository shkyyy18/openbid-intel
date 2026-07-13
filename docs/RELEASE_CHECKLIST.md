# Release checklist

A release is ready when all of the following are true:

- Linux and Windows CI pass.
- The offline release check passes without network access.
- Synthetic demo data builds the Markdown digest and portable HTML dashboard.
- Configuration schemas and bundled profile packs validate.
- Ranking changes have deterministic tests and remain explainable.
- No credentials, personal data, customer lists, confidential notices, or generated local databases are staged.
- README quick start, screenshots, changelog, roadmap, security policy, contribution guide, and data-handling documentation are current.
- Version, tag, and release notes agree.

Run `python run.py --db data/release-check.db release-check` before tagging.
