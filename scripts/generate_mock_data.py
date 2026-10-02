"""Generate all mock data files for the Kriterion demo.

Produces:
  data/mock/candidates.json
  data/mock/market_trends.json
  data/mock/supplier_quotes.json
  data/mock/compliance_policies.json
  data/mock/historical_decisions.json
  data/reference/trademark_sample.json
  data/reference/certification_matrix.json
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MOCK_DIR = DATA_DIR / "mock"
REF_DIR = DATA_DIR / "reference"

CATEGORIES = ["beauty", "electronics", "home_living", "fashion", "food_beverage", "pet_supplies", "toys"]
CATEGORY_WEIGHTS = [25, 20, 15, 15, 10, 8, 7]

PLATFORMS = ["tiktok_shop", "shopee"]
PLATFORM_WEIGHTS = [60, 40]

SOURCE_COUNTRIES = ["CN", "KR", "JP", "TH"]
SOURCE_WEIGHTS = [70, 15, 10, 5]

TARGET_COUNTRIES = ["US", "UK", "ID", "PH", "MY", "TH"]
TARGET_WEIGHTS = [40, 20, 15, 10, 10, 5]

CURRENCIES = {"US": "USD", "UK": "GBP", "ID": "IDR", "PH": "PHP", "MY": "MYR", "TH": "THB"}

# Price ranges by category (min, max, typical)
PRICE_RANGES = {
    "beauty": (3, 80, 25),
    "electronics": (10, 300, 60),
    "home_living": (5, 120, 35),
    "fashion": (5, 100, 30),
    "food_beverage": (2, 50, 15),
    "pet_supplies": (5, 80, 25),
    "toys": (3, 60, 20),
}

# Weight ranges by category (min_kg, max_kg)
WEIGHT_RANGES = {
    "beauty": (0.1, 2.0),
    "electronics": (0.2, 15.0),
    "home_living": (0.5, 25.0),
    "fashion": (0.1, 3.0),
    "food_beverage": (0.2, 10.0),
    "pet_supplies": (0.2, 8.0),
    "toys": (0.1, 5.0),
}

FREIGHT_MODES = {
    "sea": {"cost_per_kg_range": (0.8, 2.5), "days_range": (30, 45)},
    "air": {"cost_per_kg_range": (4.0, 8.0), "days_range": (5, 10)},
    "express": {"cost_per_kg_range": (8.0, 15.0), "days_range": (3, 5)},
}

PRODUCT_NAMES = {
    "beauty": [
        "Vitamin C Serum", "Retinol Night Cream", "Hyaluronic Acid Moisturizer", "Niacinamide Toner",
        "Snail Mucin Essence", "Green Tea Cleanser", "Peptide Eye Cream", "AHA BHA Exfoliant",
        "Sunscreen SPF50+", "CC Cream", "Lip Tint Set", "Hair Growth Serum",
        "Collagen Sheet Mask", "Tea Tree Oil Serum", "Ceramide Barrier Cream",
    ],
    "electronics": [
        "Wireless Earbuds TWS", "LED Desk Lamp", "Mini Projector", "Smart Watch Fitness",
        "Portable Charger 20000mAh", "USB-C Hub 7-in-1", "Bluetooth Speaker Mini",
        "Ring Light 10inch", "Webcam 1080P", "Mechanical Keyboard 60%",
        "Wireless Mouse Ergonomic", "Phone Grip Stand", "Cable Organizer Box",
    ],
    "home_living": [
        "Silicone Kitchen Utensils Set", "Electric Milk Frother", "Vacuum Storage Bags",
        "LED Strip Lights 5M", "Shower Caddy Rustproof", "Laundry Detergent Sheets",
        "Microfiber Cleaning Cloth Set", "Food Storage Container Set", "Air Purifier Mini",
        "Humidifier USB", "Desk Organizer Bamboo", "Drawer Dividers Set",
    ],
    "fashion": [
        "Oversized Graphic Tee", "High Waist Leggings", "Cropped Hoodie",
        "Silk Scrunchie Set", "Canvas Tote Bag", "Platform Sneakers",
        "Boho Maxi Dress", "Ribbed Tank Top Set", "Denim Jacket Oversized",
        "Wireless Bra Seamless", "Swim Cover Up", "Bucket Hat Reversible",
    ],
    "food_beverage": [
        "Matcha Powder Organic", "Instant Coffee Specialty", "Seaweed Snacks",
        "Rice Crackers Variety", "Dried Mango Slices", "Coconut Water Powder",
        "Mochi Variety Pack", "Kimchi Instant Noodles", "Honey Sticks",
        "Protein Bar Variety", "Tea Sampler Gift Set", "Soy Sauce Premium",
    ],
    "pet_supplies": [
        "Cat Laser Toy", "Dog Harness No-Pull", "Pet Water Fountain",
        "Cat Scratching Post", "Dog Dental Chews", "Pet Grooming Glove",
        "Automatic Feeder", "Catnip Toys Set", "Dog Poop Bag Dispenser",
        "Pet Seat Cover", "Fish Tank LED Light", "Hamster Wheel Silent",
    ],
    "toys": [
        "Fidget Spinner Metal", "Building Blocks Set", "Plush Toy Kawaii",
        "Puzzle 1000pc", "RC Car Mini", "Doll Clothes Set",
        "Water Gun Summer", "Slime Kit DIY", "Board Game Family",
        "Sticker Album", "Magnetic Tiles Set", "Action Figure Collection",
    ],
}

PORTS = {
    "CN": ["Shanghai", "Shenzhen", "Ningbo", "Guangzhou"],
    "KR": ["Busan", "Incheon"],
    "JP": ["Tokyo", "Osaka", "Yokohama"],
    "TH": ["Bangkok", "Laem Chabang"],
}

CERT_REQUIREMENTS = {
    "US": {"beauty": ["FDA"], "electronics": ["FCC", "UL"], "food_beverage": ["FDA", "USDA"], "toys": ["CPSC", "ASTM"]},
    "UK": {"beauty": ["UKCA"], "electronics": ["CE", "UKCA"], "food_beverage": ["FSA"], "toys": ["CE", "EN71"]},
    "ID": {"beauty": ["BPOM"], "electronics": ["SNI"], "food_beverage": ["BPOM", "Halal"], "toys": ["SNI"]},
    "PH": {"beauty": ["FDA-PH"], "electronics": ["BPS"], "food_beverage": ["FDA-PH"], "toys": ["BPS"]},
    "MY": {"beauty": ["NPRA"], "electronics": ["SIRIM"], "food_beverage": ["MOH", "Halal"], "toys": ["MC"]},
    "TH": {"beauty": ["FDA-TH"], "electronics": ["TISI"], "food_beverage": ["FDA-TH"], "toys": ["TISI"]},
}


def _weighted_choice(items: list, weights: list[int]) -> str:
    return random.choices(items, weights=weights, k=1)[0]


def generate_candidates(n: int = 500) -> list[dict]:
    records = []
    for i in range(n):
        cat = _weighted_choice(CATEGORIES, CATEGORY_WEIGHTS)
        platform = _weighted_choice(PLATFORMS, PLATFORM_WEIGHTS)
        source = _weighted_choice(SOURCE_COUNTRIES, SOURCE_WEIGHTS)
        target = _weighted_choice(TARGET_COUNTRIES, TARGET_WEIGHTS)
        pmin, pmax, ptyp = PRICE_RANGES[cat]
        price = round(random.lognormvariate(float(ptyp), 0.5), 2)
        price = max(pmin, min(pmax, price))
        wmin, wmax = WEIGHT_RANGES[cat]
        weight = round(random.uniform(wmin, wmax), 3)
        name_prefix = random.choice(PRODUCT_NAMES[cat])
        records.append({
            "name": f"{name_prefix} #{random.randint(100, 999)}",
            "category": cat,
            "subcategory": f"{cat}_sub_{random.randint(1, 5)}",
            "platform": platform,
            "source_country": source,
            "target_country": target,
            "price_usd": price,
            "currency": "USD",
            "moq": random.randint(50, 2000),
            "weight_kg": weight,
            "status": "pending",
            "metadata": {
                "supplier_id": f"SUP-{random.randint(1000, 9999)}",
                "has_brand": random.random() > 0.5,
                "image_count": random.randint(1, 8),
            },
        })
    return records


def generate_market_trends(n: int = 3000) -> list[dict]:
    records = []
    months = [datetime(2025, m, 1) for m in range(1, 13)]
    combos = [(c, p, t) for c in CATEGORIES for p in PLATFORMS for t in TARGET_COUNTRIES]
    for cat, platform, country in combos:
        base_volume = random.randint(5000, 500000)
        base_growth = random.uniform(-15, 40)
        for month in months:
            noise = random.uniform(0.85, 1.15)
            volume = int(base_volume * noise * (1 + random.uniform(-0.05, 0.05)))
            growth = round(base_growth + random.uniform(-5, 5), 2)
            keywords = random.sample(["viral", "trending", "new arrival", "best seller", "limited edition", "summer", "gift", "premium"], k=3)
            records.append({
                "category": cat,
                "platform": platform,
                "country": country,
                "period_month": month.strftime("%Y-%m-%d"),
                "search_volume": volume,
                "growth_rate_pct": growth,
                "avg_rating": round(random.uniform(3.5, 4.9), 2),
                "review_count": random.randint(10, 5000),
                "top_keywords": keywords,
                "influencer_mentions": random.randint(0, 50),
                "creator_sellers": random.randint(0, 20),
                "avg_monthly_revenue_usd": round(random.uniform(1000, 200000), 2),
            })
    return records[:n]


def generate_supplier_quotes(n: int = 2000) -> list[dict]:
    records = []
    supplier_ids = [f"SUP-{i:04d}" for i in range(1, 201)]
    for _ in range(n):
        cat = random.choice(CATEGORIES)
        source = random.choice(SOURCE_COUNTRIES)
        pmin, pmax, ptyp = PRICE_RANGES[cat]
        # Supplier price is typically 20-40% of retail
        unit_price = round(random.uniform(ptyp * 0.2, ptyp * 0.4), 2)
        mode = random.choices(["sea", "air", "express"], weights=[60, 30, 10], k=1)[0]
        freight_info = FREIGHT_MODES[mode]
        freight_per_kg = round(random.uniform(*freight_info["cost_per_kg_range"]), 2)
        records.append({
            "supplier_id": random.choice(supplier_ids),
            "category": cat,
            "source_country": source,
            "unit_price_usd": unit_price,
            "moq": random.randint(50, 1000),
            "lead_time_days": random.randint(*freight_info["days_range"]),
            "freight_mode": mode,
            "freight_cost_per_kg": freight_per_kg,
            "port_of_origin": random.choice(PORTS.get(source, ["Unknown"])),
        })
    return records


def generate_compliance_policies(n: int = 500) -> list[dict]:
    records = []
    rule_types = ["certification", "prohibition", "duty", "labeling", "ingredient"]
    severity_by_type = {
        "certification": ["block", "warn"],
        "prohibition": ["block"],
        "duty": ["info", "warn"],
        "labeling": ["warn", "info"],
        "ingredient": ["block", "warn"],
    }
    for _ in range(n):
        cat = random.choice(CATEGORIES)
        target = random.choice(TARGET_COUNTRIES)
        rule = random.choice(rule_types)
        severity = random.choice(severity_by_type.get(rule, ["info"]))
        certs = CERT_REQUIREMENTS.get(target, {}).get(cat, [])
        duty = round(random.uniform(0, 15), 2) if rule == "duty" else None
        banned = []
        if rule == "ingredient" and cat == "beauty":
            banned = random.sample(["hydroquinone", "mercury", "formaldehyde", "parabens", "phthalates"], k=random.randint(1, 2))
        description = f"{rule.capitalize()} requirement for {cat} in {target}"
        if certs:
            description += f": requires {', '.join(certs)}"
        records.append({
            "category": cat,
            "target_country": target,
            "rule_type": rule,
            "description": description,
            "severity": severity,
            "required_certs": certs if rule in ("certification", "labeling") else [],
            "banned_substances": banned,
            "import_duty_pct": duty,
        })
    return records[:n]


def generate_historical_decisions(n: int = 200) -> list[dict]:
    records = []
    for _ in range(n):
        cat = random.choice(CATEGORIES)
        platform = random.choice(PLATFORMS)
        target = random.choice(TARGET_COUNTRIES)
        verdict = random.choices(["go", "watch", "no_go"], weights=[40, 35, 25], k=1)[0]
        scores = {
            "market_demand": round(random.uniform(3, 10), 1),
            "competition": round(random.uniform(3, 10), 1),
            "cost_margin": round(random.uniform(3, 10), 1),
            "compliance_risk": round(random.uniform(3, 10), 1),
            "supply_stability": round(random.uniform(3, 10), 1),
            "trend_momentum": round(random.uniform(3, 10), 1),
            "return_rate": round(random.uniform(3, 10), 1),
        }
        outcome = random.choices(["success", "neutral", "failure"], weights=[50, 30, 20], k=1)[0] if verdict == "go" else "failure"
        records.append({
            "candidate_snapshot": {
                "name": f"Product-{random.randint(1000, 9999)}",
                "category": cat,
                "platform": platform,
                "target_country": target,
                "price_usd": round(random.uniform(5, 100), 2),
            },
            "verdict": verdict,
            "scores": scores,
            "key_evidence_summary": f"Market {'favorable' if scores['market_demand'] > 6 else 'weak'}, margin {'adequate' if scores['cost_margin'] > 6 else 'thin'}",
            "outcome_actual": outcome,
            "lessons_learned": f"{'High demand validated' if outcome == 'success' else 'Compliance gap missed' if outcome == 'failure' else 'Mixed signals'}",
        })
    return records


def generate_trademarks(n: int = 100) -> list[dict]:
    records = []
    well_known = [
        ("Apple", "electronics", "US"), ("Samsung", "electronics", "KR"),
        ("Dyson", "home_living", "UK"), ("L'Oréal", "beauty", "US"),
        ("Nike", "fashion", "US"), ("LEGO", "toys", "DK"),
        ("Purina", "pet_supplies", "US"), ("Nestlé", "food_beverage", "CH"),
        ("Sony", "electronics", "JP"), ("Unilever", "beauty", "UK"),
        ("Adidas", "fashion", "DE"), ("Panasonic", "electronics", "JP"),
        ("Colgate", "beauty", "US"), ("Hasbro", "toys", "US"),
        ("Whiskas", "pet_supplies", "US"),
    ]
    for name, cat, owner_country in well_known:
        for target in random.sample(TARGET_COUNTRIES, k=random.randint(2, 4)):
            records.append({
                "name": name,
                "category": cat,
                "country": target,
                "status": "active",
                "owner": f"{name} Inc. ({owner_country})",
            })
    # Add some generic marks
    while len(records) < n:
        cat = random.choice(CATEGORIES)
        name = f"Brand{random.randint(100, 999)}"
        country = random.choice(TARGET_COUNTRIES)
        records.append({
            "name": name,
            "category": cat,
            "country": country,
            "status": random.choice(["active", "pending", "expired"]),
            "owner": f"Owner-{random.randint(1, 50)}",
        })
    return records[:n]


def generate_certification_matrix() -> dict:
    """Generate country x category certification requirements matrix."""
    matrix = {}
    for country, cat_certs in CERT_REQUIREMENTS.items():
        matrix[country] = {}
        for cat, certs in cat_certs.items():
            matrix[country][cat] = {
                "required_certs": certs,
                "notes": f"Must obtain {', '.join(certs)} before listing",
            }
    return matrix


def main() -> None:
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    REF_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating candidates...")
    candidates = generate_candidates(500)
    with open(MOCK_DIR / "candidates.json", "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    print(f"  → {len(candidates)} candidates")

    print("Generating market trends...")
    trends = generate_market_trends(3000)
    with open(MOCK_DIR / "market_trends.json", "w", encoding="utf-8") as f:
        json.dump(trends, f, indent=2, ensure_ascii=False)
    print(f"  → {len(trends)} trend records")

    print("Generating supplier quotes...")
    quotes = generate_supplier_quotes(2000)
    with open(MOCK_DIR / "supplier_quotes.json", "w", encoding="utf-8") as f:
        json.dump(quotes, f, indent=2, ensure_ascii=False)
    print(f"  → {len(quotes)} supplier quotes")

    print("Generating compliance policies...")
    policies = generate_compliance_policies(500)
    with open(MOCK_DIR / "compliance_policies.json", "w", encoding="utf-8") as f:
        json.dump(policies, f, indent=2, ensure_ascii=False)
    print(f"  → {len(policies)} compliance policies")

    print("Generating historical decisions...")
    decisions = generate_historical_decisions(200)
    with open(MOCK_DIR / "historical_decisions.json", "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2, ensure_ascii=False)
    print(f"  → {len(decisions)} historical decisions")

    print("Generating trademark samples...")
    trademarks = generate_trademarks(100)
    with open(REF_DIR / "trademark_sample.json", "w", encoding="utf-8") as f:
        json.dump(trademarks, f, indent=2, ensure_ascii=False)
    print(f"  → {len(trademarks)} trademarks")

    print("Generating certification matrix...")
    cert_matrix = generate_certification_matrix()
    with open(REF_DIR / "certification_matrix.json", "w", encoding="utf-8") as f:
        json.dump(cert_matrix, f, indent=2, ensure_ascii=False)
    print("  → certification matrix")

    print("\n✅ All mock data generated successfully!")


if __name__ == "__main__":
    main()
