"""Read-only scan for BTC date ranges in a research folder. Writes nothing.
Usage:  python scan_prior_exposure.py "C:\\path\\to\\Crypto" > scan_report.txt
"""
import sys, os, re, sqlite3, csv
from datetime import datetime, timezone

HOLD_START = datetime(2025, 10, 15, tzinfo=timezone.utc)
HOLD_END = datetime(2026, 9, 30, 23, 55, tzinfo=timezone.utc)
TS_NAMES = ("open_time", "opentime", "timestamp", "time", "date", "datetime", "ts", "open_ts", "candle_time", "dt")
TEXT_EXT = (".md", ".py", ".json", ".yaml", ".yml", ".toml", ".txt", ".ini", ".cfg", ".env.example", ".ipynb", ".log")
KEYWORDS = re.compile(r"testnet|mainnet|fapi|futures|perp|spot|defaultType|since|start_date|end_date|date_from|date_to|backtest", re.I)
DATE_RE = re.compile(r"\b(20[12]\d)[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b")

def to_dt(v):
    try:
        if isinstance(v, (int, float)):
            x = float(v)
            if 1e12 <= x < 1e14: return datetime.fromtimestamp(x / 1000, tz=timezone.utc)
            if 1e9 <= x < 1e11: return datetime.fromtimestamp(x, tz=timezone.utc)
            return None
        s = str(v).strip()
        if s.replace(".", "", 1).isdigit(): return to_dt(float(s))
        s = s.replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def verdict(lo, hi):
    if lo is None or hi is None: return "UNKNOWN"
    return "OVERLAP" if (lo <= HOLD_END and hi >= HOLD_START) else "no overlap"

def report(path, what, lo, hi):
    f = lambda d: d.strftime("%Y-%m-%d %H:%M UTC") if d else "UNKNOWN"
    print(f"[{verdict(lo, hi)}] {path} | {what} | first={f(lo)} last={f(hi)}")

def scan_csv(path):
    with open(path, newline="", encoding="utf-8", errors="ignore") as fh:
        r = csv.reader(fh); head = next(r, None)
        if not head: return
        idx = [i for i, h in enumerate(head) if h.strip().lower() in TS_NAMES]
        if not idx: idx = [0]
        lo = hi = None
        for row in r:
            if len(row) <= idx[0]: continue
            d = to_dt(row[idx[0]])
            if d: lo = d if lo is None or d < lo else lo; hi = d if hi is None or d > hi else hi
        report(path, f"csv col '{head[idx[0]]}'", lo, hi)

def scan_sqlite(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    for (t,) in con.execute("select name from sqlite_master where type='table'"):
        cols = [c[1] for c in con.execute(f'pragma table_info("{t}")')]
        for c in cols:
            if c.lower() in TS_NAMES:
                try:
                    a, b = con.execute(f'select min("{c}"), max("{c}") from "{t}"').fetchone()
                    report(path, f"table {t}.{c}", to_dt(a), to_dt(b))
                except Exception as e:
                    print(f"[UNKNOWN] {path} | table {t}.{c} | error {e}")
    con.close()

def scan_parquet(path):
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        cols = [c for c in df.columns if str(c).lower() in TS_NAMES]
        src = df[cols[0]] if cols else df.index.to_series()
        s = [to_dt(x.to_pydatetime() if hasattr(x, "to_pydatetime") else x) for x in (src.min(), src.max())]
        report(path, f"parquet '{cols[0] if cols else 'index'}'", s[0], s[1])
    except Exception as e:
        print(f"[UNKNOWN] {path} | parquet unreadable ({e})")

def scan_text(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for n, line in enumerate(fh, 1):
                if DATE_RE.search(line) or KEYWORDS.search(line):
                    print(f"  [text] {path}:{n}: {line.strip()[:160]}")
    except Exception:
        pass

def main(root):
    print(f"Scan root: {root}\nHoldout: {HOLD_START:%Y-%m-%d %H:%M} to {HOLD_END:%Y-%m-%d %H:%M} UTC\n")
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in (".git", ".venv", "venv", "__pycache__", "node_modules")]
        for name in sorted(fn):
            p = os.path.join(dp, name); low = name.lower()
            try:
                if low.endswith((".sqlite", ".db", ".sqlite3")): scan_sqlite(p)
                elif low.endswith(".csv"): scan_csv(p)
                elif low.endswith(".parquet"): scan_parquet(p)
                elif low.endswith(TEXT_EXT) and low != ".env": scan_text(p)
                elif low.endswith((".png", ".jpg", ".html", ".svg", ".pdf")):
                    print(f"  [manual] {p} | image/report: date range not machine-readable, check by hand")
            except Exception as e:
                print(f"[UNKNOWN] {p} | {e}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
