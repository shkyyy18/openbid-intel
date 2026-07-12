# Public Data Handling Rules

This repository is designed for public procurement notices. It is not an internal CRM, document vault, or repository for restricted technical material.

## Allowed in the public repository

- Source code and generic configuration structure;
- public notice URLs and small, sanitized test fixtures;
- synthetic examples that cannot be mistaken for a current opportunity;
- documentation describing scoring and collection behavior;
- aggregated test results without customer-private notes.

## Keep local and untracked

- `data/*.db` and generated reports;
- sales feedback, contacts, phone numbers, email addresses, and meeting notes;
- Feishu webhooks, cookies, tokens, signed URLs, and request headers;
- downloaded tender attachments unless redistribution is clearly permitted;
- internal pricing, bid strategy, qualification gaps, win/loss analysis, and customer relationships;
- non-public technical requirements or material subject to confidentiality, classification, or export controls.

## Before publishing a fixture

1. Confirm that the source was publicly accessible without authentication.
2. Keep only fields required by the test.
3. Remove personal contact data and unnecessary identifiers.
4. Replace live secrets and signed URLs with obvious placeholders.
5. Label historical or synthetic records so they cannot be presented as active opportunities.
6. Preserve the source date and a public origin reference where appropriate.

## Incident response

If sensitive information is committed, stop sharing the repository, revoke exposed credentials, remove the material from the working tree and Git history, and notify the responsible data owner. Deleting only the latest file is not sufficient after it has entered Git history.
