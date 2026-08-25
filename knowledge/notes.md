# Knowledge base (sample)

## ACME Corp — discovery notes

- Contact: Dana Reyes, VP Operations, dana.reyes@acme.example
- Current vendor: RivalHQ, contract renews in March; paying $42/seat/month.
- Pain: reporting exports take 2 days; wants API + webhook integrations.
- Security review required: SSO (SAML), SOC2 report available on request.
- Pricing anchor: we offer $29/seat/month annual, $35 monthly. Volume discount at 200+ seats.

## Objection handling playbook

- "Too expensive": reframe against cost of the current manual process ($18k/yr ops time); offer annual pricing and a 60-day pilot.
- "Won't work with our stack": cite the REST API, webhooks, and CSV import; offer a sandbox tenant within 24h.
- "Worried about downtime": 99.95% uptime SLA, status page, migration runbook with rollback.

## Technical spec sheet

- REST API: JSON over HTTPS, OAuth2 client credentials, rate limit 600 req/min.
- Webhooks: signed with HMAC-SHA256, retries with exponential backoff for 24h.
- Latency: p50 120 ms, p99 400 ms for read endpoints in us-east.
- Throughput: sustained 5k events/s per tenant on the standard plan.

## Who's who

- Dana Reyes — VP Operations, ACME Corp (economic buyer)
- Marcus Chen — Solutions Engineer, our side (technical deep-dives)
- Priya Patel — Customer Success Manager, our side (onboarding, escalations)
- Tom Okafor — Security lead, ACME Corp (runs the security review)
