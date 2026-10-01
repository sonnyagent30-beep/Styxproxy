#!/usr/bin/env python3
"""Charon Blog Citation Eval Test Cases (Sprint 18)

This script defines 10 question-answer pairs where the expected answer cites a blog post.
It also includes an eval runner that tests Charon's /reply endpoint.

Usage:
    python charon_blog_eval_cases.py [--run] [--output FILE]
"""

import argparse
import json
import sys
import time
from typing import Any

import httpx

# =============================================================================
# TEST CASES
# =============================================================================

TEST_CASES = [
    {
        "id": 1,
        "question": "What's the difference between residential and datacenter proxies?",
        "expected_topics": [
            "residential",
            "datacenter",
            "IP",
            "detection",
            "legitimacy",
        ],
        "expected_blog_slug": "residential-vs-datacenter-proxies",
        "category": "product",
        "post_id": "e6f65745-7933-421e-a59a-9e334ed277fe",
    },
    {
        "id": 2,
        "question": "Which Styxproxy plan should I choose for my needs?",
        "expected_topics": [
            "ISP",
            "residential",
            "datacenter",
            "mobile",
            "plan",
        ],
        "expected_blog_slug": "proxy-plans-comparison",
        "category": "product",
        "post_id": "ae1fa87c-01a0-4f69-80a0-e2f89fd9da28",
    },
    {
        "id": 3,
        "question": "How do I set up proxy rotation for my requests?",
        "expected_topics": [
            "rotation",
            "sticky",
            "session",
            "time-based",
            "smart",
        ],
        "expected_blog_slug": "proxy-rotation-guide",
        "category": "howto",
        "post_id": "7c8e3059-9343-4e9a-8fe8-862004b848a2",
    },
    {
        "id": 4,
        "question": "How do I configure proxies in my browser?",
        "expected_topics": [
            "browser",
            "Chrome",
            "Firefox",
            "settings",
            "credentials",
        ],
        "expected_blog_slug": "browser-proxy-setup",
        "category": "howto",
        "post_id": "b95b657e-88f4-479a-910d-2d1233256046",
    },
    {
        "id": 5,
        "question": "Why do my accounts get banned when I'm using proxies?",
        "expected_topics": [
            "warm up",
            "rate limit",
            "location",
            "rotate",
            "session",
            "ban",
        ],
        "expected_blog_slug": "account-safety-guide",
        "category": "general",
        "post_id": "d84e005e-a2e0-4f1c-b437-5120525dd3d5",
    },
    {
        "id": 6,
        "question": "What are the benefits of paid proxy services over free ones?",
        "expected_topics": [
            "free",
            "paid",
            "reliability",
            "speed",
            "security",
            "trial",
        ],
        "expected_blog_slug": "free-vs-paid-proxies",
        "category": "general",
        "post_id": "7261d688-55e7-4965-b086-a95d8225ec4a",
    },
    {
        "id": 7,
        "question": "Tell me about ISP proxies and how they work",
        "expected_topics": [
            "ISP",
            "datacenter",
            "residential",
            "static",
            "authentication",
        ],
        "expected_blog_slug": "isp-proxies-explained",
        "category": "product",
        "post_id": "dd669b47-1e79-4c85-a7ec-5990f3988c50",
    },
    {
        "id": 8,
        "question": "How do I use Python requests with rotating proxies?",
        "expected_topics": [
            "Python",
            "requests",
            "rotation",
            "session",
            "code",
        ],
        "expected_blog_slug": "python-proxy-integration",
        "category": "howto",
        "post_id": "b95b657e-88f4-479a-910d-2d1233256046",
    },
    {
        "id": 9,
        "question": "What makes mobile 4G proxies different from residential?",
        "expected_topics": [
            "mobile",
            "4G",
            "residential",
            "sticky",
            "carrier",
        ],
        "expected_blog_slug": "mobile-4g-vs-residential",
        "category": "product",
        "post_id": "cb132a49-a7fa-4484-a1a0-e04e45639be1",
    },
    {
        "id": 10,
        "question": "Can you explain common proxy mistakes that cost money?",
        "expected_topics": [
            "mistakes",
            "cost",
            "detection",
            "rotation",
            "pricing",
        ],
        "expected_blog_slug": "common-proxy-mistakes",
        "category": "general",
        "post_id": "e6f65745-7933-421e-a59a-9e334ed277fe",
    },
]

# =============================================================================
# EVAL RUNNER
# =============================================================================

CHARON_API_URL = "http://127.0.0.1:8000/api/v1/charon/reply"
TEST_SESSION_ID = "eval-test-session"


def check_topic_presence(response_text: str, expected_topics: list[str]) -> dict[str, Any]:
    """Check if expected topics are present in the response.
    
    Returns a dict with:
    - found: list of topics found
    - missing: list of topics not found
    - score: float 0-1 representing coverage
    """
    response_lower = response_text.lower()
    found = []
    missing = []
    
    for topic in expected_topics:
        if topic.lower() in response_lower:
            found.append(topic)
        else:
            missing.append(topic)
    
    score = len(found) / len(expected_topics) if expected_topics else 0
    
    return {
        "found": found,
        "missing": missing,
        "score": score,
    }


async def run_eval_case(client: httpx.AsyncClient, test_case: dict) -> dict:
    """Run a single eval case against the Charon API."""
    start_time = time.time()
    
    payload = {
        "channel": "web",
        "conversation_id": TEST_SESSION_ID,
        "user_message": test_case["question"],
        "history": [],
    }
    
    try:
        response = await client.post(CHARON_API_URL, json=payload, timeout=60.0)
        response.raise_for_status()
        result = response.json()
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        response_text = result.get("text", "")
        
        # Check topic presence
        topic_check = check_topic_presence(response_text, test_case["expected_topics"])
        
        # Determine pass/fail
        # Pass if at least 50% of expected topics are present
        passed = topic_check["score"] >= 0.5
        
        return {
            "id": test_case["id"],
            "question": test_case["question"],
            "category": test_case["category"],
            "passed": passed,
            "elapsed_ms": round(elapsed_ms, 2),
            "response_preview": response_text[:500] if response_text else "",
            "topic_check": topic_check,
            "escalated": result.get("escaped", False),
            "error": None,
        }
        
    except httpx.HTTPStatusError as e:
        return {
            "id": test_case["id"],
            "question": test_case["question"],
            "category": test_case["category"],
            "passed": False,
            "elapsed_ms": round((time.time() - start_time) * 1000, 2),
            "response_preview": "",
            "topic_check": {"found": [], "missing": test_case["expected_topics"], "score": 0},
            "escalated": False,
            "error": f"HTTP {e.response.status_code}: {str(e)}",
        }
    except Exception as e:
        return {
            "id": test_case["id"],
            "question": test_case["question"],
            "category": test_case["category"],
            "passed": False,
            "elapsed_ms": round((time.time() - start_time) * 1000, 2),
            "response_preview": "",
            "topic_check": {"found": [], "missing": test_case["expected_topics"], "score": 0},
            "escalated": False,
            "error": str(e),
        }


async def run_all_evals() -> dict:
    """Run all eval cases and return results."""
    results = []
    category_scores = {"product": [], "howto": [], "general": []}
    
    async with httpx.AsyncClient() as client:
        for test_case in TEST_CASES:
            print(f"Running test case {test_case['id']}: {test_case['question'][:50]}...")
            result = await run_eval_case(client, test_case)
            results.append(result)
            category_scores[test_case["category"]].append(result["passed"])
            print(f"  → {'PASS' if result['passed'] else 'FAIL'} ({result['elapsed_ms']}ms)")
    
    # Calculate overall score
    total_passed = sum(1 for r in results if r["passed"])
    total_tests = len(results)
    overall_score = total_passed / total_tests if total_tests else 0
    
    # Calculate category scores
    category_summary = {}
    for cat, passes in category_scores.items():
        cat_total = len(passes)
        cat_passed = sum(1 for p in passes)
        category_summary[cat] = {
            "passed": cat_passed,
            "total": cat_total,
            "score": cat_passed / cat_total if cat_total else 0,
        }
    
    return {
        "summary": {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "overall_score": round(overall_score * 100, 1),
            "category_scores": category_summary,
        },
        "results": results,
    }


def print_results(results: dict) -> None:
    """Print formatted eval results."""
    print("\n" + "=" * 60)
    print("EVAL RESULTS")
    print("=" * 60)
    
    summary = results["summary"]
    print(f"\nOverall Score: {summary['overall_score']}% ({summary['total_passed']}/{summary['total_tests']})")
    
    print("\nCategory Breakdown:")
    for cat, scores in summary["category_scores"].items():
        print(f"  {cat}: {scores['score']*100:.0f}% ({scores['passed']}/{scores['total']})")
    
    print("\n" + "-" * 60)
    print("Individual Results:")
    print("-" * 60)
    
    for result in results["results"]:
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"\n[{result['id']}] {status} ({result['elapsed_ms']}ms)")
        print(f"  Q: {result['question'][:60]}...")
        if result["error"]:
            print(f"  ERROR: {result['error']}")
        else:
            topic_check = result["topic_check"]
            print(f"  Topics found: {topic_check['found']}")
            print(f"  Topics missing: {topic_check['missing']}")
            if result.get("escalated"):
                print("  NOTE: Response was escalated")


def main():
    parser = argparse.ArgumentParser(description="Charon Blog Citation Eval")
    parser.add_argument("--run", action="store_true", help="Run the eval against Charon API")
    parser.add_argument("--output", default="blog_eval_results.json", help="Output file for results")
    args = parser.parse_args()
    
    if not args.run:
        # Just print test cases
        print("Test Cases Defined:")
        print(json.dumps(TEST_CASES, indent=2))
        return
    
    import asyncio
    
    print("Starting Charon Blog Citation Eval...")
    results = asyncio.run(run_all_evals())
    
    # Save results
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {args.output}")
    
    # Print summary
    print_results(results)
    
    # Exit with appropriate code
    if results["summary"]["overall_score"] < 50:
        sys.exit(1)


if __name__ == "__main__":
    main()
