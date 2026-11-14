"""Generates 10 fictional matches into data/matches/*.json (deterministic, seed-based).
All clubs, players, venues and quotes are invented."""
import json, random
from pathlib import Path

CLUBS = {
    "Nile City FC": dict(short="NCF", colors=["#0b3d91", "#f5c518"], venue="Pharos Arena", coach="Samir Haddad",
        players=["Omar Fathy", "Karim Nassar", "Youssef Adel", "Mido Rashed", "Tarek Selim", "Hany Gamal", "Ali Mansour",
                 "Ziad Hosny", "Mostafa Kamel", "Ramy Saber", "Ehab Lotfy", "Sherif Badr", "Adham Zaki", "Nour Eldin"]),
    "Delta Rovers": dict(short="DRV", colors=["#0f7a3d", "#ffffff"], venue="Delta Park", coach="Lena Varga",
        players=["Marco Bellini", "Jonas Petrov", "Ade Okafor", "Luis Ferreira", "Tom Hadley", "Ivan Kovac", "Sami Laine",
                 "Diego Ramos", "Paul Mercer", "Kofi Mensah", "Erik Dahl", "Hugo Laurent", "Ben Ashby", "Rui Costa Neto"]),
    "Harbor Town United": dict(short="HTU", colors=["#b5121b", "#1c1c1c"], venue="Lighthouse Ground", coach="Mark Ellery",
        players=["Jack Rowan", "Callum Pike", "Ethan Moss", "Leo Grant", "Ryan Vale", "Owen Sharp", "Kai Brooks",
                 "Noah Field", "Finn Archer", "Liam Stone", "Max Hollis", "Dan Price", "Sam Kerrigan", "Ollie Ward"]),
    "Sahara Falcons": dict(short="SAF", colors=["#d97706", "#3b2a14"], venue="Dune Stadium", coach="Rachid Bennani",
        players=["Amine Tahiri", "Bilal Saidi", "Hamza Idrissi", "Yassine Amrani", "Anas Belhaj", "Reda Ouali", "Ilyas Zerouali",
                 "Mehdi Kaddour", "Soufiane Naji", "Walid Chraibi", "Adil Fassi", "Nabil Ghazi", "Driss Alaoui", "Taha Mernissi"]),
    "Alpine Wanderers": dict(short="ALW", colors=["#1e88e5", "#e3f2fd"], venue="Glacier Park", coach="Anna Keller",
        players=["Felix Huber", "Lukas Brandt", "Jan Moser", "Nico Weber", "Simon Graf", "Tim Baumann", "Elias Frei",
                 "David Steiner", "Fabian Roth", "Moritz Kern", "Leon Vogt", "Matteo Rossi", "Jonas Egli", "Pascal Imhof"]),
    "Coral Bay Athletic": dict(short="CBA", colors=["#ec407a", "#00897b"], venue="Reef Stadium", coach="Carlos Mendes",
        players=["Rafael Souza", "Bruno Lima", "Caio Alves", "Thiago Prado", "Igor Santos", "Vitor Reis", "Leandro Melo",
                 "Danilo Rocha", "Gabriel Nunes", "Mateus Pinto", "Andre Viana", "Hugo Faria", "Pedro Matos", "Joao Brito"]),
    "Riverside Phoenix": dict(short="RVP", colors=["#6a1b9a", "#ffb300"], venue="Ember Field", coach="Grace Okoye",
        players=["Chidi Eze", "Tunde Bello", "Emeka Obi", "Femi Adeyemi", "Kwame Asante", "Yaw Boateng", "Seun Lawal",
                 "Ibrahim Sow", "Moussa Diallo", "Cheikh Ndiaye", "Joel Mbeki", "Ade Bakare", "Victor Osei", "Samuel Kalu"]),
    "Granite Hill FC": dict(short="GHF", colors=["#455a64", "#cfd8dc"], venue="Quarry Road", coach="Ian Doyle",
        players=["Sean Murphy", "Conor Walsh", "Aidan Byrne", "Ciaran Kelly", "Darragh Ryan", "Eoin Burke", "Niall Quinn Jr",
                 "Rory Hayes", "Shane Daly", "Kevin Lynch", "Brian Nolan", "Fionn Carey", "Liam Devlin", "Paddy Moran"]),
}

FIXTURES = [("Nile City FC", "Delta Rovers"), ("Harbor Town United", "Sahara Falcons"), ("Alpine Wanderers", "Coral Bay Athletic"),
            ("Riverside Phoenix", "Granite Hill FC"), ("Delta Rovers", "Harbor Town United"), ("Sahara Falcons", "Nile City FC"),
            ("Coral Bay Athletic", "Riverside Phoenix"), ("Granite Hill FC", "Alpine Wanderers"), ("Nile City FC", "Coral Bay Athletic"),
            ("Riverside Phoenix", "Delta Rovers")]

QUOTES_WIN = ["The boys gave everything tonight. This one is for the fans.", "We stayed patient and it paid off in the end.",
              "Proud of the reaction after the break. Big three points."]
QUOTES_LOSS = ["We have to look at ourselves. Not good enough today.", "We created chances but did not take them. We go again."]
QUOTES_DRAW = ["A fair result. Both teams wanted it.", "We will take the point and move on."]


def team_block(name, rng):
    c = CLUBS[name]
    return {"name": name, "short": c["short"], "colors": c["colors"], "coach": c["coach"],
            "lineup": c["players"][:11], "bench": c["players"][11:]}


def make(i, home, away):
    rng = random.Random(100 + i)
    h, a = team_block(home, rng), team_block(away, rng)
    hg, ag = rng.choice([0, 1, 1, 2, 2, 3, 4]), rng.choice([0, 0, 1, 1, 2, 3])
    events, used = [], set()

    def minute():
        while True:
            m = rng.randint(3, 89)
            if m not in used and m != 45:
                used.add(m); return m

    on_pitch = {"home": list(h["lineup"][1:]), "away": list(a["lineup"][1:])}
    for side, n in (("home", hg), ("away", ag)):
        for _ in range(n):
            scorer = rng.choice(on_pitch[side][5:])
            assist = rng.choice([p for p in on_pitch[side][2:] if p != scorer])
            events.append({"minute": minute(), "type": "goal", "team": side, "player": scorer,
                           "assist": assist if rng.random() < 0.7 else None,
                           "detail": rng.choice(["header", "left-foot finish", "right-foot finish", "penalty", "free kick", "tap-in"])})
    for _ in range(rng.randint(1, 3)):
        side = rng.choice(["home", "away"])
        events.append({"minute": minute(), "type": "yellow_card", "team": side, "player": rng.choice(on_pitch[side])})
    if rng.random() < 0.4:
        side = rng.choice(["home", "away"])
        events.append({"minute": minute(), "type": "red_card", "team": side, "player": rng.choice(on_pitch[side][:5])})
    for side, blk in (("home", h), ("away", a)):
        for k in range(2):
            m = rng.randint(55, 85)
            while m in used: m += 1
            used.add(m)
            events.append({"minute": m, "type": "sub", "team": side, "player_in": blk["bench"][k], "player_out": blk["lineup"][10 - k]})
    events.append({"minute": 45, "type": "half_time"})
    events.append({"minute": 90, "type": "full_time"})
    order = {"half_time": 0.5, "full_time": 99}
    events.sort(key=lambda e: (e["minute"], order.get(e["type"], 0)))
    # half-time and full-time carry the running score
    hs = as_ = 0
    for e in events:
        if e["type"] == "goal":
            if e["team"] == "home": hs += 1
            else: as_ += 1
            e["score_after"] = f"{hs}-{as_}"
        if e["type"] in ("half_time", "full_time"):
            e["score"] = f"{hs}-{as_}"
    poss = rng.randint(38, 64)
    shots_h, shots_a = rng.randint(max(hg, 5), 19), rng.randint(max(ag, 3), 15)
    stats = {"possession": [poss, 100 - poss], "shots": [shots_h, shots_a],
             "shots_on_target": [min(shots_h, hg + rng.randint(1, 5)), min(shots_a, ag + rng.randint(0, 4))],
             "corners": [rng.randint(1, 10), rng.randint(0, 8)], "fouls": [rng.randint(6, 16), rng.randint(6, 16)]}
    res = "win" if hg > ag else "loss" if hg < ag else "draw"
    pool = {"win": QUOTES_WIN, "loss": QUOTES_LOSS, "draw": QUOTES_DRAW}[res]
    return {"id": f"m{i + 1:02d}", "competition": "Continental Premier League (fictional)", "matchday": 10 + i,
            "date": f"2026-10-{(i * 3) % 28 + 1:02d}", "venue": CLUBS[home]["venue"],
            "home": h, "away": a, "score": {"home": hg, "away": ag}, "events": events, "stats": stats,
            "quotes": [{"speaker": h["coach"], "role": f"{home} head coach", "text": rng.choice(pool)}],
            "cta": {"text": "Get tickets for the next home game", "url": f"https://example.com/{h['short'].lower()}/tickets"}}


if __name__ == "__main__":
    out = Path(__file__).parent / "matches"
    out.mkdir(exist_ok=True)
    for i, (hm, aw) in enumerate(FIXTURES):
        m = make(i, hm, aw)
        (out / f"{m['id']}.json").write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")
        print(m["id"], hm, m["score"]["home"], "-", m["score"]["away"], aw)
