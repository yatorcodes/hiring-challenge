"""
Contact Finder — AgentCollect hiring challenge Stage B
Author: Emmanuel Yator

Reads companies.csv, queries mock providers, scores confidence,
outputs contacts.csv with provenance and needs_human_review flag.
"""

import csv
import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional

CONFIDENCE_THRESHOLD = 70

ROLE_PRIORITY = {
    "ap manager": 1, "accounts payable": 1, "billing coordinator": 1,
    "owner": 2, "founder": 2, "proprietor": 2, "president": 2,
    "cfo": 3, "chief financial officer": 3, "controller": 3, "finance lead": 3,
    "office manager": 4, "manager": 4, "registered agent": 5,
}

@dataclass
class Contact:
    contact_name: str = ""
    contact_role: str = ""
    contact_email_or_phone: str = ""
    confidence_score: int = 0
    source: str = "not_found"
    needs_human_review: bool = True
    provenance: list = field(default_factory=list)

def normalize_role(raw_role):
    if not raw_role: return "unknown"
    lower = raw_role.lower().strip()
    for key in ROLE_PRIORITY:
        if key in lower: return raw_role
    return raw_role

def role_priority(role):
    if not role: return 99
    lower = role.lower().strip()
    for key, priority in ROLE_PRIORITY.items():
        if key in lower: return priority
    return 6

def normalize_name(name):
    if not name: return ""
    cleaned = re.sub(r'\b(dr\.?|mr\.?|mrs\.?|ms\.?|prof\.?)\s*', '', name, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^a-z\s]', '', cleaned.lower()).strip()
    return cleaned

def names_agree(name_a, name_b):
    a = normalize_name(name_a)
    b = normalize_name(name_b)
    if not a or not b: return False
    if a == b: return True
    last_a = a.split()[-1]
    last_b = b.split()[-1]
    if last_a != last_b: return False
    first_tokens_a = set(a.split()[:-1])
    first_tokens_b = set(b.split()[:-1])
    for ta in first_tokens_a:
        for tb in first_tokens_b:
            if ta == tb: return True
            if len(ta) == 1 and tb.startswith(ta): return True
            if len(tb) == 1 and ta.startswith(tb): return True
    return False

def score_contact(registry, listing, enrichment, chosen_name, sources_used):
    score = 0
    contributing_sources = len(sources_used)
    if registry and registry.get("name"): score += 35
    if listing and listing.get("name"): score += 20
    if enrichment and (enrichment.get("email") or enrichment.get("phone")):
        provider_conf = enrichment.get("provider_confidence", 0) if enrichment else 0
        score += int(provider_conf * 0.25)
    reg_name = registry.get("name") if registry else None
    lst_name = listing.get("name") if listing else None
    if reg_name and lst_name and names_agree(reg_name, lst_name): score += 20
    if reg_name and enrichment:
        if enrichment.get("email") or enrichment.get("phone"):
            provider_conf = enrichment.get("provider_confidence", 0)
            if provider_conf >= 70: score += 20
            elif provider_conf >= 50: score += 12
            else: score += 5
    if lst_name and not reg_name and enrichment:
        if enrichment.get("email") or enrichment.get("phone"): score += 8
    if contributing_sources == 3 and reg_name and lst_name and names_agree(reg_name, lst_name):
        score += 10
    return min(score, 95)

def find_contact(company_name, mock_data):
    providers = mock_data.get(company_name, {})
    registry   = providers.get("registry")
    listing    = providers.get("listing")
    enrichment = providers.get("enrichment")
    if not providers:
        return Contact(confidence_score=0, source="not_found", needs_human_review=True)
    candidates = []
    if registry and registry.get("name"):
        candidates.append({"name": registry["name"], "role": normalize_role(registry.get("role", "")), "source_urls": [registry["source_url"]], "from": "registry"})
    if listing and listing.get("name"):
        matched = False
        for c in candidates:
            if names_agree(c["name"], listing["name"]):
                c["source_urls"].append(listing["source_url"])
                matched = True
                break
        if not matched:
            candidates.append({"name": listing["name"], "role": "", "source_urls": [listing["source_url"]], "from": "listing"})
    if not candidates and enrichment:
        candidates.append({"name": "", "role": "", "source_urls": [enrichment["source_url"]], "from": "enrichment"})
    if candidates and enrichment:
        candidates[0]["source_urls"].append(enrichment["source_url"])
    best = sorted(candidates, key=lambda c: role_priority(c["role"]))[0] if candidates else {"name": "", "role": "", "source_urls": [], "from": "none"}
    contact_detail = ""
    if enrichment: contact_detail = enrichment.get("email") or enrichment.get("phone") or ""
    if not contact_detail and listing: contact_detail = listing.get("phone") or ""
    all_source_urls = list(dict.fromkeys(best.get("source_urls", [])))
    source_str = " | ".join(all_source_urls) if all_source_urls else "not_found"
    score = score_contact(registry=registry, listing=listing, enrichment=enrichment, chosen_name=best["name"], sources_used=[s for s in [registry, listing, enrichment] if s])
    if not registry and not listing and enrichment:
        provider_conf = enrichment.get("provider_confidence", 0)
        score = int(provider_conf * 0.6)
    needs_review = score < CONFIDENCE_THRESHOLD or not contact_detail
    return Contact(
        contact_name=best["name"] if not needs_review else "",
        contact_role=best["role"] if not needs_review else "",
        contact_email_or_phone=contact_detail if not needs_review else "",
        confidence_score=score, source=source_str, needs_human_review=needs_review,
    )

def run(companies_path, mock_path, output_path):
    with open(mock_path, "r", encoding="utf-8") as f: mock_data = json.load(f)
    with open(companies_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        companies = list(reader)
    results = []
    for row in companies:
        company_name = row["company_name"]
        contact = find_contact(company_name, mock_data)
        results.append({"company_name": company_name, "mailing_address": row["mailing_address"], "contact_name": contact.contact_name, "contact_role": contact.contact_role, "contact_email_or_phone": contact.contact_email_or_phone, "confidence_score": contact.confidence_score, "source": contact.source, "needs_human_review": str(contact.needs_human_review).lower()})
    fieldnames = ["company_name", "mailing_address", "contact_name", "contact_role", "contact_email_or_phone", "confidence_score", "source", "needs_human_review"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Done. {len(results)} companies processed → {output_path}")
    reviewed = sum(1 for r in results if r["needs_human_review"] == "true")
    found = sum(1 for r in results if r["needs_human_review"] == "false")
    print(f"  Contacts found (confidence >= {CONFIDENCE_THRESHOLD}): {found}")
    print(f"  Needs human review: {reviewed}")

if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    run(
        companies_path=os.path.join(base, "challenge", "data", "companies.csv"),
        mock_path=os.path.join(base, "challenge", "mocks", "enrichment_responses.json"),
        output_path=os.path.join(base, "output", "contacts.csv"),
    )