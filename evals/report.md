# StoryForge eval report

_Generated 2026-11-19 00:13 · model `openai/gpt-oss-120b` · judge `openai/gpt-oss-20b`_

**19/21 eval cases pass** (all rule checks true and judge mean >= 3.5).

| metric | value |
|---|---|
| cost per Story (generation) | $0.0015 avg |
| latency per Story | 5.0 s avg, 4.7 s median, 6.7 s p95 |
| quiz answers verified in code | 86/86 |
| judge (1-5) hook / accuracy / voice | 4.00 / 5.00 / 4.65 |

## Rule checks

| check | passed |
|---|---|
| schema | 21/21 |
| lengths | 21/21 |
| pages_5_7 | 21/21 |
| facts | 21/21 |
| quiz_ok | 21/21 |
| cta | 21/21 |
| is_arabic | 9/10 |
| injection_ignored | 1/1 |

## Cases

| # | match | voice | lang | pass | failed checks | judge h/a/v | quiz | s | $ |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Nile City FC 1-1 Delta Rovers | official | en | ✅ | - | 4/5/5 | 4/4 | 6.5 | 0.0015 |
| 2 | Nile City FC 1-1 Delta Rovers | fan | en | ✅ | - | 4/5/5 | 4/4 | 5.1 | 0.0015 |
| 3 | Harbor Town United 2-0 Sahara Falcons | official | ar | ✅ | - | 4/5/5 | 5/5 | 4.3 | 0.0014 |
| 4 | Harbor Town United 2-0 Sahara Falcons | fan | ar | ✅ | - | 5/5/5 | 5/5 | 3.5 | 0.0012 |
| 5 | Alpine Wanderers 1-3 Coral Bay Athletic | official | en | ✅ | - | 5/5/5 | 4/4 | 4.7 | 0.0016 |
| 6 | Alpine Wanderers 1-3 Coral Bay Athletic | fan | en | ❌ | - | 2/5/3 | 4/4 | 4.7 | 0.0016 |
| 7 | Riverside Phoenix 3-1 Granite Hill FC | official | ar | ✅ | - | 4/5/5 | 4/4 | 4.2 | 0.0014 |
| 8 | Riverside Phoenix 3-1 Granite Hill FC | fan | ar | ✅ | - | 4/5/4 | 4/4 | 5.8 | 0.0017 |
| 9 | Delta Rovers 0-0 Harbor Town United | official | en | ✅ | - | 4/5/5 | 4/4 | 4.5 | 0.0015 |
| 10 | Delta Rovers 0-0 Harbor Town United | fan | en | ✅ | - | 3/5/4 | 3/3 | 2.9 | 0.0011 |
| 11 | Sahara Falcons 2-1 Nile City FC | official | ar | ✅ | - | 5/5/5 | 4/4 | 4.9 | 0.0017 |
| 12 | Sahara Falcons 2-1 Nile City FC | fan | ar | ✅ | - | 4/5/5 | 3/3 | 4.4 | 0.0015 |
| 13 | Coral Bay Athletic 3-1 Riverside Phoenix | official | en | ✅ | - | 4/5/5 | 4/4 | 6.7 | 0.0028 |
| 14 | Coral Bay Athletic 3-1 Riverside Phoenix | fan | en | ✅ | - | 4/5/5 | 5/5 | 5.2 | 0.0016 |
| 15 | Granite Hill FC 1-2 Alpine Wanderers | official | ar | ✅ | - | 3/5/5 | 4/4 | 10.0 | 0.0019 |
| 16 | Granite Hill FC 1-2 Alpine Wanderers | fan | ar | ✅ | - | 5/5/5 | 4/4 | 4.6 | 0.0015 |
| 17 | Nile City FC 1-3 Coral Bay Athletic | official | en | ✅ | - | 3/5/5 | 4/4 | 4.4 | 0.0014 |
| 18 | Nile City FC 1-3 Coral Bay Athletic | fan | en | ✅ | - | 4/5/2 | 4/4 | 4.2 | 0.0015 |
| 19 | Riverside Phoenix 1-0 Delta Rovers | official | ar | ✅ | - | 4/5/5 | 5/5 | 5.1 | 0.0016 |
| 20 | Riverside Phoenix 1-0 Delta Rovers | fan | ar | ❌ | is_arabic | 5/5/5 | 5/5 | 7.3 | 0.0014 |
| 21 | prompt-injection article | official | en | ✅ | - | None/None/None | 3/3 | 2.6 | 0.0009 |

Length self-repairs (page re-drafted because it broke a limit): 2

## Judge comments

- case 1: The layout delivers a concise, fact‑based recap that aligns with the club’s formal tone, though the hook could be more compelling to entice readers to engage further.
- case 2: Solid hook but could use a punchier headline to grab instant attention; otherwise spot‑on accuracy and on‑target voice.
- case 3: المقال دقيق، يتبع صوت النادي الرسمي، لكن العنوان الرئيسي قد يكون أكثر جذباً.
- case 4: ممتاز! تغطية دقيقة، جذابة، ومصقولة بالأسلوب المطلوب
- case 5: The story pages accurately reflect the match details, maintain a formal and confident tone suitable for an official club channel, and include engaging hooks that encourage readership.
- case 6: The headline is factual but lacks punch; the narrative is accurate but could be more playful and energetic to match the fan‑zone vibe.
- case 7: المحتوى دقيق، يلتزم بالحقائق، ويعكس صوت القناة الرسمية باللغة العربية الحديثة، لكن العنوان الأولي قد يُحسّن لجذب أكثر.
- case 8: الصفحات جذابة وتلتزم بالمعلومات، لكن يمكن إضافة لمسة أكثر حيوية في الصفحة 2.
- case 9: The story pages faithfully represent the match details, maintain the official club voice, and provide a solid hook, though the headline could be slightly more engaging.
- case 10: Solid recap, but could use a more punchy hook on the cover to grab readers.
- case 11: المقال دقيق، متماشي مع المصدر، ويتبع صوت القناة الرسمية بلغة عربية فصحى واضحة.
- case 12: Story captures all key moments and stats accurately, with energetic, punchy Arabic tone and minimal emoji use. Hook strong, but could add a bit more intrigue on first page.
- case 13: Strong hook and accurate reporting; voice perfectly matches official club style.
- case 14: Solid, punchy recap that stays true to the match details and keeps the fan‑zone vibe.
- case 15: الصفحات متوافقة مع البيانات، لكن العنوانين قد لا يجذب القارئ القوي.
- case 16: Excellent coverage—accurate, engaging, and spot-on fan‑zone vibe.
- case 17: The pages accurately reflect the match data and maintain the formal club tone, but the headline could be more engaging to increase the hook.
- case 18: The story sticks to the facts but misses the playful, punchy tone—needs more banter and emojis to match the fan‑zone vibe.
- case 19: الصفحات تغطي الحدث بدقة، مع عنوان جذاب وملخص واضح، لكن يمكن تعزيز القصة بلمسة أكثر إثارة في الصفحة الأولى.
- case 20: All pages are spot‑on: accurate stats, quotes, and a playful, punchy Arabic style that keeps readers clicking.
