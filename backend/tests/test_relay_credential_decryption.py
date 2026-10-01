"""
Regression tests for the paid-relay credential decryption defect.

The defect: RelayAuth.refresh() cached the raw styxproxy_password column, which
holds Fernet ciphertext for every credential written via set_password(). verify()
then compared the customer's typed 16-char password against ~120 bytes of
ciphertext, so every encrypted credential was rejected with a correct password.

Invariant under test:
    For every active credential, the relay accepts exactly the password the
    customer was shown.

Guards here each carry a negative control: a check that passes on both the
fixed and the broken tree proves nothing. See the skill note "a substring check
can self-satisfy on the very name it is searching for".
"""

import ast
import asyncio
import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RELAY_PATH = REPO_ROOT / "backend" / "relay" / "relay_paid.py"


def load_relay_module():
    """Import relay_paid.py by path, isolated from the app package.

    The relay is a standalone script (deployed to /opt/styxproxy-relay/), not
    part of the `app` package, so it cannot be imported normally. It reads
    DATABASE_URL at import time and exits without it, so it must be set even
    though nothing connects in these tests.
    """
    os.environ.setdefault("DATABASE_URL", "postgresql://unused:unused@127.0.0.1:1/unused")
    spec = importlib.util.spec_from_file_location("relay_paid_under_test", RELAY_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError(f"cannot load relay module from {RELAY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# A fixed, valid Fernet key (base64url of 32 random bytes) for deterministic
# tests. Generated once; not a production value.
TEST_KEY = "I6aWU73VjjXusWQ10X8JqVRuejrNNVqJZGHhlGawTYk="


@pytest.fixture(scope="module")
def relay():
    os.environ["CRED_ENCRYPTION_KEY"] = TEST_KEY
    mod = load_relay_module()
    # Neutralise any real /opt/styxproxy/.env on the build host.
    setattr(mod, "_ENV_CACHE", {})
    return mod


@pytest.fixture(scope="module")
def fernet(relay):
    from cryptography.fernet import Fernet

    return Fernet(TEST_KEY.encode("ascii"))


# ─── decrypt_stored_password: the two shapes ────────────────────────────────


def test_decrypts_fernet_ciphertext(relay, fernet):
    """An encrypted row must yield the plaintext the customer was shown."""
    plaintext = "52bIYPGD02CXEKpL"
    stored = fernet.encrypt(plaintext.encode("utf-8"))
    assert stored.startswith(relay.FERNET_PREFIX)
    assert relay.decrypt_stored_password(stored, fernet) == plaintext


def test_decrypts_legacy_raw_plaintext(relay, fernet):
    """A legacy unencrypted row must keep working — no customer is logged out."""
    plaintext = "ihX0Al0VuH3auUZJ"
    stored = plaintext.encode("utf-8")
    assert not stored.startswith(relay.FERNET_PREFIX)
    assert relay.decrypt_stored_password(stored, fernet) == plaintext


def test_none_and_empty_are_unusable(relay, fernet):
    assert relay.decrypt_stored_password(None, fernet) is None
    assert relay.decrypt_stored_password(b"", fernet) is None


# ─── Fail-closed behaviour ──────────────────────────────────────────────────


def test_wrong_key_does_not_fall_back_to_ciphertext(relay):
    """The core safety property.

    A Fernet-prefixed value that will not decrypt must return None. It must NOT
    fall back to "treat the blob as plaintext", because verify() would then
    compare the customer's input against the ciphertext — reproducing the exact
    bug being fixed, invisibly, whenever CRED_ENCRYPTION_KEY is wrong.
    """
    from cryptography.fernet import Fernet

    # Encrypt with key A, decrypt with key B (both valid, different).
    ciphertext = Fernet(TEST_KEY.encode("ascii")).encrypt(b"52bIYPGD02CXEKpL")
    other_key = Fernet(Fernet.generate_key())

    assert relay.decrypt_stored_password(ciphertext, other_key) is None


def test_missing_fernet_instance_rejects_encrypted(relay):
    """No key configured must reject, not treat the blob as a password."""
    from cryptography.fernet import Fernet

    ciphertext = Fernet(TEST_KEY.encode("ascii")).encrypt(b"52bIYPGD02CXEKpL")
    assert relay.decrypt_stored_password(ciphertext, None) is None


def test_undecodable_non_fernet_blob_is_refused(relay, fernet):
    """Not Fernet, not valid UTF-8 -> refuse rather than guess."""
    assert relay.decrypt_stored_password(b"\xff\xfe\x00\x01", fernet) is None


# ─── verify(): the end-to-end invariant ─────────────────────────────────────


def _make_auth(relay, dsn="postgresql://unused", ttl=30):
    return relay.RelayAuth(dsn, ttl_seconds=ttl)


def _prime_cache(auth, passwords, upstreams):
    """Populate the auth cache directly, bypassing the DB.

    refresh() is the unit under test elsewhere; verify() only reads the cache,
    so priming it keeps these tests hermetic.
    """
    auth._cache = {u: p.encode("utf-8") for u, p in passwords.items()}
    auth._user_to_upstream = dict(upstreams)
    auth._expires_at = float("inf")  # never auto-refresh


def test_verify_accepts_decrypted_password_for_fernet_row(relay, fernet):
    """The regression itself: ciphertext row + correct password -> accepted."""
    username = "sty_tdgnavf1"
    plaintext = "52bIYPGD02CXEKpL"
    upstream = {"host": "la.residential.rayobyte.com", "port": 1080}

    # What refresh() now stores: the DECRYPTED password.
    stored_plaintext = relay.decrypt_stored_password(
        fernet.encrypt(plaintext.encode()), fernet
    )
    auth = _make_auth(relay)
    _prime_cache(auth, {username: stored_plaintext}, {username: upstream})

    result = asyncio.run(auth.verify(username, plaintext))
    assert result is not None
    assert result["username"] == username


def test_verify_still_rejects_wrong_password(relay, fernet):
    """Negative control: the fix must not turn the relay into an open proxy.

    This is the assertion that would have passed on the broken tree if the test
    only checked the happy path.
    """
    username = "sty_tdgnavf1"
    plaintext = "52bIYPGD02CXEKpL"
    auth = _make_auth(relay)
    _prime_cache(auth, {username: plaintext}, {username: {"host": "h", "port": 1}})

    assert asyncio.run(auth.verify(username, "wrongpassword")) is None
    assert asyncio.run(auth.verify(username, plaintext + "x")) is None
    assert asyncio.run(auth.verify(username, "")) is None


def test_verify_rejects_username_with_no_upstream(relay, fernet):
    """A credential with no relay entry must still be refused (no upstream).

    This is why `sty_d10b3d10` remains rejected after the decrypt fix: its
    password is fine, but there is no upstream to route to.
    """
    username = "sty_d10b3d10"
    auth = _make_auth(relay)
    _prime_cache(auth, {username: "hhIHEufKfTQkA4ly"}, {})
    assert asyncio.run(auth.verify(username, "hhIHEufKfTQkA4ly")) is None


# ─── Source guards: the defect must not come back ───────────────────────────


def _refresh_source(relay) -> str:
    import inspect

    return inspect.getsource(relay.RelayAuth.refresh)


def test_refresh_does_not_cache_raw_column(relay):
    """Guard: refresh() must route the column through the decryptor."""
    src = _refresh_source(relay)
    # The bug assigned the column value straight into the cache.
    assert "new_passwords[username] = bytes(pw)" not in src
    assert 'new_passwords[username] = bytes(row["styxproxy_password"])' not in src
    assert "decrypt_stored_password(" in src


def test_negative_control_raw_cache_guard_bites(relay):
    """Prove the guard above is not vacuous."""
    src = _refresh_source(relay)
    buggy = (
        "pw = row['styxproxy_password']\n"
        "if pw:\n"
        "    new_passwords[username] = bytes(pw)\n"
    )

    def would_pass(candidate: str) -> bool:
        return (
            "new_passwords[username] = bytes(pw)" not in candidate
            and "decrypt_stored_password(" in candidate
        )

    assert would_pass(src) is True
    assert would_pass(buggy) is False


def test_no_writer_assigns_plaintext_to_the_column():
    """Guard: no service may write raw plaintext to styxproxy_password.

    `catalog.py` and both `proxy_management.py` rotation paths did exactly this,
    which is how credentials minted encrypted were silently downgraded to
    plaintext — and therefore rejected by the relay.

    Implemented with AST, not regex. A regex cannot tell the three forms apart:

      - ``cred.styxproxy_password = x``       attribute write (proxy_management)
      - ``StyxproxyCredential(styxproxy_password=x)``  kwarg write (catalog.py)
      - ``styxproxy_password = generate_...()``          LOCAL VARIABLE
        (credential.py:184 — legitimate, it holds the plaintext that is then
        handed to set_password(), and a dot-anchored or naive regex flags it)

    A negative control confirms the kwarg form is caught and the local-variable
    form is not.
    """
    offenders = []
    for rel in (
        "backend/app/services/catalog.py",
        "backend/app/services/proxy_management.py",
        "backend/app/services/credential.py",
    ):
        tree = ast.parse((REPO_ROOT / rel).read_text())
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
                value = node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets = [node.target]
                value = node.value
            else:
                # constructor / call kwargs: f(styxproxy_password=...)
                if isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg == "styxproxy_password":
                            offenders.append(
                                f"{rel}:{node.lineno}: kwarg "
                                f"styxproxy_password={ast.unparse(kw.value)}"
                            )
                continue

            for tgt in targets:
                # Only attribute writes touch the column; a bare Name is a local.
                if not (isinstance(tgt, ast.Attribute) and tgt.attr == "styxproxy_password"):
                    continue
                if "ciphertext" in ast.unparse(value):
                    continue  # the one legitimate form
                offenders.append(
                    f"{rel}:{node.lineno}: {ast.unparse(tgt)} = {ast.unparse(value)}"
                )

    assert offenders == [], f"plaintext writes to styxproxy_password: {offenders}"


def test_negative_control_catches_constructor_kwarg_writer():
    """Prove the writer guard above is not vacuous.

    `catalog.py` wrote the plaintext as a constructor kwarg, not an attribute
    assignment. A guard anchored on `\\.styxproxy_password\\s*=` passes on the
    broken tree — this is the guard that would have shipped green while the
    defect stood.
    """
    source = (
        "cred = StyxproxyCredential(\n"
        "    styxproxy_username=our_username,\n"
        "    styxproxy_password=our_password.encode('utf-8'),\n"
        ")\n"
        "local_password = generate_styxproxy_password()\n"
        "cred2.styxproxy_password = new_password.encode('utf-8')\n"
    )

    def offenders_from(src: str):
        found = []
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call):
                for kw in node.keywords:
                    if kw.arg == "styxproxy_password":
                        found.append(ast.unparse(kw.value))
            elif isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Attribute) and tgt.attr == "styxproxy_password":
                        found.append(ast.unparse(node.value))
        return found

    found = offenders_from(source)
    # Both real write forms are caught...
    assert any("encode" in f for f in found), found
    # ...and the legitimate local variable is NOT flagged.
    assert not any("generate_styxproxy_password" in f for f in found), found

    # The old, dot-anchored regex missed the kwarg form entirely.
    assert re.search(r"\.styxproxy_password\s*=", "styxproxy_password=x.encode()") is None


def test_no_reader_decodes_the_column_without_decrypting():
    """Guard: readers must not hand ciphertext to customers as their password."""
    offenders = []
    for rel in (
        "backend/app/services/payment_status.py",
        "backend/app/routers/proxies.py",
    ):
        text = (REPO_ROOT / rel).read_text()
        if "styxproxy_password.decode" in text:
            offenders.append(f"{rel}: decodes the column directly")
        if "get_password()" not in text:
            offenders.append(f"{rel}: never calls get_password()")
    assert offenders == [], f"ciphertext-leaking readers: {offenders}"


def test_model_accessor_tolerates_both_shapes():
    """`get_password()` must serve legacy and encrypted rows identically."""
    from cryptography.fernet import Fernet

    f = Fernet(TEST_KEY.encode("ascii"))
    os.environ["CRED_ENCRYPTION_KEY"] = TEST_KEY

    from app.models import StyxproxyCredential

    legacy = StyxproxyCredential(styxproxy_username="sty_legacy")
    legacy.styxproxy_password = b"ihX0Al0VuH3auUZJ"
    assert legacy.get_password() == "ihX0Al0VuH3auUZJ"

    modern = StyxproxyCredential(styxproxy_username="sty_modern")
    modern.styxproxy_password = f.encrypt(b"52bIYPGD02CXEKpL")
    assert modern.get_password() == "52bIYPGD02CXEKpL"

    # set_password() round-trips.
    fresh = StyxproxyCredential(styxproxy_username="sty_fresh")
    fresh.set_password("SxNFOVp3no2JQNIb")
    assert fresh.styxproxy_password.startswith(b"gAAAA")
    assert fresh.get_password() == "SxNFOVp3no2JQNIb"


def test_relay_unit_declares_the_encryption_key():
    """Guard: the relay systemd unit must supply CRED_ENCRYPTION_KEY.

    The unit was previously absent from the repo entirely, so a re-deploy could
    silently drop the key and reject every encrypted credential again.
    """
    unit = REPO_ROOT / "backend" / "relay" / "styxproxy-relay-paid.service"
    assert unit.exists(), "relay systemd unit missing from the repo"
    text = unit.read_text()
    assert "EnvironmentFile=/opt/styxproxy/.env" in text
    assert "/opt/styxproxy-relay/relay_paid.py" in text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "LIVE PRODUCTION DEFECT, unresolved — this is the reason the paid relay "
        "authenticates nobody. The unit connects as role `styxproxy` while "
        "styxproxy_credentials has FORCEd RLS granted only to `styxproxy_app`, "
        "so refresh() caches 0 users and every credential is rejected. Tracked "
        "on kanban t_1c4a4582; needs a reviewed decision between granting "
        "`styxproxy` a SELECT policy and repointing the unit at `styxproxy_app`. "
        "strict=True so this XPASSes the moment the role is corrected and the "
        "xfail marker has to be removed."
    ),
)
def test_relay_unit_dsn_role_must_see_credentials():
    """Guard: the relay's DB role must actually see credential rows.

    This is the check whose absence let the relay authenticate nobody for an
    unknown period. `styxproxy_credentials` has FORCEd RLS whose only policy
    (`creds_app_all`) is granted to `styxproxy_app`. A relay connecting as any
    other role gets `SELECT`/`UPDATE` privileges it can never exercise, because
    RLS filters every row — so `refresh()` caches 0 users and EVERY customer is
    rejected, with no error anywhere. Only the relay is affected:
    `styxproxy_relay_entries` has no RLS, so bandwidth metering kept working and
    the failure was invisible in the logs.

    The same trap has already been sprung once in this repo: a card reported
    "RLS is not the problem, that role sees all 35 rows" — a true statement
    about `styxproxy_app`, verified with the WRONG identity, while the relay
    ran as `styxproxy` and saw 0.

    This test is static by design (it cannot open a production DB from CI). It
    pins the two facts that made the failure possible, so that changing either
    role or the unit's DSN is a deliberate act:
      1. the RLS on the credentials table is FORCEd, and
      2. the relay unit does not name the policy-owning role in its DSN.
    """
    unit = (REPO_ROOT / "backend" / "relay" / "styxproxy-relay-paid.service").read_text()
    m = re.search(r'Environment="DATABASE_URL=([^"]+)"', unit)
    assert m, "relay unit must set DATABASE_URL explicitly"
    dsn = m.group(1)

    # The role is the DSN's userinfo, before the password.
    userinfo = dsn.split("://", 1)[1].split("@", 1)[0]
    role = userinfo.split(":", 1)[0]

    # The role that owns the RLS policy, per backend/db/migrations.
    policy_owner = "styxproxy_app"

    if role != policy_owner:
        # Not automatically wrong — but it MUST be a deliberate, reviewed choice,
        # so the mismatch is stated loudly rather than discovered in production.
        pytest.fail(
            f"The relay unit connects as DB role {role!r}, but "
            f"styxproxy_credentials has FORCEd RLS whose only policy "
            f"(creds_app_all) is granted to {policy_owner!r}. A relay running as "
            f"{role!r} sees ZERO credential rows: refresh() caches no users and "
            f"every customer is rejected with no error logged. Either grant "
            f"{role!r} a SELECT policy on styxproxy_credentials, or point the "
            f"unit at {policy_owner!r} — and say which, in the unit's comments."
        )