"""Credential-material guard for everything Charon sends to an LLM.

WHY THIS MODULE EXISTS
----------------------
`POST /api/v1/charon/reply` takes a field called `user_message`. That name is
the whole problem: it is the CUSTOMER CHAT PROMPT, and
`app/routers/charon.py` hands it to `agent.reply()`, which

  1. persists it via `_persist_message()` into the `charon_messages` table, and
  2. appends it to `messages`, which `app/services/charon/llm.py` POSTs to
     `https://api.longcat.ai/chat/completions`.

So anything an internal caller puts in `user_message` is, by construction, both
AT REST and IN FLIGHT to a third-party model provider.

That is not hypothetical. The live n8n workflow `Sy0H7iuGMaDg1Af5`
("Credentials Delivered", `active=true`, versionId `47fa55cd-…`,
updatedAt 2026-10-01T07:49:43Z) has a `Call Charon` node whose body is

    ={{JSON.stringify({user_message: "Your proxy credentials are ready!\\n\\nProxy: "
      + $json.proxy_ip + ":" + $json.proxy_port + "\\nUsername: " + $json.styxproxy_username
      + "\\nPassword: " + $json.styxproxy_password + "\\nExpires: " + $json.expires_at,
      customer_phone: $json.phone, channel: $json.channel})}}

so every credential delivery routed through n8n put a live customer's proxy
username and PLAINTEXT PASSWORD into a third-party LLM request and into the
conversation table. 17 such rows are persisted in production
(`charon_messages`, all `role='user'`, 2026-09-30 → 2026-10-01).

n8n is an external system, so the workflow body is devops' to change — but a
backend that forwards whatever it is handed is not a defence. This module is the
backend-side control: it is pure, dependency-free and importable without a
config-valid environment, so it can be unit-tested directly.

WHAT IT DOES, AND WHY TWO TIERS
-------------------------------
Detected material is a LABELLED SECRET ASSIGNMENT — `Password: hunter2`,
`password=hunter2`, `"styxproxy_password": "…"`. The label is what makes it
unambiguous; a bare word `password` is not a secret.

  * `machine_notification` — the label-value form PLUS delivery-bundle
    companions (`Proxy:`, `Username:`, `Expires:`, `…credentials are ready`).
    This is machine-to-machine, never a customer typing. It is REJECTED with
    HTTP 422 so the n8n execution goes red and the misconfiguration is visible.
    It is not merely redacted, because a redacted-but-accepted delivery bundle
    would spend LLM tokens on a meaningless notification and read as success.

  * everything else — REDACTED in place. A customer who pastes their login
    details into the chat widget should still get an answer; only the value is
    removed. Refusing that would be a support regression.

Prose ("my password is hunter2") is deliberately NOT matched: any pattern wide
enough to catch it also corrupts "my password is not working". See the
docstring on `test_prose_pasting_is_out_of_scope_and_that_is_a_deliberate_choice`.

Both tiers remove the secret. Redaction is idempotent, so applying this at the
router AND again inside `agent.reply()` cannot double-mangle a message.

DELIBERATELY NOT DONE
---------------------
The word "password" in prose is not redacted. A regex wide enough to catch
"my password is hunter2" also eats "my password is not working", which is one
of the most common real support messages. Precision beats recall here: a false
positive silently corrupts a customer's conversation, and the actual exposure
being fixed is the machine bundle, which this module detects exactly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

REDACTED = "[REDACTED]"

# Delivery-bundle companion labels, used only as a COUNT. A single companion
# (`Username: stx_user`) is something a customer types; a bundle of them is not.
_BUNDLE_COMPANION = re.compile(
    r"(?im)^[^\S\n]*(?P<label>"
    r"proxy|proxy[_\s-]?ip|proxy[_\s-]?port|username|user|host|port"
    r"|expires|expires[_\s-]?at"
    r")\s*[:=]"
)

# How many distinct companion labels make a message a machine bundle. Two, not
# one: a customer pasting their own login block writes `Username:` and
# `Password:` and nothing else, and refusing that is a support regression — the
# exact failure the two-tier design exists to avoid. The n8n delivery body emits
# Proxy, Username, Password AND Expires, so it clears two comfortably.
_MIN_BUNDLE_COMPANIONS = 2

# The literal phrasing the n8n node uses. Checked separately because a bundle
# whose labels got reworded still reads as a machine notification, and because
# this phrasing alone is unambiguous — no customer writes it.
_DELIVERY_PREAMBLE = re.compile(r"proxy\s+credentials\s+are\s+ready", re.IGNORECASE)

# A labelled secret assignment. Two groups matter for correctness:
#   `sep`   — the `:` / `=` and its surrounding space, which must be RE-EMITTED.
#             Dropping it turns `Password: hunter2` into `Password[REDACTED]`,
#             which reads as a rendering bug and breaks the very log line an
#             operator greps for. Found by a test asserting the label survives.
#   `quote` — captured so a quoted JSON value keeps its quotes. With an empty
#             `quote` group, `(?P=quote)` matches the empty string, so quoted and
#             unquoted values are handled by one pattern.
_SECRET_ASSIGNMENT = re.compile(
    r"(?P<label>"
    r"\b(?:styxproxy[_\s-]*)?"
    r"(?:pass(?:word|wd|phrase)|secret|api[_\s-]*key|auth[_\s-]*token|access[_\s-]*token)"
    r"\b"
    r")"
    r"(?P<sep>[^\S\n]{0,4}[:=][^\S\n]*)"
    r"(?P<quote>[\"']?)"
    r"(?P<value>[^\s\"',;]+)"
    r"(?P=quote)",
    re.IGNORECASE,
)

# Values that are placeholders, not secrets. Redacting these would be harmless
# but noisy; more importantly, leaving them alone keeps the guard from reporting
# the literal-brace n8n breakage (`Password: {{ $json.styxproxy_password }}`) as
# a credential leak, which it is not.
_PLACEHOLDER_VALUES = frozenset(
    {
        "{{",
        "}}",
        "null",
        "none",
        "undefined",
        "true",
        "false",
        "n/a",
        "***",
        "xxx",
        "changeme",
        "redacted",
        REDACTED.lower(),
    }
)


@dataclass(frozen=True)
class CharonTextGuard:
    """Result of inspecting one piece of text bound for Charon.

    `redacted` is safe to persist and to forward to the LLM. The remaining
    fields are for logging and assertions only and must never be logged with the
    value attached.
    """

    redacted: str
    secret_labels: tuple[str, ...] = ()
    machine_notification: bool = False
    hits: int = 0

    @property
    def has_secret(self) -> bool:
        return self.hits > 0

    @property
    def must_reject(self) -> bool:
        """True when this text is a machine credential delivery, not a human."""
        return self.machine_notification and self.has_secret


def _is_placeholder(value: str) -> bool:
    v = value.strip().strip("\"'").lower()
    if v in _PLACEHOLDER_VALUES:
        return True
    # A bare n8n/templating token, e.g. `{{`, `{{ $json.x }}`, `${PASSWORD}`.
    return bool(re.fullmatch(r"\{\{?.*\}?\}|\$\{.*\}|<[^>]*>|\[[^\]]*\]", v, re.DOTALL))


def inspect_text(text: str | None) -> CharonTextGuard:
    """Inspect `text` and return it with any labelled secret value redacted.

    Never raises, never returns None, and is safe to call on any string —
    including empty, None, or a value that is not `str` at all (it is coerced).
    """
    if not text:
        return CharonTextGuard(redacted="")

    original = text if isinstance(text, str) else str(text)

    labels: list[str] = []
    hits = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal hits
        value = match.group("value")
        if _is_placeholder(value):
            return match.group(0)
        hits += 1
        labels.append(match.group("label").strip())
        return (
            f"{match.group('label')}{match.group('sep')}"
            f"{match.group('quote')}{REDACTED}{match.group('quote')}"
        )

    redacted = _SECRET_ASSIGNMENT.sub(_sub, original)

    companions = {
        m.group("label").strip().lower() for m in _BUNDLE_COMPANION.finditer(redacted)
    }
    machine = bool(hits) and (
        len(companions) >= _MIN_BUNDLE_COMPANIONS
        or bool(_DELIVERY_PREAMBLE.search(redacted))
    )

    return CharonTextGuard(
        redacted=redacted,
        secret_labels=tuple(dict.fromkeys(labels)),
        machine_notification=machine,
        hits=hits,
    )


def redact_text(text: str | None) -> str:
    """Convenience wrapper: `text` with labelled secret values replaced."""
    return inspect_text(text).redacted


def redact_mapping(values: dict | None) -> dict:
    """Redact every string leaf of a caller-supplied mapping.

    `ChatReplyRequest.page_context` is a free-form `dict` supplied by the
    caller, persisted to `charon_conversations.page_context`, and partly folded
    into the system prompt by `page_templates.get_page_prompt_addition`. Nothing
    on the model constrains its keys, so a password dropped in there would reach
    the LLM without ever passing through `user_message`.
    """
    if not isinstance(values, dict):
        return {}

    def _walk(value) -> object:
        if isinstance(value, str):
            return redact_text(value)
        if isinstance(value, dict):
            return {k: _walk(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            walked = [_walk(v) for v in value]
            return type(value)(walked) if isinstance(value, tuple) else walked
        return value

    walked: dict = {k: _walk(v) for k, v in values.items()}
    return walked
