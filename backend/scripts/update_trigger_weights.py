"""
Nightly job: recalculate trigger weights from the last 7 days of engagement data.
Learns from aggregate behavior across ALL sessions.

Formula:
  positive_rate = (opens + converted × 1.5) / total_engaged
  engagement_boost = min(engagement_rate, 1.0)
  signal = (positive_rate - 0.40) × engagement_boost
  new_weight = clamp(old_weight + 0.10 × signal, 0.2, 3.0)

Constants: BASELINE=0.40, LEARNING_RATE=0.10, MIN=0.2, MAX=3.0, MIN_FIRES=20, MIN_DATA=10

Author: Oyebiyi Ayomide
"""
import os
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.environ["DATABASE_URL"]

BASELINE_RATE = 0.40
LEARNING_RATE = 0.10
MIN_WEIGHT = 0.2
MAX_WEIGHT = 3.0
MIN_FIRES_FOR_LEARNING = 20
MIN_DATA_POINTS = 10

ALL_TRIGGERS = [
    'repeat_pricing', 'pricing_dwell', 'product_browse', 'cart_abandon',
    'order_confusion', 'session_stuck', 'scroll_bottom', 'exit_intent', 'geo_question'
]


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


async def main():
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        for trigger_id in ALL_TRIGGERS:
            # Get last known weight
            result = await session.execute(
                text("SELECT weight FROM trigger_weights WHERE trigger_id = :tid"),
                {"tid": trigger_id}
            )
            row = result.fetchone()
            if not row:
                continue
            old_weight = float(row[0])

            # Get aggregate stats from last 7 days
            stats = await session.execute(
                text("""
                    SELECT
                        COUNT(*) FILTER (WHERE outcome IN ('opened_chat', 'converted')) AS engaged,
                        COUNT(*) AS fires
                    FROM trigger_events
                    WHERE trigger_id = :tid
                      AND fired_at > NOW() - INTERVAL '7 days'
                """),
                {"tid": trigger_id}
            )
            stat_row = stats.fetchone()
            if not stat_row:
                print(f"  {trigger_id}: no data")
                continue
            engaged = stat_row[0] or 0
            fires = stat_row[1] or 0

            if fires < MIN_DATA_POINTS:
                print(f"  {trigger_id}: skipped (only {fires} fires, need {MIN_DATA_POINTS})")
                continue

            positive_rate = engaged / fires if fires > 0 else 0
            engagement_rate = engaged / fires if fires > 0 else 0
            engagement_boost = min(engagement_rate, 1.0)
            signal = (positive_rate - BASELINE_RATE) * engagement_boost
            new_weight = clamp(old_weight + LEARNING_RATE * signal, MIN_WEIGHT, MAX_WEIGHT)

            if fires >= MIN_FIRES_FOR_LEARNING:
                await session.execute(
                    text("""
                        UPDATE trigger_weights
                        SET weight = :nw,
                            positive_rate = :pr,
                            updated_at = NOW()
                        WHERE trigger_id = :tid
                    """),
                    {"nw": round(new_weight, 3), "pr": round(positive_rate, 4), "tid": trigger_id}
                )
                print(f"  {trigger_id}: fires={fires}, pos_rate={positive_rate:.3f}, "
                      f"old={old_weight:.3f} → new={new_weight:.3f}")
            else:
                print(f"  {trigger_id}: skipped (only {fires} fires, need {MIN_FIRES_FOR_LEARNING} to learn)")

        await session.commit()

    await engine.dispose()
    print("Weight recalculation complete.")


if __name__ == "__main__":
    asyncio.run(main())
