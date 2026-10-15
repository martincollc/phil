"""Market discovery — AGENT-EDITABLE.

This is my sensing layer. `core/scan.py` calls `queries()` and then applies the
protected admissibility filters (banned classes, resolution floor, price
bounds) to whatever comes back. I decide WHAT TO LOOK FOR; core decides what is
allowed. A query I write cannot let a banned market through, so I can explore
freely.

Why this file exists (operator, 2026-08-03): for two days I produced zero bets
and correctly logged "no qualifying candidate" every cycle. The cause was not
the market — it was that scan paged in endDate order through a near-term
universe thousands of sub-daily markets deep and never escaped day 0. My
candidate pool was an artifact of a tool I could not edit and could not see
into. Now I can. Use it: if the pool looks structurally wrong, change the
queries and say so in the retro.

Contract: return a list of dicts of gamma `/markets` query params. Optional
`_label` names the query in scan's stderr. Anything raising here falls back to
core's default query (loudly), so a bug degrades sensing but never blinds me.
Gamma params that work: closed, order (endDate|volume24hr|liquidity),
ascending, end_date_min, end_date_max, volume_num_min, liquidity_num_min,
tag_id, related_tags.
"""


def queries(now, min_end, horizon, args, protected):
    iso = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    base = {"closed": "false", "end_date_min": iso(min_end),
            "end_date_max": iso(horizon)}

    return [
        # 1. Well-covered events out to the horizon. The lifetime-volume floor
        #    is what lets pagination escape today; do NOT add a 24h-volume
        #    floor here — an event five days out legitimately has little volume
        #    today, which re-creates the blindness this file was made to fix.
        {**base, "_label": "liquid-multiday", "order": "endDate",
         "ascending": "true", "volume_num_min": 50000},

        # 2. Deep books regardless of date order — surfaces the biggest events
        #    in the window (ATP/WTA main draws, major-league fixtures) even if
        #    thousands of small markets resolve sooner. Venue us (2026-10-14
        #    scan stderr) drops liquidity_num_min; volume_num_min is the US
        #    gateway's nearest supported floor.
        {**base, "_label": "by-liquidity", "order": "liquidity",
         "ascending": "false", "volume_num_min": 20000},

        # 3. Today's active markets, kept from the old behaviour so nothing
        #    imminent is lost: heavy recent trading, near-term resolution.
        {"closed": "false", "_label": "active-today", "order": "volume24hr",
         "ascending": "false", "end_date_min": iso(min_end),
         "end_date_max": iso(min(horizon, now.replace(microsecond=0) +
                                 __import__("datetime").timedelta(hours=36)))},

        # 4. Category-targeted, asymmetric floor (operator-notes.md 2026-08-05:
        #    a $20k econ market with a free official benchmark is worth more
        #    research time than a $400k tennis match with no reachable status
        #    source — queries 1-3 are volume/liquidity-first and bury these).
        #    tag_id 100328 = Polymarket's "Economy" tag; verified live
        #    2026-08-05 it surfaces Fed-rate-decision markets ($300k-590k
        #    volume24hr, FOMC tag 100478 is a subset) and GDP brackets
        #    ($700-2800 volume24hr, would never clear query 1's 50k floor).
        #    These resolve off an official print/vote, not a narrative read —
        #    the fact-finality profile the settled evidence favors. No volume
        #    floor here on purpose; thin but mechanically-resolving is the
        #    point. (climate-weather tag 1474 checked same day: 0 live
        #    markets currently, so not included — revisit if that changes.)
        {**base, "_label": "econ-tag", "tag_id": 100328, "order": "volume24hr",
         "ascending": "false"},

        # 5. Venue us, GAME markets (operator, port step 3, 2026-10-15).
        #    A full paged count of the US gateway on the operator Mac
        #    (2026-10-15, 20,000 sports markets) showed `categories=sports`
        #    alone returns season FUTURES first (NFL 3,615, NHL 752, EPL 435
        #    ...) and the gateway ignored orderBy/endDateMin on that query, so
        #    scan's 400-row page budget never reached a single game. The
        #    lever that works is `sportsMarketTypes`. One query per type, so
        #    a type name the gateway rejects fails only its own query (scan
        #    logs it and moves on). Winners only: spreads, totals, halves and
        #    exact scores are line-constructed and the screener's HARD RULE
        #    pins them to divergence 0 (screener-filters.json
        #    line_constructed). Types seen live 2026-10-15 are marked; the
        #    unmarked ones are the same naming pattern for sports whose
        #    games were not listed that day - read scan stderr and drop any
        #    that error.
        *[{**base, "_label": f"us-games-{t}", "categories": ["sports"],
           "sportsMarketTypes": [t]}
          for t in (
              "football_team_full_game_winner",    # seen: NFL 14, CFB 112
              "basketball_team_full_game_winner",  # seen: NBA 17, VTB 1
              "soccer_team_full_time_winner",      # seen: UEL, UECL, La Liga
              "ufc_fight_winner",                  # seen: 10
              "moneyline",                         # seen: boxing 1
              "baseball_team_full_game_winner",    # pattern guess (MLB)
              "hockey_team_full_game_winner",      # pattern guess (NHL)
          )],
    ]
