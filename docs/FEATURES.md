# Feature reference

## AADE invoices

- Supports `1.1`, `2.1`, `5.1`, `11.1`, `11.2`, and `11.4` only, to keep the workflow appropriate for small businesses.
- Uses real AADE Test and Production endpoints; Test is not a local simulator.
- Generates invoice XML with issuer/counterpart rules, payment-method details, EUR currency, totals, per-line VAT, VAT exemptions, income classifications, and E3 types.
- Requires a valid exemption reason for every 0% VAT line and an income classification for every line.
- Limits the issue date to today and keeps series/next number configurable.
- Stores drafts, transmitted invoices, and cancelled invoices. Only drafts can be deleted.
- Can call AADE `CancelInvoice` for a transmitted invoice.

## Credits and retail

- `5.1` uses a searchable transmitted `1.1`/`2.1` MARK selector, copies the original data, saves the original MARK, sends `correlatedInvoices`, and prints the correlated MARK in PDF notes.
- `11.4` uses a searchable transmitted `11.1`/`11.2` selector to copy lines. It does not send `counterpart` or `correlatedInvoices`, because AADE forbids those fields for `11.4`.
- `11.1`, `11.2`, and `11.4` apply retail customer defaults (`ΠΕΛΑΤΗΣ ΛΙΑΝΙΚΗΣ`, `000000000`) and hide saved-client selection.

## Clients and reporting

- VIES checks Greek VAT numbers with the `EL` service code.
- ΓΕΜΗ enrichment can provide a legal name, address, primary activity, and ΓΕΜΗ number when public service availability allows it.
- Client records retain VAT, address, profession, and ΓΕΜΗ information for reuse in invoices.
- Search, autocomplete, pagination, safe deletion, client-specific date filters, and type-level transmitted-invoice totals are included.
- Dashboard reports transmitted turnover/VAT, drafts, recent invoices, and top customers.

## PDFs, templates, and email

- Browser-inline PDF includes business profile/logo, client data, document type/series/number/date, lines, per-line VAT, totals, payment method, UID, MARK, and clickable AADE QR URL.
- PDF notes include free text, automatic VAT-exemption text, and `5.1` original MARK.
- Reuse an existing invoice as an editable fresh draft, or save a transmitted invoice as a named template.
- Resend delivery is manual and available only for transmitted invoices; it attaches the PDF and uses the configured sender details.

## Security, access, and accessibility

- Password-hashed local users with administrator/user roles.
- Optional Cloudflare Turnstile, enabled only when both site key and secret are configured.
- Optional authenticator-app TOTP 2FA: QR enrollment, one-time-code challenge at login, encrypted secret storage, and password + current code required for disablement.
- AADE credentials, Resend key, Turnstile secret, and TOTP seeds are encrypted at rest using a local Fernet key.
- Developer log records XML, sign-in events, client lookups, PDF generation, cancellation, email, template actions, and sensitive-setting reveals.
- Accessibility pop-up provides text scaling, high contrast, readable spacing, underlined links, reduced motion, visible focus outlines, and browser-local preferences. It is WCAG 2.1-oriented and does not claim full conformance.
