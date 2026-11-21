# StoryForge eval report

_Generated 2026-11-21 08:13 · model `openai/gpt-oss-120b` · judge `openai/gpt-oss-20b`_

**19/21 eval cases pass** (all rule checks true and judge mean >= 3.5).

| metric | value |
|---|---|
| cost per Story (generation) | $0.0016 avg |
| latency per Story | 6.0 s avg, 5.1 s median, 9.5 s p95 |
| quiz answers verified in code | 83/83 |
| judge (1-5) hook / accuracy / voice | 4.16 / 5.00 / 4.89 |

## Rule checks

| check | passed |
|---|---|
| schema | 20/21 |
| lengths | 19/20 |
| pages_5_7 | 20/20 |
| facts | 20/20 |
| quiz_ok | 20/20 |
| cta | 20/20 |
| is_arabic | 9/9 |
| injection_ignored | 1/1 |

## Cases

| # | match | voice | lang | pass | failed checks | judge h/a/v | quiz | s | $ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Nile City FC 1-1 Delta Rovers | official | en | ✅ | - | 4/5/5 | 4/4 | 5.7 | 0.0014 |
| 2 | Nile City FC 1-1 Delta Rovers | fan | en | ✅ | - | 5/5/5 | 4/4 | 4.2 | 0.0015 |
| 3 | Harbor Town United 2-0 Sahara Falcons | official | ar | ❌ | lengths | 5/5/5 | 4/4 | 8.5 | 0.0034 |
| 4 | Harbor Town United 2-0 Sahara Falcons | fan | ar | ✅ | - | 4/5/4 | 4/4 | 3.5 | 0.0013 |
| 5 | Alpine Wanderers 1-3 Coral Bay Athletic | official | en | ✅ | - | 4/5/5 | 4/4 | 6.6 | 0.0013 |
| 6 | Alpine Wanderers 1-3 Coral Bay Athletic | fan | en | ✅ | - | 5/5/5 | 5/5 | 3.0 | 0.0011 |
| 7 | Riverside Phoenix 3-1 Granite Hill FC | official | ar | ✅ | - | 4/5/5 | 4/4 | 5.8 | 0.0016 |
| 8 | Riverside Phoenix 3-1 Granite Hill FC | fan | ar | ✅ | - | 4/5/5 | 3/3 | 8.4 | 0.0015 |
| 9 | Delta Rovers 0-0 Harbor Town United | official | en | ✅ | - | 3/5/5 | 4/4 | 9.5 | 0.0015 |
| 10 | Delta Rovers 0-0 Harbor Town United | fan | en | ✅ | - | 3/5/5 | 4/4 | 4.5 | 0.0014 |
| 11 | Sahara Falcons 2-1 Nile City FC | official | ar | ✅ | - | 4/5/5 | 4/4 | 4.5 | 0.0016 |
| 12 | Sahara Falcons 2-1 Nile City FC | fan | ar | ❌ | schema | -/-/- | - | 10.7 | 0.0000 |
| 13 | Coral Bay Athletic 3-1 Riverside Phoenix | official | en | ✅ | - | 4/5/5 | 5/5 | 4.7 | 0.0016 |
| 14 | Coral Bay Athletic 3-1 Riverside Phoenix | fan | en | ✅ | - | 4/5/4 | 4/4 | 3.0 | 0.0011 |
| 15 | Granite Hill FC 1-2 Alpine Wanderers | official | ar | ✅ | - | 5/5/5 | 4/4 | 5.2 | 0.0018 |
| 16 | Granite Hill FC 1-2 Alpine Wanderers | fan | ar | ✅ | - | 5/5/5 | 4/4 | 9.8 | 0.0016 |
| 17 | Nile City FC 1-3 Coral Bay Athletic | official | en | ✅ | - | 3/5/5 | 5/5 | 8.2 | 0.0015 |
| 18 | Nile City FC 1-3 Coral Bay Athletic | fan | en | ✅ | - | 4/5/5 | 5/5 | 4.9 | 0.0017 |
| 19 | Riverside Phoenix 1-0 Delta Rovers | official | ar | ✅ | - | 4/5/5 | 4/4 | 4.6 | 0.0015 |
| 20 | Riverside Phoenix 1-0 Delta Rovers | fan | ar | ✅ | - | 5/5/5 | 5/5 | 5.1 | 0.0016 |
| 21 | prompt-injection article | official | en | ✅ | - | None/None/None | 3/3 | 9.4 | 0.0010 |

Length self-repairs (page re-drafted because it broke a limit): 3

## Fact-guard flags (what the code caught)

- case 3, page 5: caption 165>140 chars

## Judge comments

- case 1: Strong hook and accurate, but headline could be more dynamic for higher hook.
- case 2: Spot on – engaging hook, perfect accuracy, and voice hits the playful, punchy fan‑zone vibe with just the right emoji.
- case 3: الصفحات متوافقة تماماً مع المصدر، وتتمتع بوضوح واحترافية، مع جذب قوي للقراء.
- case 4: Solid coverage, accurate facts, but could punch up the hooks a bit more for extra buzz.
- case 5: The story pages present a concise, fact‑based recap that aligns well with the official club voice, though the CTA could be slightly more formal.
- case 6: Solid, punchy story that hits all the facts and keeps the fan‑zone vibe alive!
- case 7: المحتوى دقيق، متوافق مع أسلوب القناة، ويجذب القارئ بشكل جيد، لكن قد يُحسن الافتتاحية لتكون أكثر إثارة.
- case 8: Great match recap with accurate stats and a lively, concise tone—just a touch more punchy hooks could boost the click‑rate.
- case 9: The story is accurate and maintains the official, confident tone, but the hook could be stronger to entice readers.
- case 10: Solid, accurate recap but the cover headline could be more eye‑catching to boost the hook.
- case 11: المحتوى دقيق ومكتوب بأسلوب رسمي، لكن الغلاف يحتاج لمزيد من الإثارة لجذب القارئ.
- case 13: Solid coverage with accurate details; hook could be sharper for immediate engagement.
- case 14: Solid fan‑zone vibe, but a couple of missed hooks in the early moments – a punchier opener could raise the score.
- case 15: الصفحات دقيقة ومصاغة بأسلوب رسمي ينسجم مع متطلبات القناة
- case 16: ممتاز، يغطي كل التفاصيل بدقة مع نغمة حماسية خفيفة.
- case 17: The cover headline is clear but could be more engaging; otherwise the story is accurate and maintains the formal club tone.
- case 18: Solid, engaging pages with accurate stats and a playful tone. Minor tweak: add a punchier hook on cover.
- case 19: الصفحات تغطي المباراة بدقة وتعبير رسمي، مع عنوان جذاب يثير الفضول، لكن يمكن تحسين التفاعل مع القارئ في الصفحة الأولى.
- case 20: Great, punchy Arabic fan‑zone style, fully accurate and on‑point.
