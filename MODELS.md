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

مجموع: **99** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`k1`** | GPT-6.1 Sol | `openai/gpt-6.1-sol` | 🧠 استدلال | 1M | `کاپری مدل k1` |
| **`k2`** | GPT-6 Astra | `openai/gpt-6-astra` | 🧠 استدلال | 1M | `کاپری مدل k2` |
| **`k3`** | GPT-6 Sol | `openai/gpt-6-sol` | 🧠 استدلال | 1M | `کاپری مدل k3` |
| **`k4`** | GPT-6 Luna | `openai/gpt-6-luna` | 🧠 استدلال | 1M | `کاپری مدل k4` |
| **`k5`** | GPT-5.6 Sol | `openai/gpt-5.6-sol` | 💬 عمومی | 1M | `کاپری مدل k5` |
| **`k6`** | GPT-5.6 Terra | `openai/gpt-5.6-terra` | ⚡ پرسرعت | 1M | `کاپری مدل k6` |
| **`k7`** | GPT-5.6 Luna | `openai/gpt-5.6-luna` | ⚡ پرسرعت | 1M | `کاپری مدل k7` |
| **`k8`** | Fable 5.1 | `anthropic/claude-fable-5-1` | 🧠 استدلال | 1M | `کاپری مدل k8` |
| **`k9`** | Fable 5 | `anthropic/claude-fable-5` | 🧠 استدلال | 1M | `کاپری مدل k9` |
| **`k10`** | Sonnet 5.5 | `anthropic/claude-sonnet-5.5` | 💬 عمومی | 1M | `کاپری مدل k10` |
| **`k11`** | Opus 5.5 | `anthropic/claude-opus-5.5` | 🧠 استدلال | 1M | `کاپری مدل k11` |
| **`k12`** | Opus 5 | `anthropic/claude-opus-5` | 🧠 استدلال | 1M | `کاپری مدل k12` |
| **`k13`** | Sonnet 4.5 | `anthropic/claude-sonnet-4.5` | 💬 عمومی | 1M | `کاپری مدل k13` |
| **`k14`** | Opus 4.8 | `anthropic/claude-opus-4.8` | 🧠 استدلال | 1M | `کاپری مدل k14` |
| **`k15`** | Haiku 5.5 | `anthropic/claude-haiku-5.5` | ⚡ پرسرعت | 1M | `کاپری مدل k15` |
| **`k16`** | Sonnet 4 | `anthropic/claude-sonnet-4` | 💬 عمومی | 1M | `کاپری مدل k16` |
| **`k17`** | Opus 4.7 | `anthropic/claude-opus-4.7` | 🧠 استدلال | 1M | `کاپری مدل k17` |
| **`k18`** | Opus 4.6 | `anthropic/claude-opus-4.6` | 🧠 استدلال | 1M | `کاپری مدل k18` |
| **`k19`** | Opus 4.5 | `anthropic/claude-opus-4.5` | 🧠 استدلال | 200K | `کاپری مدل k19` |
| **`k20`** | Sonnet 5 | `anthropic/claude-sonnet-5` | 💬 عمومی | 1M | `کاپری مدل k20` |
| **`k21`** | Sonnet 4.6 | `anthropic/claude-sonnet-4.6` | 💬 عمومی | 1M | `کاپری مدل k21` |
| **`k22`** | Haiku 4.5 | `anthropic/claude-haiku-4.5` | ⚡ پرسرعت | 200K | `کاپری مدل k22` |
| **`k23`** | Gemini 3.8 Flash | `google/gemini-3.8-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k23` |
| **`k24`** | Gemini 3.7 Flash | `google/gemini-3.7-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k24` |
| **`k25`** | Gemini 3.5 Flash | `google/gemini-3.5-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k25` |
| **`k26`** | Gemini 3.6 Flash | `google/gemini-3.6-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k26` |
| **`k27`** | Gemini 3.1 Pro | `google/gemini-3.1-pro` | 🧠 استدلال | 1M | `کاپری مدل k27` |
| **`k28`** | Gemini 3 Flash | `google/gemini-3-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k28` |
| **`k29`** | Gemini 2.5 Flash | `google/gemini-2.5-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k29` |
| **`k30`** | Gemini 2.5 Pro | `google/gemini-2.5-pro` | 🧠 استدلال | 1M | `کاپری مدل k30` |
| **`k31`** | Grok 4.7 | `x-ai/grok-4.7` | 💬 عمومی | 500K | `کاپری مدل k31` |
| **`k32`** | Grok 4.6 | `x-ai/grok-4.6` | 💬 عمومی | 500K | `کاپری مدل k32` |
| **`k33`** | Grok 4.5 | `x-ai/grok-4.5` | 💬 عمومی | 500K | `کاپری مدل k33` |
| **`k34`** | Kimi K3 Agent | `moonshotai/kimi-k3-agent` | 💬 عمومی | 262K | `کاپری مدل k34` |
| **`k35`** | Kimi K2.8 Preview Agent | `moonshotai/kimi-k2.8-preview-agent` | 💬 عمومی | 262K | `کاپری مدل k35` |
| **`k36`** | Mistral Large 4 | `mistralai/mistral-large-4-0` | 💬 عمومی | 256K | `کاپری مدل k36` |
| **`k37`** | Mistral Large 3 | `mistralai/mistral-large-2512` | 💬 عمومی | 256K | `کاپری مدل k37` |
| **`k38`** | Mistral Medium 3.5 | `mistralai/mistral-medium-3.5` | 💬 عمومی | 256K | `کاپری مدل k38` |
| **`k39`** | Mistral Small 4 | `mistralai/mistral-small-2603` | ⚡ پرسرعت | 256K | `کاپری مدل k39` |
| **`k40`** | Codestral | `mistralai/codestral-2508` | 💻 کدنویسی | 256K | `کاپری مدل k40` |
| **`k41`** | Devstral 2 | `mistralai/devstral-medium` | 💻 کدنویسی | 256K | `کاپری مدل k41` |
| **`k42`** | Ministral 3 14B | `mistralai/ministral-14b` | ⚡ پرسرعت | 256K | `کاپری مدل k42` |
| **`k43`** | Ministral 3 8B | `mistralai/ministral-8b` | ⚡ پرسرعت | 256K | `کاپری مدل k43` |
| **`k44`** | Ministral 3 3B | `mistralai/ministral-3b` | ⚡ پرسرعت | 128K | `کاپری مدل k44` |
| **`k45`** | MiniMax M3.1 Flash | `minimax/minimax-m3.1-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k45` |
| **`k46`** | MiniMax M3 | `minimax/minimax-m3` | ⚡ پرسرعت | 1M | `کاپری مدل k46` |
| **`k47`** | MiniMax M2.7 | `minimax/minimax-m2.7` | ⚡ پرسرعت | 204K | `کاپری مدل k47` |
| **`k48`** | MiniMax M2.7 Highspeed | `minimax/minimax-m2.7-highspeed` | ⚡ پرسرعت | 204K | `کاپری مدل k48` |
| **`k49`** | MiniMax M2.5 | `minimax/minimax-m2.5` | ⚡ پرسرعت | 204K | `کاپری مدل k49` |
| **`k50`** | MiniMax M2.5 Highspeed | `minimax/minimax-m2.5-highspeed` | ⚡ پرسرعت | 204K | `کاپری مدل k50` |
| **`k51`** | MiniMax M2.1 | `minimax/minimax-m2.1` | ⚡ پرسرعت | 204K | `کاپری مدل k51` |
| **`k52`** | MiniMax M2.1 Highspeed | `minimax/minimax-m2.1-highspeed` | ⚡ پرسرعت | 204K | `کاپری مدل k52` |
| **`k53`** | MiniMax M2 | `minimax/minimax-m2` | ⚡ پرسرعت | 204K | `کاپری مدل k53` |
| **`k54`** | MiMo v2.6 Pro | `xiaomi/mimo-v2.6-pro` | 🧠 استدلال | 1M | `کاپری مدل k54` |
| **`k55`** | MiMo v2.6 Flash | `xiaomi/mimo-v2.6-flash` | ⚡ پرسرعت | 1M | `کاپری مدل k55` |
| **`k56`** | MiMo v2.5 | `xiaomi/mimo-v2.5` | 💬 عمومی | 1M | `کاپری مدل k56` |
| **`k57`** | Qwen3.8 Omni Flash (Free) | `qwen/qwen3.8-omni-flash:free` | ⚡ پرسرعت | 1M | `کاپری مدل k57` |
| **`k58`** | Qwen3.8 Max (Free) | `qwen/qwen3.8-max:free` | 💬 عمومی | 1M | `کاپری مدل k58` |
| **`k59`** | Qwen3.7 Max (Free) | `qwen/qwen3.7-max:free` | 💬 عمومی | 1M | `کاپری مدل k59` |
| **`k60`** | Qwen3.7 Plus (Free) | `qwen/qwen3.7-plus:free` | 💬 عمومی | 1M | `کاپری مدل k60` |
| **`k61`** | Qwen3.7 Flash (Free) | `qwen/qwen3.7-flash:free` | ⚡ پرسرعت | 1M | `کاپری مدل k61` |
| **`k62`** | Qwen3.6 Plus (Free) | `qwen/qwen3.6-plus:free` | 💬 عمومی | 1M | `کاپری مدل k62` |
| **`k63`** | Qwen3.6 Max Preview (Free) | `qwen/qwen3.6-max-preview:free` | 💬 عمومی | 262K | `کاپری مدل k63` |
| **`k64`** | Qwen3.6 27B (Free) | `qwen/qwen3.6-27b:free` | 💬 عمومی | 262K | `کاپری مدل k64` |
| **`k65`** | Qwen3.5 Plus (Free) | `qwen/qwen3.5-plus:free` | 💬 عمومی | 1M | `کاپری مدل k65` |
| **`k66`** | Qwen3.5 Omni Plus (Free) | `qwen/qwen3.5-omni-plus:free` | 💬 عمومی | 262K | `کاپری مدل k66` |
| **`k67`** | Qwen3.6 35B A3B (Free) | `qwen/qwen3.6-35b-a3b:free` | 💬 عمومی | 262K | `کاپری مدل k67` |
| **`k68`** | Qwen3.5 Flash (Free) | `qwen/qwen3.5-flash:free` | ⚡ پرسرعت | 1M | `کاپری مدل k68` |
| **`k69`** | Qwen3.5 397B A17B (Free) | `qwen/qwen3.5-397b-a17b:free` | 💬 عمومی | 262K | `کاپری مدل k69` |
| **`k70`** | Qwen3.5 Omni Flash (Free) | `qwen/qwen3.5-omni-flash:free` | ⚡ پرسرعت | 262K | `کاپری مدل k70` |
| **`k71`** | Qwen3 Max (Free) | `qwen/qwen3-max:free` | 💬 عمومی | 262K | `کاپری مدل k71` |
| **`k72`** | Qwen Plus 0728 (Free) | `qwen/qwen-plus-2025-07-28:free` | 💬 عمومی | 131K | `کاپری مدل k72` |
| **`k73`** | Qwen3 Coder Plus (Free) | `qwen/qwen3-coder-plus:free` | 🧠 استدلال | 1M | `کاپری مدل k73` |
| **`k74`** | Qwen3 VL Plus (Free) | `qwen/qwen3-vl-plus:free` | 🖼 چندوجهی | 262K | `کاپری مدل k74` |
| **`k75`** | Qwen3 Omni Flash (Free) | `qwen/qwen3-omni-flash:free` | ⚡ پرسرعت | 262K | `کاپری مدل k75` |
| **`k76`** | LongCat 2.5 Preview (Free) | `meituan/longcat-2.5-preview:free` | 💬 عمومی | 1M | `کاپری مدل k76` |
| **`k77`** | LongCat 2.0 | `meituan/longcat-2.0` | 💬 عمومی | 1M | `کاپری مدل k77` |
| **`k78`** | Nemotron 3 Ultra | `nvidia/nemotron-3-ultra` | 💬 عمومی | 1M | `کاپری مدل k78` |
| **`k79`** | Nemotron 3 Nano Omni | `nvidia/nemotron-3-nano-omni` | 💬 عمومی | 256K | `کاپری مدل k79` |
| **`k80`** | Big Pickle (Free) | `stealth/big-pickle` | 💬 عمومی | 200K | `کاپری مدل k80` |
| **`k81`** | SenseNova 6.8 Flash-Lite | `sensenova/sensenova-6.8-flash-lite` | ⚡ پرسرعت | 262K | `کاپری مدل k81` |
| **`k82`** | Command A+ | `cohere/command-a-plus` | 💬 عمومی | 436K | `کاپری مدل k82` |
| **`k83`** | North Mini Code | `cohere/north-mini-code` | 💻 کدنویسی | 256K | `کاپری مدل k83` |
| **`k84`** | Command A Reasoning | `cohere/command-a-reasoning` | 🧠 استدلال | 288K | `کاپری مدل k84` |
| **`k85`** | Command A Vision | `cohere/command-a-vision` | 🖼 چندوجهی | 128K | `کاپری مدل k85` |
| **`k86`** | Command A | `cohere/command-a` | 💬 عمومی | 288K | `کاپری مدل k86` |
| **`k87`** | Command A Translate | `cohere/command-a-translate` | 💬 عمومی | 8K | `کاپری مدل k87` |
| **`k88`** | North Small Translate | `cohere/north-small-translate` | ⚡ پرسرعت | 32K | `کاپری مدل k88` |
| **`k89`** | Command R+ (08-2024) | `cohere/command-r-plus-08-2024` | 🧠 استدلال | 128K | `کاپری مدل k89` |
| **`k90`** | Command R (08-2024) | `cohere/command-r-08-2024` | 💬 عمومی | 128K | `کاپری مدل k90` |
| **`k91`** | Command R7B (12-2024) | `cohere/command-r7b-12-2024` | 💬 عمومی | 132K | `کاپری مدل k91` |
| **`k92`** | Aya Expanse 32B | `cohere/aya-expanse-32b` | 💬 عمومی | 128K | `کاپری مدل k92` |
| **`k93`** | Aya Vision 32B | `cohere/aya-vision-32b` | 🖼 چندوجهی | 16K | `کاپری مدل k93` |
| **`k94`** | Tiny Aya Global | `cohere/tiny-aya-global` | ⚡ پرسرعت | 8K | `کاپری مدل k94` |
| **`k95`** | Tiny Aya Earth | `cohere/tiny-aya-earth` | ⚡ پرسرعت | 8K | `کاپری مدل k95` |
| **`k96`** | Tiny Aya Fire | `cohere/tiny-aya-fire` | ⚡ پرسرعت | 8K | `کاپری مدل k96` |
| **`k97`** | Tiny Aya Water | `cohere/tiny-aya-water` | ⚡ پرسرعت | 8K | `کاپری مدل k97` |
| **`k98`** | ChatGPT Images 2.5 | `openai/gpt-image-2.5` | 🖼 چندوجهی | - | `کاپری مدل k98` |
| **`k99`** | SenseNova U1.5 Lite | `sensenova/sensenova-u1.5-lite` | ⚡ پرسرعت | - | `کاپری مدل k99` |

## ۲. مدل‌های ارائه‌دهنده B.AI (پیشوند `b`)

مجموع: **62** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`b1`** | MiniMax-M3.1-Flash | `MiniMax-M3.1-Flash` | 🧠 استدلال | 128K+ | `کاپری مدل b1` |
| **`b2`** | MiniMax-M3 | `MiniMax-M3` | 🧠 استدلال | 128K+ | `کاپری مدل b2` |
| **`b3`** | MiniMax-M2.7 | `MiniMax-M2.7` | 🧠 استدلال | 128K+ | `کاپری مدل b3` |
| **`b4`** | Jev 1.13.0 | `jev-1.13.0` | 💬 عمومی | 128K+ | `کاپری مدل b4` |
| **`b5`** | Jev-Latest | `jev-latest` | 💬 عمومی | 128K+ | `کاپری مدل b5` |
| **`b6`** | DeepSeek-V4.1-Flash | `DeepSeek-V4.1-Flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b6` |
| **`b7`** | DeepSeek-V4-Pro | `DeepSeek-V4-Pro` | 🧠 استدلال | 128K+ | `کاپری مدل b7` |
| **`b8`** | Hy4-preview | `Hy4-preview` | 💬 عمومی | 128K+ | `کاپری مدل b8` |
| **`b9`** | Hy3 | `Hy3` | 💬 عمومی | 128K+ | `کاپری مدل b9` |
| **`b10`** | MiMo-V2.6-Pro | `MiMo-V2.6-Pro` | 🧠 استدلال | 128K+ | `کاپری مدل b10` |
| **`b11`** | MiMo-V2.6-Flash | `MiMo-V2.6-Flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b11` |
| **`b12`** | GLM-5.3-Flash | `Z.ai` | 💬 عمومی | 128K+ | `کاپری مدل b12` |
| **`b13`** | GLM-5.3-FlashX | `GLM-5.3-FlashX` | ⚡ پرسرعت | 128K+ | `کاپری مدل b13` |
| **`b14`** | GLM-5.3 | `GLM-5.3` | 💬 عمومی | 128K+ | `کاپری مدل b14` |
| **`b15`** | GLM-5.2 | `GLM-5.2` | 💬 عمومی | 128K+ | `کاپری مدل b15` |
| **`b16`** | GLM-5.1 | `GLM-5.1` | 💬 عمومی | 128K+ | `کاپری مدل b16` |
| **`b17`** | Qwen3.8-Flash | `Qwen3.8-Flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b17` |
| **`b18`** | Qwen3.8-Max | `Qwen3.8-Max` | 🧠 استدلال | 128K+ | `کاپری مدل b18` |
| **`b19`** | Qwen3.8-27B | `Qwen3.8-27B` | 💬 عمومی | 128K+ | `کاپری مدل b19` |
| **`b20`** | Kimi K3.1 Pro | `Kimi K3.1 Pro` | 🧠 استدلال | 128K+ | `کاپری مدل b20` |
| **`b21`** | Kimi K3.1 Pro Highspeed | `Kimi K3.1 Pro Highspeed` | 🧠 استدلال | 128K+ | `کاپری مدل b21` |
| **`b22`** | Kimi K3 | `Kimi K3` | 💬 عمومی | 128K+ | `کاپری مدل b22` |
| **`b23`** | Kimi K2.8 Preview | `Kimi K2.8 Preview` | 💬 عمومی | 128K+ | `کاپری مدل b23` |
| **`b24`** | Kimi-K2.6 | `Kimi-K2.6` | 💬 عمومی | 128K+ | `کاپری مدل b24` |
| **`b25`** | Claude Opus 5.5 | `Claude Opus 5.5` | 🧠 استدلال | 128K+ | `کاپری مدل b25` |
| **`b26`** | Claude Sonnet 5.5 | `Claude Sonnet 5.5` | 💬 عمومی | 128K+ | `کاپری مدل b26` |
| **`b27`** | Claude Haiku 5.5 | `Claude Haiku 5.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل b27` |
| **`b28`** | Claude Fable 5.1 | `Claude Fable 5.1` | 🧠 استدلال | 128K+ | `کاپری مدل b28` |
| **`b29`** | Claude Fable 5 | `Claude Fable 5` | 🧠 استدلال | 128K+ | `کاپری مدل b29` |
| **`b30`** | Claude Opus 5 | `Claude Opus 5` | 🧠 استدلال | 128K+ | `کاپری مدل b30` |
| **`b31`** | Claude Opus 4.8 | `Claude Opus 4.8` | 🧠 استدلال | 128K+ | `کاپری مدل b31` |
| **`b32`** | Claude Opus 4.7 | `Claude Opus 4.7` | 🧠 استدلال | 128K+ | `کاپری مدل b32` |
| **`b33`** | Claude Opus 4.6 | `Claude Opus 4.6` | 🧠 استدلال | 128K+ | `کاپری مدل b33` |
| **`b34`** | Claude Opus 4.5 | `Claude Opus 4.5` | 🧠 استدلال | 128K+ | `کاپری مدل b34` |
| **`b35`** | Claude Sonnet 5 | `Claude Sonnet 5` | 💬 عمومی | 128K+ | `کاپری مدل b35` |
| **`b36`** | Claude Sonnet 4.6 | `Claude Sonnet 4.6` | 💬 عمومی | 128K+ | `کاپری مدل b36` |
| **`b37`** | Claude Sonnet 4.5 | `Claude Sonnet 4.5` | 💬 عمومی | 128K+ | `کاپری مدل b37` |
| **`b38`** | Claude Haiku 4.5 | `Claude Haiku 4.5` | ⚡ پرسرعت | 128K+ | `کاپری مدل b38` |
| **`b39`** | GPT-6.1 Sol | `GPT-6.1 Sol` | 🧠 استدلال | 128K+ | `کاپری مدل b39` |
| **`b40`** | GPT-6 Astra | `GPT-6 Astra` | 🧠 استدلال | 128K+ | `کاپری مدل b40` |
| **`b41`** | GPT-6 Sol | `GPT-6 Sol` | 🧠 استدلال | 128K+ | `کاپری مدل b41` |
| **`b42`** | GPT-6 Luna | `GPT-6 Luna` | 🧠 استدلال | 128K+ | `کاپری مدل b42` |
| **`b43`** | GPT-5.6 Sol | `GPT-5.6 Sol` | 💬 عمومی | 128K+ | `کاپری مدل b43` |
| **`b44`** | GPT-5.6 Terra | `GPT-5.6 Terra` | 💬 عمومی | 128K+ | `کاپری مدل b44` |
| **`b45`** | GPT-5.6 Luna | `GPT-5.6 Luna` | ⚡ پرسرعت | 128K+ | `کاپری مدل b45` |
| **`b46`** | GPT-5.5 | `GPT-5.5` | 💬 عمومی | 128K+ | `کاپری مدل b46` |
| **`b47`** | GPT-5.5-Instant | `GPT-5.5-Instant` | ⚡ پرسرعت | 128K+ | `کاپری مدل b47` |
| **`b48`** | GPT-5.4 | `GPT-5.4` | 💬 عمومی | 128K+ | `کاپری مدل b48` |
| **`b49`** | GPT-5.2 | `GPT-5.2` | 💬 عمومی | 128K+ | `کاپری مدل b49` |
| **`b50`** | GPT-5.4 Pro | `GPT-5.4 Pro` | 🧠 استدلال | 128K+ | `کاپری مدل b50` |
| **`b51`** | GPT-5.4 mini | `GPT-5.4 mini` | ⚡ پرسرعت | 128K+ | `کاپری مدل b51` |
| **`b52`** | GPT-5 mini | `GPT-5 mini` | ⚡ پرسرعت | 128K+ | `کاپری مدل b52` |
| **`b53`** | GPT-5.4 nano | `GPT-5.4 nano` | ⚡ پرسرعت | 128K+ | `کاپری مدل b53` |
| **`b54`** | GPT-5 nano | `GPT-5 nano` | ⚡ پرسرعت | 128K+ | `کاپری مدل b54` |
| **`b55`** | GPT Image 2 | `GPT Image 2` | 🖼 چندوجهی | 128K+ | `کاپری مدل b55` |
| **`b56`** | Gemini 4 Argon | `Gemini 4 Argon` | ⚡ پرسرعت | 128K+ | `کاپری مدل b56` |
| **`b57`** | Gemini 3.8 flash | `Gemini 3.8 flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b57` |
| **`b58`** | Gemini 3.6 flash | `Gemini 3.6 flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b58` |
| **`b59`** | Gemini 3.5 flash-lite | `Gemini 3.5 flash-lite` | ⚡ پرسرعت | 128K+ | `کاپری مدل b59` |
| **`b60`** | Gemini 3.5 flash | `Gemini 3.5 flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b60` |
| **`b61`** | Gemini 3.1 Pro | `Gemini 3.1 Pro` | 🧠 استدلال | 128K+ | `کاپری مدل b61` |
| **`b62`** | Gemini 3 Flash | `Gemini 3 Flash` | ⚡ پرسرعت | 128K+ | `کاپری مدل b62` |

## ۳. مدل‌های ارائه‌دهنده AnyAPI (پیشوند `a`)

مجموع: **70** مدل

| UID | نام مدل | شناسه فنی (Model ID) | دسته‌بندی | کانتکست | دستور فراخوانی |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`a1`** | Gemini 2.5 Flash Lite | `google/gemini-2.5-flash-lite` | ⚡ پرسرعت | 1,048,576 | `کاپری مدل a1` |
| **`a2`** | Gemini 3.6 Flash | `google/gemini-3.6-flash` | ⚡ پرسرعت | 1,048,576 | `کاپری مدل a2` |
| **`a3`** | Gemma 4 26B A4B It Free | `google/gemma-4-26b-a4b-it:free` | 💬 عمومی | 262,144 | `کاپری مدل a3` |
| **`a4`** | Nemotron 3 Nano Omni 30B A3B Reasoning Free | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 🧠 استدلال | - | `کاپری مدل a4` |
| **`a5`** | Nemotron 3 Ultra 550B A55B Free | `nvidia/nemotron-3-ultra-550b-a55b:free` | 💬 عمومی | - | `کاپری مدل a5` |
| **`a6`** | Dots 3 Note Preview Free | `dots-studio/dots-3-note-preview:free` | 💬 عمومی | - | `کاپری مدل a6` |
| **`a7`** | Nemotron 3.5 Lightning Free | `nvidia/nemotron-3.5-lightning:free` | 💬 عمومی | 1,000,000 | `کاپری مدل a7` |
| **`a8`** | Claude Sonnet 4 | `anthropic/claude-sonnet-4` | 💬 عمومی | 200,000 | `کاپری مدل a8` |
| **`a9`** | Nova Lite V1 | `amazon/nova-lite-v1` | ⚡ پرسرعت | 300,000 | `کاپری مدل a9` |
| **`a10`** | Gpt Oss 120B | `openai/gpt-oss-120b` | 💬 عمومی | 131,072 | `کاپری مدل a10` |
| **`a11`** | Gpt Oss 20B | `openai/gpt-oss-20b` | 💬 عمومی | 131,072 | `کاپری مدل a11` |
| **`a12`** | Nova 2 Lite V1 | `amazon/nova-2-lite-v1` | ⚡ پرسرعت | 1,000,000 | `کاپری مدل a12` |
| **`a13`** | Claude Haiku 4.5 | `anthropic/claude-haiku-4.5` | ⚡ پرسرعت | 200,000 | `کاپری مدل a13` |
| **`a14`** | Qwen3 Coder 30B A3B Instruct | `qwen/qwen3-coder-30b-a3b-instruct` | 💻 کدنویسی | 160,000 | `کاپری مدل a14` |
| **`a15`** | Qwen3 32B | `qwen/qwen3-32b` | 💬 عمومی | 40,960 | `کاپری مدل a15` |
| **`a16`** | Kimi K2.5 | `moonshotai/kimi-k2.5` | 💬 عمومی | 262,144 | `کاپری مدل a16` |
| **`a17`** | Gemini 2.5 Flash | `google/gemini-2.5-flash` | ⚡ پرسرعت | 1,048,576 | `کاپری مدل a17` |
| **`a18`** | Gemini 2.5 Pro | `google/gemini-2.5-pro` | 🧠 استدلال | 1,048,576 | `کاپری مدل a18` |
| **`a19`** | Gemini 2.0 Flash 001 | `google/gemini-2.0-flash-001` | ⚡ پرسرعت | 1,000,000 | `کاپری مدل a19` |
| **`a20`** | Claude Sonnet 4.6 | `anthropic/claude-sonnet-4.6` | 💬 عمومی | 1,000,000 | `کاپری مدل a20` |
| **`a21`** | Claude Opus 4.6 | `anthropic/claude-opus-4.6` | 🧠 استدلال | 1,000,000 | `کاپری مدل a21` |
| **`a22`** | Kimi K2 Thinking | `moonshotai/kimi-k2-thinking` | 🧠 استدلال | 262,144 | `کاپری مدل a22` |
| **`a23`** | Gpt 4.1 | `openai/gpt-4.1` | 💬 عمومی | 1,047,576 | `کاپری مدل a23` |
| **`a24`** | Gpt 4.1 Mini | `openai/gpt-4.1-mini` | ⚡ پرسرعت | 1,047,576 | `کاپری مدل a24` |
| **`a25`** | Gpt 4.1 Nano | `openai/gpt-4.1-nano` | ⚡ پرسرعت | 1,047,576 | `کاپری مدل a25` |
| **`a26`** | O1 Pro | `openai/o1-pro` | 🧠 استدلال | 200,000 | `کاپری مدل a26` |
| **`a27`** | O1 | `openai/o1` | 🧠 استدلال | 200,000 | `کاپری مدل a27` |
| **`a28`** | Gpt 4O 2024 11 20 | `openai/gpt-4o-2024-11-20` | 💬 عمومی | 128,000 | `کاپری مدل a28` |
| **`a29`** | Gpt 4O 2024 08 06 | `openai/gpt-4o-2024-08-06` | 💬 عمومی | 128,000 | `کاپری مدل a29` |
| **`a30`** | Gpt 4O Mini | `openai/gpt-4o-mini` | ⚡ پرسرعت | 128,000 | `کاپری مدل a30` |
| **`a31`** | Gpt 4O Mini 2024 07 18 | `openai/gpt-4o-mini-2024-07-18` | ⚡ پرسرعت | 128,000 | `کاپری مدل a31` |
| **`a32`** | Gpt 4O | `openai/gpt-4o` | 💬 عمومی | 128,000 | `کاپری مدل a32` |
| **`a33`** | Gpt 4 Turbo | `openai/gpt-4-turbo` | ⚡ پرسرعت | 128,000 | `کاپری مدل a33` |
| **`a34`** | Gpt 3.5 Turbo 0613 | `openai/gpt-3.5-turbo-0613` | ⚡ پرسرعت | 4,095 | `کاپری مدل a34` |
| **`a35`** | Gpt 3.5 Turbo Instruct | `openai/gpt-3.5-turbo-instruct` | ⚡ پرسرعت | 4,095 | `کاپری مدل a35` |
| **`a36`** | Gpt 3.5 Turbo 16K | `openai/gpt-3.5-turbo-16k` | ⚡ پرسرعت | 16,385 | `کاپری مدل a36` |
| **`a37`** | Gpt 3.5 Turbo | `openai/gpt-3.5-turbo` | ⚡ پرسرعت | 16,385 | `کاپری مدل a37` |
| **`a38`** | Gpt 4 | `openai/gpt-4` | 💬 عمومی | 8,191 | `کاپری مدل a38` |
| **`a39`** | Command R7B 12 2024 | `cohere/command-r7b-12-2024` | 💬 عمومی | 128,000 | `کاپری مدل a39` |
| **`a40`** | Command R Plus 08 2024 | `cohere/command-r-plus-08-2024` | 💬 عمومی | 128,000 | `کاپری مدل a40` |
| **`a41`** | Command R 08 2024 | `cohere/command-r-08-2024` | 💬 عمومی | 128,000 | `کاپری مدل a41` |
| **`a42`** | Qwen 2.5 Coder 32B Instruct | `qwen/qwen-2.5-coder-32b-instruct` | 💻 کدنویسی | 32,768 | `کاپری مدل a42` |
| **`a43`** | Deepseek R1 0528 | `deepseek/deepseek-r1-0528` | 🧠 استدلال | 163,840 | `کاپری مدل a43` |
| **`a44`** | Deepseek Chat | `deepseek/deepseek-chat` | 💬 عمومی | 163,840 | `کاپری مدل a44` |
| **`a45`** | Weaver | `mancer/weaver` | 💬 عمومی | 8,000 | `کاپری مدل a45` |
| **`a46`** | Remm Slerp L2 13B | `undi95/remm-slerp-l2-13b` | 💬 عمومی | 6,144 | `کاپری مدل a46` |
| **`a47`** | Mythomax L2 13B | `gryphe/mythomax-l2-13b` | 💬 عمومی | 4,096 | `کاپری مدل a47` |
| **`a48`** | Mistral Small 3.2 24B Instruct | `mistralai/mistral-small-3.2-24b-instruct` | ⚡ پرسرعت | 128,000 | `کاپری مدل a48` |
| **`a49`** | Mistral Small 3.1 24B Instruct | `mistralai/mistral-small-3.1-24b-instruct` | ⚡ پرسرعت | 128,000 | `کاپری مدل a49` |
| **`a50`** | Mistral Large 2407 | `mistralai/mistral-large-2407` | 💬 عمومی | 131,072 | `کاپری مدل a50` |
| **`a51`** | Mixtral 8X22B Instruct | `mistralai/mixtral-8x22b-instruct` | ⚡ پرسرعت | 65,536 | `کاپری مدل a51` |
| **`a52`** | Wizardlm 2 8X22B | `microsoft/wizardlm-2-8x22b` | 💬 عمومی | 65,535 | `کاپری مدل a52` |
| **`a53`** | Mistral Large | `mistralai/mistral-large` | 💬 عمومی | 128,000 | `کاپری مدل a53` |
| **`a54`** | Claude 3 Haiku | `anthropic/claude-3-haiku` | ⚡ پرسرعت | 200,000 | `کاپری مدل a54` |
| **`a55`** | Sonar Reasoning Pro | `perplexity/sonar-reasoning-pro` | 🧠 استدلال | 128,000 | `کاپری مدل a55` |
| **`a56`** | Sonar Pro | `perplexity/sonar-pro` | 🧠 استدلال | 200,000 | `کاپری مدل a56` |
| **`a57`** | Sonar Deep Research | `perplexity/sonar-deep-research` | 💬 عمومی | 128,000 | `کاپری مدل a57` |
| **`a58`** | O3 Mini High | `openai/o3-mini-high` | 🧠 استدلال | 200,000 | `کاپری مدل a58` |
| **`a59`** | O3 Mini | `openai/o3-mini` | 🧠 استدلال | 200,000 | `کاپری مدل a59` |
| **`a60`** | Sonar | `perplexity/sonar` | 💬 عمومی | 127,072 | `کاپری مدل a60` |
| **`a61`** | Llama 3.3 70B Instruct | `meta-llama/llama-3.3-70b-instruct` | ⚡ پرسرعت | 131,072 | `کاپری مدل a61` |
| **`a62`** | Qwen3 Coder | `qwen/qwen3-coder` | 💻 کدنویسی | 262,144 | `کاپری مدل a62` |
| **`a63`** | Ui Tars 1.5 7B | `bytedance/ui-tars-1.5-7b` | 🖼 چندوجهی | 128,000 | `کاپری مدل a63` |
| **`a64`** | Deepseek Chat V3.1 | `deepseek/deepseek-chat-v3.1` | 💬 عمومی | 32,768 | `کاپری مدل a64` |
| **`a65`** | Gpt 5 Mini | `openai/gpt-5-mini` | ⚡ پرسرعت | 400,000 | `کاپری مدل a65` |
| **`a66`** | Gpt 5 Nano | `openai/gpt-5-nano` | ⚡ پرسرعت | 400,000 | `کاپری مدل a66` |
| **`a67`** | Claude Opus 4.1 | `anthropic/claude-opus-4.1` | 🧠 استدلال | 200,000 | `کاپری مدل a67` |
| **`a68`** | Claude Sonnet 4.5 | `anthropic/claude-sonnet-4.5` | 💬 عمومی | 1,000,000 | `کاپری مدل a68` |
| **`a69`** | Claude Opus 4.5 | `anthropic/claude-opus-4.5` | 🧠 استدلال | 200,000 | `کاپری مدل a69` |
| **`a70`** | Gpt 5.1 Codex Max | `openai/gpt-5.1-codex-max` | 💻 کدنویسی | - | `کاپری مدل a70` |

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
