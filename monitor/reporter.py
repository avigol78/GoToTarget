"""
Weekly analysis report.

Produces:
  1. A text summary printed to stdout
  2. A PNG chart saved to disk (requires matplotlib)

Key question: when are there staffing shortages vs. surpluses?

We define:
  demand   = calls + waiting          (how many callers need attention right now)
  supply   = connected - on_break     (volunteers actually available)
  gap      = supply - demand          (positive = surplus, negative = shortage)
"""
import datetime
import statistics
from collections import defaultdict

DAYS_HE = ["שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת", "ראשון"]


def _gap(row: dict) -> float | None:
    calls     = row.get("calls")     or 0
    waiting   = row.get("waiting")   or 0
    connected = row.get("connected") or 0
    on_break  = row.get("on_break")  or 0
    demand = calls + waiting
    supply = connected - on_break
    return supply - demand


def generate_report(rows: list, output_chart: str = "eran_report.png") -> None:
    if not rows:
        print("אין נתונים לדוח.")
        return

    print("\n" + "=" * 64)
    print("  דוח ניטור מרכז השיחות – ער\"ן")
    print(f"  תקופה: {rows[0]['ts'][:16]}  עד  {rows[-1]['ts'][:16]}")
    print(f"  סה\"כ מדגמים: {len(rows)}")
    print("=" * 64)

    # ── Overall stats ────────────────────────────────────────────
    for field, label in [
        ("calls",     "שיחות פעילות (ממוצע)     "),
        ("waiting",   "פונים ממתינים (ממוצע)    "),
        ("connected", "מתנדבים מחוברים (ממוצע)  "),
        ("on_break",  "מתנדבים בהפסקה (ממוצע)   "),
    ]:
        vals = [r[field] for r in rows if r.get(field) is not None]
        if vals:
            print(f"  {label}: {statistics.mean(vals):.1f}  (מקס {max(vals)}, מין {min(vals)})")

    # ── Gap stats ────────────────────────────────────────────────
    gaps = [g for r in rows if (g := _gap(r)) is not None]
    if gaps:
        print(f"\n  פער ממוצע (היצע פחות ביקוש): {statistics.mean(gaps):+.1f}")
        print(f"  גרוע ביותר (מחסור): {min(gaps):+.1f}")
        print(f"  טוב ביותר  (עודף):  {max(gaps):+.1f}")

    # ── By day of week ───────────────────────────────────────────
    print("\n  פירוט לפי יום בשבוע:")
    by_day: dict[int, list] = defaultdict(list)
    for r in rows:
        g = _gap(r)
        if g is not None:
            by_day[r["day_of_week"]].append(g)

    for dow in range(7):
        if dow in by_day:
            vals = by_day[dow]
            avg = statistics.mean(vals)
            status = "✓ עודף" if avg > 0 else "✗ מחסור"
            print(f"    יום {DAYS_HE[dow]:6s}: פער ממוצע {avg:+.1f}  ({status})")

    # ── By hour of day ───────────────────────────────────────────
    print("\n  שעות עם המחסור הגדול ביותר (10 מובילות):")
    by_hour: dict[int, list] = defaultdict(list)
    for r in rows:
        g = _gap(r)
        if g is not None:
            by_hour[r["hour"]].append(g)

    hour_avgs = [(h, statistics.mean(v)) for h, v in by_hour.items()]
    hour_avgs.sort(key=lambda x: x[1])  # ascending = worst first
    for h, avg in hour_avgs[:10]:
        bar = "█" * max(0, int(-avg))
        print(f"    {h:02d}:00  פער {avg:+.1f}  {bar}")

    print("\n  שעות עם העודף הגדול ביותר (5 מובילות):")
    for h, avg in sorted(hour_avgs, key=lambda x: -x[1])[:5]:
        bar = "█" * max(0, int(avg))
        print(f"    {h:02d}:00  פער {avg:+.1f}  {bar}")

    print("=" * 64 + "\n")

    # ── Chart ────────────────────────────────────────────────────
    _try_plot(rows, by_hour, output_chart)


def _try_plot(rows: list, by_hour: dict, output_chart: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        timestamps = [datetime.datetime.fromisoformat(r["ts"]) for r in rows]
        gaps = [_gap(r) for r in rows]

        fig, axes = plt.subplots(2, 1, figsize=(14, 9))
        fig.suptitle('ניטור מרכז השיחות – ער"ן', fontsize=14)

        # Top: time-series of gap
        ax = axes[0]
        ax.plot(timestamps, gaps, color="steelblue", linewidth=0.8, alpha=0.7)
        ax.axhline(0, color="red", linewidth=1, linestyle="--", label="שיווי משקל")
        ax.fill_between(timestamps, gaps, 0,
                        where=[g < 0 for g in gaps],
                        alpha=0.3, color="red", label="מחסור")
        ax.fill_between(timestamps, gaps, 0,
                        where=[g >= 0 for g in gaps],
                        alpha=0.3, color="green", label="עודף")
        ax.set_ylabel("פער (היצע פחות ביקוש)")
        ax.set_title("פער לאורך הזמן")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        fig.autofmt_xdate()

        # Bottom: average gap per hour
        ax2 = axes[1]
        hours = sorted(by_hour.keys())
        avgs = [statistics.mean(by_hour[h]) for h in hours]
        colors = ["green" if a >= 0 else "red" for a in avgs]
        ax2.bar(hours, avgs, color=colors, alpha=0.7)
        ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_xlabel("שעה")
        ax2.set_ylabel("פער ממוצע")
        ax2.set_title("פער ממוצע לפי שעה")
        ax2.set_xticks(range(0, 24))

        plt.tight_layout()
        plt.savefig(output_chart, dpi=120, bbox_inches="tight")
        print(f"[✓] גרף נשמר: {output_chart}")
    except ImportError:
        print("[!] matplotlib לא מותקן – גרף לא נוצר.")
    except Exception as exc:
        print(f"[!] שגיאה ביצירת גרף: {exc}")
