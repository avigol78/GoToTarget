"""
Entry point for the ERAN call-centre monitor.

Commands
--------
login    – open a browser, let the user log in and save the session
collect  – start periodic data collection (runs until Ctrl+C)
report   – print a weekly summary and save a chart
export   – dump all rows to CSV

Examples
--------
    python -m monitor.main login
    python -m monitor.main collect
    python -m monitor.main report
    python -m monitor.main report --days 3 --chart my_chart.png
    python -m monitor.main export --out data.csv
"""
import argparse
import csv
import logging
import sys

from monitor.config import DB_PATH
from monitor.storage import get_conn, fetch_recent_days, fetch_all


def cmd_login(_args) -> None:
    from monitor.auth import login_interactive
    login_interactive()


def cmd_collect(args) -> None:
    from monitor.collector import run_collector
    run_collector(args.db)


def cmd_report(args) -> None:
    from monitor.reporter import generate_report
    conn = get_conn(args.db)
    rows = fetch_recent_days(conn, days=args.days)
    if not rows:
        print(f"[!] אין נתונים ב-{args.days} הימים האחרונים.")
        sys.exit(0)
    generate_report(rows, output_chart=args.chart)


def cmd_export(args) -> None:
    conn = get_conn(args.db)
    rows = fetch_all(conn)
    if not rows:
        print("[!] אין נתונים לייצוא.")
        sys.exit(0)
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"[✓] יוצאו {len(rows)} שורות ל: {args.out}")


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description='ניטור מרכז השיחות של ער"ן',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db", default=DB_PATH, help="נתיב לקובץ SQLite (ברירת מחדל: %(default)s)")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="כניסה ראשונית לאתר (שמירת סשן)")

    collect_p = sub.add_parser("collect", help="התחל ניטור רציף")
    collect_p.set_defaults(func=cmd_collect)

    report_p = sub.add_parser("report", help="הפק דוח שבועי")
    report_p.add_argument("--days", type=int, default=7, help="מספר ימים לדוח (ברירת מחדל: 7)")
    report_p.add_argument("--chart", default="eran_report.png", help="שם קובץ הגרף")
    report_p.set_defaults(func=cmd_report)

    export_p = sub.add_parser("export", help="ייצוא נתונים ל-CSV")
    export_p.add_argument("--out", default="eran_data.csv", help="שם קובץ הפלט")
    export_p.set_defaults(func=cmd_export)

    # Attach default funcs
    for name, func in [("login", cmd_login), ("collect", cmd_collect)]:
        sub.choices[name].set_defaults(func=func)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
