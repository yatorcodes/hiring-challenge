# PLAN.md

## Architecture

Input: `data/companies.csv` (company_name, mailing_address)
Output: one row per company with contact_name, contact_role,
contact_email_or_phone, confidence_score, source, needs_human_review

Pipeline:

1. **Ingest** — parse CSV, normalize company names
   (strip LLC/Inc/Co suffixes for cleaner lookups), 
   normalize addresses (state, zip)

2. **Enrich** — fan out to three independent mock providers 
   in parallel per company:
   - Business registry (authoritative identity + role)
   - Web/maps listing (contact surface, role signal)
   - Email/phone enrichment (contact details)

3. **Merge** — per company, collect all provider results,
   dedupe by (name, email/phone), score confidence,
   select best candidate, flag low-confidence rows

4. **Output** — write results CSV with all required fields
   including provenance and needs_human_review flag

Components:
- `enricher.py` — orchestrates provider calls per company
- `providers/` — one module per mock provider
- `scorer.py` — confidence scoring + merge logic
- `output.py` — formats and writes results
- `run.py` — entry point, reads CSV, calls enricher, writes output

## Sources & strategy

Three source types, each independently fallible:

**Business registry mock**
Most authoritative for identity — registered agent, owner name,
business type. Fails on: unregistered DBAs, very small sole
proprietors, recently formed entities.
Contributes heavily to confidence when it confirms a name.

**Web/maps listing mock**
Good for phone numbers, sometimes surfaces owner name in
listing description. Fails on: businesses with no web presence,
name mismatches between registry and listing.
Cross-reference with registry to catch false positives.

**Email/phone enrichment mock**
Directly returns contact details but lowest trust alone —
enrichment providers can have stale or inferred data.
Confidence boost only when name matches another source.

Strategy: precision over recall. I will not return a contact
if only one source finds it and the name cannot be corroborated.
A verified "cannot find" is better than an invented contact.

## Quality

**Confidence scoring logic (0-100):**
- Registry match alone: 45
- Web/maps match alone: 35
- Enrichment match alone: 30
- Any two sources agree on name: +25
- All three sources agree on name: +35
- Role matches target priority (AP > owner > CFO > office mgr): +10
- Address corroborates company identity: +5
- Cap at 95 — never 100, provenance is never perfect

**needs_human_review:**
true when confidence < 70 OR contact_email_or_phone is empty

**Deduplication:**
Within a company, group results by normalized name
(lowercase, strip titles). If two providers return
"Jane Smith" and "J. Smith" at same company, treat as
same candidate and merge, boost confidence.

**Provenance:**
Every field records which provider(s) it came from.
source field format: "registry+enrichment" or "maps" etc.
No value is returned without a traceable source.

**Cannot-verify representation:**
contact_name = "" (empty, not null, not "Unknown")
confidence_score = 0
needs_human_review = true
source = "not_found"
This is an honest result, not a failure.

**False-positive risk:**
Biggest risk: name collision — two businesses with similar
names at nearby addresses. Mitigation: require address
substring match before accepting registry result as
belonging to this company.

## Privacy / compliance

**Will do:**
- Business contact info only (owner, AP manager, CFO)
- Record provenance for every value returned
- Support needs_human_review flag for human suppression/review
- Respect "not found" — never infer or guess
- US B2B scope only per dataset

**Will NOT do:**
- Return personal/home addresses or personal email addresses
- Infer identity from any protected characteristic
- Scrape real sites (mocks only for this challenge)
- Return a contact without a traceable source
- Treat a high-confidence guess as verified fact

## Clarifying questions

**1. What happens when the same natural person appears as
   decision-maker at multiple companies in the dataset?**
- Why it matters: deduplication logic and suppression lists
  operate per-company, but if one opt-out covers all their
  businesses we need to know that scope. Also affects
  whether we dedupe across companies or only within.
- Default assumption: treat each company independently.
  Opt-outs are per company_name, not per person.
- What changes if answered: if opt-outs are person-scoped,
  I'd build a cross-company person index and propagate
  suppression across all their associated businesses.

**2. Is there a maximum acceptable latency per company
   lookup, or is this a batch-overnight job?**
- Why it matters: if real-time, providers must be called
  with aggressive timeouts and partial results are
  acceptable. If batch, I can afford retries, fallbacks,
  and slower consensus-building across sources.
- Default assumption: batch job, no real-time constraint.
  I'll optimize for result quality over speed.
- What changes if answered: real-time would change the
  merge strategy — first confident result wins rather than
  waiting for all three providers. Confidence scoring
  would need a "fast path" for single-source high-trust hits.

**3. When a provider returns a contact role that doesn't
   match our priority list exactly (e.g. "billing
   coordinator" or "controller"), how should we map it?**
- Why it matters: the priority order is
  AP > owner > CFO > office manager, but real provider
  data uses inconsistent role labels. Without a mapping
  rule I'll either drop valid contacts or misrank them.
- Default assumption: I'll build a lightweight role
  normalizer — "billing coordinator" maps to AP,
  "controller" maps to CFO, "proprietor" maps to owner.
  Anything unmappable gets office manager as fallback.
- What changes if answered: a client-supplied role taxonomy
  would replace my heuristic mapper entirely, which would
  be more accurate for their specific vertical.