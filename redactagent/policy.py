"""Purpose-based redaction policies.

The same document is redacted differently depending on why it is being shared:
an IRB research extract keeps the year of admission but pseudonymises the patient,
a court filing keeps the parties' names but masks their ID numbers, and a public
release removes everything except officials acting in their official capacity.
Policies are plain YAML files in /policies so compliance officers can edit them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import config
from .schema import CATEGORIES, Finding

ACTIONS = ("redact", "pseudonymize", "generalize_year", "keep")


@dataclass
class Policy:
    id: str
    name: str
    description: str
    default: str = "redact"
    categories: dict[str, str] = field(default_factory=dict)
    role_overrides: list[dict] = field(default_factory=list)
    legal_basis: str = ""

    def action_for(self, f: Finding) -> str:
        for rule in self.role_overrides:
            cond = rule.get("when", {})
            cats = cond.get("category")
            roles = cond.get("role")
            if cats and f.category not in ([cats] if isinstance(cats, str) else cats):
                continue
            if roles and (f.role or "other") not in ([roles] if isinstance(roles, str) else roles):
                continue
            return rule["action"]
        return self.categories.get(f.category, self.default)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "description": self.description, "legal_basis": self.legal_basis,
                "default": self.default, "categories": self.categories, "role_overrides": self.role_overrides}


def load_policies(folder: Path | None = None) -> dict[str, Policy]:
    folder = folder or config.POLICY_DIR
    out = {}
    docs = [(p, yaml.safe_load(p.read_text(encoding="utf-8"))) for p in folder.glob("*.yaml")]
    for p, d in sorted(docs, key=lambda x: (x[1].get("order", 99), x[0].name)):
        pol = Policy(id=d["id"], name=d["name"], description=d.get("description", ""), default=d.get("default", "redact"),
                     categories=d.get("categories", {}), role_overrides=d.get("role_overrides", []),
                     legal_basis=d.get("legal_basis", ""))
        for a in list(pol.categories.values()) + [r["action"] for r in pol.role_overrides] + [pol.default]:
            assert a in ACTIONS, f"{p.name}: unknown action {a}"
        for c in pol.categories:
            assert c in CATEGORIES, f"{p.name}: unknown category {c}"
        out[pol.id] = pol
    return out


def _year(text: str) -> str:
    m = re.search(r"(?:19|20)\d{2}", text)
    if m:
        return m.group(0)
    m = re.search(r"(\d{2,3})\s?年", text)  # ROC calendar
    if m:
        return str(int(m.group(1)) + 1911)
    return "[YEAR]"


ROLE_LABEL = {"subject": "PERSON", "professional": "STAFF", "party": "PARTY", "witness": "WITNESS", "family": "RELATIVE"}
CAT_LABEL = {"GOV_ID": "ID", "DATE_OF_BIRTH": "DOB", "PHONE": "PHONE", "EMAIL": "EMAIL", "ADDRESS": "ADDRESS",
             "MEDICAL_RECORD_NO": "MRN", "HEALTH_INSURANCE_NO": "NHI", "FINANCIAL_ACCOUNT": "ACCOUNT",
             "LICENSE_PLATE": "PLATE", "QUASI_IDENTIFIER": "QUASI-ID", "DATE": "DATE", "SIGNATURE": "SIGNATURE",
             "FACE_PHOTO": "PHOTO", "SEAL_STAMP": "SEAL"}


def _norm(s: str) -> str:
    s = re.sub(r"^(dr|mr|ms|mrs)\.?\s+", "", s.strip(), flags=re.I)
    return re.sub(r"[\s\-.,]", "", s).lower()


def apply(policy: Policy, findings: list[Finding]) -> None:
    """Set action + printed label on every finding. Pseudonyms are consistent within a document:
    'Hsu', 'Ms. Hsu' and 'Hsu Chih-wei' all become the same [PERSON-1]."""
    registry: dict[str, list[tuple[str, str]]] = {}  # label prefix -> [(normalised text, label)]
    counters: dict[str, int] = {}
    # longer names first so that surname-only mentions attach to the full name
    order = sorted(findings, key=lambda f: (f.page, -len(f.text)))
    for f in order:
        f.action = policy.action_for(f)
        if f.action == "keep":
            f.label = ""
        elif f.action == "generalize_year":
            f.label = _year(f.text)
        elif f.action == "pseudonymize":
            prefix = ROLE_LABEL.get(f.role or "", "PERSON") if f.category == "PERSON_NAME" else CAT_LABEL.get(f.category, f.category)
            key = _norm(f.text)
            label = None
            for k, lab in registry.get(prefix, []):
                if key and (key == k or (len(key) >= 2 and (key in k or k in key))):
                    label = lab
                    break
            if label is None:
                counters[prefix] = counters.get(prefix, 0) + 1
                label = f"[{prefix}-{counters[prefix]}]"
                registry.setdefault(prefix, []).append((key, label))
            f.label = label
        else:
            f.label = ""
