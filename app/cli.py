"""CLI: python -m app.cli data/matches/m01.json --voice fan --lang ar"""
import argparse, json
from pathlib import Path

from . import llm, factcheck


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="match .json or article .txt")
    ap.add_argument("--voice", default="official", choices=list(llm.VOICES))
    ap.add_argument("--lang", default="en", choices=list(llm.LANGS))
    a = ap.parse_args()
    p = Path(a.source)
    if p.suffix == ".json":
        match = json.loads(p.read_text(encoding="utf-8")); article = None; facts = factcheck.facts_from_match(match)
    else:
        match = None; article = p.read_text(encoding="utf-8"); facts = factcheck.facts_from_article(article)
    story, log = llm.generate_story(match, article, a.voice, a.lang, ref=p.stem)
    rep = factcheck.check_story(story, facts, a.lang)
    print(json.dumps(story, indent=2, ensure_ascii=False))
    print("\nFACT GUARD:", "OK" if rep["ok"] else "FLAGS", json.dumps({k: v for k, v in rep.items() if v}, ensure_ascii=False))
    print(f"COST ${log['usd']:.5f} | {log['tokens_in']} in / {log['tokens_out']} out | {log['ms']} ms | retries {log['retries']}")


if __name__ == "__main__":
    main()
