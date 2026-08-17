# 🎵 SpotifyXRefer Bot

Professional Telegram Referral Bot — **3 referrals = 1 FREE Spotify Premium Link**

---

## ✨ Features

| Feature | Details |
|---|---|
| 👥 Referral System | Har user ko unique referral link milta hai, har referral properly count hota hai |
| 🎁 Auto Rewards | Har 3 referrals = 1 Spotify Premium Link (script me `REFS_PER_LINK` se change kar sakte ho) |
| ➕ Add Links | Admin bot se hi links add karta hai — script me koi change nahi |
| 🚫 Duplicate Check | Pehle se maujood link add karne par bot "duplicate" kehkar skip kar deta hai |
| 🔒 Force Join | Bot start karte hi channel join check hota hai — verify ke baad hi interface dikhta hai. Admin bot se hi channel add/remove karta hai |
| 🛠️ Admin Panel | Links add/remove, status, users stats, broadcast — sab buttons se |
| 📣 Broadcast | Ek message se sabhi users ko message |
| 💾 SQLite Database | Data automatically save hota hai, restart par kuch nahi jata |

---

## 🛠️ Setup (Windows)

### Step 1 - Token lo
1. Telegram me **@BotFather** kholo
2. `/token` bhejo aur apna bot (`SpotifyXrefer_bot`) select karo
3. Token copy karo

### Step 2 - Apna Telegram ID lo
1. **@getmyid_bot** kholo aur `/start` bhejo
2. Jo number aaya woh **aapka Telegram ID** hai

### Step 3 - `bot.py` me config set karo

```python
BOT_TOKEN = "1234567890:AAHdjhfkhsdf..."   # <- Apna token
ADMIN_IDS = [123456789]                     # <- Apna Telegram ID
REFS_PER_LINK = 3                           # Har 3 refer = 1 link
```

### Step 4 - Run karo
`run.bat` double-click karo (pehli baar pip install khud ho jayega).

Ya manually:
```cmd
pip install -r requirements.txt
python bot.py
```

✅ Bot chalte hi screen par `SpotifyXRefer Bot started...` dikhega.

---

## 📖 Kaise Use Kare

### Users ke liye
- `/start` → **Sabse pehle force join check** — channel join karke *Verify* dabao, uske baad hi interface milega
- Referral link share karo: `https://t.me/SpotifyXRefer_bot?start=ref_<id>`
- Har 3 friends join = 1 reward → *Claim* dabao
- `/status` → Apne stats dekho, `/help` → Help

### Admin ke liye
Bot me `/admin` bhejo → Admin Panel khulega:

| Button | Kaam |
|---|---|
| ➕ Add Links | Ek message me 1 ya multiple links bhejo (space/new line se alag). Duplicate links automatically **skip** ho jayenge |
| ➖ Remove Link | Link copy karke bhejo, delete ho jayega |
| 📊 Links Status | Kitne total, used, remaining links hain |
| 👥 Users Stats | Total users, referrals, claims |
| 📢 Force Join Channels | Channel list dekho, add karo, remove karo |
| 👤 Admins | Bot se hi kisi ko admin banao / hatao |
| 📣 Broadcast | Sabhi users ko message bhejo |

### Force Join Channel Add karna
1. Admin Panel → `📢 Force Join Channels` → `➕ Add Channel`
2. Channel ka **link** bhejo (`https://t.me/mychannel`) ya `@username` ya ID
3. ⚠️ **Bot ko channel me Admin banana zaroori hai** (nahi to verify nahi hoga)

Users jab `/claim` karenge to pehle wo channel join karna hoga, tabhi link milega.

---

## ⚠️ Important Notes

1. **Bot ko har channel me Admin banao** jise force join me dalna hai
2. **Script chalti rehni chahiye** — 24/7 ke liye VPS/Railway/Render use karo, ya apna PC on rakho
3. Claim karne se pehle force join check hota hai
4. Har user ka referral **sirf ek baar** count hota hai (dusri baar /start karne se count nahi badhta) — isse fake referral nahi ginte
5. Data `spotifyxrefer.db` file me save hota hai — backup ke liye bas ye file copy karo

---

## 🗂️ Files

```
SpotifyXReferBot/
├── bot.py            # Main bot script
├── requirements.txt  # Python libraries
├── run.bat           # Ek click me run karne ke liye
└── spotifyxrefer.db  # Database (auto-create hota hai)
```