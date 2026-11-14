"""FeedAdapter: where match data comes from. A real deployment plugs a licensed live provider
(Opta/Stats Perform, Sportradar) into the same interface."""
import json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_EVENTS = {"goal", "red_card", "sub", "half_time", "full_time"}


class FeedAdapter:
    name = "base"
    def list_matches(self) -> list[dict]: raise NotImplementedError
    def get_match(self, match_id: str) -> dict: raise NotImplementedError
    def events(self, match_id: str):
        """Yields events in order. Live providers would push; replay just iterates."""
        yield from self.get_match(match_id)["events"]


class JsonReplayAdapter(FeedAdapter):
    name = "replay"
    dir = ROOT / "data" / "matches"

    def list_matches(self):
        out = []
        for p in sorted(self.dir.glob("*.json")):
            m = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": m["id"], "label": f"{m['home']['name']} {m['score']['home']}-{m['score']['away']} {m['away']['name']}"})
        return out

    def get_match(self, match_id):
        return json.loads((self.dir / f"{match_id}.json").read_text(encoding="utf-8"))


class StatsBombAdapter(FeedAdapter):
    """StatsBomb Open Data (github.com/statsbomb/open-data). Text only, no crests/photos. Data: StatsBomb."""
    name = "statsbomb"
    BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data/"
    COMP, SEASON = 43, 106  # FIFA World Cup 2022
    cache = ROOT / "data" / "statsbomb"

    def _get(self, path):
        self.cache.mkdir(exist_ok=True)
        f = self.cache / path.replace("/", "_")
        if not f.exists():
            f.write_bytes(urllib.request.urlopen(self.BASE + path, timeout=30).read())
        return json.loads(f.read_text(encoding="utf-8"))

    def _catalog(self):
        return {str(m["match_id"]): m for m in self._get(f"matches/{self.COMP}/{self.SEASON}.json")}

    def list_matches(self):
        ms = sorted(self._catalog().values(), key=lambda m: m["match_date"], reverse=True)[:12]
        return [{"id": str(m["match_id"]), "label": f"{m['home_team']['home_team_name']} {m['home_score']}-{m['away_score']} "
                 f"{m['away_team']['away_team_name']} (WC 2022)"} for m in ms]

    def get_match(self, match_id):
        meta = self._catalog()[str(match_id)]
        ev = self._get(f"events/{match_id}.json")
        lineups = self._get(f"lineups/{match_id}.json")
        nick = {p["player_name"]: (p.get("player_nickname") or p["player_name"]) for t in lineups for p in t["lineup"]}
        n = lambda full: nick.get(full, full)
        home, away = meta["home_team"]["home_team_name"], meta["away_team"]["away_team_name"]
        side = lambda e: "home" if e["team"]["name"] == home else "away"
        teams = {"home": {"name": home, "short": home[:3].upper(), "colors": ["#1f2a44", "#c9a227"],
                          "coach": n((meta["home_team"].get("managers") or [{"name": "Head coach"}])[0]["name"]), "lineup": [], "bench": []},
                 "away": {"name": away, "short": away[:3].upper(), "colors": ["#3a1f44", "#7fd1b9"],
                          "coach": n((meta["away_team"].get("managers") or [{"name": "Head coach"}])[0]["name"]), "lineup": [], "bench": []}}
        for t in lineups:
            s = "home" if t["team_name"] == home else "away"
            teams[s]["lineup"] = [n(p["player_name"]) for p in t["lineup"]]
        out, hs, as_, last = [], 0, 0, 90
        stats = {"shots": [0, 0], "shots_on_target": [0, 0], "fouls": [0, 0], "passes": [0, 0]}
        for e in ev:
            t, per = e["type"]["name"], e.get("period", 1)
            if per > 4: break  # skip penalty shoot-out
            last = max(last, e["minute"])
            i = 0 if e.get("team", {}).get("name") == home else 1
            if t == "Pass": stats["passes"][i] += 1
            if t == "Foul Committed": stats["fouls"][i] += 1
            if t == "Shot":
                stats["shots"][i] += 1
                oc = e["shot"]["outcome"]["name"]
                if oc in ("Goal", "Saved", "Saved To Post"): stats["shots_on_target"][i] += 1
                if oc == "Goal":
                    if i == 0: hs += 1
                    else: as_ += 1
                    out.append({"minute": e["minute"], "type": "goal", "team": side(e), "player": n(e["player"]["name"]),
                                "assist": None, "detail": e["shot"].get("type", {}).get("name", "").lower() or "finish",
                                "score_after": f"{hs}-{as_}"})
            if t == "Own Goal For":
                if i == 0: hs += 1
                else: as_ += 1
                out.append({"minute": e["minute"], "type": "goal", "team": side(e), "player": "own goal", "assist": None,
                            "detail": "own goal", "score_after": f"{hs}-{as_}"})
            card = (e.get("foul_committed") or e.get("bad_behaviour") or {}).get("card", {}).get("name")
            if card in ("Red Card", "Second Yellow"):
                out.append({"minute": e["minute"], "type": "red_card", "team": side(e), "player": n(e["player"]["name"])})
            if t == "Substitution":
                pin = n(e["substitution"]["replacement"]["name"])
                teams[side(e)]["bench"].append(pin)
                out.append({"minute": e["minute"], "type": "sub", "team": side(e), "player_in": pin, "player_out": n(e["player"]["name"])})
            if t == "Half End" and per == 1 and not any(x["type"] == "half_time" for x in out):
                out.append({"minute": e["minute"], "type": "half_time", "score": f"{hs}-{as_}"})
        # penalty shoot-out (period 5): kept as its own result, not added to the match score
        pens = [0, 0]
        for e in ev:
            if e.get("period") == 5 and e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
                pens[0 if e["team"]["name"] == home else 1] += 1
        ft = {"minute": last, "type": "full_time", "score": f"{hs}-{as_}"}
        if any(pens):
            ft["penalties"] = f"{pens[0]}-{pens[1]}"
            ft["winner"] = home if pens[0] > pens[1] else away
            ft["detail"] = f"after extra time; {ft['winner']} won {max(pens)}-{min(pens)} on penalties"
        out.append(ft)
        tot = sum(stats["passes"]) or 1
        stats["possession"] = [round(100 * stats["passes"][0] / tot), 100 - round(100 * stats["passes"][0] / tot)]
        stats.pop("passes")
        return {"id": str(match_id), "competition": "FIFA World Cup 2022 (StatsBomb Open Data)", "matchday": 0,
                "date": meta["match_date"], "venue": (meta.get("stadium") or {}).get("name", ""),
                "home": teams["home"], "away": teams["away"], "score": {"home": hs, "away": as_}, "events": out,
                "stats": stats, "quotes": [], **({"penalties": {"score": ft["penalties"], "winner": ft["winner"]}} if any(pens) else {}), "cta": {"text": "Watch the full highlights", "url": "https://example.com/highlights"},
                "credit": "Data: StatsBomb Open Data"}


ADAPTERS = {"replay": JsonReplayAdapter(), "statsbomb": StatsBombAdapter()}
