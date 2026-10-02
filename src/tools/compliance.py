"""Compliance & risk tools — for Compliance & Risk Agent."""

from __future__ import annotations

from datetime import datetime

from langchain_core.tools import tool

from src.db.connection import async_session_factory
from src.db.repository import query_compliance_policies, query_trademarks
from src.tools.provenance import dataset_url


@tool
async def check_trademark(product_name: str, category: str, target_country: str) -> dict:
    """Check trademark/patent conflicts for a product name in a target country.

    Searches the trademark database for potential conflicts.
    """
    async with async_session_factory() as session:
        results = await query_trademarks(session, product_name, target_country)

    # Filter to active trademarks only
    active = [r for r in results if r.status == "active"]
    conflicts = []
    for r in active:
        # Simple similarity: product name contains trademark name or vice versa
        if r.name.lower() in product_name.lower() or product_name.lower() in r.name.lower():
            conflicts.append({
                "trademark_name": r.name,
                "category": r.category,
                "owner": r.owner,
                "status": r.status,
            })

    return {
        "product_name": product_name,
        "target_country": target_country,
        "trademarks_checked": len(results),
        "conflicts_found": len(conflicts),
        "conflicts": conflicts,
        "risk_level": "high" if len(conflicts) > 0 else "low",
        "source_url": dataset_url("trademarks", name=product_name, country=target_country),
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def check_certifications(category: str, source_country: str, target_country: str) -> dict:
    """Check required certifications for cross-border sale.

    Returns required certs and certification gaps.
    """
    async with async_session_factory() as session:
        policies = await query_compliance_policies(session, category, target_country)

    required_certs = set()
    for p in policies:
        if p.required_certs:
            required_certs.update(p.required_certs)

    return {
        "category": category,
        "source_country": source_country,
        "target_country": target_country,
        "required_certifications": list(required_certs),
        "certification_count": len(required_certs),
        "policies_checked": len(policies),
        "source_url": dataset_url("compliance_policies", category=category, target_country=target_country),
        "fetch_time": datetime.now().isoformat(),
    }


@tool
async def check_policy_compliance(product_name: str, category: str, target_country: str) -> dict:
    """Check platform and regulatory policy compliance.

    Returns blocks, warnings, and informational notes.
    """
    async with async_session_factory() as session:
        policies = await query_compliance_policies(session, category, target_country)

    blocks = []
    warnings = []
    info = []

    for p in policies:
        entry = {
            "rule_type": p.rule_type,
            "description": p.description,
            "severity": p.severity,
        }
        if p.banned_substances:
            entry["banned_substances"] = p.banned_substances
        if p.import_duty_pct is not None:
            entry["import_duty_pct"] = float(p.import_duty_pct)

        if p.severity == "block":
            blocks.append(entry)
        elif p.severity == "warn":
            warnings.append(entry)
        else:
            info.append(entry)

    return {
        "product_name": product_name,
        "category": category,
        "target_country": target_country,
        "blocks": blocks,
        "warnings": warnings,
        "info": info,
        "block_count": len(blocks),
        "warning_count": len(warnings),
        "is_compliant": len(blocks) == 0,
        "source_url": dataset_url("compliance_policies", category=category, target_country=target_country),
        "fetch_time": datetime.now().isoformat(),
    }
