"""Hinglish versions of the most-seen bot messages (enable with UI_LANG=hinglish).
Each text keeps exactly the same number of {} placeholders as the English original (checked by tests)."""

HINGLISH = {
    "START_TXT": """<b>{}, {}

Main <a href="https://telegram.me/{}">{}</a> hoon, ek powerful auto-filter bot ❤‍🔥

<blockquote><i>✨ Kuch bhi search karo, seconds me mil jayega.</i></blockquote></b>""",
    "SEARCHING_TXT": """<b><i>'{}' dhoond raha hoon... 🔎</i></b>""",
    "PM_SEARCH_DISABLED_TXT": """<b>{},

<i>Main yahan search nahi karta. Files search karne ke liye hamare group me aao.</i></b>""",
    "MAINTENANCE_TXT": """<b>🛑 Service maintenance me hai 🛑</b>

<b>Hey {}, hum system update kar rahe hain, isliye service abhi band hai.</b>

<blockquote>Thodi der baad dobara try karo. 😊</blockquote>""",
    "ALRT_TXT": """{},

Ye aapki request nahi hai.""",
    "OLD_ALRT_TXT": """{},

Aap mera purana message use kar rahe ho.

Please request dobara bhejo.""",
    "PRE_STREAM": """<b>🔒 Sirf premium users ke liye

💳 Unlock karne ke liye upgrade karo</b>""",
    "CUDNT_FND": """<b>‼️ Spelling galat lag rahi hai bhai!</b>

😊 Tension nahi, neeche se sahi wala chuno 👇</b>""",
    "DYM_TXT": """<b>🤔 Kya aapka matlab inme se koi hai?</b>

<code>{}</code> mere database me nahi mila, {}.
👇 Sahi title par tap karo</b>""",
    "I_CUDNT": """<b>Sorry, {} aapki request ke liye koi file nahi mili 😕

Google par spelling check karke dobara try karo 😃</b>""",
    "NOT_FOUND_TXT": """<b>😌 Ye file mere database me available nahi hai.</b>""",
    "MELCOW_ENG": """<b>{},

🍁 {} me aapka swagat hai

🔍 Jo chahiye wo type karo aur dhoondna shuru karo.</b>""",
    "FREE_TRIAL": """<b>🥳 Badhai ho

🎉 Ab se <u>5 minute</u> ke liye free trial use kar sakte ho!

Premium chahiye 👉🏻 /plan</b>""",
}
