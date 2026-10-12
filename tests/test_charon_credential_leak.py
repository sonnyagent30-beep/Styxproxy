"""The live `Call Charon` node must never put a customer credential on the wire
to an LLM-backed endpoint, and the backend must not forward one if it does.

THE GAP THIS FILE CLOSES
------------------------
t_2a4daeda added `test_no_code_path_posts_credentials_to_the_charon_llm_endpoint`
and a `deliver_credentials_direct` deletion guard. Both look at PYTHON. The
defect that was live in production was in the n8n WORKFLOW JSON, which no
Python assertion can see — and the repo snapshot
`credentials-delivered-workflow.json` that a Python-side grep would read is
STALE (it still carries the pre-fix `message`/`phone` keys), so it misrepresents
production in the one direction that makes the leak look absent.

Verified against production by read-only GET on 2026-10-01: workflow
`Sy0H7iuGMaDg1Af5` ("Credentials Delivered", `active=true`, versionId
`47ea55cd-0df0-4304-8945-79546f85e38a`, updatedAt 2026-10-01T07:49:43Z) holds

    ={{JSON.stringify({user_message: "Your proxy credentials are ready!\\n\\nProxy: "
      + $json.proxy_ip + ":" + $json.proxy_port + "\\nUsername: " + $json.styxproxy_username
      + "\\nPassword: " + $json.styxproxy_password + "\\nExpires: " + $json.expires_at,
      customer_phone: $json.phone, channel: $json.channel})}}

`user_message` is the customer chat prompt: `ChatReplyRequest` (charon.py:128)
→ `post_reply` → `agent.reply` → `_persist_message` (charon_messages, at rest)
and `messages.append(Message(role="user", ...))` → `llm.py` → POST
`https://api.longcat.ai/chat/completions`. 17 such rows are persisted in
production today. Contract correctness (right field names) and data safety (no
secret in the field) are different properties; only the first was guarded.

WHAT IS ASSERTED HERE
---------------------
1. The credential guard itself, against the REAL live node body as its fixture —
   so the test breaks if either the leak or the defence changes.
2. Every credential-bearing token the live node reads must not reach a
   Charon-bound key. This is the assertion that goes red while the workflow is
   still live and unfixed, which is the point: the exposure is real, so a
   passing suite must not be achievable while it exists.
3. The same for the repo snapshot, which is the copy a human greps.
4. That the node body is the ONLY place a password could hide in the workflow —
   matched on HTTP method + url, not on the display name, so renaming the node
   cannot make these assertions vacuous.

READ-ONLY BY CONSTRUCTION: exactly one n8n GET, no other verb. n8n on this
platform honours only `PUT` for writes and a `PUT` with an empty body silently
wipes the workflow to `name:"x"`, 0 nodes — so this file must never grow a write
path. Changing the live workflow is t_8a9c42a4's lane (devops), not the app repo's.
"""
from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SNAPSHOT = REPO / "credentials-delivered-workflow.json"

WORKFLOW_ID = "Sy0H7iuGMaDg1Af5"
N8N_BASE = os.environ.get("N8N_BASE_URL", "http://127.0.0.1:5679")

# The keys on `ChatReplyRequest` that reach persistence and the LLM. Only these
# are Charon-bound; a credential in any of them is the leak.
LLM_BOUND_KEYS = frozenset({"user_message", "history", "page_context"})

# Anything matching these inside an LLM-bound value is a credential. The live
# node reads `$json.styxproxy_password`; `styxproxy_password` also appears as a
# bare key name, so both the reference and the name are listed.
SECRET_TOKENS = (
    "styxproxy_password",
    "bun_password",
    "proxy_password",
    "plaintext_password",
)


# ── the guard, unit-tested first ───────────────────────────────────────────


def test_live_node_body_is_redacted_by_the_guard():
    """The exact production payload must lose its password value.

    The fixture is the live body verbatim, not a hand-written approximation, so
    this fails if the real payload shape ever changes.
    """
    from app.services.charon.credential_guard import inspect_text

    body = (
        "Your proxy credentials are ready!\n\n"
        "Proxy: 198.51.100.7:1080\n"
        "Username: stx_real_user\n"
        "Password: realpass\n"
        "Expires: 2026-10-30T00:00:00Z"
    )
    guard = inspect_text(body)

    assert "realpass" not in guard.redacted, "the password value survived redaction"
    assert "Password: [REDACTED]" in guard.redacted, (
        f"expected the label to be kept and only the value replaced, got "
        f"{guard.redacted!r}"
    )
    assert guard.must_reject, (
        "a delivery bundle (password + Proxy:/Username: companions) must be "
        "classified as a machine notification so it is REFUSED, not answered"
    )


def test_prose_pasting_is_out_of_scope_and_that_is_a_deliberate_choice():
    """A human support message must still get an ANSWER — and is not redacted.

    This test pins a documented LIMITATION, not a win. The guard matches a
    labelled assignment (`Password: x`, `password=x`). It does not match prose
    ("my password is hunter2"), because any pattern wide enough to catch that
    also catches:

        "my password is not working"  ->  "my password is [REDACTED] working"

    which silently corrupts one of the most common real support messages and
    hands the customer a worse answer than before. Precision beats recall here.

    So a customer who types their password into the chat widget still has it
    forwarded. That is a real, smaller residual exposure than the machine bundle
    this card is about, it is the customer's own credential in their own
    conversation, and closing it properly needs a secret-scanner (entropy /
    dictionary / known-format detection), not a wider regex. Recorded as a known
    limitation rather than papered over.
    """
    from app.services.charon.credential_guard import inspect_text

    untouched = inspect_text("my password is not working")
    assert untouched.redacted == "my password is not working"
    assert not untouched.has_secret

    # And confirm the accepted-shape case a customer WOULD hit is the labelled
    # one, which does redact, without refusing the conversation.
    labelled = inspect_text("my login details are\nUsername: stx_user\nPassword: hunter2")
    assert "hunter2" not in labelled.redacted
    assert labelled.has_secret
    assert not labelled.must_reject, (
        "a labelled secret in prose is not a machine delivery bundle; refusing it "
        "would break real support conversations"
    )


def test_guard_leaves_ordinary_chat_untouched():
    """Prose about passwords is not a secret and must survive byte-identical.

    A regex wide enough to also catch "my password is not working" would corrupt
    the most common real support message. This pins the precision.
    """
    from app.services.charon.credential_guard import inspect_text

    for message in (
        "what is your password policy?",
        "my password is not working",
        "I forgot my password, can you reset it?",
        "how do I change my password?",
        "",
        "Proxy: 1.2.3.4:1080",
        "Username: stx_user",
    ):
        guard = inspect_text(message)
        assert guard.redacted == message, f"guard altered ordinary text: {message!r}"
        assert not guard.has_secret
        assert not guard.must_reject


def test_guard_does_not_report_the_literal_brace_artefact_as_a_secret():
    """`Password: {{ $json.styxproxy_password }}` contains no secret.

    That body was live for ~1 minute on 2026-10-01 (5 rows in
    `charon_messages`). Treating a template placeholder as a leaked credential
    would page someone about a non-event; treating it as harmless is correct
    because the value never existed.
    """
    from app.services.charon.credential_guard import inspect_text

    guard = inspect_text(
        "Your proxy credentials are ready!\n\n"
        "Proxy: {{ $json.proxy_ip }}:{{ $json.proxy_port }}\n"
        "Username: {{ $json.styxproxy_username }}\n"
        "Password: {{ $json.styxproxy_password }}\n"
        "Expires: {{ $json.expires_at }}"
    )

    assert not guard.has_secret, f"placeholder reported as a secret: {guard.redacted!r}"
    assert not guard.must_reject


def test_redaction_is_idempotent():
    """The router and agent both screen, so double application must be a no-op.

    If redaction were not idempotent, the second pass would mangle the marker
    into something else and every downstream log line would be misleading.
    """
    from app.services.charon.credential_guard import redact_text

    once = redact_text("Password: realpass\nProxy: 1.2.3.4:1080")
    twice = redact_text(once)

    assert once == twice, f"redaction is not idempotent: {once!r} -> {twice!r}"
    assert "realpass" not in twice


# ── node-body extraction, shared by the live and snapshot assertions ────────


def _charon_node(nodes: list[dict]) -> dict:
    """The node that actually calls Charon, matched on method + url.

    Matching on the display name `Call Charon` would let a rename turn every
    assertion below into a silent pass over nothing.
    """
    for node in nodes:
        params = node.get("parameters", {})
        if (
            node.get("type") == "n8n-nodes-base.httpRequest"
            and str(params.get("method", "GET")).upper() == "POST"
            and "charon/reply" in str(params.get("url", ""))
        ):
            return node
    raise AssertionError(
        "no POST node targeting charon/reply found. Either the workflow no longer "
        "calls Charon (so the leak is gone and this file should be retired), or "
        "it changed node type/url (re-audit by hand before trusting anything here)."
    )


def _llm_bound_text(node: dict) -> str:
    """Every character of the node body that would reach Charon.

    Deliberately the whole body, not a parsed key/value map. The leak does not
    need a key called `user_message` to be a leak — it needs a secret to reach a
    key that IS LLM-bound, and the body is a JS expression whose shape n8n
    resolves at run time, not at read time.
    """
    return json.dumps(node.get("parameters", {}), sort_keys=True)


def _assert_no_secret_reaches_llm(node: dict, source: str) -> None:
    body = _llm_bound_text(node)
    for token in SECRET_TOKENS:
        assert token not in body, (
            f"{source}: the Charon node body references {token!r}.\n"
            f"Everything in this node's parameters is POSTed to an endpoint that "
            f"persists to charon_messages AND forwards the text to "
            f"api.longcat.ai. Credentials go out by email "
            f"(send_order_active_email); n8n should carry order_id/tx_ref only, "
            f"and the backend must resolve anything else."
        )


# ── 1. the live workflow (read-only, one GET) ─────────────────────────────


def _fetch_live_workflow() -> dict | None:
    key = os.environ.get("N8N_API_KEY")
    if not key:
        return None
    req = urllib.request.Request(
        f"{N8N_BASE.rstrip('/')}/api/v1/workflows/{WORKFLOW_ID}",
        headers={"X-N8N-API-KEY": key},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


@pytest.fixture(scope="module")
def live_workflow():
    try:
        workflow = _fetch_live_workflow()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        pytest.skip(f"n8n API not reachable from here ({exc}); live checks skipped")
    if workflow is None:
        pytest.skip("N8N_API_KEY not set; live workflow checks skipped")
    return workflow


def test_live_workflow_identity_and_activity(live_workflow):
    """Assert identity as well as `active`.

    Three same-named `Credentials Delivered` workflows exist and only the
    `active=true` one serves the webhook path, so a read of the wrong ID must not
    be able to pass the assertions below vacuously.
    """
    assert live_workflow["id"] == WORKFLOW_ID
    assert live_workflow["active"] is True, (
        "the workflow this file reads is inactive, so it is not the one serving "
        "/webhook/credentials-delivered"
    )


def test_live_charon_node_carries_no_credential(live_workflow):
    """THE assertion. Red while the live workflow still sends the password.

    This is expected to be red against production as of this commit: the
    workflow body has not been changed yet, because writes to the live workflow
    belong to t_8a9c42a4 (devops). It is deliberately not xfailed. An xfail here
    would report the suite green while customer plaintext passwords keep flowing
    into a third-party LLM request, which is the exact failure mode this file
    exists to end.
    """
    node = _charon_node(live_workflow["nodes"])
    _assert_no_secret_reaches_llm(node, f"live workflow {WORKFLOW_ID}")


def test_live_workflow_no_node_anywhere_carries_a_password(live_workflow):
    """Belt and braces across the WHOLE workflow, not just the Charon node.

    A future edit could add a second HTTP node, or move the password into a Set
    node that a later node interpolates. Both would leak while a Charon-node-only
    assertion stayed green.
    """
    offenders = []
    for node in live_workflow["nodes"]:
        blob = json.dumps(node.get("parameters", {}), sort_keys=True)
        if any(token in blob for token in SECRET_TOKENS):
            offenders.append(node.get("name"))

    assert not offenders, (
        f"node(s) {offenders} reference a credential field name. The webhook "
        f"payload legitimately carries the password (it comes from the fulfilment "
        f"worker), but nothing in this workflow may pass it on to an LLM-backed "
        f"endpoint. Grep the node JSON, not just the Charon node."
    )


def test_the_credential_bearing_fields_are_the_ones_we_think(live_workflow):
    """Pin the LLM-bound key set against the real node.

    Without this, `_llm_bound_text` scans the whole body and the assertion holds
    for the wrong reason: any future node that stops sending `user_message`
    entirely would still pass, and the test would be guarding a shape that no
    longer exists.
    """
    body = json.dumps(live_workflow["nodes"], sort_keys=True)
    assert "user_message" in body, (
        "the live node no longer sends user_message; if credential delivery moved "
        "to another endpoint, re-audit which keys are LLM-bound by hand"
    )
    assert LLM_BOUND_KEYS <= {"user_message", "history", "page_context"}


# ── 2. the repo snapshot (runs anywhere) ───────────────────────────────────


def test_repo_snapshot_carries_no_credential():
    """The checked-in copy must not hand back the leaky version either.

    This file is what anyone greps to answer "what does this workflow send?",
    and what anyone re-imports to rebuild the workflow. While it carries the
    password it propagates the defect to the next person who rebuilds from it,
    even after the live workflow is fixed.

    It is now the credential-FREE target shape rather than an export of the
    live (still-leaky) workflow, so a re-import is safe. That is a deliberate
    divergence from production, recorded in the snapshot's own `notes`; the live
    workflow is devops' to change (t_8a9c42a4).
    """
    assert SNAPSHOT.exists(), (
        f"{SNAPSHOT} is missing. The checked-in workflow snapshot is the copy a "
        f"human greps and a human re-imports; without it the only record of this "
        f"contract is the live n8n database."
    )

    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    offenders = [
        node.get("name")
        for node in snapshot["nodes"]
        if any(
            token in json.dumps(node.get("parameters", {}), sort_keys=True)
            for token in SECRET_TOKENS
        )
    ]

    assert not offenders, (
        f"repo snapshot node(s) {offenders} carry a credential field name. "
        f"This file is re-importable: importing it would rebuild the leak."
    )


def test_repo_snapshot_sends_order_context_not_credentials():
    """The snapshot's positive shape, so the check above cannot pass vacuously.

    Asserting the ABSENCE of a token is only meaningful if the file is
    structurally the thing we think it is. This pins that the Charon node posts
    a non-empty `user_message` naming the order, and uses the model's real field
    names — the same drift the live-workflow assertions guard.
    """
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    node = _charon_node(snapshot["nodes"])
    body = node["parameters"]["jsonBody"]

    assert body.startswith("={{JSON.stringify("), (
        "jsonBody must keep the ={{JSON.stringify( wrapper. A plain JSON string "
        "containing {{ makes n8n send the braces literally."
    )
    assert "user_message" in body, "snapshot must send the model's field name"
    assert "customer_phone" in body, (
        "'customer_phone', not 'phone' - Pydantic ignores unknown keys, so a "
        "wrong name is a silent drop, not a 422"
    )
    # Key boundaries, not bare substrings. `"message:" not in body` is wrong in a
    # way that reads like a passing guard: `user_message:` CONTAINS `message:`,
    # so the check can only ever fail — the corrected body trips it too. Match a
    # key in object-literal position (after `{` or `,`, followed by `:`) so
    # `user_message` and `message` are distinguishable.
    import re as _re

    keys = set(_re.findall(r"[{,]\s*([A-Za-z_$][\w$]*)\s*:", body))
    assert "message" not in keys, f"legacy 'message' key in the body: {sorted(keys)}"
    assert "phone" not in keys, f"legacy 'phone' key in the body: {sorted(keys)}"
    assert keys == {"user_message", "customer_phone", "channel"}, (
        f"expected exactly the three delivery keys, got {sorted(keys)}"
    )
    assert "$json.order_id" in body and "$json.tx_ref" in body, (
        "the snapshot should carry order context so the backend can resolve the "
        "order, rather than the credential itself"
    )


# ── 3. controls: the assertions must actually bite ─────────────────────────


def test_the_secret_assertion_fails_on_the_known_leaky_body():
    """NEGATIVE CONTROL, built from the real pre-fix node.

    A guard that passes on both a clean and a leaky tree proves nothing. This
    reconstructs the live node's actual parameter dict and asserts the check
    rejects it.
    """
    leaky_node = {
        "name": "Call Charon",
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {
            "method": "POST",
            "url": "https://api.styxproxy.com/api/v1/charon/reply",
            "jsonBody": (
                '={{JSON.stringify({user_message: "Your proxy credentials are '
                'ready!\\n\\nProxy: " + $json.proxy_ip + ":" + $json.proxy_port '
                '+ "\\nUsername: " + $json.styxproxy_username + "\\nPassword: " '
                '+ $json.styxproxy_password + "\\nExpires: " + $json.expires_at, '
                "customer_phone: $json.phone, channel: $json.channel})}}"
            ),
        },
    }

    with pytest.raises(AssertionError, match="styxproxy_password"):
        _assert_no_secret_reaches_llm(leaky_node, "negative control")

    # And the whole-workflow sweep catches it too, not just the Charon node.
    assert "Call Charon" in [
        node.get("name")
        for node in [leaky_node]
        if any(
            token in json.dumps(node.get("parameters", {}), sort_keys=True)
            for token in SECRET_TOKENS
        )
    ]


def test_the_secret_assertion_passes_on_a_credential_free_body():
    """POSITIVE CONTROL.

    The known-good shape is order context only, which is what the n8n node
    should send: the backend resolves the order, the customer gets credentials
    by email, and nothing sensitive crosses this boundary.
    """
    clean_node = {
        "name": "Call Charon",
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {
            "method": "POST",
            "url": "https://api.styxproxy.com/api/v1/charon/reply",
            "jsonBody": (
                '={{JSON.stringify({user_message: "Order " + $json.order_id '
                '+ " (" + $json.tx_ref + ") is now active. The customer has been '
                'emailed their proxy credentials.", customer_phone: $json.phone, '
                "channel: $json.channel})}}"
            ),
        },
    }

    _assert_no_secret_reaches_llm(clean_node, "positive control")


def test_charon_node_matcher_survives_a_rename():
    """The matcher keys on method + url, not on the node's display name.

    Proven by renaming the node here: if it matched on `Call Charon`, this
    fixture would raise and the live assertions would be checking a fiction.
    """
    renamed = {
        "name": "Notify Assistant",
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {
            "method": "POST",
            "url": "https://api.styxproxy.com/api/v1/charon/reply",
        },
    }

    assert _charon_node([renamed])["name"] == "Notify Assistant"


def test_charon_node_matcher_ignores_a_get_and_a_different_url():
    """Precondition on the matcher: it must not match the wrong node."""
    wrong_method = {
        "name": "Fetch Charon",
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {"method": "GET", "url": "https://api.styxproxy.com/api/v1/charon/reply"},
    }
    wrong_url = {
        "name": "Post Elsewhere",
        "type": "n8n-nodes-base.httpRequest",
        "parameters": {"method": "POST", "url": "https://api.styxproxy.com/api/v1/orders"},
    }

    with pytest.raises(AssertionError, match="no POST node targeting charon/reply"):
        _charon_node([wrong_method, wrong_url])


# ── 4. the guard is actually WIRED IN, on both routes ──────────────────────
#
# A correct guard that nothing calls is the same as no guard. These assert the
# wiring by BEHAVIOUR (call the screening function with the real model and check
# what the model looks like afterwards), not by grepping for the call site — a
# grep passes on a call inside a branch that never executes.


def test_screening_refuses_the_live_delivery_payload():
    """`post_reply` must 422 the exact payload n8n sends today.

    The value is the production body verbatim. Before this guard existed the same
    payload persisted to `charon_messages` and was POSTed to api.longcat.ai.
    """
    import pytest as _pytest
    from fastapi import HTTPException

    from app.routers.charon import ChatReplyRequest, _screen_inbound_text

    payload = ChatReplyRequest(
        user_message=(
            "Your proxy credentials are ready!\n\nProxy: 198.51.100.7:1080\n"
            "Username: stx_real_user\nPassword: realpass\n"
            "Expires: 2026-10-30T00:00:00Z"
        ),
        customer_phone="+2348000000000",
        channel="whatsapp",
    )

    with _pytest.raises(HTTPException) as excinfo:
        _screen_inbound_text(payload)

    assert excinfo.value.status_code == 422, (
        f"expected 422 so the n8n execution goes visibly red, got "
        f"{excinfo.value.status_code}"
    )
    assert "realpass" not in str(excinfo.value.detail), (
        "the refusal message must not echo the secret back"
    )


def test_screening_redacts_in_place_on_the_model_not_just_the_return_value():
    """The payload object itself must be clean.

    This is the property the handler depends on: everything downstream reads
    `payload.user_message` again — `agent.reply()`, the escalation email body,
    the assistant persist. Screening only the return value would leave the
    escalation email mailing the customer's password to staff.
    """
    from app.routers.charon import ChatReplyRequest, _screen_inbound_text

    payload = ChatReplyRequest(
        user_message="my login details are\nUsername: stx_user\nPassword: hunter2",
        customer_phone="+2348000000000",
        page_context={"plan_code": "NG-RES-5", "note": "Password: leaked-in-ctx"},
    )

    _screen_inbound_text(payload)

    assert "hunter2" not in payload.user_message, (
        f"the model still carries the secret: {payload.user_message!r}"
    )
    assert "leaked-in-ctx" not in str(payload.page_context), (
        f"page_context still carries the secret: {payload.page_context!r}"
    )
    # The non-secret context must survive, or the guard is destroying data.
    assert payload.page_context["plan_code"] == "NG-RES-5"


def test_screening_covers_history_entries():
    """`history` is caller-supplied and is forwarded to the LLM verbatim.

    `post_reply` builds `Message(role=m.role, content=m.content)` from it with no
    filtering, so a password in a history entry reaches the model exactly as one
    in `user_message` would.
    """
    from app.routers.charon import ChatMessage, ChatReplyRequest, _screen_inbound_text

    payload = ChatReplyRequest(
        user_message="hello",
        history=[ChatMessage(role="user", content="Password: historysecret")],
    )

    _screen_inbound_text(payload)

    assert "historysecret" not in payload.history[0].content


def _screened_handler_names() -> set[str]:
    """Names of the coroutine handlers in charon.py that call the screen.

    AST, not a substring count, for two reasons that both bit this card already:
    a substring count matches the identifier inside the helper's own docstring
    and inside comments (so the expected number is a guess about prose), and it
    cannot say WHICH handler screens. Naming the enclosing function is what makes
    the assertion about coverage rather than about a magic integer.
    """
    import ast

    tree = ast.parse((BACKEND / "app" / "routers" / "charon.py").read_text(encoding="utf-8"))

    screened: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Name)
                and inner.func.id == "_screen_inbound_text"
            ):
                screened.add(node.name)
                break
    return screened


def test_every_handler_that_takes_a_user_message_screens_it():
    """Coverage, by handler name.

    The two handlers that accept a `ChatReplyRequest` and forward its
    `user_message` to the LLM are `post_reply` and `post_reply_stream`. Each has
    its own `agent.reply()` call, its own escalation-email block and (on the
    stream route) its own native-LLM path. Screening one and not the other leaves
    an identical hole on a sibling route.

    This is stated as a set of NAMES so that a third route added later without the
    call is a visible diff against this test rather than a silent regression.
    """
    screened = _screened_handler_names()

    assert {"post_reply", "post_reply_stream"} <= screened, (
        f"handlers calling _screen_inbound_text: {sorted(screened)}. Both "
        f"post_reply and post_reply_stream accept a ChatReplyRequest and forward "
        f"its user_message to an LLM-backed path, so both must screen."
    )
    assert "_screen_inbound_text" not in screened, (
        "precondition broken: the helper screens itself, which would make the "
        "coverage assertion above meaningless"
    )


def test_the_screen_coverage_check_detects_a_missing_route_call():
    """NEGATIVE CONTROL for the AST coverage check.

    Built by removing one call from a real source string, so this proves the
    check is sensitive to the exact defect it guards rather than passing on any
    tree that happens to contain the helper.
    """
    import ast

    def screened_in(source: str) -> set[str]:
        tree = ast.parse(source)
        found: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Name)
                    and inner.func.id == "_screen_inbound_text"
                ):
                    found.add(node.name)
                    break
        return found

    vulnerable = """
async def post_reply(payload):
    await _screen_inbound_text(payload)

async def post_reply_stream(payload):
    return payload
"""
    assert screened_in(vulnerable) == {"post_reply"}, (
        "precondition: a stream route without the call must be detectable"
    )
    assert "post_reply_stream" not in screened_in(vulnerable)


# ── 5. the JSONL log, which is served back UNAUTHENTICATED ────────────────
#
# Found while fixing item 1, and more severe than it. `/charon/logs` and
# `/charon/conversations` are `public_only` (no auth) and `_get_conversations()`
# puts `log["user_message"]` straight into `last_message`. Verified live on
# 2026-10-01 with no credentials of any kind:
#
#   $ curl -s "https://api.styxproxy.com/api/v1/charon/conversations?limit=1"
#   HTTP 200 ... "last_message":"Your proxy credentials are ready!\n\nProxy:
#   1.2.3.4:1080\nUsername: sty_e2e\nPassword: pw\nExpires: 2030-..."
#
# 12 of the 50 most recent conversations carry a password in that field, served
# to anyone on the internet. So the ingress guard alone is not sufficient: the
# 17 records already on disk keep leaking until the READ path is screened too.


def test_log_reader_redacts_passwords_already_on_disk(tmp_path, monkeypatch):
    """`_read_logs` must screen on the way OUT.

    This is the assertion that matters for the existing exposure. Redacting only
    on write would leave every record already in `/tmp/charon.log` readable, and
    those records are the ones actually being served today.
    """
    import importlib
    import json as _json

    # `from app.routers import charon` yields the APIRouter, not the module:
    # `app/routers/__init__.py` rebinds the name to the router object. A plain
    # import makes `_read_logs` an AttributeError, which in a test that expects
    # a redaction failure reads as "the log reader is gone", not "the guard is
    # missing". importlib is the codebase convention for exactly this.
    charon_router = importlib.import_module("app.routers.charon")

    log_file = tmp_path / "charon.log"
    log_file.write_text(
        _json.dumps(
            {
                "ts": "2026-10-01T08:43:18Z",
                "channel": "web",
                "conversation_id": "sess-1",
                "user_message": (
                    "Your proxy credentials are ready!\n\nProxy: 1.2.3.4:1080\n"
                    "Username: sty_e2e\nPassword: pw\nExpires: 2030-01-01"
                ),
            }
        )
        + "\n"
        + _json.dumps(
            {
                "ts": "2026-10-01T09:00:00Z",
                "channel": "web",
                "conversation_id": "sess-2",
                "user_message": "how much is 5GB?",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(charon_router, "CHARON_LOG_PATH", str(log_file))

    records = charon_router._read_logs(limit=100)

    assert len(records) == 2, "precondition: both log lines were read"
    assert "pw" not in records[0]["user_message"], (
        f"the password survived the read path: {records[0]['user_message']!r}. "
        f"This endpoint is unauthenticated."
    )
    assert "Password: [REDACTED]" in records[0]["user_message"]
    # Non-secret fields must be untouched, or the log becomes useless.
    assert records[0]["conversation_id"] == "sess-1"
    assert records[0]["channel"] == "web"
    assert records[1]["user_message"] == "how much is 5GB?", (
        "an ordinary message must pass through byte-identical"
    )


@pytest.mark.asyncio
async def test_log_writer_redacts_before_writing(tmp_path, monkeypatch):
    """`_persist_log` must screen at the WRITE too.

    Screening only on read means the secret is still written to disk, still lands
    in any log shipper, and still sits in a backup. Two gates, because they fail
    independently: this one protects the file, the read one protects the rows
    that predate it.

    async because `app.routers.charon` wraps `_persist_log` in an event hook that
    calls `asyncio.create_task(_broadcast_event(...))` to fan out to SSE
    subscribers. Called synchronously it raises `RuntimeError: no running event
    loop`, which surfaces as a harness error rather than a redaction failure — so
    the test would have looked like a broken test instead of a broken guard.
    Exercising it as async also covers the SSE egress the hook creates.
    """
    import importlib

    from app.services.charon import agent

    # Import the router so its SSE event hook is installed, then call whatever
    # `_persist_log` the agent module currently holds (possibly the wrapper).
    importlib.import_module("app.routers.charon")

    log_file = tmp_path / "charon.log"
    monkeypatch.setenv("CHARON_LOG_DIR", str(tmp_path))

    agent._persist_log(
        {
            "channel": "whatsapp",
            "conversation_id": "sess-9",
            "user_message": "Proxy: 1.2.3.4:1080\nPassword: writetest",
        }
    )

    # Let the create_task'd broadcast run, so the hook's own screening is
    # exercised rather than skipped at teardown.
    await asyncio.sleep(0)

    written = log_file.read_text(encoding="utf-8")
    assert "writetest" not in written, f"the secret reached the log file: {written!r}"
    assert "Password: [REDACTED]" in written


def test_conversation_summaries_derive_from_screened_logs(tmp_path, monkeypatch):
    """`last_message` is the field the public endpoint actually returns.

    `_get_conversations` truncates `log["user_message"]` to 100 chars into
    `last_message`. Truncation is not redaction — a 100-char window of the
    production delivery body still contains `Password: <value>`. This asserts
    through the real function rather than through `_read_logs`, so the property
    is pinned where it is consumed.
    """
    import importlib
    import json as _json

    # `from app.routers import charon` yields the APIRouter, not the module:
    # `app/routers/__init__.py` rebinds the name to the router object. A plain
    # import makes `_read_logs` an AttributeError, which in a test that expects
    # a redaction failure reads as "the log reader is gone", not "the guard is
    # missing". importlib is the codebase convention for exactly this.
    charon_router = importlib.import_module("app.routers.charon")

    log_file = tmp_path / "charon.log"
    log_file.write_text(
        _json.dumps(
            {
                "ts": "2026-10-01T08:43:18Z",
                "channel": "web",
                "conversation_id": "sess-1",
                "user_message": (
                    "Your proxy credentials are ready!\n\nProxy: 1.2.3.4:1080\n"
                    "Username: sty_e2e\nPassword: summarysecret\nExpires: 2030"
                ),
                "escalated": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(charon_router, "CHARON_LOG_PATH", str(log_file))

    summaries = charon_router._get_conversations()

    assert summaries, "precondition: a conversation was derived from the log"
    assert "summarysecret" not in summaries[0].last_message, (
        f"the public /charon/conversations payload would carry the password: "
        f"{summaries[0].last_message!r}"
    )
