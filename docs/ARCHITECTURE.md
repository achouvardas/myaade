# Service architecture

## Public access and application service

```mermaid
flowchart LR
  Browser[Browser] --> DNS[Cloudflare DNS]
  DNS --> Tunnel[Cloudflare Tunnel]
  Tunnel --> CF[cloudflared systemd service]
  CF --> Gunicorn[Gunicorn on 127.0.0.1:5050]
  Gunicorn --> Flask[Elefthero Flask application]
  Flask --> SQLite[(SQLite database)]
  Flask --> Instance[instance/: Fernet key, PDFs, logo]
```

The included `myaade.service` starts Gunicorn and restarts it after boot or failure. `myaade-cloudflared.service` runs the Cloudflare Tunnel process. Adjust their example paths before using them in another deployment.

## Authentication service

```mermaid
sequenceDiagram
  participant U as User
  participant E as Elefthero
  participant C as Turnstile
  participant A as Authenticator app
  U->>E: Email and password
  opt Turnstile fully configured
    U->>C: Complete widget
    C-->>E: Verification token
  end
  E->>E: Verify password hash
  opt User enabled TOTP
    E-->>U: Request six-digit code
    U->>A: Read rotating code
    U->>E: Submit code
    E->>E: Verify encrypted TOTP seed
  end
  E-->>U: Authenticated session
```

## AADE submission service

```mermaid
flowchart TD
  Draft[Invoice editor] --> Validate[Validate VAT, exemption, classification and payment method]
  Validate --> XML[Generate myDATA XML]
  XML --> Sent[Audit sent XML]
  Sent --> AADE{Configured environment}
  AADE -->|Test| Test[AADE Test]
  AADE -->|Production| Production[AADE Production]
  Test --> Response[Parse response]
  Production --> Response
  Response --> Received[Audit received XML]
  Received --> Result[Store MARK, UID, QR URL and state]
  Result --> PDF[PDF, manual email, reports]
```

## Client enrichment service

```mermaid
flowchart LR
  VAT[Greek VAT entered] --> VIES[VIES validation using EL]
  VIES --> Client[(SQLite client record)]
  Client --> GEMI[Optional ΓΕΜΗ lookup]
  GEMI --> Details[Name, address, activity, ΓΕΜΗ]
  Details --> Client
  VIES --> Log[Activity log]
  GEMI --> Log
```
