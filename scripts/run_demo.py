"""End-to-end demo runner.

1. Generates mock data if not present
2. Seeds database and vector store
3. Submits a candidate for evaluation
4. Watches the workflow progress via SSE
5. Prints the final decision card
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import settings

API_BASE = f"http://localhost:{8000}"


async def run_demo() -> None:
    import httpx

    async with httpx.AsyncClient(base_url=API_BASE, timeout=60.0) as client:
        # 1. List candidates
        print("📋 Listing candidates...")
        resp = await client.get("/candidates?limit=5")
        candidates = resp.json().get("items", [])
        if not candidates:
            print("  No candidates found. Please run `make seed` first.")
            return

        # 2. Pick the first pending candidate
        candidate = candidates[0]
        candidate_id = candidate["id"]
        print(f"  Selected: {candidate['name']} ({candidate['category']}, {candidate['platform']})")

        # 3. Trigger workflow
        print("\n🚀 Starting workflow...")
        resp = await client.post("/workflow/run", json={"candidate_id": candidate_id})
        run_data = resp.json()
        run_id = run_data["run_id"]
        print(f"  Run ID: {run_id}")

        # 4. Poll status
        print("\n⏳ Waiting for workflow to complete...")
        for _ in range(60):
            await asyncio.sleep(2)
            resp = await client.get(f"/workflow/{run_id}/status")
            status_data = resp.json()
            current = status_data.get("current_node", "?")
            wf_status = status_data.get("status", "?")
            print(f"  [{wf_status}] Current node: {current}")
            if wf_status in ("completed", "failed"):
                break

        # 5. Get decision card
        if wf_status == "completed":
            print("\n✅ Workflow completed! Fetching decision card...")
            resp = await client.get(f"/decisions?run_id={run_id}")
            cards = resp.json().get("items", [])
            if cards:
                card = cards[0]
                print(f"\n{'='*60}")
                print(f"  DECISION CARD")
                print(f"{'='*60}")
                print(f"  Candidate: {candidate['name']}")
                print(f"  Verdict:    {card['verdict'].upper()}")
                print(f"  Score:      {card['overall_score']}/10")
                print(f"\n  Dimension Scores:")
                for dim, score in card.get("scores", {}).items():
                    bar = "█" * int(score) + "░" * (10 - int(score))
                    print(f"    {dim:20s} [{bar}] {score}")
                if card.get("risk_flags"):
                    print(f"\n  ⚠ Risk Flags: {json.dumps(card['risk_flags'], indent=4)}")
                if card.get("watch_reasons"):
                    print(f"\n  👁 Watch Reasons: {json.dumps(card['watch_reasons'], indent=4)}")
                print(f"{'='*60}")
            else:
                print("  No decision card found.")
        else:
            print(f"\n❌ Workflow failed: {status_data.get('error_message', 'unknown')}")


if __name__ == "__main__":
    asyncio.run(run_demo())
