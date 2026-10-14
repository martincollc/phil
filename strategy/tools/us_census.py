"""Census of the Polymarket US gateway: which category / sportsMarketType
values and slug prefixes the live market list actually carries, so discovery
queries target real values instead of guesses (2026-10-14: us-sports with
categories=['sports'] returned only minor tennis/table tennis 3 scans running).

Usage: python3 strategy/tools/us_census.py [extra key=value gateway params...]
"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "core"))
import venue_us  # noqa: E402


def main(argv):
    params = {"closed": False, "limit": 200, "orderBy": "volume24hr",
              "orderDirection": "desc"}
    for a in argv:
        k, _, val = a.partition("=")
        params[k] = val
    body = venue_us.get_json("/v1/markets", params)
    rows = body.get("markets", []) if isinstance(body, dict) else (body or [])
    print(f"rows {len(rows)}")
    if not rows:
        return
    print("keys", sorted(rows[0].keys()))
    for key in ("category", "categories", "sportsMarketType", "marketType", "tags"):
        c = collections.Counter(str(r.get(key)) for r in rows)
        print(key, c.most_common(15))
    c = collections.Counter(r.get("slug", "").split("-")[0] + "-" +
                            r.get("slug", "").split("-")[1] if "-" in r.get("slug", "") else r.get("slug", "")
                            for r in rows)
    print("slug prefix", c.most_common(25))


if __name__ == "__main__":
    main(sys.argv[1:])
