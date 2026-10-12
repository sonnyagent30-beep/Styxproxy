# ADR-003: Name as Referral Code

**Date:** 2026-06-26
**Status:** Accepted
**Deciders:** Sonny (agent), Dannion

---

## Context

Styxproxy needs a referral system. The question: what is the referral identifier that customers share with friends?

Options: a random code (BUNCHE7K), a separate referral code field, or the customer's name.

---

## Decision

**Customer's name IS the referral code.** No separate code field needed.

---

## Why Name as Code

| Factor | Decision |
|--------|---------|
| **No extra field** | Already saving customer name — no new data needed |
| **Memorable** | "Use my name, Chidi" is natural and easy to share |
| **Unique by design** | System enforces name uniqueness — if "Chidi" is taken, customer picks another |
| **Simple UX** | "Enter their name" during checkout — no separate referral code to find/copy |
| **Numbers allowed** | Customers can use "Chidi_22" or "ChidiPro" if their preferred name is taken |

**Alternatives considered:**

| Alternative | Why Not |
|-------------|---------|
| Random code (BUNCHE7K) | Extra step to find and share code; not memorable |
| Separate referral code field | More complex; extra UI element; codes can be forgotten |
| Phone number as code | Privacy risk; people don't want to share their number |
| Auto-generated nickname | Less personal; harder to remember/share |

---

## Consequences

**Positive:**
- Zero extra fields — name already exists
- Natural, personal sharing: "Tell them my name when ordering"
- Easy onboarding: just ask for name after first payment
- System suggests alternatives if name is taken (Chidi → Chidi_22, RealChidi)

**Negative:**
- Can't change your name without losing referral history
- Two customers with same preferred name must negotiate
- If customer refuses to give name, no referral for them

**Mitigation:** System recommends alternatives immediately when a name is taken. Admin can rename customers if needed.

---

## Self-Referral Prevention

Customer cannot use their own name as a referral code. The system checks:
```
IF referred_name == customer_name AND same phone → reject referral
```

---

## Uniqueness Enforcement

```javascript
// When customer enters name
const normalized = name.toLowerCase().trim();
const existing = db.query(
  "SELECT phone FROM customers WHERE LOWER(name) = $1",
  [normalized]
);

if (existing.length === 0) {
  // Available — save it
} else if (existing[0].phone === currentPhone) {
  // Their own name — allowed
} else {
  // Taken — show suggestions
}
```

---

## Full Referral Flow

1. Customer completes first payment
2. Styxproxy asks: "What should we call you?"
3. Customer enters name → system checks uniqueness → saves
4. Customer shares name with friend
5. Friend says friend's name during checkout
6. Referrer gets 5% credit on friend's first order

---

## Rollback

If name-as-code causes issues, can add a separate `referral_code` column later. Name would become display-only and the separate code would be the actual referral identifier.
