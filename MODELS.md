# 🤖 راهنمای جامع کاتالوگ مدل‌های هوش مصنوعی کاپری (Capri AI Models)

این سند شامل فهرست کامل تمام مدل‌های پشتیبانی‌شده در ربات کاپری به همراه **شناسه اختصاصی یکتا (UID)**، مشخصات فنی، و نحوه سوییچ فوری به هر مدل است.

---

## ⚡ نحوه انتخاب سریع مدل‌ها (Quick Commands)

شما می‌توانید به چندین روش طبیعی یا با شناسه یکتا مدل فعال ربات را فوراً عوض کنید:

### ۱. با شناسه یکتا (UID) - سریع‌ترین روش:
- `k1` یا `کاپری مدل k1` ⬅️ پرچمدار کیرو (`openai/gpt-6.1-sol`)
- `b1` یا `کاپری مدل b1` ⬅️ مدل مینی‌مکس بای (`MiniMax-M3.1-Flash`)
- `a2` یا `کاپری مدل a2` ⬅️ جمینای ۳.۶ فلش از انی (`google/gemini-3.6-flash`)
- `o3` یا `کاپری مدل o3` ⬅️ نموترون لایتنینگ از اوپن‌روتر (`nvidia/nemotron-3.5-lightning:free`)
- `g1` یا `کاپری مدل g1` ⬅️ کوئن ۲۷ میلیاردی از گروک (`qwen/qwen3.8-27b`)
- `h1` یا `کاپری مدل h1` ⬅️ مدل بومی هوشیا (`GLM-4.5-Flash`)
- `i1` یا `کاپری مدل i1` ⬅️ مرکوری ۳ از اینسپشن (`mercury-3`)

### ۲. با نام سرویس دهنده (پرچمدار پیش‌فرض سرویس فعال می‌شود):
- `کاپری مدل کیرو` ⬅️ سوییچ به پرچمدار رسمی XKIRO (`openai/gpt-6.1-sol`)
- `کاپری مدل بای` ⬅️ سوییچ به پرچمدار رسمی B.AI (`GPT-6.1 Sol`)
- `کاپری مدل انی` ⬅️ سوییچ به پرچمدار رسمی AnyAPI (`google/gemini-3.6-flash`)
- `کاپری مدل اوپن روتر` ⬅️ سوییچ به پرچمدار سریع OpenRouter (`nvidia/nemotron-3.5-lightning:free`)

### ۳. بر اساس کاربرد هوشمند:
- `کاپری مدل کدنویسی` ⬅️ انتخاب بهترین مدل برنامه‌نویسی و حل باگ
- `کاپری مدل استدلال` یا `کاپری مدل قوی` ⬅️ انتخاب قدرتمندترین مدل تحلیلی
- `کاپری مدل سریع` ⬅️ فوق‌سریع‌ترین مدل پاسخ‌دهی
- `کاپری مدل تصویر` ⬅️ مدل چندوجهی تحلیل تصاویر و اسناد
- `کاپری مدل قبلی` ⬅️ بازگشت به مدلی که قبلاً تنظیم کرده بودید
- `کاپری مدل فعلی چیه؟` ⬅️ نمایش مدل و ارائه‌دهنده در حال استفاده

---

## ۱. مدل‌های ارائه‌دهنده XKIRO (پیشوند `k`)

مجموع: **97** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`k1`** | Ministral 3 14B | `mistralai/ministral-14b` | ⚡ پرسرعت | 128K+ | `کاپری مدل k1` |
| **`k2`** | Gemini 3.6 Flash | `google/gemini-3.6-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k2` |
| **`k3`** | GPT-6.1 Sol | `openai/gpt-6.1-sol` | 🧠 استدلال | 128K+ | `کاپری مدل k3` |
| **`k4`** | Sonnet 4.6 | `anthropic/claude-sonnet-4.6` | 💬 عمومی | 128K+ | `کاپری مدل k4` |
| **`k5`** | Fable 5 | `anthropic/claude-fable-5` | 🧠 استدلال | 128K+ | `کاپری مدل k5` |
| **`k6`** | Grok 4.5 | `x-ai/grok-4.5` | 💬 عمومی | 128K+ | `کاپری مدل k6` |
| **`k7`** | Opus 4.8 | `anthropic/claude-opus-4.8` | 🧠 استدلال | 128K+ | `کاپری مدل k7` |
| **`k8`** | Fable 5.1 | `anthropic/claude-fable-5-1` | 🧠 استدلال | 128K+ | `کاپری مدل k8` |
| **`k9`** | Grok 4.7 | `x-ai/grok-4.7` | 💬 عمومی | 128K+ | `کاپری مدل k9` |
| **`k10`** | Haiku 5.5 | `anthropic/claude-haiku-5.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل k10` |
| **`k11`** | Sonnet 5.5 | `anthropic/claude-sonnet-5.5` | 💬 عمومی | 128K+ | `کاپری مدل k11` |
| **`k12`** | Opus 5 | `anthropic/claude-opus-5` | 🧠 استدلال | 128K+ | `کاپری مدل k12` |
| **`k13`** | Haiku 4.5 | `anthropic/claude-haiku-4.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل k13` |
| **`k14`** | Opus 4.5 | `anthropic/claude-opus-4.5` | 🧠 استدلال | 128K+ | `کاپری مدل k14` |
| **`k15`** | MiniMax M3 | `minimax/minimax-m3` | ⚡ پرسرعت | 128K+ | `کاپری مدل k15` |
| **`k16`** | MiniMax M2.7 | `minimax/minimax-m2.7` | ⚡ پرسرعت | 128K+ | `کاپری مدل k16` |
| **`k17`** | MiniMax M2.7 Highspeed | `minimax/minimax-m2.7-highspeed` | ⚡ پرسرعت | 128K+ | `کاپری مدل k17` |
| **`k18`** | GPT-6 Astra | `openai/gpt-6-astra` | 🧠 استدلال | 128K+ | `کاپری مدل k18` |
| **`k19`** | GPT-6 Sol | `openai/gpt-6-sol` | 🧠 استدلال | 128K+ | `کاپری مدل k19` |
| **`k20`** | Gemini 3.8 Flash | `google/gemini-3.8-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k20` |
| **`k21`** | Kimi K2.8 Preview Agent | `moonshotai/kimi-k2.8-preview-agent` | 💬 عمومی | 128K+ | `کاپری مدل k21` |
| **`k22`** | Qwen3 VL Plus (Free) | `qwen/qwen3-vl-plus:free` | 🖼 چندوجهی | 128K+ | `کاپری مدل k22` |
| **`k23`** | Gemini 3.7 Flash | `google/gemini-3.7-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k23` |
| **`k24`** | Grok 4.6 | `x-ai/grok-4.6` | 💬 عمومی | 128K+ | `کاپری مدل k24` |
| **`k25`** | North Mini Code | `cohere/north-mini-code` | 💻 کدنویسی | 128K+ | `کاپری مدل k25` |
| **`k26`** | Command R (08-2024) | `cohere/command-r-08-2024` | 💬 عمومی | 128K+ | `کاپری مدل k26` |
| **`k27`** | Qwen Plus 0728 (Free) | `qwen/qwen-plus-2025-07-28:free` | 💬 عمومی | 128K+ | `کاپری مدل k27` |
| **`k28`** | SenseNova 6.8 Flash-Lite | `sensenova/sensenova-6.8-flash-lite` | ⚡ پرسرعت | 128K+ | `کاپری مدل k28` |
| **`k29`** | Command A | `cohere/command-a` | 💬 عمومی | 128K+ | `کاپری مدل k29` |
| **`k30`** | Aya Vision 32B | `cohere/aya-vision-32b` | 🖼 چندوجهی | 128K+ | `کاپری مدل k30` |
| **`k31`** | Ministral 3 3B | `mistralai/ministral-3b` | ⚡ پرسرعت | 128K+ | `کاپری مدل k31` |
| **`k32`** | Sonnet 4 | `anthropic/claude-sonnet-4` | 💬 عمومی | 128K+ | `کاپری مدل k32` |
| **`k33`** | Tiny Aya Earth | `cohere/tiny-aya-earth` | ⚡ پرسرعت | 128K+ | `کاپری مدل k33` |
| **`k34`** | Tiny Aya Global | `cohere/tiny-aya-global` | ⚡ پرسرعت | 128K+ | `کاپری مدل k34` |
| **`k35`** | Command R+ (08-2024) | `cohere/command-r-plus-08-2024` | 🧠 استدلال | 128K+ | `کاپری مدل k35` |
| **`k36`** | Aya Expanse 32B | `cohere/aya-expanse-32b` | 💬 عمومی | 128K+ | `کاپری مدل k36` |
| **`k37`** | GPT-5.6 Terra | `openai/gpt-5.6-terra` | ⚡ پرسرعت | 128K+ | `کاپری مدل k37` |
| **`k38`** | Tiny Aya Fire | `cohere/tiny-aya-fire` | ⚡ پرسرعت | 128K+ | `کاپری مدل k38` |
| **`k39`** | MiniMax M3.1 Flash | `minimax/minimax-m3.1-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k39` |
| **`k40`** | Command A+ | `cohere/command-a-plus` | 💬 عمومی | 128K+ | `کاپری مدل k40` |
| **`k41`** | Opus 4.6 | `anthropic/claude-opus-4.6` | 🧠 استدلال | 128K+ | `کاپری مدل k41` |
| **`k42`** | GPT-6 Luna | `openai/gpt-6-luna` | 🧠 استدلال | 128K+ | `کاپری مدل k42` |
| **`k43`** | Gemini 3.5 Flash | `google/gemini-3.5-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k43` |
| **`k44`** | Sonnet 4.5 | `anthropic/claude-sonnet-4.5` | 💬 عمومی | 128K+ | `کاپری مدل k44` |
| **`k45`** | Gemini 3.1 Pro | `google/gemini-3.1-pro` | 🧠 استدلال | 128K+ | `کاپری مدل k45` |
| **`k46`** | GPT-5.6 Luna | `openai/gpt-5.6-luna` | ⚡ پرسرعت | 128K+ | `کاپری مدل k46` |
| **`k47`** | Sonnet 5 | `anthropic/claude-sonnet-5` | 💬 عمومی | 128K+ | `کاپری مدل k47` |
| **`k48`** | Gemini 2.5 Flash | `google/gemini-2.5-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k48` |
| **`k49`** | Mistral Large 4 | `mistralai/mistral-large-4-0` | 💬 عمومی | 128K+ | `کاپری مدل k49` |
| **`k50`** | Kimi K3 Agent | `moonshotai/kimi-k3-agent` | 💬 عمومی | 128K+ | `کاپری مدل k50` |
| **`k51`** | Mistral Large 3 | `mistralai/mistral-large-2512` | 💬 عمومی | 128K+ | `کاپری مدل k51` |
| **`k52`** | Mistral Medium 3.5 | `mistralai/mistral-medium-3.5` | 💬 عمومی | 128K+ | `کاپری مدل k52` |
| **`k53`** | Mistral Small 4 | `mistralai/mistral-small-2603` | ⚡ پرسرعت | 128K+ | `کاپری مدل k53` |
| **`k54`** | Devstral 2 | `mistralai/devstral-medium` | 💻 کدنویسی | 128K+ | `کاپری مدل k54` |
| **`k55`** | Opus 5.5 | `anthropic/claude-opus-5.5` | 🧠 استدلال | 128K+ | `کاپری مدل k55` |
| **`k56`** | Codestral | `mistralai/codestral-2508` | 💻 کدنویسی | 128K+ | `کاپری مدل k56` |
| **`k57`** | Command A Translate | `cohere/command-a-translate` | 💬 عمومی | 128K+ | `کاپری مدل k57` |
| **`k58`** | Gemini 3 Flash | `google/gemini-3-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k58` |
| **`k59`** | MiniMax M2.5 | `minimax/minimax-m2.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل k59` |
| **`k60`** | MiniMax M2.1 | `minimax/minimax-m2.1` | ⚡ پرسرعت | 128K+ | `کاپری مدل k60` |
| **`k61`** | Qwen3 Omni Flash (Free) | `qwen/qwen3-omni-flash:free` | ⚡ پرسرعت | 128K+ | `کاپری مدل k61` |
| **`k62`** | Ministral 3 8B | `mistralai/ministral-8b` | ⚡ پرسرعت | 128K+ | `کاپری مدل k62` |
| **`k63`** | MiMo v2.6 Pro | `xiaomi/mimo-v2.6-pro` | 🧠 استدلال | 128K+ | `کاپری مدل k63` |
| **`k64`** | Gemini 2.5 Pro | `google/gemini-2.5-pro` | 🧠 استدلال | 128K+ | `کاپری مدل k64` |
| **`k65`** | MiMo v2.6 Flash | `xiaomi/mimo-v2.6-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل k65` |
| **`k66`** | Opus 4.7 | `anthropic/claude-opus-4.7` | 🧠 استدلال | 128K+ | `کاپری مدل k66` |
| **`k67`** | MiniMax M2.5 Highspeed | `minimax/minimax-m2.5-highspeed` | ⚡ پرسرعت | 128K+ | `کاپری مدل k67` |
| **`k68`** | MiniMax M2.1 Highspeed | `minimax/minimax-m2.1-highspeed` | ⚡ پرسرعت | 128K+ | `کاپری مدل k68` |
| **`k69`** | MiniMax M2 | `minimax/minimax-m2` | ⚡ پرسرعت | 128K+ | `کاپری مدل k69` |
| **`k70`** | MiMo v2.5 | `xiaomi/mimo-v2.5` | 💬 عمومی | 128K+ | `کاپری مدل k70` |
| **`k71`** | Qwen3.6 Plus (Free) | `qwen/qwen3.6-plus:free` | 💬 عمومی | 128K+ | `کاپری مدل k71` |
| **`k72`** | Qwen3.7 Max (Free) | `qwen/qwen3.7-max:free` | 💬 عمومی | 128K+ | `کاپری مدل k72` |
| **`k73`** | LongCat 2.0 | `meituan/longcat-2.0` | 💬 عمومی | 128K+ | `کاپری مدل k73` |
| **`k74`** | LongCat 2.5 Preview (Free) | `meituan/longcat-2.5-preview:free` | 💬 عمومی | 128K+ | `کاپری مدل k74` |
| **`k75`** | GPT-5.6 Sol | `openai/gpt-5.6-sol` | 💬 عمومی | 128K+ | `کاپری مدل k75` |
| **`k76`** | Qwen3.7 Plus (Free) | `qwen/qwen3.7-plus:free` | 💬 عمومی | 128K+ | `کاپری مدل k76` |
| **`k77`** | Nemotron 3 Ultra | `nvidia/nemotron-3-ultra` | 💬 عمومی | 128K+ | `کاپری مدل k77` |
| **`k78`** | Big Pickle (Free) | `stealth/big-pickle` | 💬 عمومی | 128K+ | `کاپری مدل k78` |
| **`k79`** | Qwen3.5 Omni Flash (Free) | `qwen/qwen3.5-omni-flash:free` | ⚡ پرسرعت | 128K+ | `کاپری مدل k79` |
| **`k80`** | Command R7B (12-2024) | `cohere/command-r7b-12-2024` | 💬 عمومی | 128K+ | `کاپری مدل k80` |
| **`k81`** | Nemotron 3 Nano Omni | `nvidia/nemotron-3-nano-omni` | 💬 عمومی | 128K+ | `کاپری مدل k81` |
| **`k82`** | Qwen3.8 Max (Free) | `qwen/qwen3.8-max:free` | 💬 عمومی | 128K+ | `کاپری مدل k82` |
| **`k83`** | Qwen3.8 Omni Flash (Free) | `qwen/qwen3.8-omni-flash:free` | ⚡ پرسرعت | 128K+ | `کاپری مدل k83` |
| **`k84`** | Qwen3.7 Flash (Free) | `qwen/qwen3.7-flash:free` | ⚡ پرسرعت | 128K+ | `کاپری مدل k84` |
| **`k85`** | Qwen3.6 Max Preview (Free) | `qwen/qwen3.6-max-preview:free` | 💬 عمومی | 128K+ | `کاپری مدل k85` |
| **`k86`** | Qwen3 Coder Plus (Free) | `qwen/qwen3-coder-plus:free` | 🧠 استدلال | 128K+ | `کاپری مدل k86` |
| **`k87`** | North Small Translate | `cohere/north-small-translate` | ⚡ پرسرعت | 128K+ | `کاپری مدل k87` |
| **`k88`** | Qwen3.6 27B (Free) | `qwen/qwen3.6-27b:free` | 💬 عمومی | 128K+ | `کاپری مدل k88` |
| **`k89`** | Qwen3.5 Plus (Free) | `qwen/qwen3.5-plus:free` | 💬 عمومی | 128K+ | `کاپری مدل k89` |
| **`k90`** | Command A Vision | `cohere/command-a-vision` | 🖼 چندوجهی | 128K+ | `کاپری مدل k90` |
| **`k91`** | Command A Reasoning | `cohere/command-a-reasoning` | 🧠 استدلال | 128K+ | `کاپری مدل k91` |
| **`k92`** | Qwen3.5 Omni Plus (Free) | `qwen/qwen3.5-omni-plus:free` | 💬 عمومی | 128K+ | `کاپری مدل k92` |
| **`k93`** | Qwen3.6 35B A3B (Free) | `qwen/qwen3.6-35b-a3b:free` | 💬 عمومی | 128K+ | `کاپری مدل k93` |
| **`k94`** | Qwen3.5 Flash (Free) | `qwen/qwen3.5-flash:free` | ⚡ پرسرعت | 128K+ | `کاپری مدل k94` |
| **`k95`** | Tiny Aya Water | `cohere/tiny-aya-water` | ⚡ پرسرعت | 128K+ | `کاپری مدل k95` |
| **`k96`** | Qwen3.5 397B A17B (Free) | `qwen/qwen3.5-397b-a17b:free` | 💬 عمومی | 128K+ | `کاپری مدل k96` |
| **`k97`** | Qwen3 Max (Free) | `qwen/qwen3-max:free` | 💬 عمومی | 128K+ | `کاپری مدل k97` |

## ۲. مدل‌های ارائه‌دهنده B.AI (پیشوند `b`)

مجموع: **62** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`b1`** | Minimax M3.1 Flash | `minimax-m3.1-flash` | 🧠 استدلال | 128K+ | `کاپری مدل b1` |
| **`b2`** | Minimax M3 | `minimax-m3` | 🧠 استدلال | 128K+ | `کاپری مدل b2` |
| **`b3`** | Minimax M2.7 | `minimax-m2.7` | 🧠 استدلال | 128K+ | `کاپری مدل b3` |
| **`b4`** | Glm 5.1 | `glm-5.1` | 💬 عمومی | 128K+ | `کاپری مدل b4` |
| **`b5`** | Glm 5.2 | `glm-5.2` | 💬 عمومی | 128K+ | `کاپری مدل b5` |
| **`b6`** | Gpt 6.1 Sol | `gpt-6.1-sol` | 🧠 استدلال | 128K+ | `کاپری مدل b6` |
| **`b7`** | Gpt 6 Astra | `gpt-6-astra` | 🧠 استدلال | 128K+ | `کاپری مدل b7` |
| **`b8`** | Gpt 6 Sol | `gpt-6-sol` | 🧠 استدلال | 128K+ | `کاپری مدل b8` |
| **`b9`** | Gpt 6 Luna | `gpt-6-luna` | 🧠 استدلال | 128K+ | `کاپری مدل b9` |
| **`b10`** | Gpt 5.6 Sol | `gpt-5.6-sol` | 💬 عمومی | 128K+ | `کاپری مدل b10` |
| **`b11`** | Gpt 5.6 Terra | `gpt-5.6-terra` | 💬 عمومی | 128K+ | `کاپری مدل b11` |
| **`b12`** | Gpt 5.6 Luna | `gpt-5.6-luna` | ⚡ پرسرعت | 128K+ | `کاپری مدل b12` |
| **`b13`** | Gpt 5.5 | `gpt-5.5` | 💬 عمومی | 128K+ | `کاپری مدل b13` |
| **`b14`** | Gpt 5.5 Instant | `gpt-5.5-instant` | ⚡ پرسرعت | 128K+ | `کاپری مدل b14` |
| **`b15`** | Gpt 5.4 | `gpt-5.4` | 💬 عمومی | 128K+ | `کاپری مدل b15` |
| **`b16`** | Gpt 5.2 | `gpt-5.2` | 💬 عمومی | 128K+ | `کاپری مدل b16` |
| **`b17`** | Gpt 5.4 Pro | `gpt-5.4-pro` | 🧠 استدلال | 128K+ | `کاپری مدل b17` |
| **`b18`** | Gpt 5.4 Mini | `gpt-5.4-mini` | ⚡ پرسرعت | 128K+ | `کاپری مدل b18` |
| **`b19`** | Gpt 5 Mini | `gpt-5-mini` | ⚡ پرسرعت | 128K+ | `کاپری مدل b19` |
| **`b20`** | Gpt 5.4 Nano | `gpt-5.4-nano` | ⚡ پرسرعت | 128K+ | `کاپری مدل b20` |
| **`b21`** | Gpt 5 Nano | `gpt-5-nano` | ⚡ پرسرعت | 128K+ | `کاپری مدل b21` |
| **`b22`** | Gpt Image 2 | `gpt-image-2` | 🖼 چندوجهی | 128K+ | `کاپری مدل b22` |
| **`b23`** | Claude Opus 5.5 | `claude-opus-5.5` | 🧠 استدلال | 128K+ | `کاپری مدل b23` |
| **`b24`** | Claude Sonnet 5.5 | `claude-sonnet-5.5` | 💬 عمومی | 128K+ | `کاپری مدل b24` |
| **`b25`** | Claude Haiku 5.5 | `claude-haiku-5.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل b25` |
| **`b26`** | Claude Fable 5.1 | `claude-fable-5.1` | 🧠 استدلال | 128K+ | `کاپری مدل b26` |
| **`b27`** | Claude Fable 5 | `claude-fable-5` | 🧠 استدلال | 128K+ | `کاپری مدل b27` |
| **`b28`** | Claude Opus 5 | `claude-opus-5` | 🧠 استدلال | 128K+ | `کاپری مدل b28` |
| **`b29`** | Claude Opus 4.8 | `claude-opus-4.8` | 🧠 استدلال | 128K+ | `کاپری مدل b29` |
| **`b30`** | Claude Opus 4.7 | `claude-opus-4.7` | 🧠 استدلال | 128K+ | `کاپری مدل b30` |
| **`b31`** | Claude Opus 4.6 | `claude-opus-4.6` | 🧠 استدلال | 128K+ | `کاپری مدل b31` |
| **`b32`** | Claude Opus 4.5 | `claude-opus-4.5` | 🧠 استدلال | 128K+ | `کاپری مدل b32` |
| **`b33`** | Claude Sonnet 5 | `claude-sonnet-5` | 💬 عمومی | 128K+ | `کاپری مدل b33` |
| **`b34`** | Claude Sonnet 4.6 | `claude-sonnet-4.6` | 💬 عمومی | 128K+ | `کاپری مدل b34` |
| **`b35`** | Claude Sonnet 4.5 | `claude-sonnet-4.5` | 💬 عمومی | 128K+ | `کاپری مدل b35` |
| **`b36`** | Claude Haiku 4.5 | `claude-haiku-4.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل b36` |
| **`b37`** | Gemini 4 Argon | `gemini-4-argon` | ⚡ پرسرعت | 128K+ | `کاپری مدل b37` |
| **`b38`** | Gemini 3.8 Flash | `gemini-3.8-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b38` |
| **`b39`** | Gemini 3.6 Flash | `gemini-3.6-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b39` |
| **`b40`** | Gemini 3.5 Flash Lite | `gemini-3.5-flash-lite` | ⚡ پرسرعت | 128K+ | `کاپری مدل b40` |
| **`b41`** | Gemini 3.5 Flash | `gemini-3.5-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b41` |
| **`b42`** | Gemini 3.1 Pro | `gemini-3.1-pro` | 🧠 استدلال | 128K+ | `کاپری مدل b42` |
| **`b43`** | Gemini 3 Flash | `gemini-3-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b43` |
| **`b44`** | Hy4 Preview | `hy4-preview` | 💬 عمومی | 128K+ | `کاپری مدل b44` |
| **`b45`** | Mimo V2.6 Pro | `mimo-v2.6-pro` | 🧠 استدلال | 128K+ | `کاپری مدل b45` |
| **`b46`** | Glm 5.3 Flash | `glm-5.3-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b46` |
| **`b47`** | Glm 5.3 Flashx | `glm-5.3-flashx` | ⚡ پرسرعت | 128K+ | `کاپری مدل b47` |
| **`b48`** | Kimi K3.1 Pro | `kimi-k3.1-pro` | 🧠 استدلال | 128K+ | `کاپری مدل b48` |
| **`b49`** | Kimi K3.1 Pro Highspeed | `kimi-k3.1-pro-highspeed` | 🧠 استدلال | 128K+ | `کاپری مدل b49` |
| **`b50`** | Kimi K3 | `kimi-k3` | 💬 عمومی | 128K+ | `کاپری مدل b50` |
| **`b51`** | Glm 5.3 | `glm-5.3` | 💬 عمومی | 128K+ | `کاپری مدل b51` |
| **`b52`** | Mimo V2.6 Flash | `mimo-v2.6-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b52` |
| **`b53`** | Kimi K2.8 Preview | `kimi-k2.8-preview` | 💬 عمومی | 128K+ | `کاپری مدل b53` |
| **`b54`** | Kimi K2.6 | `kimi-k2.6` | 💬 عمومی | 128K+ | `کاپری مدل b54` |
| **`b55`** | Hy3 | `hy3` | 💬 عمومی | 128K+ | `کاپری مدل b55` |
| **`b56`** | Qwen3.8 Flash | `qwen3.8-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b56` |
| **`b57`** | Qwen3.8 Max | `qwen3.8-max` | 🧠 استدلال | 128K+ | `کاپری مدل b57` |
| **`b58`** | Qwen3.8 27B | `qwen3.8-27b` | 💬 عمومی | 128K+ | `کاپری مدل b58` |
| **`b59`** | Jev 1.13.0 | `jev-1.13.0` | 💬 عمومی | 128K+ | `کاپری مدل b59` |
| **`b60`** | Deepseek V4.1 Flash | `deepseek-v4.1-flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b60` |
| **`b61`** | Deepseek V4 Pro | `deepseek-v4-pro` | 🧠 استدلال | 128K+ | `کاپری مدل b61` |
| **`b62`** | Jev Latest | `jev-latest` | 💬 عمومی | 128K+ | `کاپری مدل b62` |

## ۳. مدل‌های ارائه‌دهنده AnyAPI (پیشوند `a`)

مجموع: **7** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`a1`** | Gemini 2.5 Flash Lite | `google/gemini-2.5-flash-lite` | ⚡ پرسرعت | 1048576 | `کاپری مدل a1` |
| **`a2`** | Gemma 4 26B A4B It Free | `google/gemma-4-26b-a4b-it:free` | 💬 عمومی | 262144 | `کاپری مدل a2` |
| **`a3`** | Nemotron 3 Nano Omni 30B A3B Reasoning Free | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 🧠 استدلال | 128K | `کاپری مدل a3` |
| **`a4`** | Nemotron 3 Ultra 550B A55B Free | `nvidia/nemotron-3-ultra-550b-a55b:free` | 🧠 استدلال | 128K | `کاپری مدل a4` |
| **`a5`** | Dots 3 Note Preview Free | `dots-studio/dots-3-note-preview:free` | 💬 عمومی | 128K | `کاپری مدل a5` |
| **`a6`** | Nemotron 3.5 Lightning Free | `nvidia/nemotron-3.5-lightning:free` | ⚡ پرسرعت | 1000000 | `کاپری مدل a6` |
| **`a7`** | Gemini 3.6 Flash | `google/gemini-3.6-flash` | ⚡ پرسرعت | 1048576 | `کاپری مدل a7` |

## ۴. مدل‌های ارائه‌دهنده OpenRouter (رایگان) (پیشوند `o`)

مجموع: **15** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`o1`** | Nemotron 3 Ultra 550B | `nvidia/nemotron-3-ultra-550b-a55b:free` | 🧠 استدلال | 128K | `کاپری مدل o1` |
| **`o2`** | Nemotron 3 Super 120B | `nvidia/nemotron-3-super-120b-a12b:free` | 💬 عمومی | 128K | `کاپری مدل o2` |
| **`o3`** | Nemotron 3.5 Lightning | `nvidia/nemotron-3.5-lightning:free` | ⚡ پرسرعت | 128K | `کاپری مدل o3` |
| **`o4`** | Nemotron 3.5 Super VL | `nvidia/nemotron-3.5-super-vl:free` | 🖼 چندوجهی | 128K | `کاپری مدل o4` |
| **`o5`** | Gemma 4 31B | `google/gemma-4-31b-it:free` | 💬 عمومی | 262K | `کاپری مدل o5` |
| **`o6`** | Gemma 4 26B | `google/gemma-4-26b-a4b-it:free` | ⚡ پرسرعت | 262K | `کاپری مدل o6` |
| **`o7`** | Laguna S 2.1 | `poolside/laguna-s-2.1:free` | 💻 کدنویسی | 128K | `کاپری مدل o7` |
| **`o8`** | Laguna XS 2.1 | `poolside/laguna-xs-2.1:free` | 💻 کدنویسی | 128K | `کاپری مدل o8` |
| **`o9`** | North Mini Code | `cohere/north-mini-code:free` | 💻 کدنویسی | 128K | `کاپری مدل o9` |
| **`o10`** | Flint v1.0 | `recursive/flint-v1.0:free` | 💬 عمومی | 128K | `کاپری مدل o10` |
| **`o11`** | LFM 2.5 | `liquid/lfm-2.5-2.6b:free` | ⚡ پرسرعت | 128K | `کاپری مدل o11` |
| **`o12`** | Xing 4.0 29B | `xingchen-agi/xing4.0-29b-a4b:free` | 💬 عمومی | 128K | `کاپری مدل o12` |
| **`o13`** | Dots 3 Note | `dots-studio/dots-3-note-preview:free` | 💬 عمومی | 128K | `کاپری مدل o13` |
| **`o14`** | Inkling | `thinkingmachines/inkling:free` | 🧠 استدلال | 128K | `کاپری مدل o14` |
| **`o15`** | Inkling Small | `thinkingmachines/inkling-small:free` | ⚡ پرسرعت | 128K | `کاپری مدل o15` |

## ۵. سایر ارائه‌دهندگان معتبر (Groq, Hooshia, Inception) (پیشوند `g, h, i`)

مجموع: **7** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`g1`** | Qwen 3.8 27B | `qwen/qwen3.8-27b` | ⚡ پرسرعت | 128K | `کاپری مدل g1` |
| **`g2`** | GPT-OSS 120B | `openai/gpt-oss-120b` | 🧠 استدلال | 128K | `کاپری مدل g2` |
| **`g3`** | GPT-OSS 20B | `openai/gpt-oss-20b` | ⚡ پرسرعت | 128K | `کاپری مدل g3` |
| **`h1`** | GLM 4.5 Flash | `GLM-4.5-Flash` | ⚡ پرسرعت | 128K | `کاپری مدل h1` |
| **`h2`** | GLM 4.6V Flash (Vision) | `GLM-4.6V-Flash` | 🖼 چندوجهی | 128K | `کاپری مدل h2` |
| **`h3`** | GLM 4.7 Flash | `GLM-4.7-Flash` | 🧠 استدلال | 128K | `کاپری مدل h3` |
| **`i1`** | Mercury 3 | `mercury-3` | ⚡ پرسرعت | 128K | `کاپری مدل i1` |
