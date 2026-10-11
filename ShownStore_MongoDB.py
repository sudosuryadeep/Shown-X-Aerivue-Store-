# SHOWN X STORE BOT

from __future__ import annotations

import asyncio
import html
import json
import logging
import os
import random
import re
import secrets
import string
import time
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv  
from pathlib import Path
from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaPhoto,
    InputMediaVideo,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter, TelegramError
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

load_dotenv()

# ============================================================
# EASY CONFIGURATION — edit these values directly, no .env needed
# ============================================================
APP_NAME = "ShownXStore Bot"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # Set in hosting environment
OWNER_USERNAME = "@WhoIsShown"  # Owner handle (for reference)
OWNER_ID =  8984851474 # Numeric Telegram user ID
MONGODB_URI = os.getenv("MONGODB_URI", "")  # MongoDB Atlas connection string
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "shown_x_store")
BOT_USERNAME = ""  # Optional; auto-detected on startup
USER_LOG_CHANNEL_ID = 0  # 0 disables user activity logs
RICH_MESSAGES_ENABLED = True
CONCURRENT_UPDATES = 512
HEALTH_CHECK_PORT = 10000  # Fixed port; configure your hosting service to use this port
BOT_VERSION = "v18.0-ui"
_BOT_INSTANCE = None


def _validate_config() -> None:
    """Fail early with an actionable message if the top-level settings are unchanged."""
    missing = []
    if not BOT_TOKEN or "PASTE_YOUR_" in BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not isinstance(OWNER_ID, int) or OWNER_ID <= 0:
        missing.append("OWNER_ID (must be your numeric Telegram user ID)")
    if missing:
        raise RuntimeError(
            "Edit the EASY CONFIGURATION block at the top of this file. Set: "
            + ", ".join(missing)
        )


# ============================================================
# PREMIUM EMOJI + TEXT STYLE ENGINE (auto-applied to everything)
# ============================================================
import re as _pre_re
import html as _pre_html

_PREMIUM_EMOJI_IDS_1 = [
    "5967280668885913944", "5258476306152038031", "5213395028038132311", "5260342697075416641",
    "5258236805890710909", "5260450573768990626", "5429571366384842791", "5956561916573782596",
    "5870930636742595124", "5956561916573782596", "5258514780469075716", "5359719332542718652",
    "5463274047771000031", "5282964865349081926", "5418010521309815154", "5372917041193828849",
    "5870930636742595124", "5260379144167890225", "6280818246476111911", "6111547907393987376",
    "5199552030615558774", "6235403472741603087", "5384544226333711035", "6098159343281121498",
    "6319074379175043387", "5445355530111437729", "5258514780469075716", "6100129320225741245",
    "6100384016081361171", "6098236364929635183", "5453957997418004470", "5462921117423384478",
    "6280578093379754919", "5416081784641168838", "6100388225149310843", "5244837092042750681",
    "5258477770735885832", "5375464961822695044", "5359529383319084413", "5257974976094412956",
    "6201822626692734126", "5897850551156084824", "6005986106703613755", "6203998186541948045",
    "6278463693864838049", "5416081784641168838", "5213395028038132311", "6100258190719457801",
    "6100670735213139506", "6098125829651307984", "6219792052599660507", "5409008750893734809",
    "6269400956387987689", "5447203607294265305", "5453902265922376865", "5377599075237502153",
    "5915833712368424979", "5415722218569089767", "5197480146981906157", "5388846172951558229",
    "5305336095863485125", "5388941018714356665", "6319074379175043387", "5305603955793867793",
    "5280816565657300091",
]

_PREMIUM_EMOJI_LIST_1 = [
    "\u2709\ufe0f", "\U0001f512", "\u2705", "\u274c", "\u2b05\ufe0f", "\u27a1\ufe0f", "\U0001f50e",
    "\U0001f4c4", "\U0001f4ca", "\U0001f4c4",
    "\U0001f4c2", "\U0001f48e", "\U0001f635", "\U0001f49d", "\U0001f3ab", "\U0001f680", "\U0001f4ca",
    "\U0001f53c", "\U0001f4ac", "\U0001f451",
    "\U0001fa99", "\u2b50", "\U0001f381", "\U0001f4b0", "\U0001f48e",
    "\U0001f4e4", "\U0001f4c2", "\U0001f6e1", "\U0001f381", "\U0001f4e2", "\U0001f465", "\U0001f6e0",
    "\u2699\ufe0f", "\U0001f7e2", "\U0001f6ab", "\U0001f4c8",
    "\U0001f4c4", "\U0001f3ac", "\u2795", "\U0001f5bc", "\U0001f399", "\U0001f4d6", "\U0001f4f7",
    "\U0001f451", "\u2b50\ufe0f", "\U0001f7e2", "\u2705", "\U0001f534", "\U0001f7e2",
    "\U0001f389", "\U0001f525", "\U0001f3c6", "\U0001f947", "\U0001f948", "\U0001f949", "\U0001f39f",
    "\U0001f3b0", "\U0001f352", "\U0001f34b\u200d\U0001f7e9", "\U0001f347", "\U0001f349", "\U0001f34a",
    "\U0001f48e", "7\ufe0f\u20e3", "\U0001f3b2",
]

_PREMIUM_EMOJI_IDS_2 = [
    "5418010521309815154", "5258500400918587241", "5451732530048802485", "6332591195306334733",
    "6280368657889501500", "5888781182249738113", "6280648681167266267", "6111396350883010682",
    "5258205968025525531", "5444856076954520455", "5258134813302332906", "5350460637182993292",
    "5803057229909202251", "6280712659000107348", "5258331647358540449", "5870930744116776638",
    "6221832909389570589", "6098271033905650109", "5447203607294265305", "5453902265922376865",
    "6222239449518971912", "5458603043203327669", "6203974332293586380", "5260502250815513613",
    "6172537761552142514", "5280774071250872500", "5384490809825450636", "6278178593935728769",
    "6098271033905650109", "6323166881712709901", "6203957491726818885", "5846210329700217522",
    "5258476306152038031", "5258476306152038031", "6334528491844798409", "5462990652943904884",
    "6280289450102628695", "5197434882321567830", "5469641199348363998", "5445353829304387411",
    "5444856076954520455", "6280368657889501500", "6203998186541948045", "5188187560035234546",
    "6100670735213139506",
]

_PREMIUM_EMOJI_LIST_2 = [
    "\U0001f3ab", "\u270d\ufe0f", "\u23f3", "\U0001f51c",
    "\U0001f464", "\U0001f194", "\U0001f4c5", "\u26d3", "\U0001f4f8", "\U0001f9fe", "\U0001f4e6",
    "\U0001f3af", "\u267b\ufe0f", "\U0001f5d1", "\u270d\ufe0f", "\U0001f4cc", "\U0001f31f",
    "\U0001f947", "\U0001f948", "\U0001f949",
    "\u26a1\ufe0f", "\U0001f514", "\U0001f38a", "\U0001f973", "\U0001f340", "\U0001f37e", "\U0001f381",
    "\U0001f6e1", "\U0001f947", "\U0001f948",
    "\u2705", "\u274c", "\u26a0\ufe0f", "\U0001f512", "\U0001f513", "\U0001f477", "\U0001f634",
    "\U0001f4b0", "\U0001f4b5", "\u2b50\ufe0f", "\U0001f4b3", "\U0001f9fe",
    "\U0001f464", "\U0001f451", "\u26d4\ufe0f",
]

PREMIUM_EMOJI_MAP: dict[str, str] = {}
for _emj, _eid in list(zip(_PREMIUM_EMOJI_LIST_1, _PREMIUM_EMOJI_IDS_1)) + list(
    zip(_PREMIUM_EMOJI_LIST_2, _PREMIUM_EMOJI_IDS_2)
):
    PREMIUM_EMOJI_MAP.setdefault(_emj, _eid)
# also register the plain (no variation-selector) form of every emoji
for _emj, _eid in list(PREMIUM_EMOJI_MAP.items()):
    _plain = _emj.replace("\ufe0f", "")
    if _plain and _plain != _emj:
        PREMIUM_EMOJI_MAP.setdefault(_plain, _eid)
    PREMIUM_EMOJI_MAP.setdefault(_emj + "\ufe0f", _eid)


# ---- extra emojis found in bot text that had no premium id yet ----
_EXTRA_PREMIUM_ALIASES = {
    "\U0001f4c1": "\U0001f4c2",      # folder -> open folder
    "\U0001f3e0": "\U0001f4c2",      # house -> open folder
    "\U0001f4cb": "\U0001f9fe",      # clipboard -> receipt
    "\u2796": "\u26d4\ufe0f",         # minus -> no entry
    "\U0001f4dc": "\U0001f4c4",      # scroll -> page
    "\u2b07\ufe0f": "\U0001f4e4",     # down arrow -> inbox
    "\u2b07": "\U0001f4e4",
    "\U0001f4e5": "\U0001f4e4",      # inbox -> outbox
    "\U0001f4dd": "\u270d\ufe0f",     # memo -> writing hand
    "\u270f\ufe0f": "\u270d\ufe0f",
    "\u270f": "\u270d\ufe0f",
    "\U0001f4e1": "\U0001f4e2",      # satellite -> loudspeaker
    "\U0001f50d": "\U0001f50e",      # magnifier
    "\U0001f6a7": "\u26a0\ufe0f",     # construction -> warning
    "\u2754": "\U0001f4ac",          # question -> speech balloon
    "\U0001f3f7\ufe0f": "\U0001f3ab",  # label -> ticket
    "\U0001f3f7": "\U0001f3ab",
    "\U0001f517": "\u26d3",          # link -> chains
    "\U0001f522": "7\ufe0f\u20e3",    # numbers -> 7
    "\U0001f3b5": "\U0001f399",      # music -> mic
    "\U0001f39e\ufe0f": "\U0001f3ac",
    "\U0001f39e": "\U0001f3ac",
    "\U0001f3a5": "\U0001f3ac",      # camera -> clapper
    "\U0001f4e9": "\u2709\ufe0f",     # envelope w/ arrow -> envelope
    "\U0001f44b": "\U0001f464",      # wave -> person
    "\U0001f440": "\U0001f464",      # eyes -> person
    "\U0001f447": "\U0001f4cc",      # down finger -> pin
    "\U0001f552": "\u23f3",          # clock -> hourglass
    "\U0001f4b1": "\U0001f4b0",      # currency -> money bag
    "\U0001f504": "\u267b\ufe0f",     # refresh -> recycle
    "\U0001f34b": "\U0001f352",      # lemon -> cherries
    "\U0001f300": "\u26a1\ufe0f",     # cyclone -> zap
    "\U0001f622": "\U0001f635",      # cry -> dizzy
    "\U0001f511": "\U0001f512",      # key -> lock
    "\U0001f6d2": "\U0001f4b3",      # cart -> card
    "\U0001f4db": "\U0001f194",      # name badge -> id
}
for _src_emj, _ref in _EXTRA_PREMIUM_ALIASES.items():
    _rid = PREMIUM_EMOJI_MAP.get(_ref) or PREMIUM_EMOJI_MAP.get(_ref.replace("\ufe0f", ""))
    if _rid:
        PREMIUM_EMOJI_MAP.setdefault(_src_emj, _rid)
        PREMIUM_EMOJI_MAP.setdefault(_src_emj + "\ufe0f", _rid)
        PREMIUM_EMOJI_MAP.setdefault(_src_emj.replace("\ufe0f", ""), _rid)

# Buy Files uses these exact custom emoji IDs.  Keep the Unicode fallback
# only for Telegram button text; the button monkeypatch converts it to the
# custom icon before sending.
PREMIUM_EMOJI_MAP["📁"] = "5357315181649076022"
PREMIUM_EMOJI_MAP["🪙"] = "5377690785674175481"
PREMIUM_EMOJI_MAP["🆓"] = "5841267724285646096"
PREMIUM_EMOJI_MAP["🛍"] = "5350699789551935589"
PREMIUM_EMOJI_MAP["📁\ufe0f"] = "5357315181649076022"
PREMIUM_EMOJI_MAP["🪙\ufe0f"] = "5377690785674175481"
PREMIUM_EMOJI_MAP["🆓\ufe0f"] = "5841267724285646096"
PREMIUM_EMOJI_MAP["🛍\ufe0f"] = "5350699789551935589"
PREMIUM_EMOJI_MAP["➡️"] = "5325526651222652842"
PREMIUM_EMOJI_MAP["➡"] = "5325526651222652842"
# 💎 Gems + ⭐ Stars (paid currency) — exact custom emoji IDs requested.
GEM_EMOJI_ID = "5463349398677254406"
STAR_EMOJI_ID = "6235403472741603087"
for _k in ("💎", "💎\ufe0f"):
    PREMIUM_EMOJI_MAP[_k] = GEM_EMOJI_ID
for _k in ("⭐", "⭐\ufe0f", "\u2b50", "\u2b50\ufe0f"):
    PREMIUM_EMOJI_MAP[_k] = STAR_EMOJI_ID

_EMOJI_RE = _pre_re.compile(
    "|".join(_pre_re.escape(k) for k in sorted(PREMIUM_EMOJI_MAP, key=len, reverse=True))
)

# ---------------- text style: 𝗙ɪʀꜱᴛ ʟᴇᴛᴛᴇʀ ʙᴏʟᴅ, ʀᴇꜱᴛ ꜱᴍᴀʟʟ ᴄᴀᴩꜱ ----------------
_BOLD_UPPER = {chr(ord("A") + i): chr(0x1D5D4 + i) for i in range(26)}
_SMALL_CAPS = dict(
    zip(
        "abcdefghijklmnopqrstuvwxyz",
        ["\u1d00", "\u0299", "\u1d04", "\u1d05", "\u1d07", "\ua730", "\u0262", "\u029c", "\u026a",
         "\u1d0a", "\u1d0b", "\u029f", "\u1d0d", "\u0274", "\u1d0f", "\u1d29", "q", "\u0280",
         "\ua731", "\u1d1b", "\u1d1c", "\u1d20", "\u1d21", "x", "\u028f", "\u1d22"],
    )
)
_UNSTYLE = {}
_UNSTYLE.update({v: k for k, v in _SMALL_CAPS.items() if v != k})

_SKIP_RE = _pre_re.compile(
    r"(<[^>]+>|&[a-zA-Z#0-9]+;|https?://\S+|@[A-Za-z0-9_]+|/[a-z_]+)"
)
_WORD_RE = _pre_re.compile(r"[A-Za-z]+")


def _style_word(m: "_pre_re.Match[str]") -> str:
    w = m.group(0)
    out = []
    first = True
    for ch in w:
        if first and ch.isalpha():
            out.append(ch.upper())
            first = False
        else:
            out.append(_SMALL_CAPS.get(ch, ch))
    return "".join(out)


def stylize_text(text: str) -> str:
    """Apply the 𝗛ᴇʟʟᴏ Gᴜʏꜱ style, keeping html tags / links / commands intact."""
    if not text:
        return text
    parts = _SKIP_RE.split(text)
    out = []
    in_code = False
    for part in parts:
        if not part:
            continue
        if part.startswith("<"):
            tag = part.lower()
            if tag.startswith("<code") or tag.startswith("<pre"):
                in_code = True
            elif tag.startswith("</code") or tag.startswith("</pre"):
                in_code = False
            out.append(part)
        elif _SKIP_RE.fullmatch(part):
            out.append(part)
        elif in_code:
            out.append(part)
        else:
            out.append(_WORD_RE.sub(_style_word, part))
    return "".join(out)


def unstyle_text(text: str) -> str:
    """Reverse of stylize_text — used to route incoming keyboard button taps."""
    if not text:
        return text
    return "".join(_UNSTYLE.get(ch, ch) for ch in text)


def _wrap_emoji_segment(seg: str) -> str:
    return _EMOJI_RE.sub(
        lambda m: '<tg-emoji emoji-id="%s">%s</tg-emoji>'
        % (PREMIUM_EMOJI_MAP[m.group(0)], m.group(0)),
        seg,
    )


def premiumize_html(text: str) -> str:
    """Replace normal emoji with premium (custom) emoji inside HTML text.

    Skips content that is already inside a <tg-emoji ...>...</tg-emoji> tag
    so a manually-chosen emoji-id never gets silently overwritten by the
    PREMIUM_EMOJI_MAP lookup.
    """
    if not text:
        return text
    parts = _pre_re.split(r"(<tg-emoji[^>]*>.*?</tg-emoji>|<[^>]+>)", text)
    out = []
    in_code = 0
    for p in parts:
        if p.startswith("<tg-emoji") or p.startswith("<"):
            tag = p.lower()
            if tag.startswith(("<code", "<pre")):
                in_code += 1
            elif tag.startswith(("</code", "</pre")):
                in_code = max(0, in_code - 1)
            out.append(p)
        elif in_code:
            out.append(p)
        else:
            out.append(_wrap_emoji_segment(p))
    return "".join(out)


def beautify(text: str, parse_mode=None):
    """Stylize text + swap in premium emoji. Returns (text, parse_mode)."""
    if not text:
        return text, parse_mode
    if parse_mode is None:
        text = _pre_html.escape(text)
        parse_mode = ParseMode.HTML
    elif str(parse_mode).lower() not in ("html", "parsemode.html"):
        # markdown texts: style only, no custom-emoji tags
        return stylize_text(text), parse_mode
    # Keep outgoing HTML messages visually consistent with Telegram's blockquote style.
    styled = premiumize_html(stylize_text(text))
    if not styled.lstrip().startswith("<blockquote"):
        styled = f"<blockquote>{styled}</blockquote>"
    return styled, parse_mode


def _install_premium_style() -> None:
    """Monkeypatch the Bot + keyboard classes so every message/button is styled."""
    from telegram import Bot

    def _patch_text(name: str, field: str) -> None:
        original = getattr(Bot, name, None)
        if original is None or getattr(original, "_premium_patched", False):
            return

        async def wrapper(self, *args, __orig=original, __field=field, **kwargs):
            if __field in kwargs and isinstance(kwargs[__field], str):
                new_text, pm = beautify(kwargs[__field], kwargs.get("parse_mode"))
                kwargs[__field] = new_text
                kwargs["parse_mode"] = pm
            return await __orig(self, *args, **kwargs)

        wrapper._premium_patched = True  # type: ignore[attr-defined]
        setattr(Bot, name, wrapper)

    for _m in ("send_message", "edit_message_text"):
        _patch_text(_m, "text")
    for _m in (
        "send_photo", "send_document", "send_video", "send_audio", "send_voice",
        "send_animation", "send_video_note", "edit_message_caption", "copy_message",
    ):
        _patch_text(_m, "caption")

    # callback answers: plain text only (no html / custom emoji support)
    _orig_answer = Bot.answer_callback_query
    if not getattr(_orig_answer, "_premium_patched", False):
        async def _answer(self, *args, **kwargs):
            if isinstance(kwargs.get("text"), str):
                kwargs["text"] = stylize_text(kwargs["text"])
            elif args and isinstance(args[0], str) and len(args) > 1 and isinstance(args[1], str):
                args = (args[0], stylize_text(args[1])) + args[2:]
            return await _orig_answer(self, *args, **kwargs)

        _answer._premium_patched = True  # type: ignore[attr-defined]
        Bot.answer_callback_query = _answer  # type: ignore[assignment]

    # buttons: Bot API 10.x supports icon_custom_emoji_id on both button types.
    # If the installed python-telegram-bot is older, we silently keep the plain emoji.
    import inspect as _inspect

    for _cls in (InlineKeyboardButton, KeyboardButton):
        _orig_init = _cls.__init__
        if getattr(_orig_init, "_premium_patched", False):
            continue
        try:
            _supports_icon = "icon_custom_emoji_id" in _inspect.signature(_orig_init).parameters
        except (TypeError, ValueError):
            _supports_icon = False

        def _init(self, text=None, *args, __orig=_orig_init, __icon=_supports_icon, **kwargs):
            if text is None and isinstance(kwargs.get("text"), str):
                text = kwargs.pop("text")
            if isinstance(text, str):
                if __icon and "icon_custom_emoji_id" not in kwargs:
                    # Only a leading emoji is a Telegram button icon.  An
                    # emoji in the title/price area must stay in that
                    # position; extracting it here moved 🪙 away from
                    # ``File Name 🪙 1000`` to the button's far left.
                    leading_text = text.lstrip()
                    m = _EMOJI_RE.match(leading_text)
                    if m:
                        emoji = m.group(0)
                        kwargs["icon_custom_emoji_id"] = (
                            PREMIUM_EMOJI_MAP.get(emoji)
                            or PREMIUM_EMOJI_MAP.get(emoji.replace("\ufe0f", ""))
                        )
                        leading_offset = len(text) - len(leading_text)
                        end = leading_offset + m.end()
                        text = (text[:leading_offset] + text[end:]).strip()
                text = stylize_text(text)
            if text is None:
                return __orig(self, *args, **kwargs)
            return __orig(self, text, *args, **kwargs)

        _init._premium_patched = True  # type: ignore[attr-defined]
        _cls.__init__ = _init  # type: ignore[assignment]



async def _normalize_incoming(update, context) -> None:
    """Convert styled keyboard-button text back to plain text before routing."""
    msg = getattr(update, "effective_message", None)
    if msg is None or not getattr(msg, "text", None):
        return
    plain = unstyle_text(msg.text)
    routes = globals().get("TEXT_ROUTES") or {}
    if routes and plain not in routes:
        stripped = _EMOJI_RE.sub("", plain).strip().casefold()
        for key in routes:
            if _EMOJI_RE.sub("", key).strip().casefold() == stripped:
                plain = key
                break
    if plain != msg.text:
        try:
            with msg._unfrozen():
                msg.text = plain
        except Exception:
            try:
                object.__setattr__(msg, "text", plain)
            except Exception:
                pass


_install_premium_style()


# ============================================================
# SAME-MESSAGE EDIT ENGINE
# ------------------------------------------------------------
# Every inline-button screen calls ``query.edit_message_text``.  Telegram
# refuses that call when the message is a photo/video/GIF (it has a caption,
# not text) or a Rich Message, which is why screens used to delete + resend.
# This patch makes the call smart for ALL existing and new handlers:
#   • text message          -> editMessageText   (same message)
#   • photo/video/GIF/doc   -> editMessageCaption (same message, media stays)
#   • "message is not modified" -> silently ignored (double taps)
#   • truly uneditable (rich msg / too long caption / too old)
#                           -> delete + send fresh (last resort only)
# ============================================================
_CAPTION_SAFE_LIMIT = 900  # Telegram caption hard limit is 1024


def _visible_len(text: str) -> int:
    plain = _pre_re.sub(r"<[^>]+>", "", text or "")
    return len(_pre_html.unescape(plain))


def _msg_has_media(msg) -> bool:
    if msg is None:
        return False
    return any(
        getattr(msg, attr, None)
        for attr in ("photo", "video", "animation", "document", "audio", "voice")
    )


def _is_not_modified(exc: Exception) -> bool:
    return "not modified" in str(exc).lower()


def _plain_after_style(text: str, parse_mode) -> str | None:
    """What Telegram will show for ``text`` after our styling (tags removed).

    Used to detect that only the buttons changed (e.g. Buy Files page 1 -> 2),
    so we can edit just the keyboard and keep the very same message.
    """
    if text is None:
        return None
    pm = str(parse_mode).lower() if parse_mode is not None else None
    if pm is None:
        return stylize_text(text).strip()
    if pm in ("html", "parsemode.html"):
        styled = stylize_text(text)
        return _pre_html.unescape(_pre_re.sub(r"<[^>]+>", "", styled)).strip()
    return None  # markdown: don't guess


def _install_smart_edit() -> None:
    from telegram import CallbackQuery

    orig_edit_text = CallbackQuery.edit_message_text
    if getattr(orig_edit_text, "_smart_patched", False):
        return

    async def smart_edit_message_text(self, text=None, *args, **kwargs):
        if text is None:
            text = kwargs.pop("text", "")
        msg = self.message
        parse_mode = kwargs.get("parse_mode")
        reply_markup = kwargs.get("reply_markup")
        has_media = _msg_has_media(msg)

        # Pagination (Buy Files, My Purchases, lists...) usually changes only
        # the buttons. Editing just the keyboard can't fail on caption/entity
        # rules, so the same message is always kept.
        if msg is not None and reply_markup is not None:
            current = (msg.caption if has_media else msg.text) or ""
            new_plain = _plain_after_style(text, parse_mode)
            if new_plain is not None and new_plain == current.strip():
                try:
                    return await self.edit_message_reply_markup(reply_markup=reply_markup)
                except BadRequest as exc:
                    if _is_not_modified(exc):
                        return True
                    log.warning("Keyboard-only edit failed, trying full edit: %s", exc)

        if msg is not None and has_media:
            if _visible_len(text) <= _CAPTION_SAFE_LIMIT:
                try:
                    return await self.edit_message_caption(
                        caption=text, parse_mode=parse_mode, reply_markup=reply_markup,
                    )
                except BadRequest as exc:
                    if _is_not_modified(exc):
                        return True
                    log.warning("Caption edit failed, resending as new message: %s", exc)
        else:
            try:
                return await orig_edit_text(self, text, *args, **kwargs)
            except BadRequest as exc:
                if _is_not_modified(exc):
                    return True
                # A parse error would fail again on resend; deleting first
                # would just make the user's message disappear.
                if msg is None or "parse" in str(exc).lower():
                    raise
                log.warning("Text edit failed, resending as new message: %s", exc)

        # Last resort: the message can't be edited (Rich Message, caption
        # too long, too old...). Replace it so the button never looks dead.
        chat_id = getattr(msg, "chat_id", None) or self.from_user.id
        try:
            await msg.delete()
        except TelegramError:
            pass
        return await self.get_bot().send_message(
            chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup,
        )

    smart_edit_message_text._smart_patched = True  # type: ignore[attr-defined]
    CallbackQuery.edit_message_text = smart_edit_message_text  # type: ignore[assignment]


_install_smart_edit()
# ============================================================

# Telegram Bot API 10.1 Rich Message support.  Use the raw PTB request
# layer because older python-telegram-bot releases do not expose the new
# sendRichMessage method yet.


def _rich_media_binding(file_id: str, media_type: str):
    """Return the Rich HTML reference and InputRichMessageMedia payload."""
    media_type = (media_type or "").strip().lower()
    if media_type in {"gif", "mp4_animation"}:
        media_type = "animation"
    if media_type == "photo":
        return (
            "tg://photo?id=hero_media",
            {"id": "hero_media", "media": {"type": "photo", "media": file_id}},
        )
    if media_type in {"video", "animation"}:
        return (
            "tg://video?id=hero_media",
            {"id": "hero_media", "media": {"type": media_type, "media": file_id}},
        )
    return None, None


def _rich_slideshow_binding(slides: list[dict]):
    """Build a <tg-slideshow> Rich HTML block plus its InputRichMessageMedia
    bindings, for a swipeable multi-image welcome slideshow (Bot API 10.2).
    Each slide dict is {"file_id": ..., "type": "photo"|"video"|"animation"}.
    """
    if not slides:
        return "", []
    figures = []
    media = []
    for i, slide in enumerate(slides):
        media_type = (slide.get("type") or "photo").strip().lower()
        if media_type in {"gif", "mp4_animation"}:
            media_type = "animation"
        slide_id = f"slide{i}"
        tag = "video" if media_type in {"video", "animation"} else "img"
        figures.append(f'<figure><{tag} src="tg://{"video" if tag == "video" else "photo"}?id={slide_id}"/></figure>')
        media.append({"id": slide_id, "media": {"type": media_type, "media": slide["file_id"]}})
    html_block = "<tg-slideshow>" + "".join(figures) + "</tg-slideshow>"
    return html_block, media


async def _send_rich_message(bot, chat_id: int | str, rich_message: dict, reply_markup=None):
    post = getattr(bot, "_post", None)
    if post is None:
        raise RuntimeError("Installed python-telegram-bot has no request layer")
    payload = {"chat_id": chat_id, "rich_message": rich_message}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup.to_dict()
    result = await post("sendRichMessage", data=payload)
    if isinstance(result, dict) and result.get("ok") is False:
        raise TelegramError(result.get("description", "Telegram rejected Rich Message"))
    return result


async def _send_rich_message_draft(
    bot,
    chat_id: int | str,
    draft_id: int,
    rich_message: dict,
    can_stop: bool = True,
    keep_on_stop: bool = False,
):
    """Send an ephemeral Rich Message draft while a screen is loading."""
    post = getattr(bot, "_post", None)
    if post is None:
        raise RuntimeError("Installed python-telegram-bot has no request layer")
    payload = {
        "chat_id": chat_id,
        "draft_id": draft_id,
        "rich_message": rich_message,
        "can_stop": can_stop,
        "keep_on_stop": keep_on_stop,
    }
    result = await post("sendRichMessageDraft", data=payload)
    if isinstance(result, dict) and result.get("ok") is False:
        raise TelegramError(result.get("description", "Telegram rejected Rich Message draft"))
    return result


async def send_rich_draft_or_ignore(bot, chat_id: int | str, draft_id: int, rich_html: str):
    """Best-effort draft preview; normal bot flows must never depend on it."""
    if not RICH_MESSAGES_ENABLED:
        return None
    try:
        return await _send_rich_message_draft(
            bot,
            chat_id,
            draft_id,
            {"html": premiumize_html(rich_html)},
        )
    except (TelegramError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
        log.debug("Rich Message draft unavailable: %s", exc)
        return None


async def _send_legacy_media(
    bot,
    chat_id: int | str,
    file_id: str,
    media_type: str,
    caption: str,
    reply_markup=None,
):
    media_type = (media_type or "").strip().lower()
    if media_type in {"gif", "mp4_animation"}:
        media_type = "animation"
    if media_type == "photo":
        return await bot.send_photo(
            chat_id, file_id, caption=caption, parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    if media_type == "video":
        return await bot.send_video(
            chat_id, file_id, caption=caption, parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    if media_type == "animation":
        return await bot.send_animation(
            chat_id, file_id, caption=caption, parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
    return await bot.send_message(
        chat_id, caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


async def _send_legacy_media_group(bot, chat_id, slides: list[dict]):
    """Classic-client fallback for a multi-image welcome slideshow: send the
    images as a swipeable Telegram album (media group) before the text menu.
    Media groups cannot carry inline keyboards, so the caption/buttons still
    go out separately right after this."""
    if not slides:
        return None
    items = []
    for i, slide in enumerate(slides[:10]):  # Telegram album hard limit is 10
        media_type = (slide.get("type") or "photo").strip().lower()
        if media_type in {"gif", "mp4_animation"}:
            media_type = "animation"
        file_id = slide["file_id"]
        if media_type == "video":
            items.append(InputMediaVideo(file_id))
        elif media_type == "animation":
            # Telegram media groups don't support animations; send as video
            # so it still appears in the swipeable album.
            items.append(InputMediaVideo(file_id))
        else:
            items.append(InputMediaPhoto(file_id))
    try:
        return await bot.send_media_group(chat_id, items)
    except TelegramError as exc:
        log.warning("Welcome slideshow media group failed: %s", exc)
        return None


async def send_rich_or_fallback(
    bot,
    chat_id,
    rich_html,
    fallback_html,
    reply_markup=None,
    media_file_id="",
    media_type="",
    slides: list[dict] | None = None,
):
    normalized_media_type = (media_type or "").strip().lower()
    if normalized_media_type in {"gif", "mp4_animation"}:
        normalized_media_type = "animation"
    rich_payload = {"html": premiumize_html(rich_html)}

    if slides:
        # A multi-image slideshow takes priority over a single hero image.
        slideshow_html, slideshow_media = _rich_slideshow_binding(slides)
        rich_payload["html"] = slideshow_html + rich_payload["html"]
        rich_payload["media"] = slideshow_media
    else:
        media_ref, media_binding = (
            _rich_media_binding(media_file_id, media_type)
            if media_file_id else (None, None)
        )
        if media_ref and media_binding:
            if normalized_media_type == "photo":
                hero = f'<figure><img src="{media_ref}"/></figure>'
            else:
                hero = f'<figure><video src="{media_ref}"></video></figure>'
            rich_payload["html"] = hero + rich_payload["html"]
            rich_payload["media"] = [media_binding]

    if RICH_MESSAGES_ENABLED:
        try:
            return await _send_rich_message(
                bot, chat_id, rich_payload, reply_markup=reply_markup
            )
        except (TelegramError, AttributeError, TypeError, ValueError, RuntimeError) as exc:
            log.warning("Rich Message unavailable; using HTML fallback: %s", exc)

    if slides:
        await _send_legacy_media_group(bot, chat_id, slides)
        return await bot.send_message(
            chat_id, fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
    if media_file_id:
        return await _send_legacy_media(
            bot, chat_id, media_file_id, media_type, fallback_html, reply_markup
        )
    return await bot.send_message(
        chat_id, fallback_html, parse_mode=ParseMode.HTML, reply_markup=reply_markup
    )


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("NOBITA_X_STORE_BOT")

# Suppress noisy PTBUserWarning (per_message=False) logs from ConversationHandler.
import warnings as _warnings
from telegram.warnings import PTBUserWarning as _PTBUserWarning
_warnings.filterwarnings("ignore", category=_PTBUserWarning)

DEFAULT_COIN_PACKAGES = [
    {"coins": 100, "stars": 3},
    {"coins": 500, "stars": 15},
    {"coins": 900, "stars": 25},
    {"coins": 2000, "stars": 50},
    {"coins": 4500, "stars": 100},
]
# 💎 Gems are the PAID currency: only admins can give them or users buy them
# with Telegram Stars. No reward (daily bonus, referral, redeem, mystery...)
# ever pays out Gems.
DEFAULT_GEM_PACKAGES = [
    {"gems": 100, "stars": 100},
    {"gems": 200, "stars": 200},
    {"gems": 500, "stars": 500},
]

LEGACY_DEFAULT_COIN_PACKAGES = [
    {"coins": 100, "stars": 3},
    {"coins": 500, "stars": 15},
    {"coins": 1000, "stars": 28},
    {"coins": 2500, "stars": 65},
    {"coins": 5000, "stars": 120},
]

DEFAULT_SETTINGS = {
    "bot_name": APP_NAME,
    "referral_reward": "50",
    "daily_bonus": "25",
    "premium_daily_bonus_multiplier": "2",
    "premium_daily_bonus": "40",
    "support_username": "p4ime",
    "payment_username": "p4ime",
    "force_join": "1",
    "maintenance": "0",
    "star_rate": "30",
    "coin_packages": json.dumps(DEFAULT_COIN_PACKAGES),
    "gem_packages": json.dumps(DEFAULT_GEM_PACKAGES),
    "premium_pricing": json.dumps([
        {"days": 7, "price": 300},
        {"days": 30, "price": 900},
        {"days": 90, "price": 2200},
        {"days": 0, "price": 6000},
    ]),
    "coin_rate_bdt": "5",
    "bdt_payment_details": "bKash (Send Money): 01XXXXXXXXX\nNagad (Send Money): 01XXXXXXXXX",
    "mystery_box_pricing": json.dumps([
        {"tier": "random", "label": "🎁 Random File", "price": 100},
        {"tier": "rare", "label": "💎 Rare File", "price": 500},
        {"tier": "premium", "label": "👑 Premium Project", "price": 1000},
    ]),
    "referral_milestones": json.dumps([
        {"count": 5, "reward": 100},
        {"count": 10, "reward": 250},
        {"count": 25, "reward": 700},
        {"count": 50, "reward": 1500},
    ]),
    "streak_rewards": json.dumps([
        {"days": 3, "reward": 30},
        {"days": 7, "reward": 100},
        {"days": 14, "reward": 250},
        {"days": 30, "reward": 600},
    ]),
}

FILE_TYPE_ICON = {
    "document": "📄", "video": "🎬", "audio": "🎵", "photo": "🖼",
    "voice": "🎙", "animation": "🎞", "video_note": "🎥",
}

USE_CUSTOM_EMOJI = False
CUSTOM_EMOJI: dict[str, str] = {
}

DIVIDER = "───────────────────"


_db_lock = asyncio.Lock()


DUPLICATE_COOLDOWN_SECONDS = 0.6
FLOOD_WINDOW_SECONDS = 3.0
FLOOD_MAX_ACTIONS = 12

_last_action_by_key: dict[tuple[int, str], float] = {}
_recent_action_times: dict[int, list[float]] = {}

_user_action_locks: dict[int, asyncio.Lock] = {}
_user_action_locks_guard = asyncio.Lock()

# Home-menu messages pass through guard_user before their actual handler.
# Avoid doing the same SQLite reads/writes for every single button tap.
# Admin-panel callbacks do not normally use guard_user, which is why the
# slowdown is most visible on the user-facing home menu.
_guard_auth_cache: dict[int, tuple[float, bool, bool]] = {}
_guard_touch_cache: dict[int, float] = {}
_GUARD_AUTH_CACHE_TTL = 300.0  # was 15s — matched o.py's 5-min cache pattern, cut a blocking Atlas round trip from nearly every message
_GUARD_TOUCH_CACHE_TTL = 60.0


async def get_user_action_lock(user_id: int) -> asyncio.Lock:
    async with _user_action_locks_guard:
        lock = _user_action_locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            _user_action_locks[user_id] = lock
        return lock


async def group_restriction_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Silently discard every update received outside a private chat.

    The log chat/channel is output-only: log_user_activity() may send records
    there, but incoming messages from that chat must not activate bot handlers.
    """
    chat = update.effective_chat
    if chat is None or chat.type == "private":
        return
    # Do not reply, delete, react, or otherwise expose the bot in groups,
    # supergroups, channels, or the configured log destination.
    raise ApplicationHandlerStop


async def flood_guard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return

    if update.callback_query:
        action_id = update.callback_query.data or ""
    elif update.message and update.message.text:
        action_id = update.message.text
    else:
        return

    now = time.monotonic()

    # Keys include free text, so prune old entries to keep memory bounded.
    if len(_last_action_by_key) > 50_000:
        cutoff = now - 60
        for k in [k for k, t in _last_action_by_key.items() if t < cutoff]:
            _last_action_by_key.pop(k, None)
        for uid in [u for u, h in _recent_action_times.items() if not h or h[-1] < cutoff]:
            _recent_action_times.pop(uid, None)

    key = (user.id, action_id)
    last_same = _last_action_by_key.get(key, 0.0)
    _last_action_by_key[key] = now
    if now - last_same < DUPLICATE_COOLDOWN_SECONDS:
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except TelegramError:
                pass
        raise ApplicationHandlerStop

    history = _recent_action_times.setdefault(user.id, [])
    history[:] = [t for t in history if now - t < FLOOD_WINDOW_SECONDS]
    history.append(now)
    if len(history) > FLOOD_MAX_ACTIONS:
        if update.callback_query:
            try:
                await update.callback_query.answer("⏳ Please slow down a little.", show_alert=False)
            except TelegramError:
                pass
        raise ApplicationHandlerStop


class RateLimiter:
    def __init__(self, rate: float):
        self.interval = 1.0 / rate
        self._lock = asyncio.Lock()
        self._next_time = time.monotonic()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._next_time - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = time.monotonic()
            self._next_time = now + self.interval


TELEGRAM_SEND_LIMITER = RateLimiter(25)

_sqlite_db = None
_settings_cache: dict[str, str] = {}
_settings_cache_lock = asyncio.Lock()

# Short-lived cache of "user has passed the force-join check" results.
# guard_user() runs on every single message, and without this the bot would
# re-verify channel membership via the Telegram API on every message from
# every user — the single biggest source of per-message latency. A user's
# membership status rarely changes second to second, so it's safe to trust
# a recent "passed" result for a short window instead of re-checking live
# every time.
_force_join_pass_cache: dict[int, tuple[list, float]] = {}
_FORCE_JOIN_CACHE_TTL = 1800  # seconds (30 min) — a user who joined stays joined


class SQLiteRow(dict):
    """Dict row that also supports SQLite-style numeric indexing."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return self.get(key)


class _SQLiteRowCompat:
    Row = SQLiteRow


aiosqlite = _SQLiteRowCompat()


class ReturnDocument:
    BEFORE = False
    AFTER = True


class UpdateOne:
    def __init__(self, filter, update, upsert=False):
        self.filter = filter
        self.update = update
        self.upsert = upsert


class _WriteResult:
    def __init__(self, matched_count=0, modified_count=0, inserted_id=None):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.inserted_id = inserted_id


_MISSING = object()


def _path_get(doc, path, default=None):
    current = doc
    for part in str(path).split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _path_set(doc, path, value):
    parts = str(path).split(".")
    current = doc
    for part in parts[:-1]:
        if not isinstance(current.get(part), dict):
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


def _path_unset(doc, path):
    parts = str(path).split(".")
    current = doc
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict):
        current.pop(parts[-1], None)


def _expr_value(expr, doc):
    if isinstance(expr, str) and expr.startswith("$"):
        return _path_get(doc, expr[1:])
    if isinstance(expr, dict) and "$ifNull" in expr:
        args = expr["$ifNull"]
        val = _expr_value(args[0], doc) if args else None
        return val if val is not None else (_expr_value(args[1], doc) if len(args) > 1 else None)
    return expr


def _compare(left, op, right):
    if op == "$in":
        if isinstance(left, list):
            return any(item in right for item in left)
        return left in right
    if op == "$ne":
        return left is _MISSING or left != right
    if op == "$exists":
        return (left is not _MISSING) == bool(right)
    if op == "$regex":
        if left is _MISSING or left is None:
            return False
        flags = re.I if False else 0
        try:
            return re.search(str(right), str(left), flags) is not None
        except re.error:
            return False
    if op == "$type":
        if right == "number":
            return isinstance(left, (int, float)) and not isinstance(left, bool)
        if right == "string":
            return isinstance(left, str)
        if right == "null":
            return left is None
        return True
    if left is _MISSING:
        return op == "$lte" and right is None
    try:
        if op == "$gt": return left > right
        if op == "$gte": return left >= right
        if op == "$lt": return left < right
        if op == "$lte": return left <= right
    except (TypeError, ValueError):
        return False
    return False


def _matches(doc, query):
    if not query:
        return True
    for key, expected in query.items():
        if key == "$and":
            if not all(_matches(doc, q) for q in expected):
                return False
            continue
        if key == "$or":
            if not any(_matches(doc, q) for q in expected):
                return False
            continue
        if key == "$expr":
            expr = expected
            if isinstance(expr, dict) and "$lt" in expr:
                args = expr["$lt"]
                left = _expr_value(args[0], doc)
                right = _expr_value(args[1], doc)
                try:
                    if not left < right:
                        return False
                except (TypeError, ValueError):
                    return False
            continue
        actual = _path_get(doc, key, _MISSING)
        if isinstance(expected, dict) and any(str(k).startswith("$") for k in expected):
            for op, value in expected.items():
                if op == "$options":
                    continue
                if op == "$regex":
                    flags = re.I if "i" in str(expected.get("$options", "")).lower() else 0
                    if actual is _MISSING or actual is None:
                        return False
                    try:
                        if re.search(str(value), str(actual), flags) is None:
                            return False
                    except re.error:
                        return False
                elif not _compare(actual, op, value):
                    return False
        elif expected is None:
            if actual is not _MISSING and actual is not None:
                return False
        elif isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual is _MISSING or actual != expected:
            return False
    return True


def _apply_update(doc, update, inserting=False):
    result = dict(doc)
    if not any(str(k).startswith("$") for k in update):
        return dict(update)
    for field, value in update.get("$set", {}).items():
        _path_set(result, field, value)
    if inserting:
        for field, value in update.get("$setOnInsert", {}).items():
            if _path_get(result, field, _MISSING) is _MISSING:
                _path_set(result, field, value)
    for field, amount in update.get("$inc", {}).items():
        current = _path_get(result, field, 0)
        if current is None:
            current = 0
        _path_set(result, field, current + amount)
    for field, value in update.get("$max", {}).items():
        current = _path_get(result, field, _MISSING)
        if current is _MISSING or current is None or current < value:
            _path_set(result, field, value)
    for field in update.get("$unset", {}):
        _path_unset(result, field)
    return result


def _apply_projection(doc, projection):
    if not projection:
        return dict(doc)
    includes = {k for k, v in projection.items() if v and k != "_id"}
    excludes = {k for k, v in projection.items() if not v}
    if includes:
        out = {k: _path_get(doc, k) for k in includes if _path_get(doc, k, _MISSING) is not _MISSING}
        if projection.get("_id", 1) and "_id" in doc:
            out["_id"] = doc["_id"]
    else:
        out = dict(doc)
    for key in excludes:
        _path_unset(out, key)
    return out


class LocalCursor:
    def __init__(self, loader):
        self._loader = loader
        self._sort_spec = []
        self._skip = 0
        self._limit = 0

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, str):
            self._sort_spec = [(key_or_list, direction or 1)]
        else:
            self._sort_spec = list(key_or_list)
        return self

    def skip(self, count):
        self._skip = max(0, int(count or 0))
        return self

    def limit(self, count):
        self._limit = int(count or 0)
        return self

    async def to_list(self, length=None):
        rows = await self._loader()
        for key, direction in reversed(self._sort_spec):
            rows.sort(
                key=lambda d: (_path_get(d, key, None) is None, _path_get(d, key, None)),
                reverse=int(direction) < 0,
            )
        if self._skip:
            rows = rows[self._skip:]
        lim = self._limit if self._limit > 0 else None
        if length is not None:
            lim = min(lim, length) if lim is not None else length
        if lim is not None:
            rows = rows[:lim]
        return rows

    def __aiter__(self):
        async def iterate():
            for row in await self.to_list():
                yield row
        return iterate()


class MongoCursor:
    """Adapter preserving the bot's async cursor API over Motor cursors."""
    def __init__(self, cursor):
        self.cursor = cursor

    def sort(self, key_or_list, direction=None):
        if isinstance(key_or_list, str):
            self.cursor = self.cursor.sort(key_or_list, direction if direction is not None else 1)
        else:
            self.cursor = self.cursor.sort(key_or_list)
        return self

    def skip(self, count):
        self.cursor = self.cursor.skip(max(0, int(count or 0)))
        return self

    def limit(self, count):
        self.cursor = self.cursor.limit(int(count or 0))
        return self

    async def to_list(self, length=None):
        return await self.cursor.to_list(length=length)

    def __aiter__(self):
        return self.cursor.__aiter__()


class MongoCollection:
    """Compatibility wrapper over a real MongoDB collection."""
    def __init__(self, database, name):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError("Invalid MongoDB collection name")
        self.database = database
        self.name = name
        self.collection = database.database[name]

    def find(self, query=None, projection=None):
        return MongoCursor(self.collection.find(query or {}, projection))

    async def find_one(self, query=None, projection=None, sort=None):
        return await self.collection.find_one(query or {}, projection, sort=sort)

    async def insert_one(self, document):
        return await self.collection.insert_one(dict(document))

    async def insert_many(self, documents):
        return await self.collection.insert_many([dict(d) for d in documents])

    async def update_one(self, query, update, upsert=False):
        return await self.collection.update_one(query or {}, update, upsert=upsert)

    async def update_many(self, query, update, upsert=False):
        return await self.collection.update_many(query or {}, update, upsert=upsert)

    async def find_one_and_update(self, query, update, upsert=False,
                                  return_document=ReturnDocument.BEFORE,
                                  projection=None, sort=None, **kwargs):
        from pymongo import ReturnDocument as MongoReturnDocument
        rd = MongoReturnDocument.AFTER if bool(return_document) else MongoReturnDocument.BEFORE
        return await self.collection.find_one_and_update(
            query or {}, update, upsert=upsert, return_document=rd,
            projection=projection, sort=sort, **kwargs
        )

    async def delete_many(self, query=None):
        return await self.collection.delete_many(query or {})

    async def count_documents(self, query=None):
        return await self.collection.count_documents(query or {})

    def aggregate(self, pipeline):
        return MongoCursor(self.collection.aggregate(pipeline))

    async def create_index(self, spec, unique=False, **kwargs):
        if isinstance(spec, str):
            spec = [(spec, 1)]
        return await self.collection.create_index(spec, unique=unique, **kwargs)

    async def bulk_write(self, operations, ordered=True):
        from pymongo import UpdateOne as MongoUpdateOne
        ops = [MongoUpdateOne(op.filter, op.update, upsert=op.upsert) for op in operations]
        if not ops:
            return _WriteResult()
        return await self.collection.bulk_write(ops, ordered=ordered)


class MongoDatabase:
    def __init__(self, uri, database_name):
        if not uri:
            raise RuntimeError("Set MONGODB_URI in your hosting environment.")
        if not database_name:
            raise RuntimeError("Set MONGODB_DATABASE in your hosting environment.")
        self.uri = uri
        self.database_name = database_name
        self.client = None
        self.database = None

    async def open(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        self.client = AsyncIOMotorClient(self.uri, serverSelectionTimeoutMS=10000)
        self.database = self.client[self.database_name]
        await self.client.admin.command("ping")

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def __getitem__(self, name):
        return MongoCollection(self, name)

    async def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.database = None


class SQLiteCursor:
    def __init__(self, rows):
        self.rows = rows
        self.index = 0

    async def fetchone(self):
        if self.index >= len(self.rows):
            return None
        row = self.rows[self.index]
        self.index += 1
        return row

    async def fetchall(self):
        rows = self.rows[self.index:]
        self.index = len(self.rows)
        return rows



def _value(token, params, pos):
    token = token.strip()
    if token == "?":
        return params[pos[0]]
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    try:
        return int(token)
    except ValueError:
        return token


def _conditions(where, params):
    if not where:
        return {}
    pos = [0]
    clauses = re.split(r"\s+AND\s+", where, flags=re.I)
    parts = []
    for clause in clauses:
        clause = clause.strip().strip("()")
        # Support the OR expression used by premium statistics as well as
        # the original AND-only queries.  The previous adapter treated the
        # whole "a=1 OR b>?" text as one value, returning incorrect totals.
        alternatives = re.split(r"\s+OR\s+", clause, flags=re.I)
        alternative_docs = []
        for alternative in alternatives:
            alternative = alternative.strip().strip("()")
            in_match = re.match(r"([\w.]+)\s+IN\s*\((.*?)\)", alternative, re.I)
            if in_match:
                field = in_match.group(1).split(".")[-1]
                values = []
                for token in in_match.group(2).split(","):
                    values.append(_value(token, params, pos))
                    if token.strip() == "?":
                        pos[0] += 1
                alternative_docs.append({field: {"$in": values}})
                continue
            m = re.match(r"([\w.]+)\s+IS\s+(NOT\s+)?NULL", alternative, re.I)
            if m:
                alternative_docs.append({
                    m.group(1).split(".")[-1]: {"$ne": None} if m.group(2) else None
                })
                continue
            # SQLite queries in this file use both ``field=?`` and
            # ``field = ?`` forms.  Requiring spaces here silently discarded
            # every WHERE clause in the SQLite compatibility layer, so buttons
            # repeatedly returned the first document in a collection.
            m = re.match(r"([\w.]+)\s*(LIKE|!=|<>|>=|<=|=|>|<)\s*(.+)", alternative, re.I)
            if not m:
                continue
            field, op, raw = m.groups()
            field = field.split(".")[-1]
            val = _value(raw, params, pos)
            if raw.strip() == "?":
                pos[0] += 1
            if op.upper() == "LIKE":
                alternative_docs.append({
                    field: {"$regex": re.escape(str(val)).replace("%", ".*"), "$options": "i"}
                })
            else:
                alternative_docs.append({
                    field: {"=": val, "!=": {"$ne": val}, "<>": {"$ne": val},
                            ">": {"$gt": val}, "<": {"$lt": val},
                            ">=": {"$gte": val}, "<=": {"$lte": val}}[op]
                })
        if len(alternative_docs) == 1:
            parts.append(alternative_docs[0])
        elif alternative_docs:
            parts.append({"$or": alternative_docs})
    if len(parts) == 1:
        return parts[0]
    return {"$and": parts} if parts else {}



class SQLiteCompatConnection:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def commit(self):
        return None

    async def executescript(self, script):
        return None

    async def execute(self, sql, params=()):
        sql = " ".join(str(sql).split())
        params = tuple(params or ())
        command = sql.split()[0].upper()
        if command == "ALTER":
            return SQLiteCursor([])
        if command == "SELECT":
            return await self._select(sql, params)
        if command == "INSERT":
            return await self._insert(sql, params)
        if command == "UPDATE":
            return await self._update(sql, params)
        if command == "DELETE":
            return await self._delete(sql, params)
        return SQLiteCursor([])

    async def _select(self, sql, params):
        if re.search(r"last_insert_rowid", sql, re.I):
            return SQLiteCursor([SQLiteRow({"last_insert_rowid()": getattr(self, "last_id", 0)})])
        m = re.match(
            r"SELECT (.+?) FROM (\w+)"
            r"(?:\s+(?!WHERE\b|ORDER\b|LIMIT\b|OFFSET\b|JOIN\b|GROUP\b)(\w+))?(.*)",
            sql, re.I,
        )
        if not m:
            return SQLiteCursor([])
        fields, table, _alias, tail = m.groups()
        coll = _sqlite_db[table]
        where_m = re.search(r"\bWHERE\b (.*?)(?=\s+ORDER BY|\s+LIMIT|\s+OFFSET|$)", tail, re.I)
        where = _conditions(where_m.group(1), params) if where_m else {}
        # COUNT queries do not need to materialise every document.  This is
        # especially important for the admin statistics screen.
        if ("COUNT(" in fields.upper() and not re.search(r"\bJOIN\b|\bGROUP BY\b", tail, re.I)):
            count = await coll.count_documents(where)
            return SQLiteCursor([SQLiteRow({fields: count})])
        # Handle the one join used by purchase history.
        join = re.search(r"JOIN\s+(\w+)\s+(\w+)\s+ON\s+([\w.]+)\s*=\s*([\w.]+)", tail, re.I)
        group_m = re.search(r"GROUP BY\s+([\w.]+)", tail, re.I)
        order = re.search(r"ORDER BY\s+([\w.]+)(?:\s+(ASC|DESC))?", tail, re.I)
        offset_m = re.search(r"OFFSET\s+(\?|\d+)", tail, re.I)
        limit_m = re.search(r"LIMIT\s+(\?|\d+)", tail, re.I)
        is_random = "ORDER BY RANDOM()" in tail.upper()
        # Fast path: plain SELECT (no JOIN/GROUP BY) can push sort, skip and
        # limit down to SQLite instead of pulling every matching document
        # into Python first. This is the hot path for paginated screens
        # (file lists, purchase history, top files) and avoids transferring
        # the whole collection on every button press.
        #
        # ORDER BY RANDOM() gets its own fast path using SQLite's native
        # $sample aggregation stage, which picks random documents on the
        # server side instead of loading the entire collection into Python
        # and shuffling it there (the old behaviour did a full collection
        # scan + transfer for something like "pick 1 random file").
        if not join and not group_m and is_random:
            lim_val = 1
            if limit_m:
                lim_val = int(_value(
                    limit_m.group(1), params,
                    [max(0, len(params) - 1)],
                ))
            pipeline = []
            if where:
                pipeline.append({"$match": where})
            pipeline.append({"$sample": {"size": max(1, lim_val)}})
            docs = await coll.aggregate(pipeline).to_list(length=None)
            selected = []
            field_parts = [x.strip() for x in fields.split(",")]
            includes_all = fields.strip() == "*" or any(
                re.fullmatch(r"\w+\.\*", part) for part in field_parts
            )
            names = [
                part.split()[-1].split(".")[-1]
                for part in field_parts
                if not re.fullmatch(r"(?:\w+\.)?\*", part)
            ]
            for d in docs:
                row = {k: v for k, v in d.items() if k != "_id"} if includes_all else {}
                for name in names:
                    row[name] = d.get(name)
                selected.append(SQLiteRow(row))
            return SQLiteCursor(selected)
        if not join and not group_m and not is_random:
            cursor = coll.find(where)
            if order:
                key, direction = order.groups()
                key = key.split(".")[-1]
                cursor = cursor.sort(key, -1 if (direction or "").upper() == "DESC" else 1)
            off_val = None
            if offset_m:
                off_val = int(_value(offset_m.group(1), params, [len(params) - 1]))
                cursor = cursor.skip(off_val)
            if limit_m:
                lim_val = int(_value(
                    limit_m.group(1), params,
                    [max(0, len(params) - 2 if offset_m else len(params) - 1)],
                ))
                cursor = cursor.limit(lim_val)
            docs = await cursor.to_list(length=None)
            if "SUM(" in fields.upper():
                field = re.search(r"SUM\((?:\w+\.)?(\w+)\)", fields, re.I).group(1)
                val = sum((d.get(field) or 0) for d in docs)
                return SQLiteCursor([SQLiteRow({fields: val})])
            selected = []
            field_parts = [x.strip() for x in fields.split(",")]
            includes_all = fields.strip() == "*" or any(
                re.fullmatch(r"\w+\.\*", part) for part in field_parts
            )
            names = [
                part.split()[-1].split(".")[-1]
                for part in field_parts
                if not re.fullmatch(r"(?:\w+\.)?\*", part)
            ]
            for d in docs:
                row = {k: v for k, v in d.items() if k != "_id"} if includes_all else {}
                for name in names:
                    row[name] = d.get(name)
                selected.append(SQLiteRow(row))
            return SQLiteCursor(selected)
        # GROUP BY (no JOIN) gets its own fast path using SQLite's native
        # aggregation pipeline ($group + $sort + $limit run on the server).
        # The old behaviour pulled the entire collection into Python just to
        # count-and-group it locally — expensive for a frequently-clicked
        # screen like the referral leaderboard as the collection grows.
        if not join and group_m:
            group_field = group_m.group(1).split(".")[-1]
            count_alias = re.search(r"COUNT\(\*\)\s+AS\s+(\w+)", fields, re.I)
            alias = count_alias.group(1) if count_alias else "COUNT(*)"
            pipeline = []
            if where:
                pipeline.append({"$match": where})
            pipeline.append({"$group": {"_id": f"${group_field}", "_count": {"$sum": 1}}})
            if order:
                key, direction = order.groups()
                key = key.split(".")[-1]
                sort_key = "_count" if key.lower() in (alias.lower(), "cnt") else "_id"
                pipeline.append({"$sort": {sort_key: -1 if (direction or "").upper() == "DESC" else 1}})
            if limit_m:
                lim_val = int(_value(
                    limit_m.group(1), params,
                    [max(0, len(params) - 1)],
                ))
                pipeline.append({"$limit": lim_val})
            docs = await coll.aggregate(pipeline).to_list(length=None)
            return SQLiteCursor([
                SQLiteRow({group_field: d["_id"], alias: d["_count"]})
                for d in docs
            ])
        docs = await coll.find(where).to_list(length=None)
        if join:
            other, alias, left, right = join.groups()
            other_docs = await _sqlite_db[other].find({}).to_list(length=None)
            lk, rk = left.split(".")[-1], right.split(".")[-1]
            docs = [SQLiteRow({**a, **{f"{k}": v for k, v in b.items() if k not in a}})
                    for a in docs for b in other_docs if a.get(lk) == b.get(rk)]
        if group_m:
            group_field = group_m.group(1).split(".")[-1]
            count_alias = re.search(r"COUNT\(\*\)\s+AS\s+(\w+)", fields, re.I)
            alias = count_alias.group(1) if count_alias else "COUNT(*)"
            grouped = {}
            for doc in docs:
                grouped.setdefault(doc.get(group_field), 0)
                grouped[doc.get(group_field)] += 1
            return SQLiteCursor([
                SQLiteRow({group_field: value, alias: count})
                for value, count in grouped.items()
            ])
        if "COUNT(" in fields.upper() or "SUM(" in fields.upper():
            if "COUNT" in fields.upper():
                val = len(docs)
            else:
                field = re.search(r"SUM\((?:\w+\.)?(\w+)\)", fields, re.I).group(1)
                val = sum((d.get(field) or 0) for d in docs)
            return SQLiteCursor([SQLiteRow({fields: val})])
        if is_random:
            random.shuffle(docs)
        if order:
            key, direction = order.groups()
            key = key.split(".")[-1]
            if key.upper() != "RANDOM":
                docs.sort(key=lambda d: d.get(key) or 0, reverse=(direction or "").upper() == "DESC")
        # LIMIT precedes OFFSET in all existing queries; consume the final params.
        if offset_m:
            off = _value(offset_m.group(1), params, [len(params)-1])
            docs = docs[int(off):]
        if limit_m:
            limit = _value(limit_m.group(1), params, [max(0, len(params)-2 if offset_m else len(params)-1)])
            docs = docs[:int(limit)]
        selected = []
        field_parts = [x.strip() for x in fields.split(",")]
        includes_all = fields.strip() == "*" or any(
            re.fullmatch(r"\w+\.\*", part) for part in field_parts
        )
        names = [
            part.split()[-1].split(".")[-1]
            for part in field_parts
            if not re.fullmatch(r"(?:\w+\.)?\*", part)
        ]
        for d in docs:
            row = {k: v for k, v in d.items() if k != "_id"} if includes_all else {}
            for name in names:
                row[name] = d.get(name)
            selected.append(SQLiteRow(row))
        return SQLiteCursor(selected)

    async def _insert(self, sql, params):
        m = re.search(r"INTO\s+(\w+)\s*\((.*?)\)\s*VALUES\s*\((.*?)\)", sql, re.I)
        if not m:
            return SQLiteCursor([])
        table, columns, values = m.groups()
        vals, pos = [], [0]
        for token in values.split(","):
            vals.append(_value(token, params, pos))
            if token.strip() == "?": pos[0] += 1
        doc = dict(zip([c.strip() for c in columns.split(",")], vals))
        if table == "files":
            # SQLite supplied these defaults through the schema. SQLite is
            # schemaless, so missing defaults would hide new files from the
            # ``WHERE is_deleted=0`` Buy Files query.
            doc.setdefault("is_deleted", 0)
            doc.setdefault("downloads_count", 0)
            doc.setdefault("featured", 0)
            doc.setdefault("mystery_tier", None)
        elif table == "redeems":
            # These columns had SQLite defaults before the SQLite adapter was
            # introduced. Older/newly-created codes may omit them otherwise,
            # making the redeem handler compare None with the usage limit.
            doc.setdefault("used_count", 0)
            doc.setdefault("expiry_date", None)
            doc.setdefault("status", "active")
            doc.setdefault("source", "admin")
        id_fields = {"files":"file_pk","transactions":"tx_id","payments":"payment_id",
                     "redeem_uses":"id","referrals":"id","force_channels":"id",
                     "downloads":"id","purchases":"id","admin_logs":"log_id",
                     "file_requests":"request_id"}
        pk = id_fields.get(table)
        if pk and pk not in doc:
            doc[pk] = await _next_seq(table, pk)
        conflict = re.search(r"ON CONFLICT\((\w+)\).*?DO UPDATE SET (.*)", sql, re.I)
        if conflict:
            key = conflict.group(1)
            await _sqlite_db[table].update_one({key: doc.get(key)}, {"$set": doc}, upsert=True)
        elif "OR IGNORE" in sql.upper() or re.search(r"ON CONFLICT\(\w+\)\s+DO NOTHING", sql, re.I):
            key = re.search(r"ON CONFLICT\((\w+)\)", sql, re.I)
            if key:
                key = key.group(1)
            else:
                key = next((k for k in ("user_id", "code", "key") if k in doc), "_id")
            await _sqlite_db[table].update_one({key: doc.get(key)},
                                               {"$setOnInsert": doc}, upsert=True)
        else:
            await _sqlite_db[table].insert_one(doc)
        self.last_id = doc.get(pk, 0) if pk else 0
        return SQLiteCursor([])

    async def _update(self, sql, params):
        m = re.match(r"UPDATE\s+(\w+)\s+SET\s+(.*?)\s+WHERE\s+(.*)", sql, re.I)
        if not m: return SQLiteCursor([])
        table, assignments, where = m.groups()
        pos = [0]; updates = {}
        for item in assignments.split(","):
            field, expr = item.split("=", 1); field = field.strip()
            expr = expr.strip()
            inc = re.match(rf"{re.escape(field)}\s*([+-])\s*(\?|\d+)", expr, re.I)
            if inc:
                val = _value(inc.group(2), params, pos)
                if inc.group(2) == "?": pos[0] += 1
                updates[field] = {"$inc": val if inc.group(1) == "+" else -val}
            else:
                updates[field] = _value(expr, params, pos)
                if expr == "?": pos[0] += 1
        # SET placeholders come before WHERE placeholders in UPDATE queries.
        # Keep the parameter positions aligned with the original SQL call.
        filt = _conditions(where, params[pos[0]:])
        for field, value in updates.items():
            if isinstance(value, dict) and "$inc" in value:
                await _sqlite_db[table].update_many(filt, {"$inc": {field: value["$inc"]}})
            else:
                await _sqlite_db[table].update_many(filt, {"$set": {field: value}})
        return SQLiteCursor([])

    async def _delete(self, sql, params):
        m = re.match(r"DELETE FROM\s+(\w+)(?:\s+WHERE\s+(.*))?", sql, re.I)
        if m: await _sqlite_db[m.group(1)].delete_many(_conditions(m.group(2), params))
        return SQLiteCursor([])



def db_conn():
    return SQLiteCompatConnection()


async def init_db_pool() -> None:
    return None


async def close_db_pool() -> None:
    if _sqlite_db:
        await _sqlite_db.close()


_NUMERIC_SETTING_KEYS = {
    "referral_reward", "premium_daily_bonus_multiplier", "premium_daily_bonus",
    "star_rate", "coin_rate_bdt", "daily_bonus",
}
_JSON_SETTING_KEYS = {
    "coin_packages", "gem_packages", "premium_pricing", "mystery_box_pricing",
    "streak_rewards", "referral_milestones",
}


async def _repair_corrupt_settings() -> None:
    """One-time startup sanity check: if a settings value in the DB doesn't
    match its expected type (e.g. text landed in a numeric/JSON field due to
    a bad migration), reset it back to the known-good default instead of
    letting the bot crash on every use."""
    async for doc in _sqlite_db.settings.find({}):
        key, value = doc.get("key"), doc.get("value")
        default = DEFAULT_SETTINGS.get(key)
        if default is None:
            continue
        broken = False
        if key in _NUMERIC_SETTING_KEYS:
            try:
                float(value)
            except (TypeError, ValueError):
                broken = True
        elif key in _JSON_SETTING_KEYS:
            try:
                parsed = json.loads(value) if value else None
                # An empty list/dict where the default has real entries means
                # the pricing/rewards data itself is missing, not just malformed.
                if parsed in (None, [], {}) and default not in ("[]", "{}"):
                    broken = True
            except (TypeError, ValueError, json.JSONDecodeError):
                broken = True
        if broken:
            log.warning("Repairing corrupt setting %r (was %r) -> default %r", key, value, default)
            await _sqlite_db.settings.update_one({"key": key}, {"$set": {"value": default}})


async def _repair_file_ids() -> None:
    """Give every file one stable, unique numeric id.

    The SQL compatibility layer generates IDs from the counters collection.
    Imported/duplicated documents could therefore receive the same
    ``file_pk``; every inline button then opened whichever duplicate SQLite
    returned first.  Keep the first existing id and assign new ids to later
    duplicates so newly rendered buttons always identify the clicked file.
    """
    # Backfill fields that the former SQLite schema supplied through DEFAULT clauses.
    await _sqlite_db.files.update_many(
        {"is_deleted": {"$exists": False}}, {"$set": {"is_deleted": 0}}
    )
    await _sqlite_db.files.update_many(
        {"downloads_count": {"$exists": False}}, {"$set": {"downloads_count": 0}}
    )
    await _sqlite_db.files.update_many(
        {"featured": {"$exists": False}}, {"$set": {"featured": 0}}
    )
    await _sqlite_db.files.update_many(
        {"mystery_tier": {"$exists": False}}, {"$set": {"mystery_tier": None}}
    )
    files = await _sqlite_db.files.find(
        {}, {"_id": 1, "file_pk": 1}
    ).sort([("file_pk", 1), ("_id", 1)]).to_list(length=None)
    used: set[int] = set()
    next_id = 1
    repairs = 0
    for doc in files:
        raw_id = doc.get("file_pk")
        try:
            file_id = int(raw_id)
        except (TypeError, ValueError):
            file_id = 0
        if file_id > 0 and file_id not in used:
            if not isinstance(raw_id, int) or isinstance(raw_id, bool):
                await _sqlite_db.files.update_one(
                    {"_id": doc["_id"]}, {"$set": {"file_pk": file_id}}
                )
            used.add(file_id)
            next_id = max(next_id, file_id + 1)
            continue
        while next_id in used:
            next_id += 1
        await _sqlite_db.files.update_one(
            {"_id": doc["_id"]}, {"$set": {"file_pk": next_id}}
        )
        used.add(next_id)
        next_id += 1
        repairs += 1
    if repairs:
        log.warning("Repaired %d duplicate/missing file id(s)", repairs)


async def init_db() -> None:
    global _sqlite_db
    _sqlite_db = MongoDatabase(MONGODB_URI, MONGODB_DATABASE)
    await _sqlite_db.open()
    # Create MongoDB indexes used by common lookups and unique business records.
    indexes = {
        "settings": ["key"],
        "users": ["username"],
        "admins": ["user_id"],
        "files": ["file_pk", "is_deleted", "file_name"],
        "purchases": ["user_id", "file_pk"],
        "redeems": ["code", "status"],
        "redeem_uses": ["code", "user_id"],
        "referrals": ["referrer_id", "new_user_id"],
        "transactions": ["user_id", "timestamp"],
        "payments": ["payment_id", "user_id", "status"],
        "force_channels": ["username"],
        "force_join_requests": ["chat_id", "user_id", "status"],
    }
    for collection, fields in indexes.items():
        for field in fields:
            try:
                await _sqlite_db[collection].create_index(field)
            except Exception:
                log.warning("Could not create MongoDB index %s.%s", collection, field)
    for collection, spec in (
        ("files", [("is_deleted", 1), ("file_pk", -1)]),
        ("payments", [("status", 1), ("payment_id", -1)]),
        ("force_join_requests", [("chat_id", 1), ("user_id", 1)]),
    ):
        try:
            await _sqlite_db[collection].create_index(spec)
        except Exception:
            log.warning("Could not create MongoDB compound index on %s", collection)
    for collection, spec in (
        ("users", [("user_id", 1)]),
        ("wallet", [("user_id", 1)]),
        ("premium", [("user_id", 1)]),
        ("redeem_uses", [("code", 1), ("user_id", 1)]),
        ("purchases", [("user_id", 1), ("file_pk", 1)]),
        ("referrals", [("new_user_id", 1)]),
        ("redeems", [("code", 1)]),
    ):
        try:
            await _sqlite_db[collection].create_index(spec, unique=True)
        except Exception:
            log.warning("Could not create MongoDB unique index on %s", collection)
    await _repair_file_ids()
    for k, v in DEFAULT_SETTINGS.items():
        await _sqlite_db.settings.update_one({"key": k}, {"$setOnInsert": {"key": k, "value": v}}, upsert=True)
    coin_packages_row = await _sqlite_db.settings.find_one(
        {"key": "coin_packages"}, {"value": 1, "_id": 0}
    )
    try:
        stored_coin_packages = json.loads(coin_packages_row.get("value", "[]"))
    except (AttributeError, TypeError, ValueError, json.JSONDecodeError):
        stored_coin_packages = None
    if stored_coin_packages == LEGACY_DEFAULT_COIN_PACKAGES:
        await _sqlite_db.settings.update_one(
            {"key": "coin_packages"},
            {"$set": {"value": json.dumps(DEFAULT_COIN_PACKAGES)}},
        )
    await _repair_corrupt_settings()
    if OWNER_ID > 0:
        await _sqlite_db.admins.update_one(
            {"user_id": OWNER_ID},
            {"$setOnInsert": {"user_id": OWNER_ID, "added_date": datetime.utcnow().isoformat(), "role": "owner"}},
            upsert=True,
        )
    log.info("SQLite database ready: %s", _sqlite_db.path)



async def get_setting(key: str, default: str = "") -> str:
    # Settings are read on almost every screen.  Keep a process-local cache
    # so one Telegram click does not cause several round trips to Atlas.
    async with _settings_cache_lock:
        if key in _settings_cache:
            value = _settings_cache[key]
            return value if value not in (None, "") else default
        row = await _sqlite_db.settings.find_one({"key": key}, {"value": 1, "_id": 0})
        value = row.get("value") if row else default
        _settings_cache[key] = value
        return value if value not in (None, "") else default


async def get_setting_int(key: str, default: int) -> int:
    """Like get_setting but always returns a usable int, even if the stored
    value is missing, blank, or corrupted (falls back to default)."""
    raw = await get_setting(key, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        log.warning("Setting %r has invalid int value %r; using default %r", key, raw, default)
        return default


async def get_setting_float(key: str, default: float) -> float:
    """Like get_setting but always returns a usable float, even if the stored
    value is missing, blank, or corrupted (falls back to default)."""
    raw = await get_setting(key, str(default))
    try:
        return float(raw)
    except (TypeError, ValueError):
        log.warning("Setting %r has invalid float value %r; using default %r", key, raw, default)
        return default


def _reward_steps(raw, step_key: str) -> list[dict]:
    """Clean a referral_milestones / streak_rewards setting.

    Admins edit these as JSON by hand, so entries can be strings ("5"), use
    another key ("coins" instead of "reward"), or not be objects at all.
    Bad entries are skipped instead of crashing My Stats / Refer & Earn.
    """
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    steps = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            step = int(item[step_key])
            reward = int(item.get("reward", item.get("coins", 0)) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if step > 0:
            steps.append({step_key: step, "reward": reward})
    return sorted(steps, key=lambda x: x[step_key])


async def get_setting_json(key: str, default):
    """Like get_setting but always returns usable parsed JSON, even if the
    stored value is missing, blank, or corrupted (falls back to default)."""
    raw = await get_setting(key, "")
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        log.warning("Setting %r has invalid JSON value %r; using default", key, raw)
        return default


async def set_setting(key: str, value: str) -> None:
    # Use a real SQLite upsert here.  The SQL compatibility layer is useful
    # for the older handlers, but it made this frequently used path slower
    # and could leave duplicate settings in imported databases.
    await _sqlite_db.settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value}},
        upsert=True,
    )
    async with _settings_cache_lock:
        _settings_cache[key] = value



async def ensure_user(user_id: int, username: str | None, first_name: str | None,
                       referred_by: int | None = None) -> bool:
    """Returns True if this is a newly created user."""
    async with db_conn() as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        exists = await cur.fetchone()
        now = datetime.utcnow().isoformat()
        if exists:
            await db.execute(
                "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
                (username, first_name, now, user_id),
            )
            await db.commit()
            return False
        await db.execute(
            "INSERT INTO users (user_id, username, first_name, join_date, referred_by, last_seen) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, first_name, now, referred_by, now),
        )
        await db.execute(
            "INSERT OR IGNORE INTO wallet (user_id, coins) VALUES (?, 0)", (user_id,)
        )
        await db.commit()
        return True


async def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    async with db_conn() as db:
        cur = await db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
        return (await cur.fetchone()) is not None


async def is_banned(user_id: int) -> bool:
    async with db_conn() as db:
        cur = await db.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0])


async def get_user_row(user_id: int):
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return await cur.fetchone()



async def get_balance(user_id: int) -> int:
    async with db_conn() as db:
        cur = await db.execute("SELECT coins FROM wallet WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute("INSERT OR IGNORE INTO wallet (user_id, coins) VALUES (?, 0)", (user_id,))
            await db.commit()
            return 0
        return row[0]


async def add_coins(user_id: int, amount: int, tx_type: str, description: str = "") -> int:
    async with _db_lock:
        async with db_conn() as db:
            await db.execute(
                "INSERT INTO wallet (user_id, coins) VALUES (?, 0) "
                "ON CONFLICT(user_id) DO NOTHING", (user_id,)
            )
            await db.execute(
                "UPDATE wallet SET coins = coins + ? WHERE user_id=?", (amount, user_id)
            )
            await db.execute(
                "INSERT INTO transactions (user_id, tx_type, amount, description, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, tx_type, amount, description, datetime.utcnow().isoformat()),
            )
            await db.commit()
            cur = await db.execute("SELECT coins FROM wallet WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            new_balance = row[0]
    asyncio.create_task(log_user_activity(
        user_id, f"➕ <b>+{amount} coins</b> [{html.escape(tx_type)}] {html.escape(description)}\n🪙 New balance: {new_balance}"
    ))
    return new_balance


async def remove_coins(user_id: int, amount: int, tx_type: str, description: str = "") -> bool:
    """Returns False if insufficient balance."""
    async with _db_lock:
        async with db_conn() as db:
            cur = await db.execute("SELECT coins FROM wallet WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            bal = row[0] if row else 0
            if bal < amount:
                return False
            await db.execute(
                "UPDATE wallet SET coins = coins - ? WHERE user_id=?", (amount, user_id)
            )
            await db.execute(
                "INSERT INTO transactions (user_id, tx_type, amount, description, timestamp) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, tx_type, -amount, description, datetime.utcnow().isoformat()),
            )
            await db.commit()
    asyncio.create_task(log_user_activity(
        user_id, f"➖ <b>-{amount} coins</b> [{html.escape(tx_type)}] {html.escape(description)}\n🪙 New balance: {bal - amount}"
    ))
    return True



# ============================================================
# 💎 GEMS — paid currency core
# ============================================================
GEM_E = f'<tg-emoji emoji-id="{GEM_EMOJI_ID}">💎</tg-emoji>'
STAR_E = f'<tg-emoji emoji-id="{STAR_EMOJI_ID}">⭐</tg-emoji>'
COIN_E = '<tg-emoji emoji-id="5377690785674175481">🪙</tg-emoji>'


def file_currency(f) -> str:
    """'gems' for Gem-priced files, otherwise 'coins' (legacy default)."""
    try:
        cur = f.get("currency") if hasattr(f, "get") else f["currency"]
    except (KeyError, TypeError, IndexError):
        cur = None
    return "gems" if (cur or "").lower() == "gems" else "coins"


def price_text(price: int, currency: str, html_mode: bool = True) -> str:
    price = int(price or 0)
    if price <= 0:
        return "🆓 FREE"
    if currency == "gems":
        return f"💎 {price} Gems"
    return f"🪙 {price} Coins"


_seq_seeded: set[str] = set()


async def _next_seq(collection: str, pk: str) -> int:
    """Atomic auto-increment backed by a ``counters`` collection.

    The old max()+1 approach let two concurrent inserts get the same id
    (e.g. two payment requests with one payment_id, so accepting one could
    mark both as accepted). The counter is seeded once per process with
    $max, so it never goes below ids that already exist.
    """
    key = f"{collection}.{pk}"
    if key not in _seq_seeded:
        last = await _sqlite_db[collection].find_one(
            {pk: {"$type": "number"}}, {pk: 1, "_id": 0}, sort=[(pk, -1)]
        )
        await _sqlite_db.counters.update_one(
            {"_id": key}, {"$max": {"seq": int((last or {}).get(pk, 0) or 0)}}, upsert=True
        )
        _seq_seeded.add(key)
    doc = await _sqlite_db.counters.find_one_and_update(
        {"_id": key}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return int(doc["seq"])


async def _log_gem_tx(user_id: int, amount: int, tx_type: str, description: str) -> None:
    async with _db_lock:
        tx_id = await _next_seq("transactions", "tx_id")
        await _sqlite_db.transactions.insert_one({
            "tx_id": tx_id,
            "user_id": user_id,
            "tx_type": tx_type,
            "amount": amount,
            "currency": "gems",
            "description": description,
            "timestamp": datetime.utcnow().isoformat(),
        })


async def get_gems(user_id: int) -> int:
    doc = await _sqlite_db.wallet.find_one({"user_id": user_id}, {"_id": 0, "gems": 1})
    return int((doc or {}).get("gems", 0) or 0)


async def add_gems(user_id: int, amount: int, tx_type: str, description: str = "") -> int:
    doc = await _sqlite_db.wallet.find_one_and_update(
        {"user_id": user_id},
        {"$inc": {"gems": int(amount)}, "$setOnInsert": {"coins": 0}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    new_balance = int((doc or {}).get("gems", 0) or 0)
    await _log_gem_tx(user_id, int(amount), tx_type, description)
    asyncio.create_task(log_user_activity(
        user_id, f"💎 <b>+{amount} gems</b> [{html.escape(tx_type)}] {html.escape(description)}\n💎 New gems: {new_balance}"
    ))
    return new_balance


async def remove_gems(user_id: int, amount: int, tx_type: str, description: str = "") -> bool:
    """Atomic: returns False (and changes nothing) if balance is too low."""
    amount = int(amount)
    doc = await _sqlite_db.wallet.find_one_and_update(
        {"user_id": user_id, "gems": {"$gte": amount}},
        {"$inc": {"gems": -amount}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        return False
    await _log_gem_tx(user_id, -amount, tx_type, description)
    asyncio.create_task(log_user_activity(
        user_id, f"💎 <b>-{amount} gems</b> [{html.escape(tx_type)}] {html.escape(description)}\n💎 New gems: {doc.get('gems', 0)}"
    ))
    return True


async def set_gems(user_id: int, amount: int, description: str = "") -> None:
    await _sqlite_db.wallet.update_one(
        {"user_id": user_id},
        {"$set": {"gems": int(amount)}, "$setOnInsert": {"coins": 0}},
        upsert=True,
    )
    await _log_gem_tx(user_id, 0, "admin_setgems", description or f"Admin set gems to {amount}")


# ============================================================
# 🎨 UI KIT — one consistent card design for every screen
#   ┌ header box (icon + title + optional subtitle)
#   ├ content boxes (key : value rows)
#   └ italic footer hint
# Every screen is built with these helpers so the whole bot looks the same.
# ============================================================
from urllib.parse import quote as _url_quote


def ui_head(icon: str, title: str, subtitle: str | None = None) -> str:
    sub = f"\n<i>{subtitle}</i>" if subtitle else ""
    return f"<blockquote>{icon} <b>{title}</b>{sub}</blockquote>"


def ui_box(*lines) -> str:
    body = "\n".join(str(line) for line in lines if line)
    return f"<blockquote>{body}</blockquote>" if body else ""


def ui_kv(icon: str, label: str, value) -> str:
    return f"{icon} <b>{label} :</b> {value}"


def ui_screen(icon: str, title: str, *boxes: str, subtitle: str | None = None,
              footer: str | None = None) -> str:
    parts = [ui_head(icon, title, subtitle)]
    parts.extend(b for b in boxes if b)
    if footer:
        parts.append(f"<i>{footer}</i>")
    return "\n".join(parts)


def ui_bar(current: int, total: int, width: int = 10) -> str:
    total = max(1, int(total or 1))
    current = max(0, min(int(current or 0), total))
    filled = round(width * current / total)
    return "▰" * filled + "▱" * (width - filled) + f"  {int(current * 100 / total)}%"


def kb_grid(buttons: list, cols: int = 2) -> list[list]:
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


def pager_row(prefix: str, page: int, total_pages: int, style: str = "primary") -> list:
    """⬅ Prev | 📄 2/5 | Next ➡ — the middle button is informational."""
    if total_pages <= 1:
        return []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅ Prev", callback_data=f"{prefix}{page - 1}", style=style))
    row.append(InlineKeyboardButton(f"📄 {page + 1}/{total_pages}", callback_data="ui:noop", style=style))
    if page + 1 < total_pages:
        row.append(InlineKeyboardButton("Next ➡", callback_data=f"{prefix}{page + 1}", style=style))
    return row


def back_row(cb: str, label: str = "⬅ Back") -> list:
    return [InlineKeyboardButton(label, callback_data=cb, style="primary")]


async def cb_ui_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await update.callback_query.answer()
    except TelegramError:
        pass


def _pretty_tx(tx_type: str | None) -> str:
    return html.escape((tx_type or "—").replace("_", " "))


async def premium_status_line(user_id: int) -> str:
    row = await get_premium(user_id)
    if row and row["is_lifetime"]:
        return ui_kv("👑", "Premium", "<b>Lifetime</b> ✅")
    if row and row["expiry_date"]:
        try:
            if datetime.fromisoformat(row["expiry_date"]) > datetime.utcnow():
                return ui_kv("👑", "Premium", f"<b>Active</b> · till {fmt_date(row['expiry_date'])}")
        except (TypeError, ValueError):
            pass
    return ui_kv("⭐", "Premium", "<i>Not Active</i>")



async def get_premium(user_id: int):
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM premium WHERE user_id=?", (user_id,))
        return await cur.fetchone()


async def is_premium_active(user_id: int) -> bool:
    row = await get_premium(user_id)
    if not row:
        return False
    if row["is_lifetime"]:
        return True
    if row["expiry_date"] and datetime.fromisoformat(row["expiry_date"]) > datetime.utcnow():
        return True
    return False


async def grant_premium(user_id: int, days: int | None, admin_id: int) -> None:
    current = await get_premium(user_id)
    if days is not None and current and current["is_lifetime"]:
        return  # already lifetime; a timed grant must not downgrade it
    base = datetime.utcnow()
    if days is not None and current and current["expiry_date"]:
        try:
            existing = datetime.fromisoformat(str(current["expiry_date"]))
            if existing > base:
                base = existing  # extend remaining time instead of resetting it
        except (TypeError, ValueError):
            pass
    async with db_conn() as db:
        if days is None:
            await db.execute(
                "INSERT INTO premium (user_id, expiry_date, is_lifetime, granted_by, granted_at) "
                "VALUES (?, NULL, 1, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                "expiry_date=NULL, is_lifetime=1, granted_by=excluded.granted_by, granted_at=excluded.granted_at",
                (user_id, admin_id, datetime.utcnow().isoformat()),
            )
        else:
            expiry = (base + timedelta(days=days)).isoformat()
            await db.execute(
                "INSERT INTO premium (user_id, expiry_date, is_lifetime, granted_by, granted_at) "
                "VALUES (?, ?, 0, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
                "expiry_date=excluded.expiry_date, is_lifetime=0, granted_by=excluded.granted_by, granted_at=excluded.granted_at",
                (user_id, expiry, admin_id, datetime.utcnow().isoformat()),
            )
        await db.commit()


async def remove_premium(user_id: int) -> None:
    async with db_conn() as db:
        await db.execute("DELETE FROM premium WHERE user_id=?", (user_id,))
        await db.commit()

PREMIUM_FILE_DISCOUNT = 50

async def get_effective_file_price(user_id: int, listed_price: int) -> int:
    """Return the actual price paid by this user for a file."""
    listed_price = int(listed_price or 0)
    if listed_price <= 0:
        return 0
    if await is_premium_active(user_id):
        return max(0, listed_price - PREMIUM_FILE_DISCOUNT)
    return listed_price

def user_reply_keyboard(admin: bool) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("Buy Files", style="success", icon_custom_emoji_id="5312361253610475399")],
        [KeyboardButton("Daily Bonus", style="primary", icon_custom_emoji_id="5442939099906325301"),
         KeyboardButton("Mystery Box", style="success", icon_custom_emoji_id="6102393953401705076")],
        [KeyboardButton("Refer & Earn", style="primary", icon_custom_emoji_id="6001078118725456537"),
         KeyboardButton("🎟️ Redeem Code", style="primary")],
        [KeyboardButton("My Stats", style="primary", icon_custom_emoji_id="5229045747130843073"),
         KeyboardButton("Leaderboard", style="primary", icon_custom_emoji_id="6194737030165959506")],
        [KeyboardButton("My Wallet", style="primary", icon_custom_emoji_id="6321018878373667081"),
         KeyboardButton("Support", style="primary", icon_custom_emoji_id="5326026611185704811")],
    ]
    if admin:
        rows.append([KeyboardButton("👑 Admin Panel", style="primary")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_reply_keyboard(is_owner: bool = True) -> ReplyKeyboardMarkup:
    """Full admin control keyboard — replaces the user keyboard entirely while
    the admin is inside the Admin Panel. Senior/Junior admins get a reduced
    set — Force Channels and Settings are Owner-only sections. Requires
    python-telegram-bot >= 22.7 (Bot API 9.4+) for `style` to render as
    colored buttons in Telegram; see requirements.txt."""
    admin_mgr_label = "🛡 Admin Manager" if is_owner else "📋 Admin List"
    buttons = ["📤 Upload File", "📂 Manage Files", "💰 Wallet Manager", "🎟 Redeem Manager"]
    if is_owner:
        buttons += ["📡 Force Channels"]
    buttons += ["📢 Broadcast", "👥 User Manager", "👤 All Users", "👑 Premium Manager", "📊 Statistics", "🛠 Maintenance"]
    if is_owner:
        buttons += ["⚙ Settings"]
    buttons += [admin_mgr_label, "🖼 Buy Files Media"]

    rows = [
        [KeyboardButton(buttons[i], style="primary")] + (
            [KeyboardButton(buttons[i + 1], style="primary")] if i + 1 < len(buttons) else []
        )
        for i in range(0, len(buttons), 2)
    ]
    rows.append([KeyboardButton("⬅️ Back to Main", style="primary")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📤 Upload File", callback_data="ad:upload", style="primary"),
         InlineKeyboardButton("📂 Manage Files", callback_data="ad:managefiles", style="primary")],
        [InlineKeyboardButton("💰 Wallet Manager", callback_data="ad:walletmgr", style="primary"),
         InlineKeyboardButton("🎟 Redeem Manager", callback_data="ad:redeemmgr", style="primary")],
        [InlineKeyboardButton("📡 Force Channels", callback_data="ad:fcmgr", style="primary"),
         InlineKeyboardButton("📢 Broadcast", callback_data="ad:broadcast", style="primary")],
        [InlineKeyboardButton("👥 User Manager", callback_data="ad:usermgr", style="primary"),
         InlineKeyboardButton("👑 Premium Manager", callback_data="ad:premiummgr", style="primary")],
        [InlineKeyboardButton("📊 Statistics", callback_data="ad:stats", style="primary"),
         InlineKeyboardButton("🛠 Maintenance", callback_data="ad:maintenance", style="primary")],
        [InlineKeyboardButton("⚙ Settings", callback_data="ad:settings", style="primary"),
         InlineKeyboardButton("🛡 Admin Manager", callback_data="ad:adminmgr", style="primary")],
        [InlineKeyboardButton("🖼 Buy Files Media", callback_data="ad:bfmedia", style="primary"),
         InlineKeyboardButton("🎞 Welcome Slides", callback_data="ad:wslides", style="primary")],
    ]
    return InlineKeyboardMarkup(rows)


def back_button(cb: str = "ad:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data=cb, style="primary")]])



_force_channels_cache: dict = {"data": None, "ts": 0.0}
_FORCE_CHANNELS_CACHE_TTL = 300  # 5 min — avoids a DB hit on every message


async def list_force_channels():
    now = time.monotonic()
    if (
        _force_channels_cache["data"] is not None
        and (now - _force_channels_cache["ts"]) < _FORCE_CHANNELS_CACHE_TTL
    ):
        return _force_channels_cache["data"]
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM force_channels ORDER BY id")
        rows = await cur.fetchall()
    _force_channels_cache["data"] = rows
    _force_channels_cache["ts"] = now
    return rows


def _invalidate_force_channels_cache() -> None:
    _force_channels_cache["data"] = None
    _force_channels_cache["ts"] = 0.0


async def record_force_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remember a user's pending private-channel join request.

    Telegram does not expose a get-pending-join-requests API to bots. The
    ChatJoinRequest update is therefore the reliable way to know that the
    user is currently in the channel's request list. The request is kept
    until membership is confirmed, or until it expires after seven days.
    """
    request = update.chat_join_request
    if not request:
        return
    chat_id = request.chat.id
    user_id = request.from_user.id
    requested_at = (request.date or datetime.utcnow()).isoformat()

    async with db_conn() as db:
        cur = await db.execute(
            "SELECT 1 FROM force_join_requests WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        if await cur.fetchone():
            await db.execute(
                "UPDATE force_join_requests SET requested_at=?, status='pending' "
                "WHERE chat_id=? AND user_id=?",
                (requested_at, chat_id, user_id),
            )
        else:
            await db.execute(
                "INSERT INTO force_join_requests (chat_id, user_id, requested_at, status) "
                "VALUES (?, ?, ?, 'pending')",
                (chat_id, user_id, requested_at),
            )
        await db.commit()


async def has_pending_force_join_request(chat_id: int, user_id: int) -> bool:
    """Return whether this user recently sent a join request for this chat."""
    async with db_conn() as db:
        cur = await db.execute(
            "SELECT requested_at, status FROM force_join_requests "
            "WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        row = await cur.fetchone()
    if not row or row["status"] != "pending":
        return False
    try:
        requested_at = datetime.fromisoformat(row["requested_at"])
        # Telegram may provide a timezone-aware datetime while legacy
        # records were stored with naive UTC timestamps.
        if requested_at.tzinfo is not None:
            requested_at = requested_at.replace(tzinfo=None)
        if datetime.utcnow() - requested_at > timedelta(days=7):
            async with db_conn() as db:
                await db.execute(
                    "DELETE FROM force_join_requests WHERE chat_id=? AND user_id=?",
                    (chat_id, user_id),
                )
                await db.commit()
            return False
    except (TypeError, ValueError):
        return False
    return True


async def check_force_join(bot, user_id: int, *, bypass_cache: bool = False) -> list[dict]:
    """Returns list of channels the user has NOT joined.

    Each channel check is a real Telegram API call (get_chat_member), which
    typically costs 200-500ms. Checking channels one at a time in a loop
    made this function (and therefore every single message, since guard_user
    calls it) scale linearly with the number of force-join channels — 4
    channels meant 800ms-2s added to every message before the bot even
    started working on the actual request. Running the checks concurrently
    means the total cost is roughly the slowest single check, not the sum
    of all of them.

    A single result cache (matching o.py's _channel_check_cache) stores
    BOTH outcomes — joined and not-joined — for _FORCE_JOIN_CACHE_TTL, so
    every message reuses the last check instead of re-hitting Telegram.
    bypass_cache=True (used by the explicit ✅ Verify button) clears the
    user's entry first so a join made seconds ago isn't reported stale.
    """
    if (await get_setting("force_join", "1")) != "1":
        return []

    if bypass_cache:
        _force_join_pass_cache.pop(user_id, None)

    now = time.monotonic()
    cached = _force_join_pass_cache.get(user_id)
    if cached is not None and (now - cached[1]) < _FORCE_JOIN_CACHE_TTL:
        return cached[0]

    channels = await list_force_channels()
    if not channels:
        return []

    async def _check_one(ch):
        try:
            member = await bot.get_chat_member(chat_id=ch["chat_id"], user_id=user_id)
            joined = member.status not in ("left", "kicked")
            if not joined:
                # A pending request is intentionally enough to pass. Do not
                # approve it here: the channel owner may want to review it,
                # while the user should still be verified by this bot.
                joined = await has_pending_force_join_request(ch["chat_id"], user_id)
        except TelegramError:
            joined = False
        return ch, joined

    results = await asyncio.gather(*(_check_one(ch) for ch in channels))
    missing = [dict(ch) for ch, joined in results if not joined]
    _force_join_pass_cache[user_id] = (missing, now)
    return missing


async def _ensure_private_force_invite_link(bot, channel: dict) -> str | None:
    """Create a join-request link for a private force-join chat if needed."""
    existing = channel.get("invite_link")
    if existing:
        return existing
    if channel.get("username") and str(channel["username"]).startswith("@"):
        return None
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=channel["chat_id"],
            name="Bot force join",
            creates_join_request=True,
        )
        invite_link = invite.invite_link
        channel["invite_link"] = invite_link
        async with db_conn() as db:
            await db.execute(
                "UPDATE force_channels SET invite_link=? WHERE id=?",
                (invite_link, channel["id"]),
            )
            await db.commit()
        return invite_link
    except TelegramError as e:
        log.warning(
            "Could not create private force-join invite for chat %s: %s",
            channel.get("chat_id"), e,
        )
        return None


async def send_force_join_prompt(update: Update, missing: list[dict], bot) -> None:
    buttons = []
    for ch in missing:
        url = await _ensure_private_force_invite_link(bot, ch)
        if not url and ch.get("invite_link"):
            url = ch["invite_link"]
        elif ch.get("username") and str(ch["username"]).startswith("@"):
            url = f"https://t.me/{ch['username'].lstrip('@')}"
        if not url:
            continue
        buttons.append([InlineKeyboardButton(f"📢 {ch['title']}", url=url, style="primary")])
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_join", style="primary")])
    text = (
        "🔒 <b>Access Restricted</b>\n\n"
        "To use this bot, please join all required channels below, "
        "then tap <b>✅ Verify</b>.\n\n"
        "For private channels, sending a join request is enough — the bot "
        "does not approve or cancel your request. If a private button is "
        "missing, the bot needs admin permission to create its invite link."
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML
        )
    else:
        await update.effective_message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode=ParseMode.HTML
        )



(UP_FILE, UP_NAME, UP_DESC, UP_PRICE, UP_PREVIEW) = range(5)
(BC_PKG, BC_STARS, BC_SCREENSHOT) = range(10, 13)
(RD_CODE,) = range(20, 21)
(FC_ADD,) = range(30, 31)
(UM_SEARCH, UM_AMOUNT) = range(40, 42)
(RM_CODE, RM_COINS, RM_PREMIUM, RM_LIMIT, RM_EXPIRY, RM_DELETE) = range(50, 56)
(BR_CONTENT,) = range(60, 61)
(ST_VALUE,) = range(70, 71)
(EF_FIELD,) = range(80, 81)
(WB_IDS, WB_ACTION, WB_AMOUNT, WB_PREMIUM) = range(90, 94)
(BDT_AMOUNT, BDT_PROOF) = range(94, 96)
(GC_AMOUNT,) = range(96, 97)
(AM_ADD_USER, AM_ADD_ROLE) = range(97, 99)
(FR_TEXT,) = range(103, 104)
(MF_SEARCH,) = range(104, 105)
(BF_MEDIA,) = range(105, 106)
(WS_COLLECT,) = range(106, 107)
(GM_SHOT,) = range(107, 108)
(UP_CURRENCY,) = range(108, 109)

ADMIN_ONLY_MSG = "🚫 This action is for admins only."
OWNER_ONLY_MSG = "🚫 This is restricted to the Owner only. Senior/Junior admins don't have access to this section."
ADMIN_MAX_REDEEM_COINS = 300
ADMIN_MIN_REDEEM_COINS = 20
ADMIN_DAILY_REDEEM_LIMIT = 2


async def require_admin(update: Update) -> bool:
    """Gate for admin-only callbacks. Inline buttons are NOT a security
    boundary: a modified Telegram client can send any callback_data, so every
    admin handler must check the caller itself."""
    if await is_admin(update.effective_user.id):
        return True
    if update.callback_query:
        await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text(ADMIN_ONLY_MSG)
    return False


async def require_owner(update: Update) -> bool:
    """Gate for Owner-only sections (Settings, Force Channels, Payment approval,
    Bulk User Manage, Manage Files list). Senior and Junior admins are both
    blocked — only OWNER_ID passes. Sends a denial message/alert and returns
    False if the caller isn't the owner."""
    if update.effective_user.id == OWNER_ID:
        return True
    if update.callback_query:
        await update.callback_query.answer(OWNER_ONLY_MSG, show_alert=True)
    else:
        await update.effective_message.reply_text(OWNER_ONLY_MSG)
    return False


def fmt_size(num: int) -> str:
    step = 1024.0
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < step:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} {unit}"
        num /= step
    return f"{num:.1f} PB"


def fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%d %b %Y, %H:%M")
    except Exception:
        return iso



async def _update_login_streak(bot, user_id: int) -> None:
    """Increments a user's consecutive-day login streak (resets if a day was
    missed), and grants a one-time bonus whenever a configured streak
    milestone is newly reached. Cheap no-op on repeat calls within the same
    day since guard_user runs on every interaction."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    async with db_conn() as db:
        cur = await db.execute("SELECT login_streak, last_login_date FROM users WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return
        streak, last_date = row[0] or 0, row[1]
        if last_date == today:
            return

        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        new_streak = streak + 1 if last_date == yesterday else 1
        await db.execute(
            "UPDATE users SET login_streak=?, last_login_date=? WHERE user_id=?", (new_streak, today, user_id)
        )
        await db.commit()

    for r in _reward_steps(await get_setting_json("streak_rewards", []), "days"):
        if r["days"] == new_streak:
            await add_coins(user_id, r["reward"], "login_streak", f"{new_streak}-day login streak bonus")
            try:
                await bot.send_message(
                    user_id,
                    f"🔥 <b>{new_streak}-Day Login Streak!</b>\n\n🪙 Bonus: <b>+{r['reward']} Coins</b>\n\nKeep it going!",
                    parse_mode=ParseMode.HTML,
                )
            except TelegramError:
                pass
            break


async def guard_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if the update should proceed normally."""
    user = update.effective_user
    if user is None:
        return False

    now = time.monotonic()
    cached_auth = _guard_auth_cache.get(user.id)
    if cached_auth and now - cached_auth[0] < _GUARD_AUTH_CACHE_TTL:
        _, admin, banned = cached_auth
    else:
        # These two reads are independent, so keep them concurrent. They are
        # cached briefly because admin/ban changes do not need sub-second
        # propagation, while this removes two Atlas round trips from nearly
        # every home-menu click.
        admin, banned = await asyncio.gather(
            is_admin(user.id),
            is_banned(user.id),
        )
        _guard_auth_cache[user.id] = (now, admin, banned)

    # ensure_user previously ran (and was awaited) on every home-menu message.
    # On SQLite that meant a SELECT + UPDATE (and a daily-streak SELECT)
    # before the requested handler could even start, adding a full Atlas
    # round-trip to the user's perceived response time. None of this needs
    # to finish before the bot replies, so it's fired in the background
    # instead of awaited — the user gets an instant response and the
    # touch/streak update lands a moment later. Still gated to once a
    # minute per user so it doesn't spam SQLite.
    touched_at = _guard_touch_cache.get(user.id)
    if touched_at is None or now - touched_at >= _GUARD_TOUCH_CACHE_TTL:
        _guard_touch_cache[user.id] = now

        async def _touch_user_bg() -> None:
            try:
                await ensure_user(user.id, user.username, user.first_name)
                await _update_login_streak(context.bot, user.id)
            except Exception:
                log.exception("Background user-touch failed for %s", user.id)

        asyncio.create_task(_touch_user_bg())

    maintenance = (await get_setting("maintenance", "0")) == "1"
    if maintenance and not admin:
        await update.effective_message.reply_text(
            "🚧 <b>Bot is under maintenance.</b>\nPlease try again later.",
            parse_mode=ParseMode.HTML,
        )
        return False

    if banned:
        await update.effective_message.reply_text(
            "🚫 You have been banned from using this bot. Contact support if you think this is a mistake."
        )
        return False

    if not admin:
        missing = await check_force_join(context.bot, user.id)
        if missing:
            await send_force_join_prompt(update, missing, context.bot)
            return False

    return True



async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    args = context.args

    now = time.monotonic()
    cached_auth = _guard_auth_cache.get(user.id)
    if cached_auth and now - cached_auth[0] < _GUARD_AUTH_CACHE_TTL:
        _, admin, banned = cached_auth
        maintenance = (await get_setting("maintenance", "0")) == "1"
    else:
        maintenance_raw, admin, banned = await asyncio.gather(
            get_setting("maintenance", "0"),
            is_admin(user.id),
            is_banned(user.id),
        )
        maintenance = maintenance_raw == "1"
        _guard_auth_cache[user.id] = (now, admin, banned)

    if maintenance and not admin:
        await update.effective_message.reply_text(
            "🚧 <b>Bot is under maintenance.</b>\nPlease try again later.",
            parse_mode=ParseMode.HTML,
        )
        return

    if banned:
        await update.effective_message.reply_text("🚫 You have been banned from using this bot.")
        return

    # A single row fetch, reused for both the referral-eligibility check
    # below and maybe_process_referral(), instead of two separate SQLite
    # round trips for the same document.
    existing_row = await get_user_row(user.id)

    referred_by = None
    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != user.id and existing_row is None:
            referred_by = ref_id

    is_new = await ensure_user(user.id, user.username, user.first_name, referred_by)
    if is_new:
        asyncio.create_task(log_user_activity(user.id, "🆕 <b>Started the bot for the first time</b>", user.username))
        _guard_touch_cache[user.id] = now

    if not admin:
        missing = await check_force_join(context.bot, user.id)
        if missing:
            await send_force_join_prompt(update, missing, context.bot)
            return

    referred_by_id = referred_by if is_new else (existing_row["referred_by"] if existing_row else None)
    if referred_by_id:
        await process_referral(context.bot, referred_by_id, user.id)

    await show_main_menu(update, context)


async def maybe_process_referral(bot, user_id: int) -> None:
    """Grants the referral reward once the referred user actually reaches the
    bot (i.e. after passing force-join, or immediately if none is required).
    Safe to call repeatedly — process_referral() is idempotent."""
    row = await get_user_row(user_id)
    if row and row["referred_by"]:
        await process_referral(bot, row["referred_by"], user_id)


async def process_referral(bot, referrer_id: int, new_user_id: int) -> None:
    async with db_conn() as db:
        cur = await db.execute("SELECT 1 FROM users WHERE user_id=?", (referrer_id,))
        if not await cur.fetchone():
            return
        cur = await db.execute("SELECT 1 FROM referrals WHERE new_user_id=?", (new_user_id,))
        if await cur.fetchone():
            return
        reward = await get_setting_int("referral_reward", 50)
        await db.execute(
            "INSERT INTO referrals (referrer_id, new_user_id, date, reward) VALUES (?, ?, ?, ?)",
            (referrer_id, new_user_id, datetime.utcnow().isoformat(), reward),
        )
        await db.commit()

    new_balance = await add_coins(referrer_id, reward, "referral", f"Referral bonus for inviting user {new_user_id}")

    new_user_row = await get_user_row(new_user_id)
    if new_user_row and new_user_row["username"]:
        uname = f"@{new_user_row['username']}"
    elif new_user_row and new_user_row["first_name"]:
        uname = new_user_row["first_name"]
    else:
        uname = f"User {new_user_id}"

    try:
        await bot.send_message(
            referrer_id,
            "🎉 <b>New Referral Alert!</b> 🎉\n\n"
            f"👤 <b>User:</b> {html.escape(uname)}\n"
            f"🪙 <b>You earned:</b> +{reward} coins\n"
            f"💰 <b>Your new balance:</b> {new_balance} coins",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        pass

    await _check_referral_milestone(bot, referrer_id)


async def _check_referral_milestone(bot, referrer_id: int) -> None:
    """Grants a one-time bonus the first time a referrer's total count crosses
    a configured milestone (e.g. 5, 10, 25, 50 referrals)."""
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (referrer_id,))
        total = (await cur.fetchone())[0]
        cur = await db.execute("SELECT referral_milestone_reached FROM users WHERE user_id=?", (referrer_id,))
        row = await cur.fetchone()
        already_reached = row[0] if row and row[0] else 0

    milestones = _reward_steps(await get_setting_json("referral_milestones", []), "count")
    already_reached = int(already_reached or 0)
    for m in milestones:
        if total >= m["count"] > already_reached:
            await add_coins(referrer_id, m["reward"], "referral_milestone", f"Referral milestone: {m['count']} referrals")
            async with db_conn() as db:
                await db.execute("UPDATE users SET referral_milestone_reached=? WHERE user_id=?", (m["count"], referrer_id))
                await db.commit()
            try:
                await bot.send_message(
                    referrer_id,
                    f"🏆 <b>Referral Milestone Reached!</b>\n\n"
                    f"🚀 You've referred <b>{m['count']}</b> people!\n"
                    f"🪙 Bonus: <b>+{m['reward']} Coins</b>",
                    parse_mode=ParseMode.HTML,
                )
            except TelegramError:
                pass
            break


WELCOME_LINE = '<tg-emoji emoji-id="6120775833608001118">➖</tg-emoji>' * 12
WELCOME_SECTION_LINE = '<tg-emoji emoji-id="6114042712162311525">➖</tg-emoji>' * 6
WELCOME_DIAMOND = '<tg-emoji emoji-id="5280858699286471614">💎</tg-emoji>'
WELCOME_FLOWER = '<tg-emoji emoji-id="6125196652035711334">🌸</tg-emoji>'
WELCOME_CHECK = '<tg-emoji emoji-id="6168184301096542467">✔️</tg-emoji>'
WELCOME_COIN = '<tg-emoji emoji-id="5377690785674175481">🪙</tg-emoji>'
WELCOME_STAR = '<tg-emoji emoji-id="6235403472741603087">⭐</tg-emoji>'
WELCOME_CROWN_FILE = '<tg-emoji emoji-id="6176895538449880631">👑</tg-emoji>'
WELCOME_CROWN_PURCHASE = '<tg-emoji emoji-id="6177115191667333299">👑</tg-emoji>'
WELCOME_CROWN_BLOCK = (
    '<blockquote>'
    '<tg-emoji emoji-id="6176895538449880631">👑</tg-emoji>Tᴏᴛᴀʟ Fɪʟᴇ : {total_files}\n'
    '<tg-emoji emoji-id="6177115191667333299">👑</tg-emoji>Tᴏᴛᴀʟ Pᴜʀᴄʜᴀꜱᴇꜱ {total_purchases}'
    '</blockquote>'
)
WELCOME_LOVE = '<tg-emoji emoji-id="6287305455274301148">🥰</tg-emoji>'
WELCOME_HEART = '<tg-emoji emoji-id="6203769797361014730">💘</tg-emoji>'


def _rich_home_html(
    bot_name: str,
    mention: str,
    user_id: int,
    first_name: str,
    username: str | None,
    balance: int,
    ref_count: int,
    premium_status: str,
    total_files: int,
    total_purchases: int,
    gems: int = 0,
) -> str:
    """Native Rich HTML for the home screen.

    Rich HTML is deliberately kept separate from the old styled HTML string:
    the old string remains the guaranteed fallback for older Bot API servers.
    """
    safe_bot_name = html.escape(bot_name)
    safe_first_name = html.escape(first_name or "User")
    safe_username = html.escape(f"@{username}" if username else "—")
    premium_users = PREMIUM_EMOJI_MAP.get("👥")
    users_icon = (
        f'<tg-emoji emoji-id="{premium_users}">👥</tg-emoji>'
        if premium_users else "👥"
    )
    return (
        f"<h1>💎 {safe_bot_name}</h1>"
        f"<p>Welcome to <b>{safe_bot_name}</b>, {mention} ✨</p>"
        "<hr>"
        "<h2>👤 User Information</h2>"
        "<table bordered>"
        f"<tr><td><b>Username</b></td><td>{safe_username}</td></tr>"
        f"<tr><td><b>User ID</b></td><td>{user_id}</td></tr>"
        f"<tr><td><b>Name</b></td><td>{safe_first_name}</td></tr>"
        "</table>"
        "<h2>📊 Account Information</h2>"
        "<table bordered>"
        f"<tr><td>{WELCOME_COIN} <b>Wallet</b></td><td>{balance} Coins</td></tr>"
        f"<tr><td>{GEM_E} <b>Gems</b></td><td>{gems} Gems</td></tr>"
        f"<tr><td>{users_icon} <b>Referrals</b></td><td>{ref_count}</td></tr>"
        f"<tr><td>{WELCOME_STAR} <b>Premium</b></td>"
        f"<td>{html.escape(premium_status)}</td></tr>"
        f"<tr><td>{WELCOME_CROWN_FILE} <b>Total Files</b></td>"
        f"<td>{total_files}</td></tr>"
        f"<tr><td>{WELCOME_CROWN_PURCHASE} <b>Total Purchases</b></td>"
        f"<td>{total_purchases}</td></tr>"
        "</table>"
        "<details>"
        "<summary>⚙ Important Information</summary>"
        "<ul>"
        "<li>Premium custom emojis enabled</li>"
        "<li>Secure file store account</li>"
        "</ul>"
        "</details>"
        "<hr>"
        "<footer>⬇ Select a menu below to continue</footer>"
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    bot_name = APP_NAME

    now = time.monotonic()
    cached_auth = _guard_auth_cache.get(user.id)
    if cached_auth and now - cached_auth[0] < _GUARD_AUTH_CACHE_TTL:
        admin = cached_auth[1]
        balance, gems, ref_count, is_premium, total_files, total_purchases = await asyncio.gather(
            get_balance(user.id),
            get_gems(user.id),
            _count_referrals(user.id),
            is_premium_active(user.id),
            _count_active_files(),
            _count_purchases(),
        )
    else:
        # These four were previously awaited one at a time — four sequential
        # SQLite lookups before the main menu could render, on every
        # /start and every tap of the home button. Running them concurrently
        # cuts that to the cost of the single slowest call.
        admin, balance, gems, ref_count, is_premium, total_files, total_purchases = await asyncio.gather(
            is_admin(user.id),
            get_balance(user.id),
            get_gems(user.id),
            _count_referrals(user.id),
            is_premium_active(user.id),
            _count_active_files(),
            _count_purchases(),
        )

    premium_status = "Active" if is_premium else "Not Active"
    mention = user.mention_html()
    text = (
        f"<blockquote>{WELCOME_LINE}\n"
        f"{WELCOME_DIAMOND} <b>Wᴇʟᴄᴏᴍᴇ Tᴏ Fɪʟᴇ Sᴛᴏʀᴇ Bᴏᴛ !!</b>\n"
        f"{WELCOME_LINE}</blockquote>\n"
        f"{WELCOME_FLOWER} <b>Hᴇʏ</b> {mention} {WELCOME_CHECK}\n\n"
        f"<blockquote>{WELCOME_SECTION_LINE}\n"
        f"{WELCOME_COIN} <b>Wᴀʟʟᴇᴛ :</b> {balance} Coins\n"
        f"{GEM_E} <b>Gᴇᴍꜱ :</b> {gems} Gems\n"
        f"👥 <b>Rᴇꜰᴇʀʀᴀʟꜱ :</b> {ref_count}\n"
        f"{WELCOME_STAR} <b>Pʀᴇᴍɪᴜᴍ :</b> {premium_status}\n"
        f"{WELCOME_SECTION_LINE}</blockquote>\n\n"
        + WELCOME_CROWN_BLOCK.format(
            total_files=total_files,
            total_purchases=total_purchases,
        )
        + "\n\n"
        + f"<blockquote>{WELCOME_LINE}\n"
        f"{WELCOME_LOVE} <b>Dᴇᴠʟᴏᴩᴇʀ :</b> @WhoIsShown {WELCOME_HEART}\n"
        f"{WELCOME_LINE}</blockquote>"
    )
    kb = user_reply_keyboard(admin)
    # Reuse the exact media configured for Buy Files so /start and Buy Files
    # always show the same photo, video, or GIF (used only when no welcome
    # slideshow is configured — the slideshow takes priority).
    media_file_id, media_type = await _bfmedia_get()
    welcome_slides = await _welcome_slides_get()
    rich_home_html = _rich_home_html(
        bot_name,
        mention,
        user.id,
        user.first_name or "User",
        user.username,
        balance,
        ref_count,
        premium_status,
        total_files,
        total_purchases,
        gems,
    )
    # Bot API 10.2 Rich Message draft: let /start appear as a draft preview
    # before persisting the same fully-rendered home card below.
    draft_id = max(1, int(time.time() * 1000) % 2_147_483_647)
    await send_rich_draft_or_ignore(
        context.bot,
        update.effective_chat.id,
        draft_id,
        rich_home_html,
    )
    await send_rich_or_fallback(
        context.bot,
        update.effective_chat.id,
        rich_home_html,
        text,
        reply_markup=kb,
        media_file_id=media_file_id,
        media_type=media_type,
        slides=welcome_slides,
    )
async def _count_referrals(user_id: int) -> int:
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (user_id,))
        return (await cur.fetchone())[0]

async def _count_active_files() -> int:
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM files WHERE is_deleted=0")
        return (await cur.fetchone())[0]

async def _count_purchases() -> int:
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM purchases")
        return (await cur.fetchone())[0]


async def cb_verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    missing = await check_force_join(context.bot, user.id, bypass_cache=True)
    if missing:
        await query.answer("❌ You haven't joined all channels yet.", show_alert=True)
        return
    await query.answer("✅ Verified!")
    try:
        await query.message.delete()
    except BadRequest:
        pass
    await ensure_user(user.id, user.username, user.first_name)
    await maybe_process_referral(context.bot, user.id)
    await show_main_menu(update, context)



async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    text = ui_screen(
        "📖", "Help & Guide",
        ui_box(
            "📁 <b>Buy Files</b> — browse, buy & download files.",
            "📥 <b>Claim All</b> — get every free + owned file in one tap.",
        ),
        ui_box(
            f"{COIN_E} <b>Coins</b> — free: Daily Bonus, Referrals, Redeem Codes, or buy with ⭐ Stars.",
            f"{GEM_E} <b>Gems</b> — paid currency: buy with ⭐ Stars or get from admin.",
        ),
        ui_box(
            "🎁 <b>Mystery Box</b> — random file for coins.",
            "🎟 <b>Redeem</b> — claim codes or create gift codes.",
            "💬 <b>Support</b> — contact us any time.",
        ),
        footer="Tip: /request lets you ask for a file that isn't in the store yet.",
    )
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def handle_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    support_username = (await get_setting("support_username", "p4ime")).lstrip("@")
    text = ui_screen(
        "💬", "Support",
        ui_box(
            ui_kv("👤", "Contact", f"@{html.escape(support_username)}"),
            ui_kv("🕒", "Hours", "10:00 AM – 10:00 PM (IST)"),
        ),
        footer="We usually reply within a few hours.",
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Message Support", url=f"https://t.me/WhoIsShown", style="success")],
    ])
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)





async def handle_file_request_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await guard_user(update, context):
        return ConversationHandler.END
    await update.effective_message.reply_text(
        "📥 <b>Request a File</b>\n\nTell us what file/project you're looking for — we'll try to add it:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="freq:cancel", style="primary")]]),
    )
    return FR_TEXT


async def cb_file_request_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


async def conv_file_request_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    user = update.effective_user

    async with db_conn() as db:
        await db.execute(
            "INSERT INTO file_requests (user_id, request_text, status, timestamp) VALUES (?, ?, 'open', ?)",
            (user.id, text, datetime.utcnow().isoformat()),
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        req_id = (await cur.fetchone())[0]

    await update.message.reply_text("✅ <b>Request Submitted!</b>\n\nThanks — we'll review it soon.", parse_mode=ParseMode.HTML)

    uname = f"@{user.username}" if user.username else "—"
    notify = (
        f"📥 <b>New File Request #{req_id}</b>\n\n"
        f"👤 From: {html.escape(uname)}\n🆔 User ID: <code>{user.id}</code>\n\n📝 {html.escape(text)}"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Mark Fulfilled", callback_data=f"freq:done:{req_id}", style="primary")]])
    for admin_id in await get_all_admin_ids():
        try:
            await context.bot.send_message(admin_id, notify, parse_mode=ParseMode.HTML, reply_markup=kb)
        except TelegramError:
            pass
    return ConversationHandler.END


async def cb_file_request_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await is_admin(update.effective_user.id):
        await query.answer(ADMIN_ONLY_MSG, show_alert=True)
        return
    req_id = int(query.data.split(":")[2])
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM file_requests WHERE request_id=?", (req_id,))
        req = await cur.fetchone()
        if not req:
            await query.answer("❌ Not found.", show_alert=True)
            return
        await db.execute("UPDATE file_requests SET status='fulfilled' WHERE request_id=?", (req_id,))
        await db.commit()
    await query.answer("✅ Marked fulfilled")
    try:
        await query.message.delete()
    except TelegramError:
        pass
    try:
        await context.bot.send_message(
            req["user_id"],
            f"✅ <b>Your file request has been fulfilled!</b>\n\n📝 {html.escape(req['request_text'])}\n\nCheck 📁 Buy Files!",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        pass
    await log_admin_action(context.bot, update.effective_user.id, f"✅ Fulfilled file request #{req_id}")


async def handle_my_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    await send_wallet_view(update, context)


async def send_wallet_view(update: Update, context: ContextTypes.DEFAULT_TYPE, edit: bool = False) -> None:
    user = update.effective_user

    async def _referral_count() -> int:
        return await _sqlite_db.referrals.count_documents({"referrer_id": user.id})

    balance, gems, ref_count, daily_status, is_premium, premium_line = await asyncio.gather(
        get_balance(user.id),
        get_gems(user.id),
        _referral_count(),
        bonus_status_text(user.id),
        is_premium_active(user.id),
        premium_status_line(user.id),
    )
    text = ui_screen(
        "💰", "My Wallet",
        ui_box(
            ui_kv(COIN_E, "Coins", f"<b>{balance}</b>"),
            ui_kv(GEM_E, "Gems", f"<b>{gems}</b>"),
        ),
        ui_box(
            ui_kv("👥", "Referrals", f"<b>{ref_count}</b>"),
            ui_kv("🎁", "Daily Bonus", daily_status),
            premium_line,
        ),
        subtitle=html.escape(user.first_name or "User"),
        footer="🪙 Coins = free rewards  ·  💎 Gems = paid via ⭐ Stars",
    )
    buttons = [
        [InlineKeyboardButton("🪙 Buy Coins", callback_data="wallet:buycoins", style="success"),
         InlineKeyboardButton("💎 Buy Gems", callback_data="gems:buy", style="success")],
        [InlineKeyboardButton("📜 Transactions", callback_data="wallet:tx:0", style="primary"),
         InlineKeyboardButton("🔥 Refer & Earn", callback_data="wallet:refer", style="primary")],
    ]
    if not is_premium:
        buttons.append([InlineKeyboardButton("👑 Buy Premium with Coins", callback_data="wallet:buypremium", style="danger")])
    buttons.append([InlineKeyboardButton("🛍 My Purchases", callback_data="purchases:0", style="primary")])
    kb = InlineKeyboardMarkup(buttons)
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def build_refer_screen(user_id: int, back_cb: str | None = None):
    reward = await get_setting_int("referral_reward", 50)
    count = await _sqlite_db.referrals.count_documents({"referrer_id": user_id})
    milestones = _reward_steps(await get_setting_json("referral_milestones", []), "count")
    nxt = next((m for m in milestones if count < m["count"]), None)
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    if nxt:
        goal = ui_box(
            f"🎯 <b>Next Milestone :</b> {nxt['count']} referrals → +{nxt['reward']} 🪙",
            f"<code>{ui_bar(count, int(nxt['count']))}</code>",
            f"<i>{int(nxt['count']) - count} more to go!</i>",
        )
    else:
        goal = ui_box("🏆 <b>All milestones completed!</b> Legend status 🔥") if milestones else ""
    text = ui_screen(
        "🔥", "Refer & Earn",
        ui_box(
            ui_kv("🪙", "Per Referral", f"<b>+{reward} Coins</b>"),
            ui_kv("👥", "Your Referrals", f"<b>{count}</b>"),
        ),
        goal,
        ui_box("🔗 <b>Your Link</b>", f"<code>{link}</code>"),
        footer="Share your link — every new user = free coins for you.",
    )
    share_text = _url_quote("📁 Join this file store bot and get free coins!")
    rows = [
        [InlineKeyboardButton("📤 Share", url=f"https://t.me/share/url?url={_url_quote(link)}&text={share_text}", style="success"),
         InlineKeyboardButton("📋 Copy Link", copy_text=CopyTextButton(text=link), style="primary")],
        [InlineKeyboardButton("👥 My Referrals", callback_data="myrefs:0", style="primary")],
    ]
    if back_cb:
        rows.append(back_row(back_cb))
    return text, InlineKeyboardMarkup(rows)


async def cb_wallet_refer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    context.user_data["refer_back"] = "wallet:home"
    text, kb = await build_refer_screen(update.effective_user.id, back_cb="wallet:home")
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_refer_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text, kb = await build_refer_screen(
        update.effective_user.id, back_cb=context.user_data.get("refer_back")
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_wallet_buy_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if await is_premium_active(update.effective_user.id):
        await query.answer("✅ You already have Premium active.", show_alert=True)
        return
    await query.answer()
    pricing = await get_setting_json("premium_pricing", [])
    balance = await get_balance(update.effective_user.id)
    plan_lines = []
    buttons = []
    for p in pricing:
        label = "Lifetime" if p["days"] == 0 else f"{p['days']} Days"
        can = "✅" if balance >= int(p["price"]) else "🔒"
        plan_lines.append(f"{can} <b>{label}</b> — 🪙 {p['price']}")
        buttons.append(InlineKeyboardButton(
            f"👑 {label} · {p['price']}", callback_data=f"premium:buy:{p['days']}:{p['price']}", style="success"
        ))
    text = ui_screen(
        "👑", "Premium Membership",
        ui_box(ui_kv(COIN_E, "Your Coins", f"<b>{balance}</b>")),
        ui_box(
            "✨ <b>Benefits</b>",
            f"• 🪙 {PREMIUM_FILE_DISCOUNT} coins off every Coin file",
            "• 🎁 Bigger daily bonus",
            "• 👑 Premium badge & priority support",
        ),
        ui_box("📋 <b>Plans</b>", *plan_lines) if plan_lines else "",
        footer="✅ = you can afford it  ·  🔒 = need more coins",
    )
    rows = kb_grid(buttons, 2)
    rows.append(back_row("wallet:home"))
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def cb_premium_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    _, _, days, _cb_price = query.data.split(":")
    days = int(days)
    # The price inside callback_data is attacker-controlled (and can be stale
    # after an admin edits pricing). Always charge the configured price.
    plan = None
    for p in await get_setting_json("premium_pricing", []):
        try:
            if isinstance(p, dict) and int(p["days"]) == days:
                plan = p
                break
        except (KeyError, TypeError, ValueError):
            continue
    if plan is None:
        await query.answer("❌ This plan is no longer available.", show_alert=True)
        return
    price = int(plan["price"])
    if price <= 0:
        await query.answer("❌ This plan is not purchasable.", show_alert=True)
        return

    lock = await get_user_action_lock(user.id)
    async with lock:
        if await is_premium_active(user.id):
            await query.answer("✅ You already have Premium active.", show_alert=True)
            return
        ok = await remove_coins(user.id, price, "premium_purchase", f"Bought Premium ({'Lifetime' if days == 0 else f'{days} days'})")
        if not ok:
            await query.answer("❌ Not enough Coins for this plan.", show_alert=True)
            return
        await grant_premium(user.id, None if days == 0 else days, admin_id=0)

    await query.answer("👑 Premium activated!")
    label = "Lifetime" if days == 0 else f"{days} Days"
    await query.edit_message_text(
        f"🎉 <b>Premium Activated!</b>\n\n👑 Plan: <b>{label}</b>\n🪙 Paid: <b>{price} coins</b>\n\n"
        "Enjoy your Premium badge, bonus multiplier, and priority support!",
        parse_mode=ParseMode.HTML,
    )


async def bonus_status_text(user_id: int) -> str:
    row = await get_user_row(user_id)
    if row and row["last_bonus_time"]:
        last = datetime.fromisoformat(row["last_bonus_time"])
        elapsed = datetime.utcnow() - last
        if elapsed < timedelta(hours=24):
            remaining = timedelta(hours=24) - elapsed
            h, rem = divmod(int(remaining.total_seconds()), 3600)
            m = rem // 60
            return f"⏳ Available in {h}h {m}m"
    return "✅ Available now"


async def cb_wallet_tx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    page = int(query.data.split(":")[2])
    per_page = 10
    total, rows = await asyncio.gather(
        _sqlite_db.transactions.count_documents({"user_id": user.id}),
        _sqlite_db.transactions.find({"user_id": user.id}, {"_id": 0})
        .sort("tx_id", -1).skip(page * per_page).limit(per_page).to_list(length=per_page),
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    if not rows:
        body = ui_box("📭 No transactions yet.", "<i>Claim your Daily Bonus to get started!</i>")
    else:
        lines = []
        for r in rows:
            amount = int(r.get("amount") or 0)
            icon = "💎" if r.get("currency") == "gems" else "🪙"
            dot = "🟢" if amount > 0 else ("🔴" if amount < 0 else "⚪")
            sign = "+" if amount > 0 else ""
            lines.append(
                f"{dot} <b>{sign}{amount}</b> {icon}  {_pretty_tx(r.get('tx_type'))}\n"
                f"      <i>{fmt_date(r.get('timestamp'))}</i>"
            )
        body = ui_box(*lines)
    text = ui_screen("📜", "Transactions", body, subtitle=f"Total records: {total}")
    buttons = []
    nav = pager_row("wallet:tx:", page, total_pages)
    if nav:
        buttons.append(nav)
    buttons.append(back_row("wallet:home", "⬅ Back to Wallet"))
    await query.answer()
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def _buycoins_screen():
    packages = await get_setting_json("coin_packages", DEFAULT_COIN_PACKAGES)
    payment_username = (await get_setting("payment_username", "p4ime")).lstrip("@")
    text = ui_screen(
        "⭐", "Bᴜʏ Cᴏɪɴꜱ — Mᴀɴᴜᴀʟ Sᴛᴀʀꜱ Pᴀʏᴍᴇɴᴛ",
        ui_box(*[f"{COIN_E} <b>{p['coins']}</b> Cᴏɪɴꜱ  =  {STAR_E} <b>{p['stars']}</b> Sᴛᴀʀꜱ" for p in packages]),
        ui_box(
            f"📨 Sᴇɴᴅ Sᴛᴀʀꜱ Tᴏ : <b>@{html.escape(payment_username)}</b>",
            f"Aꜰᴛᴇʀ Sᴇɴᴅɪɴɢ, Tᴀᴩ {STAR_E} <b>I Hᴀᴠᴇ Pᴀɪᴅ</b> Bᴇʟᴏᴡ.",
        ),
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ I Have Paid", callback_data="buycoins:paid", style="success")],
        back_row("wallet:home"),
    ])
    return text, kb


async def cb_wallet_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()
    await send_wallet_view(update, context, edit=True)



async def cb_buycoins_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    text, kb = await _buycoins_screen()
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return ConversationHandler.END


async def cb_buycoins_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Same message: pick the package that was paid for."""
    query = update.callback_query
    await query.answer()
    packages = await get_setting_json("coin_packages", DEFAULT_COIN_PACKAGES)
    buttons = [
        InlineKeyboardButton(f"⭐ {p['stars']} → {p['coins']} Coins", callback_data=f"buycoins:pkg:{i}", style="primary")
        for i, p in enumerate(packages)
    ]
    rows = kb_grid(buttons, 2)
    rows.append([InlineKeyboardButton("✏️ Custom Amount", callback_data="buycoins:custom", style="primary")])
    rows.append(back_row("wallet:buycoins"))
    text = ui_screen(
        "⭐", "Which Package Did You Pay For?",
        ui_box("Select the exact package you sent Stars for 👇",
               "<i>Sent a different amount? Tap ✏️ Custom Amount.</i>"),
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))


async def cb_buycoins_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["bc_prompt"] = (query.message.chat_id, query.message.message_id)
    text = ui_screen(
        "✏️", "Custom Stars Amount",
        ui_box("⭐ How many Stars did you send?", "<i>Numbers only, e.g. 40</i>"),
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=_buycoins_cancel_kb())
    return BC_STARS


async def cb_buycoins_pkg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    packages = await get_setting_json("coin_packages", DEFAULT_COIN_PACKAGES)
    idx = int(query.data.split(":")[2])
    if idx < 0 or idx >= len(packages):
        text, kb = await _buycoins_screen()
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return ConversationHandler.END
    pkg = packages[idx]
    context.user_data["bc_stars"] = int(pkg["stars"])
    context.user_data["bc_prompt"] = (query.message.chat_id, query.message.message_id)
    text = ui_screen(
        "📷", "Send Payment Screenshot",
        ui_box(ui_kv(STAR_E, "Stars", f"<b>{pkg['stars']}</b>"), ui_kv(COIN_E, "Coins", f"<b>{pkg['coins']}</b>")),
        footer="Send the screenshot now as a photo or document.",
    )
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=_buycoins_cancel_kb())
    return BC_SCREENSHOT


def _buycoins_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="buycoins:cancel", style="danger")]])


async def conv_buycoins_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Please send a valid number of Stars.")
        return BC_STARS
    context.user_data["bc_stars"] = int(text)
    prompt = await update.message.reply_text(
        ui_screen("📷", "Send Payment Screenshot",
                  ui_box(ui_kv(STAR_E, "Stars", f"<b>{int(text)}</b>")),
                  footer="Send the screenshot now as a photo or document."),
        parse_mode=ParseMode.HTML,
        reply_markup=_buycoins_cancel_kb(),
    )
    context.user_data["bc_prompt"] = (prompt.chat_id, prompt.message_id)
    return BC_SCREENSHOT


async def conv_buycoins_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.photo and not update.message.document:
        await update.message.reply_text("❌ Please send a screenshot as a photo or document.")
        return BC_SCREENSHOT
    stars = context.user_data.pop("bc_stars", None)
    prompt_ref = context.user_data.pop("bc_prompt", None)
    if not stars:
        await update.message.reply_text("❌ Session expired — open 💰 My Wallet → 🪙 Buy Coins again.")
        return ConversationHandler.END

    file_id = update.message.photo[-1].file_id if update.message.photo else update.message.document.file_id
    user = update.effective_user
    if await _sqlite_db.payments.find_one({"user_id": user.id, "status": "pending"}, {"_id": 1}):
        await update.message.reply_text("⚠️ You already have a pending payment request. Please wait for admin review.")
        return ConversationHandler.END

    packages = await get_setting_json("coin_packages", [])
    coins = next((int(p["coins"]) for p in packages if int(p["stars"]) == stars), 0)
    if coins == 0:
        rate = await get_setting_float("star_rate", 30)
        coins = int(stars * rate / 30 * 100)

    async with _db_lock:
        payment_id = await _next_seq("payments", "payment_id")
        await _sqlite_db.payments.insert_one({
            "payment_id": payment_id,
            "user_id": user.id,
            "stars": stars,
            "coins": coins,
            "currency": "coins",
            "payment_method": "stars",
            "screenshot_file_id": file_id,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat(),
        })

    done_text = ui_screen(
        "✅", "Payment Request Submitted",
        ui_box(ui_kv(STAR_E, "Stars", f"<b>{stars}</b>"), ui_kv(COIN_E, "Coins", f"<b>{coins}</b>"),
               ui_kv("🆔", "Request", f"#{payment_id}")),
        footer="⏳ You'll be notified once the admin reviews it.",
    )
    back_kb = InlineKeyboardMarkup([back_row("wallet:home", "⬅ Back to Wallet")])
    edited = False
    if prompt_ref:
        try:
            await context.bot.edit_message_text(
                done_text, chat_id=prompt_ref[0], message_id=prompt_ref[1],
                parse_mode=ParseMode.HTML, reply_markup=back_kb,
            )
            edited = True
        except TelegramError:
            pass
    if not edited:
        await update.message.reply_text(done_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    uname = f"@{user.username}" if user.username else "—"
    caption = (
        "💰 <b>New Coins Payment Request</b>\n\n"
        f"👤 Username: {html.escape(uname)}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"⭐ Stars: <b>{stars}</b>\n"
        f"🪙 Coins: <b>{coins}</b>\n"
        f"📅 Time: {fmt_date(datetime.utcnow().isoformat())}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"pay:accept:{payment_id}", style="success"),
         InlineKeyboardButton("❌ Reject", callback_data=f"pay:reject:{payment_id}", style="danger")]
    ])
    try:
        if update.message.photo:
            await context.bot.send_photo(OWNER_ID, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await context.bot.send_document(OWNER_ID, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    except TelegramError:
        pass
    return ConversationHandler.END


async def cb_buycoins_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("❌ Cancelled")
    context.user_data.pop("bc_stars", None)
    context.user_data.pop("bc_prompt", None)
    text, kb = await _buycoins_screen()
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return ConversationHandler.END



# ============================================================
# 💎 BUY GEMS — Manual Star Payment (same-message flow)
# ============================================================
async def _gem_packages() -> list[dict]:
    packages = await get_setting_json("gem_packages", DEFAULT_GEM_PACKAGES)
    clean = []
    for p in packages if isinstance(packages, list) else []:
        try:
            clean.append({"gems": int(p["gems"]), "stars": int(p["stars"])})
        except (KeyError, TypeError, ValueError):
            continue
    return clean or list(DEFAULT_GEM_PACKAGES)


async def _buygems_screen_text() -> str:
    packages = await _gem_packages()
    payment_username = (await get_setting("payment_username", "P4ime")).lstrip("@")
    return ui_screen(
        STAR_E, "Bᴜʏ Gᴇᴍꜱ — Mᴀɴᴜᴀʟ Sᴛᴀʀ Pᴀʏᴍᴇɴᴛ",
        ui_box(*[f"{STAR_E} <b>{p['stars']}</b> Sᴛᴀʀꜱ  =  {GEM_E} <b>{p['gems']}</b> Gᴇᴍꜱ" for p in packages]),
        ui_box(
            f"📨 Sᴇɴᴅ Sᴛᴀʀꜱ Tᴏ : <b>@{html.escape(payment_username)}</b>",
            f"Aꜰᴛᴇʀ Sᴇɴᴅɪɴɢ, Tᴀᴩ {STAR_E} <b>I Hᴀᴠᴇ Pᴀɪᴅ</b> Bᴇʟᴏᴡ.",
        ),
        footer="💎 Gems = paid currency for premium files.",
    )


def _buygems_screen_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ I Have Paid", callback_data="gems:paid", style="success")],
        [InlineKeyboardButton("⬅ Back", callback_data="wallet:home", style="primary")],
    ])


async def cb_buygems_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop("gm_pkg", None)
    await query.edit_message_text(
        await _buygems_screen_text(), parse_mode=ParseMode.HTML, reply_markup=_buygems_screen_kb()
    )
    return ConversationHandler.END


async def cb_buygems_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Same message: ask which package the user paid for."""
    query = update.callback_query
    await query.answer()
    packages = await _gem_packages()
    rows = [
        [InlineKeyboardButton(
            f"⭐ {p['stars']} Stars → 💎 {p['gems']} Gems",
            callback_data=f"gems:pkg:{i}", style="primary",
        )]
        for i, p in enumerate(packages)
    ]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="gems:buy", style="primary")])
    await query.edit_message_text(
        f"{STAR_E} <b>Wʜɪᴄʜ Pᴀᴄᴋᴀɢᴇ Dɪᴅ Yᴏᴜ Pᴀʏ Fᴏʀ?</b>\n\nSelect the exact package you sent Stars for 👇",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def cb_buygems_pkg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    packages = await _gem_packages()
    idx = int(query.data.split(":")[2])
    if idx < 0 or idx >= len(packages):
        await query.edit_message_text(
            await _buygems_screen_text(), parse_mode=ParseMode.HTML, reply_markup=_buygems_screen_kb()
        )
        return ConversationHandler.END
    pending = await _sqlite_db.payments.find_one(
        {"user_id": update.effective_user.id, "status": "pending"}, {"_id": 1}
    )
    if pending:
        await query.edit_message_text(
            "⚠️ <b>You already have a pending payment request.</b>\nPlease wait for admin review.",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="wallet:home", style="primary")]]),
        )
        return ConversationHandler.END
    pkg = packages[idx]
    context.user_data["gm_pkg"] = pkg
    context.user_data["gm_prompt"] = (query.message.chat_id, query.message.message_id)
    await query.edit_message_text(
        f"{STAR_E} <b>Pᴀᴄᴋᴀɢᴇ :</b> {pkg['stars']} Stars → {GEM_E} {pkg['gems']} Gems\n\n"
        "📷 <b>Now send your payment screenshot</b> (photo or document).",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="gems:cancel", style="danger")]]),
    )
    return GM_SHOT


async def _edit_gems_prompt(context: ContextTypes.DEFAULT_TYPE, text: str, kb=None) -> bool:
    ref = context.user_data.pop("gm_prompt", None)
    if not ref:
        return False
    try:
        await context.bot.edit_message_text(
            text, chat_id=ref[0], message_id=ref[1], parse_mode=ParseMode.HTML, reply_markup=kb
        )
        return True
    except TelegramError:
        return False


async def conv_buygems_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if not msg.photo and not msg.document:
        await msg.reply_text("❌ Please send the screenshot as a photo or document.")
        return GM_SHOT
    pkg = context.user_data.pop("gm_pkg", None)
    if not pkg:
        await msg.reply_text("❌ Session expired — open 💰 My Wallet → 💎 Buy Gems again.")
        return ConversationHandler.END
    user = update.effective_user
    file_id = msg.photo[-1].file_id if msg.photo else msg.document.file_id

    if await _sqlite_db.payments.find_one({"user_id": user.id, "status": "pending"}, {"_id": 1}):
        await msg.reply_text("⚠️ You already have a pending payment request. Please wait for admin review.")
        return ConversationHandler.END

    async with _db_lock:
        payment_id = await _next_seq("payments", "payment_id")
        await _sqlite_db.payments.insert_one({
            "payment_id": payment_id,
            "user_id": user.id,
            "stars": pkg["stars"],
            "coins": 0,
            "gems": pkg["gems"],
            "currency": "gems",
            "payment_method": "stars",
            "screenshot_file_id": file_id,
            "status": "pending",
            "timestamp": datetime.utcnow().isoformat(),
        })

    done_text = (
        f"✅ <b>Payment Request Submitted!</b>\n\n"
        f"{STAR_E} Stars: <b>{pkg['stars']}</b>\n{GEM_E} Gems: <b>{pkg['gems']}</b>\n\n"
        "⏳ You'll be notified once the admin reviews it."
    )
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Wallet", callback_data="wallet:home", style="primary")]])
    if not await _edit_gems_prompt(context, done_text, back_kb):
        await msg.reply_text(done_text, parse_mode=ParseMode.HTML, reply_markup=back_kb)

    uname = f"@{user.username}" if user.username else "—"
    caption = (
        "💎 <b>New Gems Payment Request</b>\n\n"
        f"👤 Username: {html.escape(uname)}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"⭐ Stars: <b>{pkg['stars']}</b>\n"
        f"💎 Gems: <b>{pkg['gems']}</b>\n"
        f"📅 Time: {fmt_date(datetime.utcnow().isoformat())}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"pay:accept:{payment_id}", style="success"),
         InlineKeyboardButton("❌ Reject", callback_data=f"pay:reject:{payment_id}", style="danger")]
    ])
    try:
        if msg.photo:
            await context.bot.send_photo(OWNER_ID, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            await context.bot.send_document(OWNER_ID, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    except TelegramError:
        pass
    return ConversationHandler.END


async def cb_buygems_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("❌ Cancelled")
    context.user_data.pop("gm_pkg", None)
    context.user_data.pop("gm_prompt", None)
    await query.edit_message_text(
        await _buygems_screen_text(), parse_mode=ParseMode.HTML, reply_markup=_buygems_screen_kb()
    )
    return ConversationHandler.END


async def handle_buy_coins_bdt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not await guard_user(update, context):
        return
    rate = await get_setting("coin_rate_bdt", "5")
    details = await get_setting("bdt_payment_details", "")
    text = (
        "💵 <b>Buy Coins with Taka (৳)</b>\n"
        f"{DIVIDER}\n"
        f"💱 Rate: <b>1 ৳ = {html.escape(rate)} Coins</b>\n\n"
        f"{html.escape(details)}\n\n"
        "Send the amount via bKash/Nagad (Send Money), then tap <b>💵 I Have Paid</b> below."
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("💵 I Have Paid", callback_data="buybdt:paid", style="primary")]])
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_buybdt_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "💵 How many Taka (৳) did you send? (numbers only)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="buybdt:cancel", style="primary")]]),
    )
    return BDT_AMOUNT


async def conv_buybdt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Please send a valid Taka amount.")
        return BDT_AMOUNT
    context.user_data["bdt_amount"] = int(text)
    await update.message.reply_text(
        "📷 Please send your payment screenshot now — or type your bKash/Nagad Transaction ID as text."
    )
    return BDT_PROOF


async def conv_buybdt_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = context.user_data.pop("bdt_amount", None)
    if amount is None:
        await update.message.reply_text("❌ Something went wrong — please start again from 💵 Buy Coins (৳).")
        return ConversationHandler.END

    file_id = None
    is_photo = False
    txn_text = None
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        is_photo = True
    elif update.message.document:
        file_id = update.message.document.file_id
    elif update.message.text:
        txn_text = update.message.text.strip()
    else:
        await update.message.reply_text("❌ Please send a screenshot, or type your Transaction ID as text.")
        return BDT_PROOF

    user = update.effective_user

    async with db_conn() as db:
        cur = await db.execute("SELECT 1 FROM payments WHERE user_id=? AND status='pending'", (user.id,))
        if await cur.fetchone():
            await update.message.reply_text("⚠️ You already have a pending payment request. Please wait for admin review.")
            return ConversationHandler.END

        rate = await get_setting_float("coin_rate_bdt", 5)
        coins = int(amount * rate)

        await db.execute(
            "INSERT INTO payments (user_id, coins, screenshot_file_id, status, timestamp, payment_method, amount_bdt) "
            "VALUES (?, ?, ?, 'pending', ?, 'bdt', ?)",
            (user.id, coins, file_id, datetime.utcnow().isoformat(), amount),
        )
        await db.commit()
        cur = await db.execute("SELECT last_insert_rowid()")
        payment_id = (await cur.fetchone())[0]

    await update.message.reply_text("✅ Your payment request has been submitted. You'll be notified once reviewed.")

    uname = f"@{user.username}" if user.username else "—"
    txn_note = f"\n🧾 Transaction ID: <code>{html.escape(txn_text)}</code>" if txn_text else ""
    caption = (
        "💵 <b>New BDT Payment Request</b>\n\n"
        f"👤 Username: {html.escape(uname)}\n"
        f"🆔 User ID: <code>{user.id}</code>\n"
        f"💵 Amount: <b>৳{amount}</b>\n"
        f"🪙 Coins: <b>{coins}</b>{txn_note}\n"
        f"📅 Time: {fmt_date(datetime.utcnow().isoformat())}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Accept", callback_data=f"pay:accept:{payment_id}", style="primary"),
         InlineKeyboardButton("❌ Reject", callback_data=f"pay:reject:{payment_id}", style="primary")]
    ])
    admin_ids = [OWNER_ID]
    for admin_id in admin_ids:
        try:
            if file_id and is_photo:
                await context.bot.send_photo(admin_id, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
            elif file_id:
                await context.bot.send_document(admin_id, file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
            else:
                await context.bot.send_message(admin_id, caption, parse_mode=ParseMode.HTML, reply_markup=kb)
        except TelegramError:
            pass
    return ConversationHandler.END


async def cb_buybdt_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("❌ Cancelled.")
    context.user_data.pop("bdt_amount", None)
    return ConversationHandler.END


async def get_all_admin_ids() -> list[int]:
    ids = {OWNER_ID}
    async with db_conn() as db:
        cur = await db.execute("SELECT user_id FROM admins")
        rows = await cur.fetchall()
        for r in rows:
            ids.add(r[0])
    return list(ids)


async def get_admin_role(user_id: int) -> str | None:
    """Returns 'owner', 'senior', 'junior', or None (not an admin)."""
    if user_id == OWNER_ID:
        return "owner"
    async with db_conn() as db:
        cur = await db.execute("SELECT role FROM admins WHERE user_id=?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None


async def log_user_activity(user_id: int, action_text: str, username: str | None = None) -> None:
    """Sends a one-line notice to the User Logs channel for any notable user
    action (buy, spin, redeem, bonus, etc). Best-effort — never raises."""
    if not _BOT_INSTANCE:
        return
    if username is None:
        row = await get_user_row(user_id)
        username = row["username"] if row and row["username"] else None
    who = f"@{username}" if username else "No username"
    stamp = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    text = (
        "┏━━━━━━━━━━━━━━━━━━┓\n"
        "┃   👤 <b>USER ACTIVITY</b>\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        f"<b>User</b> : {html.escape(who)}\n"
        f"<b>ID</b>     : <code>{user_id}</code>\n\n"
        f"{action_text}\n\n"
        f"🕒 <i>{stamp}</i>"
    )
    if not USER_LOG_CHANNEL_ID:
        return
    try:
        await _BOT_INSTANCE.send_message(USER_LOG_CHANNEL_ID, text, parse_mode=ParseMode.HTML)
    except TelegramError:
        pass


async def log_admin_action(bot, actor_id: int, action_text: str) -> None:
    """Audit trail with a Senior/Junior hierarchy:
    - Junior admin actions -> notify Owner + all Senior admins.
    - Senior admin actions -> notify Owner only.
    - Owner's own actions -> no notification needed.
    Every action (including the Owner's own) is persisted to admin_logs for
    the browsable Action Log Viewer."""
    async with db_conn() as db:
        await db.execute(
            "INSERT INTO admin_logs (actor_id, action_text, timestamp) VALUES (?, ?, ?)",
            (actor_id, action_text, datetime.utcnow().isoformat()),
        )
        await db.commit()

    if actor_id == OWNER_ID:
        return
    role = await get_admin_role(actor_id)
    actor_row = await get_user_row(actor_id)
    actor_label = f"@{actor_row['username']}" if actor_row and actor_row["username"] else str(actor_id)
    role_tag = f" ({role.title()})" if role else ""
    stamp = datetime.utcnow().strftime("%d %b %Y, %H:%M UTC")
    text = (
        "┏━━━━━━━━━━━━━━━━━━┓\n"
        "┃   📋 <b>ADMIN ACTION</b>\n"
        "┗━━━━━━━━━━━━━━━━━━┛\n\n"
        f"<b>By</b>   : {html.escape(actor_label)}{role_tag}\n"
        f"<b>ID</b>   : <code>{actor_id}</code>\n\n"
        f"{action_text}\n\n"
        f"🕒 <i>{stamp}</i>"
    )

    recipients = {OWNER_ID}
    if role == "junior":
        async with db_conn() as db:
            cur = await db.execute("SELECT user_id FROM admins WHERE role='senior'")
            for r in await cur.fetchall():
                recipients.add(r[0])

    for uid in recipients:
        try:
            await bot.send_message(uid, text, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass


async def cb_payment_accept(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin = update.effective_user
    if not await require_owner(update):
        return
    payment_id = int(query.data.split(":")[2])
    # Atomic pending -> accepted. A double tap (or two admins) used to be able
    # to read "pending" twice and credit the wallet twice.
    doc = await _sqlite_db.payments.find_one_and_update(
        {"payment_id": payment_id, "status": "pending"},
        {"$set": {"status": "accepted", "admin_id": admin.id}},
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        await query.answer("⚠️ Already processed.", show_alert=True)
        return
    payment = SQLiteRow(doc)

    method_note = f"({payment['stars']} stars)" if payment["payment_method"] != "bdt" else f"(৳{payment['amount_bdt']})"
    is_gems = payment["currency"] == "gems"
    try:
        if is_gems:
            await add_gems(payment["user_id"], int(payment["gems"] or 0), "payment", f"Gems payment accepted {method_note}")
        else:
            await add_coins(payment["user_id"], payment["coins"], "payment", f"Payment accepted {method_note}")
    except Exception:
        # Do not leave a payment marked accepted when its wallet credit did
        # not complete. Restore it to pending so the admin can retry safely.
        log.exception("Wallet credit failed for payment #%s", payment_id)
        await _sqlite_db.payments.update_one(
            {"payment_id": payment_id, "status": "accepted"}, {"$set": {"status": "pending"}}
        )
        await query.answer("⚠️ Wallet credit failed; payment returned to pending.", show_alert=True)
        return
    await query.answer("✅ Accepted")
    try:
        await query.message.delete()
    except (BadRequest, TelegramError):
        pass
    try:
        credited = (
            f"{GEM_E} {payment['gems']} Gems have been added to your wallet."
            if is_gems else f"🪙 {payment['coins']} Coins have been added to your wallet."
        )
        await context.bot.send_message(
            payment["user_id"],
            f"✅ <b>Payment Accepted!</b>\n{credited}",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        pass
    amount_note = f"{payment['gems']} gems" if is_gems else f"{payment['coins']} coins"
    await log_admin_action(context.bot, admin.id, f"✅ Accepted payment #{payment_id} for user {payment['user_id']} ({amount_note})")


async def cb_payment_reject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    admin = update.effective_user
    if not await require_owner(update):
        return
    payment_id = int(query.data.split(":")[2])
    context.user_data["reject_payment_id"] = payment_id
    context.user_data["reject_chat_msg"] = (query.message.chat_id, query.message.message_id)
    await query.answer()
    await query.message.reply_text(
        "✏️ Enter rejection reason (or send - to skip):"
    )
    context.user_data["awaiting_reject_reason"] = True


async def handle_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_reject_reason"):
        return
    context.user_data["awaiting_reject_reason"] = False
    reason = update.message.text.strip()
    reason = "" if reason == "-" else reason
    payment_id = context.user_data.pop("reject_payment_id")
    reject_chat_msg = context.user_data.pop("reject_chat_msg", None)

    doc = await _sqlite_db.payments.find_one_and_update(
        {"payment_id": payment_id, "status": "pending"},
        {"$set": {"status": "rejected", "admin_id": update.effective_user.id, "reason": reason}},
        projection={"_id": 0},
        return_document=ReturnDocument.AFTER,
    )
    if not doc:
        await update.message.reply_text("⚠️ Already processed.")
        return
    payment = SQLiteRow(doc)

    await update.message.reply_text("❌ Payment rejected and user notified.")
    if reject_chat_msg:
        try:
            await context.bot.delete_message(chat_id=reject_chat_msg[0], message_id=reject_chat_msg[1])
        except TelegramError:
            pass
    try:
        msg = "❌ <b>Payment Rejected</b>"
        if reason:
            msg += f"\nReason: {html.escape(reason)}"
        await context.bot.send_message(payment["user_id"], msg, parse_mode=ParseMode.HTML)
    except TelegramError:
        pass
    await log_admin_action(
        context.bot, update.effective_user.id,
        f"❌ Rejected payment #{payment_id} for user {payment['user_id']}" + (f"\nReason: {html.escape(reason)}" if reason else "")
    )



async def handle_daily_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    user = update.effective_user
    wallet_kb = InlineKeyboardMarkup([[InlineKeyboardButton("💰 Open Wallet", callback_data="wallet:home", style="primary")]])
    lock = await get_user_action_lock(user.id)
    async with lock:
        row = await get_user_row(user.id)
        if row and row["last_bonus_time"]:
            last = datetime.fromisoformat(row["last_bonus_time"])
            elapsed = datetime.utcnow() - last
            if elapsed < timedelta(hours=24):
                remaining = timedelta(hours=24) - elapsed
                h, rem = divmod(int(remaining.total_seconds()), 3600)
                m = rem // 60
                await update.effective_message.reply_text(
                    ui_screen(
                        "⏳", "Already Claimed Today",
                        ui_box(
                            ui_kv("🕒", "Next Bonus In", f"<b>{h}h {m}m</b>"),
                            f"<code>{ui_bar(int(elapsed.total_seconds()), 86400)}</code>",
                        ),
                        footer="Come back tomorrow to keep your streak alive 🔥",
                    ),
                    parse_mode=ParseMode.HTML,
                    reply_markup=wallet_kb,
                )
                return

        premium = await is_premium_active(user.id)
        if premium:
            reward = await get_setting_int("premium_daily_bonus", 40)
            tx_label = "Premium daily bonus claim"
        else:
            reward = await get_setting_int("daily_bonus", 25)
            tx_label = "Daily bonus claim"
        new_balance = await add_coins(user.id, reward, "daily_bonus", tx_label)
        await _sqlite_db.users.update_one(
            {"user_id": user.id}, {"$set": {"last_bonus_time": datetime.utcnow().isoformat()}}
        )
    streak = int((row["login_streak"] if row else 0) or 0)
    await update.effective_message.reply_text(
        ui_screen(
            "🎁", "Daily Bonus Claimed!",
            ui_box(
                ui_kv(COIN_E, "Received", f"<b>+{reward} Coins</b>"),
                ui_kv("💰", "New Balance", f"<b>{new_balance}</b>"),
                ui_kv("🔥", "Login Streak", f"<b>{streak}</b> day(s)"),
                "👑 <i>Premium bonus applied</i>" if premium else "",
            ),
            footer=None if premium else "👑 Premium users get a bigger daily bonus!",
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=wallet_kb,
    )


async def build_mystery_screen(user_id: int):
    pricing = await get_setting_json("mystery_box_pricing", [])
    balance = await get_balance(user_id)
    if not pricing:
        return ui_screen(
            "🎁", "Mystery Box",
            ui_box(ui_kv(COIN_E, "Your Coins", f"<b>{balance}</b>")),
            ui_box("⚠️ Mystery Box tiers are not configured yet."),
        ), None
    lines, buttons = [], []
    for p in pricing:
        can = "✅" if balance >= int(p["price"]) else "🔒"
        lines.append(f"{can} {p['label']} — 🪙 <b>{p['price']}</b>")
        buttons.append([InlineKeyboardButton(
            f"{p['label']} · {p['price']} Coins",
            callback_data=f"mystery:open:{p['tier']}:{p['price']}", style="success",
        )])
    text = ui_screen(
        "🎁", "Mystery Box",
        ui_box(ui_kv(COIN_E, "Your Coins", f"<b>{balance}</b>")),
        ui_box(*lines),
        footer="Every box gives a file you don't own yet — or your coins back.",
    )
    return text, InlineKeyboardMarkup(buttons)



async def handle_mystery_box(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    text, kb = await build_mystery_screen(update.effective_user.id)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_mystery_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    text, kb = await build_mystery_screen(update.effective_user.id)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_mystery_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await guard_user(update, context):
        return
    user = update.effective_user
    _, _, tier, _cb_price = query.data.split(":")
    # Look the price up server-side; the one in callback_data can be forged
    # (e.g. mystery:open:premium:0) or stale after a pricing change.
    price = None
    for p in await get_setting_json("mystery_box_pricing", []):
        try:
            if isinstance(p, dict) and str(p["tier"]) == tier:
                price = int(p["price"])
                break
        except (KeyError, TypeError, ValueError):
            continue
    if price is None or price <= 0:
        await query.answer("❌ This box is not available.", show_alert=True)
        return
    lock = await get_user_action_lock(user.id)

    async with lock:
        ok = await remove_coins(user.id, price, "mystery_box", f"Opened {tier} mystery box")
        if not ok:
            await query.answer("❌ Not enough coins.", show_alert=True)
            return

        async with db_conn() as db:
            db.row_factory = aiosqlite.Row
            # Files this tier has ever contained.
            cur = await db.execute(
                "SELECT file_pk FROM files WHERE is_deleted=0 AND mystery_tier=? AND currency != 'gems'", (tier,)
            )
            tier_files = await cur.fetchall()
            tier_file_pks = {row["file_pk"] for row in tier_files}

            # Files from this tier the user has already won/received before.
            cur = await db.execute(
                "SELECT file_pk FROM purchases WHERE user_id=?", (user.id,)
            )
            already_owned = {row["file_pk"] for row in await cur.fetchall()}

        remaining_pks = tier_file_pks - already_owned

        if not remaining_pks:
            await add_coins(user.id, price, "mystery_box_refund", f"No new files left in {tier} tier — refunded")
            if not tier_file_pks:
                msg = "😢 No files available in this box right now — refunded."
            else:
                msg = "🎉 You've already collected every file in this box! Coins refunded — nothing new left to open."
            await query.answer(msg, show_alert=True)
            return

        async with db_conn() as db:
            db.row_factory = aiosqlite.Row
            pick_pk = random.choice(tuple(remaining_pks))
            cur = await db.execute(
                "SELECT * FROM files WHERE file_pk=?", (pick_pk,)
            )
            f = await cur.fetchone()

        if not f:
            await add_coins(user.id, price, "mystery_box_refund", f"No files available in {tier} tier — refunded")
            await query.answer("😢 No files available in this box right now — refunded.", show_alert=True)
            return

        try:
            async with db_conn() as db:
                await db.execute(
                    "INSERT INTO purchases (user_id, file_pk, price, timestamp) VALUES (?, ?, ?, ?)",
                    (user.id, f["file_pk"], price, datetime.utcnow().isoformat()),
                )
                await db.commit()
        except Exception:
            # Never keep the user's coins when fulfillment failed.
            await add_coins(user.id, price, "mystery_box_refund", "Mystery box purchase could not be saved")
            await query.answer("⚠️ Could not save the purchase — coins refunded.", show_alert=True)
            return

    await query.answer("🎉 You won a file!")
    icon = FILE_TYPE_ICON.get(f["file_kind"], "📄")
    await query.edit_message_text(
        ui_screen(
            "🎉", "Mystery Box Opened!",
            ui_box(
                ui_kv(icon, "You Won", f"<b>{html.escape(f['file_name'])}</b>"),
                ui_kv("📦", "Size", fmt_size(f["file_size"])),
                ui_kv(COIN_E, "Paid", f"{price} Coins"),
            ),
            footer="Added to 🛍 My Purchases.",
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇ Download Now", callback_data=f"file:dl:{f['file_pk']}", style="success"),
             InlineKeyboardButton("🎁 Open Another", callback_data="mystery:home", style="primary")],
        ]),
    )



async def handle_invite_friends(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    context.user_data["refer_back"] = None
    text, kb = await build_refer_screen(update.effective_user.id)
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_my_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    per_page = 10
    user = update.effective_user
    total, rows = await asyncio.gather(
        _sqlite_db.referrals.count_documents({"referrer_id": user.id}),
        _sqlite_db.referrals.find({"referrer_id": user.id}, {"_id": 0})
        .sort("date", -1).skip(page * per_page).limit(per_page).to_list(length=per_page),
    )
    total_pages = max(1, (total + per_page - 1) // per_page)
    if not rows:
        body = ui_box("😴 You haven't referred anyone yet.", "<i>Share your link to start earning!</i>")
    else:
        users = await asyncio.gather(*(get_user_row(r.get("new_user_id")) for r in rows))
        lines = []
        for i, (r, u) in enumerate(zip(rows, users), start=page * per_page + 1):
            label = f"@{u['username']}" if u and u["username"] else (u["first_name"] if u else f"User {r.get('new_user_id')}")
            lines.append(
                f"<b>{i}.</b> {html.escape(label or '—')}  ·  🪙 +{r.get('reward') or 0}\n"
                f"      <i>{fmt_date(r.get('date'))}</i>"
            )
        body = ui_box(*lines)
    text = ui_screen("👥", "My Referrals", body, subtitle=f"Total: {total}")
    kb_rows = []
    nav = pager_row("myrefs:", page, total_pages)
    if nav:
        kb_rows.append(nav)
    kb_rows.append(back_row("refer:home"))
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb_rows))


async def handle_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    user = update.effective_user
    rows = await _sqlite_db.referrals.aggregate([
        {"$group": {"_id": "$referrer_id", "cnt": {"$sum": 1}}},
        {"$sort": {"cnt": -1}},
        {"$limit": 10},
    ]).to_list(length=10)
    my_count = await _sqlite_db.referrals.count_documents({"referrer_id": user.id})
    if not rows:
        await update.effective_message.reply_text(
            ui_screen("🏆", "Leaderboard", ui_box("No referrals yet — be the first! 🚀")),
            parse_mode=ParseMode.HTML,
        )
        return
    user_rows = await asyncio.gather(*(get_user_row(r["_id"]) for r in rows))
    medals = ["🥇", "🥈", "🥉"]
    top = rows[0]["cnt"] or 1
    lines = []
    for i, (r, u) in enumerate(zip(rows, user_rows)):
        name = html.escape((u["first_name"] if u else None) or "Unknown")
        if r["_id"] == user.id:
            name = f"<u>{name}</u> (you)"
        rank = medals[i] if i < 3 else f"<b>{i + 1}.</b>"
        lines.append(f"{rank} {name} — <b>{r['cnt']}</b>")
        if i < 3:
            lines.append(f"      <code>{ui_bar(r['cnt'], top, 8)}</code>")
    if my_count:
        ahead = await _sqlite_db.referrals.aggregate([
            {"$group": {"_id": "$referrer_id", "cnt": {"$sum": 1}}},
            {"$match": {"cnt": {"$gt": my_count}}},
            {"$count": "n"},
        ]).to_list(length=1)
        my_rank = (ahead[0]["n"] if ahead else 0) + 1
        mine = ui_box(ui_kv("📍", "Your Rank", f"<b>#{my_rank}</b>  ·  {my_count} referrals"))
    else:
        mine = ui_box("📍 You're not ranked yet — invite a friend to join the board!")
    await update.effective_message.reply_text(
        ui_screen("🏆", "Top 10 Referrers", ui_box(*lines), mine),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔥 Refer & Earn", callback_data="refer:home", style="success")]]),
    )



async def handle_redeem_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    text, kb = _redeem_center()
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


def _redeem_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="redeem:cancel", style="danger")]])


def _redeem_center():
    text = ui_screen(
        "🎟", "Redeem Center",
        ui_box(
            "🔑 <b>Redeem a Code</b> — got a code? Claim its reward.",
            "🎁 <b>Gift Code</b> — turn your coins into a shareable code.",
        ),
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Redeem Code", callback_data="redeem:enter", style="success"),
         InlineKeyboardButton("🎁 Create Gift", callback_data="redeem:gift", style="primary")],
    ])
    return text, kb


async def cb_redeem_enter_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        ui_screen("🔑", "Redeem a Code", ui_box("✍️ Send your redeem code now.", "<i>Example: NOBITA2026</i>")),
        parse_mode=ParseMode.HTML,
        reply_markup=_redeem_cancel_kb(),
    )
    return RD_CODE


async def cb_redeem_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("❌ Cancelled")
    text, kb = _redeem_center()
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return ConversationHandler.END


async def handle_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip().upper()
    user = update.effective_user
    lock = await get_user_action_lock(user.id)

    async with lock:
        async with db_conn() as db:
            db.row_factory = aiosqlite.Row
            cur = await db.execute("SELECT * FROM redeems WHERE code=?", (code,))
            redeem = await cur.fetchone()

            admin = await is_admin(user.id)
            if not redeem:
                await update.message.reply_text("❌ Invalid Redeem Code.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END

            if (redeem["status"] or "active") != "active":
                await update.message.reply_text("❌ This code is no longer active.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END

            if redeem["expiry_date"]:
                try:
                    if datetime.fromisoformat(redeem["expiry_date"]) < datetime.utcnow():
                        await db.execute("UPDATE redeems SET status='expired' WHERE code=?", (code,))
                        await db.commit()
                        await update.message.reply_text("❌ This code has expired.", reply_markup=user_reply_keyboard(admin))
                        return ConversationHandler.END
                except ValueError:
                    pass

            usage_limit = int(redeem["usage_limit"] or 0)
            used_count = int(redeem["used_count"] or 0)
            if usage_limit and used_count >= usage_limit:
                await update.message.reply_text("❌ This code has reached its usage limit.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END

            cur = await db.execute(
                "SELECT 1 FROM redeem_uses WHERE code=? AND user_id=?", (code, user.id)
            )
            if await cur.fetchone():
                await update.message.reply_text("❌ You have already redeemed this code.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END

            # Reserve one use atomically. The per-user lock does not stop two
            # DIFFERENT users from both passing the limit check above.
            limit_filter = {"code": code, "status": {"$in": ["active", None]}}
            if usage_limit:
                limit_filter["$expr"] = {"$lt": [{"$ifNull": ["$used_count", 0]}, usage_limit]}
            reserved = await _sqlite_db.redeems.find_one_and_update(
                limit_filter, {"$inc": {"used_count": 1}}
            )
            if not reserved:
                await update.message.reply_text("❌ This code has reached its usage limit.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END
            try:
                await db.execute(
                    "INSERT INTO redeem_uses (code, user_id, timestamp) VALUES (?, ?, ?)",
                    (code, user.id, datetime.utcnow().isoformat()),
                )
            except Exception:
                await _sqlite_db.redeems.update_one({"code": code}, {"$inc": {"used_count": -1}})
                await update.message.reply_text("❌ You have already redeemed this code.", reply_markup=user_reply_keyboard(admin))
                return ConversationHandler.END

        # Normalise legacy stored values before wallet/premium writes.
        coin_reward = int(redeem["coin_reward"] or 0)
        premium_days = int(redeem["premium_days"] or 0)
        if coin_reward:
            await add_coins(user.id, coin_reward, "redeem", f"Redeem code {code}")
        if premium_days:
            await grant_premium(user.id, premium_days, admin_id=0)

    msg = f"✅ <b>Redeem Successful!</b>\n🪙 +{coin_reward} Coins"
    if premium_days:
        msg += f"\n⭐ +{premium_days} Days Premium"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=user_reply_keyboard(admin))
    return ConversationHandler.END



def _generate_gift_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "GIFT" + "".join(secrets.choice(alphabet) for _ in range(8))


async def cb_redeem_gift_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    balance = await get_balance(update.effective_user.id)
    await query.edit_message_text(
        ui_screen(
            "🎁", "Convert Coins to Gift Code",
            ui_box(ui_kv(COIN_E, "Your Coins", f"<b>{balance}</b>")),
            ui_box("✍️ Send how many coins to convert.",
                   "<i>Anyone can redeem the code once for that many coins.</i>"),
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=_redeem_cancel_kb(),
    )
    return GC_AMOUNT


async def conv_gift_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Please enter a valid positive number of coins.")
        return GC_AMOUNT
    amount = int(text)
    user = update.effective_user
    lock = await get_user_action_lock(user.id)

    async with lock:
        ok = await remove_coins(user.id, amount, "gift_code_created", f"Converted {amount} coins to a gift code")
        if not ok:
            await update.message.reply_text("❌ You don't have enough coins for that.")
            return ConversationHandler.END

        code = _generate_gift_code()
        code_saved = False
        try:
            async with db_conn() as db:
                for _ in range(5):
                    cur = await db.execute("SELECT 1 FROM redeems WHERE code=?", (code,))
                    if not await cur.fetchone():
                        break
                    code = _generate_gift_code()
                await db.execute(
                    "INSERT INTO redeems (code, coin_reward, premium_days, usage_limit, status, created_by, created_at, source) "
                    "VALUES (?, ?, 0, 1, 'active', ?, ?, 'user')",
                    (code, amount, user.id, datetime.utcnow().isoformat()),
                )
                await db.commit()
                # The SQLite compatibility layer is intentionally lightweight;
                # verify the write instead of assuming execute() implies that
                # the document was persisted.
                cur = await db.execute(
                    "SELECT code FROM redeems WHERE code=? AND created_by=?",
                    (code, user.id),
                )
                code_saved = (await cur.fetchone()) is not None
                if not code_saved:
                    raise RuntimeError("gift code was not found after creation")
        except Exception as e:
            log.exception("Gift code creation failed for user %s: %s", user.id, e)
            # The debit and code creation are separate SQLite operations. If
            # the second operation fails, restore the exact amount.
            try:
                await add_coins(user.id, amount, "gift_code_refund", "Gift code creation failed")
                await update.message.reply_text("⚠️ Gift code creation failed. Your coins were refunded.")
            except Exception:
                log.exception("Could not refund %s coins after gift code failure for user %s", amount, user.id)
                await update.message.reply_text(
                    "⚠️ Gift code creation failed. Please contact an admin; your failed "
                    "conversion has been logged for refund."
                )
            return ConversationHandler.END

        # Send the success reply INSIDE this try scope so that if the send
        # itself fails (network hiccup, HTML parse error, etc.) we catch it
        # and still show the user their code — instead of coins being
        # deducted, the code existing in DB, but the user seeing nothing.
        try:
            await update.message.reply_text(
                f"✅ <b>Gift Code Created!</b>\n\n🎟 Code: <code>{code}</code>\n🪙 Value: <b>{amount} Coins</b>\n\n"
                "Share this code with anyone — they can redeem it once via 🎟️ Redeem Code → Redeem a Code.",
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            log.exception("Failed to deliver gift code %s to user %s: %s", code, user.id, e)
            # Coins are already deducted and the code exists in DB — do NOT
            # refund here (that would let them redeem it AND get coins back).
            # Fall back to a plain-text message so they still get the code.
            try:
                await update.message.reply_text(
                    f"✅ Gift Code Created!\nCode: {code}\nValue: {amount} Coins\n\n"
                    "(Formatted message failed to send — here it is in plain text.)"
                )
            except Exception:
                log.exception("Could not deliver gift code %s to user %s even as plain text", code, user.id)

    return ConversationHandler.END



async def handle_my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    user = update.effective_user
    row, balance, gems, purchased, refs, redeems, premium_line = await asyncio.gather(
        get_user_row(user.id),
        get_balance(user.id),
        get_gems(user.id),
        _sqlite_db.purchases.count_documents({"user_id": user.id}),
        _sqlite_db.referrals.count_documents({"referrer_id": user.id}),
        _sqlite_db.redeem_uses.count_documents({"user_id": user.id}),
        premium_status_line(user.id),
    )
    streak = int((row["login_streak"] if row else 0) or 0)
    rewards = _reward_steps(await get_setting_json("streak_rewards", []), "days")
    nxt = next((r for r in rewards if streak < r["days"]), None)
    streak_box = ui_box(
        ui_kv("🔥", "Login Streak", f"<b>{streak}</b> day(s)"),
        (f"<code>{ui_bar(streak, int(nxt['days']))}</code>\n"
         f"<i>Next: {nxt['days']} days → +{nxt['reward']} 🪙</i>") if nxt else "",
    )
    text = ui_screen(
        "📊", "My Stats",
        ui_box(
            ui_kv("🆔", "User ID", f"<code>{user.id}</code>"),
            ui_kv("📅", "Joined", fmt_date(row["join_date"]) if row else "—"),
            premium_line,
        ),
        ui_box(
            ui_kv(COIN_E, "Coins", f"<b>{balance}</b>"),
            ui_kv(GEM_E, "Gems", f"<b>{gems}</b>"),
        ),
        ui_box(
            ui_kv("📁", "Files Owned", f"<b>{purchased}</b>"),
            ui_kv("👥", "Referrals", f"<b>{refs}</b>"),
            ui_kv("🎟", "Codes Redeemed", f"<b>{redeems}</b>"),
        ),
        streak_box,
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 My Wallet", callback_data="wallet:home", style="primary"),
         InlineKeyboardButton("🛍 My Purchases", callback_data="purchases:0", style="primary")],
    ])
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)



BF_MEDIA_KIND_LABEL = {"photo": "🖼 Photo", "video": "🎬 Video", "animation": "🎞 GIF"}


async def _bfmedia_get() -> tuple[str, str]:
    return (
        await get_setting("buyfiles_media_file_id", ""),
        await get_setting("buyfiles_media_type", ""),
    )


async def send_bf_media(chat, file_id: str, media_type: str, caption: str, kb=None):
    """Send the Buy Files media in whatever format the admin saved."""
    # Values written by older versions used a few different spellings.
    # Normalising them keeps existing SQLite settings usable after upgrade.
    media_type = (media_type or "").strip().lower()
    if media_type in {"gif", "mp4_animation"}:
        media_type = "animation"
    if media_type == "photo":
        return await chat.send_photo(file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    if media_type == "video":
        return await chat.send_video(file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    if media_type == "animation":
        return await chat.send_animation(file_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)
    return await chat.send_message(caption, parse_mode=ParseMode.HTML, reply_markup=kb)


def bfmedia_panel_keyboard(has_media: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        "♻ Change Media" if has_media else "🖼 Set Media", callback_data="bfm:set", style="primary")]]
    if has_media:
        rows.append([
            InlineKeyboardButton("👁 Preview", callback_data="bfm:preview", style="primary"),
            InlineKeyboardButton("🗑 Remove Media", callback_data="bfm:remove", style="primary"),
        ])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    return InlineKeyboardMarkup(rows)


async def bfmedia_panel_text() -> str:
    file_id, media_type = await _bfmedia_get()
    if file_id:
        status = (
            f"✅ Current Media : <b>{BF_MEDIA_KIND_LABEL.get(media_type, media_type)}</b>\n"
            f"🆔 File ID : <code>{html.escape(file_id[:40])}...</code>"
        )
    else:
        status = "❌ No media set — 📁 Buy Files will show plain text only."
    return (
        "🖼 <b>Buy Files Media Manager</b>\n\n"
        f"{status}\n\n"
        "Photo, video or GIF — jo set karoge wahi 📁 Buy Files menu ke sath dikhega.\n"
        "Ye permanently save hota hai, restart ke baad bhi rehta hai.\n\n"
        f"{DIVIDER}\n"
        "Choose an action below 👇"
    )


async def _bfmedia_guard(update: Update) -> bool:
    if await is_admin(update.effective_user.id):
        return True
    if update.callback_query:
        await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
    else:
        await update.effective_message.reply_text(ADMIN_ONLY_MSG)
    return False


async def cb_admin_bfmedia_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _bfmedia_guard(update):
        return
    file_id, _ = await _bfmedia_get()
    text = await bfmedia_panel_text()
    kb = bfmedia_panel_keyboard(bool(file_id))
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except TelegramError:
            pass
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_bfmedia_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _bfmedia_guard(update):
        return
    query = update.callback_query
    file_id, media_type = await _bfmedia_get()
    if not file_id:
        await query.answer("❌ No media set yet.", show_alert=True)
        return
    await query.answer("Sending preview...")
    try:
        await send_bf_media(
            update.effective_chat, file_id, media_type,
            "👁 <b>Preview</b> — this media is shown with 📁 Buy Files.",
            InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Media Manager", callback_data="ad:bfmedia", style="primary")]]),
        )
    except TelegramError as e:
        await update.effective_chat.send_message(f"❌ Preview failed: {html.escape(str(e))}\n\nMedia shayad delete ho chuka hai — naya set karo.")


async def cb_bfmedia_remove_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _bfmedia_guard(update):
        return
    query = update.callback_query
    file_id, _ = await _bfmedia_get()
    if not file_id:
        await query.answer("❌ No media set yet.", show_alert=True)
        return
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Remove", callback_data="bfm:removeyes", style="primary")],
        [InlineKeyboardButton("⬅ Cancel", callback_data="ad:bfmedia", style="primary")],
    ])
    await query.edit_message_text(
        "🗑 <b>Remove Buy Files Media?</b>\n\n"
        "Iske baad 📁 Buy Files sirf text message ke roop me aayega.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )


async def cb_bfmedia_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _bfmedia_guard(update):
        return
    query = update.callback_query
    await set_setting("buyfiles_media_file_id", "")
    await set_setting("buyfiles_media_type", "")
    await query.answer("✅ Media removed")
    await query.edit_message_text(
        await bfmedia_panel_text(), parse_mode=ParseMode.HTML,
        reply_markup=bfmedia_panel_keyboard(False),
    )


async def cb_admin_bfmedia_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _bfmedia_guard(update):
        return ConversationHandler.END
    prompt = (
        "🖼 <b>Set Buy Files Media</b>\n\n"
        "Send a <b>photo, video or GIF</b> to show at the top of the 📁 Buy Files menu.\n"
        "It's saved permanently and will still be there after a restart.\n\n"
        "Send /cancel to abort."
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(prompt, parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text(prompt, parse_mode=ParseMode.HTML)
    return BF_MEDIA


async def conv_bfmedia_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.photo:
        file_id, media_type = msg.photo[-1].file_id, "photo"
    elif msg.video:
        file_id, media_type = msg.video.file_id, "video"
    elif msg.animation:
        file_id, media_type = msg.animation.file_id, "animation"
    else:
        await msg.reply_text("❌ Please send a photo, video or GIF, or /cancel.")
        return BF_MEDIA
    # Save both fields in one SQLite round trip.  Saving them separately
    # briefly produced a valid file_id with an empty type, which made the
    # next Buy Files request silently fall back to text.
    await _sqlite_db.settings.bulk_write([
        UpdateOne(
            {"key": "buyfiles_media_file_id"},
            {"$set": {"key": "buyfiles_media_file_id", "value": file_id}},
            upsert=True,
        ),
        UpdateOne(
            {"key": "buyfiles_media_type"},
            {"$set": {"key": "buyfiles_media_type", "value": media_type}},
            upsert=True,
        ),
    ])
    async with _settings_cache_lock:
        _settings_cache["buyfiles_media_file_id"] = file_id
        _settings_cache["buyfiles_media_type"] = media_type
    await msg.reply_text(
        f"✅ Buy Files media updated ({BF_MEDIA_KIND_LABEL.get(media_type, media_type)})!\n"
        "Ab jab bhi koi 📁 Buy Files kholega, ye media text + buttons ke sath aayega.",
        reply_markup=bfmedia_panel_keyboard(True),
    )
    return ConversationHandler.END


# ============================================================
# WELCOME SLIDESHOW — multiple images shown as a swipeable
# Rich Message slideshow on /start (falls back to a Telegram
# media-group album for older/non-rich clients).
# ============================================================

WELCOME_SLIDES_MAX = 10


async def _welcome_slides_get() -> list[dict]:
    return await get_setting_json("welcome_slides", [])


async def _welcome_slides_set(slides: list[dict]) -> None:
    await set_setting("welcome_slides", json.dumps(slides))


def welcome_slides_panel_keyboard(count: int) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(
        "➕ Add / Replace Slides", callback_data="ws:addstart", style="primary")]]
    if count:
        rows.append([
            InlineKeyboardButton("👁 Preview", callback_data="ws:preview", style="primary"),
            InlineKeyboardButton("🗑 Clear All", callback_data="ws:clearask", style="primary"),
        ])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    return InlineKeyboardMarkup(rows)


async def welcome_slides_panel_text() -> str:
    slides = await _welcome_slides_get()
    if slides:
        status = f"✅ Current Slides : <b>{len(slides)}</b> image(s)/video(s)"
    else:
        status = "❌ No welcome slides set — /start will show a single image (Buy Files media) or text only."
    return (
        "🖼 <b>Welcome Slideshow Manager</b>\n\n"
        f"{status}\n\n"
        f"Photos/videos ek ke baad ek bhejo (max {WELCOME_SLIDES_MAX}) — /start pe swipeable "
        "slideshow ki tarah dikhenge.\n"
        "Permanently save hota hai, restart ke baad bhi rehta hai.\n\n"
        f"{DIVIDER}\n"
        "Choose an action below 👇"
    )


async def _wslides_guard(update: Update) -> bool:
    if await is_admin(update.effective_user.id):
        return True
    if update.callback_query:
        await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
    else:
        await update.effective_message.reply_text(ADMIN_ONLY_MSG)
    return False


async def cb_admin_wslides_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _wslides_guard(update):
        return
    slides = await _welcome_slides_get()
    text = await welcome_slides_panel_text()
    kb = welcome_slides_panel_keyboard(len(slides))
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
            return
        except TelegramError:
            pass
        await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_wslides_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _wslides_guard(update):
        return
    query = update.callback_query
    slides = await _welcome_slides_get()
    if not slides:
        await query.answer("❌ No slides set yet.", show_alert=True)
        return
    await query.answer("Sending preview...")
    sent = await _send_legacy_media_group(context.bot, update.effective_chat.id, slides)
    if not sent:
        await update.effective_chat.send_message("❌ Preview failed — media shayad delete ho chuka hai, naya set karo.")


async def cb_wslides_clear_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _wslides_guard(update):
        return
    query = update.callback_query
    slides = await _welcome_slides_get()
    if not slides:
        await query.answer("❌ No slides set yet.", show_alert=True)
        return
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Clear All", callback_data="ws:clearyes", style="primary")],
        [InlineKeyboardButton("⬅ Cancel", callback_data="ad:wslides", style="primary")],
    ])
    await query.edit_message_text(
        "🗑 <b>Clear All Welcome Slides?</b>\n\n"
        "Iske baad /start sirf single image (Buy Files media) ya text dikhayega.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )


async def cb_wslides_clear_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _wslides_guard(update):
        return
    query = update.callback_query
    await _welcome_slides_set([])
    await query.answer("✅ Slides cleared")
    await query.edit_message_text(
        await welcome_slides_panel_text(), parse_mode=ParseMode.HTML,
        reply_markup=welcome_slides_panel_keyboard(0),
    )


async def cb_wslides_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await _wslides_guard(update):
        return ConversationHandler.END
    context.user_data["ws_pending"] = []
    prompt = (
        "🖼 <b>Add Welcome Slides</b>\n\n"
        f"Photos ya videos ek ke baad ek bhejo (max {WELCOME_SLIDES_MAX}).\n"
        "Jab ho jaaye, <b>✅ Save</b> dabao. Ye purani slides ko replace karega.\n\n"
        "Send /cancel to abort."
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(prompt, parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text(prompt, parse_mode=ParseMode.HTML)
    return WS_COLLECT


def _wslides_collect_keyboard(count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Save ({count})", callback_data="ws:save", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="ws:cancel", style="primary")],
    ])


async def conv_wslides_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    if msg.photo:
        file_id, media_type = msg.photo[-1].file_id, "photo"
    elif msg.video:
        file_id, media_type = msg.video.file_id, "video"
    elif msg.animation:
        file_id, media_type = msg.animation.file_id, "animation"
    else:
        await msg.reply_text("❌ Please send a photo or video, or /cancel.")
        return WS_COLLECT

    pending = context.user_data.setdefault("ws_pending", [])
    if len(pending) >= WELCOME_SLIDES_MAX:
        await msg.reply_text(
            f"⚠ Max {WELCOME_SLIDES_MAX} slides reached. Tap ✅ Save to finish.",
            reply_markup=_wslides_collect_keyboard(len(pending)),
        )
        return WS_COLLECT

    pending.append({"file_id": file_id, "type": media_type})
    await msg.reply_text(
        f"➕ Added ({len(pending)}/{WELCOME_SLIDES_MAX}). Bhejte raho ya ✅ Save dabao.",
        reply_markup=_wslides_collect_keyboard(len(pending)),
    )
    return WS_COLLECT


async def cb_wslides_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    pending = context.user_data.pop("ws_pending", [])
    if not pending:
        await query.answer("❌ No slides added yet.", show_alert=True)
        return WS_COLLECT
    await _welcome_slides_set(pending)
    await query.answer("✅ Saved!")
    await query.edit_message_text(
        f"✅ Welcome slideshow updated ({len(pending)} slide(s))!\n"
        "Ab /start pe ye images swipeable slideshow ki tarah dikhenge."
    )
    return ConversationHandler.END


async def cb_wslides_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    context.user_data.pop("ws_pending", None)
    await query.answer("Cancelled")
    await query.edit_message_text("❌ Cancelled — no changes made.")
    return ConversationHandler.END


async def handle_buy_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard_user(update, context):
        return
    # Bot API 10.2 Rich Message draft: show a temporary loading preview while
    # SQLite builds the catalogue. send_file_list then persists the final card.
    draft_id = max(1, int(time.time() * 1000) % 2_147_483_647)
    await send_rich_draft_or_ignore(
        context.bot,
        update.effective_chat.id,
        draft_id,
        "<h2>📦 Loading Buy Files</h2><p>⏳ Preparing the latest catalogue...</p>",
    )
    await send_file_list(update, context, page=0)


def _rich_files_html(total_files: int, total_coins: int, rows) -> str:
    """Build the native Rich HTML version of the Buy Files catalogue."""
    table_rows = []
    for row in rows:
        name = html.escape(str(row.get("file_name") or "Unnamed file"))
        price = int(row.get("price") or 0)
        price_label = "🆓 FREE" if price == 0 else f"🪙 {price} Coins"
        table_rows.append(
            f"<tr><td>{name}</td><td>{price_label}</td></tr>"
        )

    if not table_rows:
        table = "<p>No files available right now.</p>"
    else:
        table = (
            "<table bordered>"
            "<tr><td><b>File</b></td><td><b>Price</b></td></tr>"
            + "".join(table_rows)
            + "</table>"
        )

    return (
        "<h1>📦 Buy Files</h1>"
        f"<p>📁 Total files: <b>{total_files}</b> · "
        f"🪙 Your coins: <b>{total_coins}</b></p>"
        "<details>"
        "<summary>🌟 File features</summary>"
        "<ul>"
        "<li>🎖 High quality files</li>"
        "<li>🎖 Regularly updated</li>"
        "<li>🎖 Premium files available</li>"
        "</ul>"
        "</details>"
        f"{table}"
        "<footer>👇 Select a file below to view details and price</footer>"
    )


FILES_PER_PAGE = 15          # 15 files per page (one file per row)
CLAIM_ALL_MAX = 300          # safety cap for one "Claim All" run
_claim_all_running: set[int] = set()


async def _buyfiles_header(total_files: int, coins: int, gems: int) -> str:
    return (
        '<tg-emoji emoji-id="5409380072291316349">📦</tg-emoji> <b>Buy Files</b> !!\n\n'
        f'<tg-emoji emoji-id="5357315181649076022">📁</tg-emoji> Tᴏᴛᴀʟ Fɪʟᴇꜱ : <b>{total_files}</b>\n'
        f'{COIN_E} Yᴏᴜʀ Cᴏɪɴꜱ : <b>{coins}</b>\n'
        f'{GEM_E} Yᴏᴜʀ Gᴇᴍꜱ : <b>{gems}</b>\n\n'
        '<u><tg-emoji emoji-id="6079992177079886098">🌟</tg-emoji></u><u> File Features</u>\n\n'
        '<tg-emoji emoji-id="6080033885507296503">🎖</tg-emoji>High Quality Files\n'
        '<tg-emoji emoji-id="6080033885507296503">🎖</tg-emoji>Regularly Updated\n'
        '<tg-emoji emoji-id="6080033885507296503">🎖</tg-emoji>Premium Files Available\n\n'
        "━━━━━━━━━━━━━━━━━━\n"
        '<tg-emoji emoji-id="6203998186541948045">👑</tg-emoji> <b>Select A File Below</b>\n\n'
        '<tg-emoji emoji-id="5301038027601098171">👇</tg-emoji>View File Details &amp; Price'
    )


async def send_file_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, edit: bool = False) -> None:
    per_page = FILES_PER_PAGE
    file_filter = {"is_deleted": 0}
    viewer_id = update.effective_user.id
    rows, total_files, wallet_doc = await asyncio.gather(
        _sqlite_db.files.find(
            file_filter,
            {"_id": 0, "file_pk": 1, "file_name": 1, "price": 1, "currency": 1},
        ).sort("file_pk", -1).skip(page * per_page).limit(per_page).to_list(length=per_page),
        _sqlite_db.files.count_documents(file_filter),
        _sqlite_db.wallet.find_one({"user_id": viewer_id}, {"_id": 0, "coins": 1, "gems": 1}),
    )
    coins = int((wallet_doc or {}).get("coins", 0) or 0)
    gems = int((wallet_doc or {}).get("gems", 0) or 0)
    total_pages = max(1, (total_files + per_page - 1) // per_page)

    if not rows:
        text = "📦 <b>Buy Files</b> !!\n\nNo files available right now."
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍 My Purchases", callback_data="purchases:0", style="danger")],
        ])
    else:
        text = await _buyfiles_header(total_files, coins, gems)
        buttons = []
        for r in rows:
            price = int(r.get("price") or 0)
            label = f"{r['file_name']} {price_text(price, file_currency(r))}"
            buttons.append([InlineKeyboardButton(
                label, callback_data=f"file:view:{r['file_pk']}:{page}", style="primary"
            )])
        nav = pager_row("files:list:", page, total_pages, style="success")
        if nav:
            buttons.append(nav)
        buttons.append([
            InlineKeyboardButton("📥 Claim All Files", callback_data="claimall:ask:all", style="success"),
        ])
        buttons.append([
            InlineKeyboardButton("🛍 My Purchases", callback_data="purchases:0", style="danger"),
            InlineKeyboardButton("💎 Buy Gems", callback_data="gems:buy", style="primary"),
        ])
        kb = InlineKeyboardMarkup(buttons)

    # ---- SAME MESSAGE EDIT (text msg -> text edit, media msg -> caption edit)
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        return

    # ---- fresh screen (from the keyboard "Buy Files" button).  Classic
    # messages are used on purpose: unlike Rich Messages they can be edited
    # in place by every following button.
    media_file_id, media_type = await _bfmedia_get()
    if media_file_id:
        try:
            await _send_legacy_media(
                context.bot, update.effective_chat.id, media_file_id, media_type, text, kb
            )
            return
        except TelegramError as exc:
            log.warning("Buy Files media failed, sending text instead: %s", exc)
    await context.bot.send_message(
        update.effective_chat.id, text, parse_mode=ParseMode.HTML, reply_markup=kb
    )


async def cb_files_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[2])
    await send_file_list(update, context, page, edit=True)


async def _get_file(file_pk: int):
    return await _sqlite_db.files.find_one({"file_pk": file_pk, "is_deleted": 0}, {"_id": 0})


async def _owns_file(user_id: int, file_pk: int) -> bool:
    return bool(await _sqlite_db.purchases.find_one({"user_id": user_id, "file_pk": file_pk}, {"_id": 1}))


async def get_effective_price_for_file(user_id: int, f) -> int:
    """Premium discount only applies to Coin files — Gems are paid currency."""
    price = int(f.get("price") or 0)
    if file_currency(f) == "gems":
        return max(0, price)
    return await get_effective_file_price(user_id, price)


async def cb_file_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    file_pk = int(parts[2])
    back_page = int(parts[3]) if len(parts) > 3 else 0
    user = update.effective_user

    f, owned = await asyncio.gather(_get_file(file_pk), _owns_file(user.id, file_pk))
    if not f:
        await query.edit_message_text(
            "❌ File not found (it may have been removed).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data=f"files:list:{back_page}", style="primary")]]),
        )
        return

    currency = file_currency(f)
    listed = int(f.get("price") or 0)
    icon = FILE_TYPE_ICON.get(f.get("file_kind"), "📄")
    effective_price = await get_effective_price_for_file(user.id, f)
    desc = html.escape(f["description"]) if f.get("description") else "<i>No description</i>"
    info_box = ui_box(
        ui_kv("📦", "Size", f"<b>{fmt_size(f.get('file_size') or 0)}</b>"),
        ui_kv("🗂", "Type", html.escape((f.get("file_kind") or "document").title())),
        ui_kv("⬇", "Downloads", f"<b>{int(f.get('downloads_count') or 0)}</b>"),
        ui_kv("📅", "Added", fmt_date(f.get("upload_date"))),
    )
    if owned:
        price_box = ui_box("✅ <b>You own this file</b> — download any time.")
        buttons = [[InlineKeyboardButton("⬇ Download", callback_data=f"file:dl:{file_pk}", style="success")]]
    elif listed == 0:
        price_box = ui_box("🆓 <b>FREE</b> — no coins needed.")
        buttons = [[InlineKeyboardButton("⬇ Download Free", callback_data=f"file:dl:{file_pk}", style="success")]]
    else:
        if currency == "gems":
            have = await get_gems(user.id)
            price_line = ui_kv(GEM_E, "Price", f"<b>{effective_price} Gems</b>")
            have_line = ui_kv("👛", "You Have", f"{have} Gems {'✅' if have >= effective_price else '❌'}")
        else:
            have = await get_balance(user.id)
            if effective_price < listed:
                price_line = ui_kv(COIN_E, "Price", f"<s>{listed}</s> <b>{effective_price} Coins</b> 👑")
            else:
                price_line = ui_kv(COIN_E, "Price", f"<b>{effective_price} Coins</b>")
            have_line = ui_kv("👛", "You Have", f"{have} Coins {'✅' if have >= effective_price else '❌'}")
        price_box = ui_box(price_line, have_line)
        buy_label = "💎 Buy with Gems" if currency == "gems" else "🛒 Buy Now"
        buttons = [[InlineKeyboardButton(buy_label, callback_data=f"file:buy:{file_pk}", style="success")]]
    text = ui_screen(
        icon, html.escape(f["file_name"]),
        ui_box(f"📝 {desc}"),
        info_box,
        price_box,
    )
    buttons.append([InlineKeyboardButton("⬅ Back to Files", callback_data=f"files:list:{back_page}", style="primary")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_file_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await guard_user(update, context):
        return
    file_pk = int(query.data.split(":")[2])
    user = update.effective_user
    back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Files", callback_data="files:list:0", style="primary")]])
    lock = await get_user_action_lock(user.id)
    async with lock:
        f = await _get_file(file_pk)
        if not f:
            await query.edit_message_text("❌ File not found.", reply_markup=back_kb)
            return
        if await _owns_file(user.id, file_pk):
            await query.edit_message_text(
                "✅ You already own this file.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬇ Download", callback_data=f"file:dl:{file_pk}", style="success")],
                    [InlineKeyboardButton("⬅ Back to Files", callback_data="files:list:0", style="primary")],
                ]),
            )
            return

        currency = file_currency(f)
        effective_price = await get_effective_price_for_file(user.id, f)
        if effective_price > 0:
            if currency == "gems":
                ok = await remove_gems(user.id, effective_price, "purchase", f"Purchased file: {f['file_name']}")
            else:
                ok = await remove_coins(user.id, effective_price, "purchase", f"Purchased file: {f['file_name']}")
            if not ok:
                if currency == "gems":
                    have = await get_gems(user.id)
                    await query.edit_message_text(
                        f"❌ <b>Not enough Gems.</b>\n\n{GEM_E} Price: <b>{effective_price}</b>\n"
                        f"{GEM_E} You have: <b>{have}</b>\n\nBuy Gems with ⭐ Stars to continue.",
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💎 Buy Gems", callback_data="gems:buy", style="success")],
                            [InlineKeyboardButton("⬅ Back to Files", callback_data="files:list:0", style="primary")],
                        ]),
                    )
                else:
                    await query.edit_message_text(
                        "❌ <b>Not enough Coins.</b>\n\nPlease top up your wallet to continue.",
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("💰 Open Wallet", callback_data="wallet:home", style="primary")],
                            [InlineKeyboardButton("⬅ Back to Files", callback_data="files:list:0", style="primary")],
                        ]),
                    )
                return

        try:
            async with _db_lock:
                pid = await _next_seq("purchases", "id")
                await _sqlite_db.purchases.insert_one({
                    "id": pid,
                    "user_id": user.id,
                    "file_pk": file_pk,
                    "price": effective_price,
                    "currency": currency,
                    "timestamp": datetime.utcnow().isoformat(),
                })
        except Exception:
            log.exception("Purchase save failed for user %s file %s", user.id, file_pk)
            if effective_price > 0:
                if currency == "gems":
                    await add_gems(user.id, effective_price, "purchase_refund", f"Purchase could not be saved: {f['file_name']}")
                else:
                    await add_coins(user.id, effective_price, "purchase_refund", f"Purchase could not be saved: {f['file_name']}")
            await query.edit_message_text("⚠️ Purchase failed. Your balance has been refunded.", reply_markup=back_kb)
            return

    paid = price_text(effective_price, currency)
    await query.edit_message_text(
        ui_screen(
            "✅", "Purchase Successful!",
            ui_box(
                ui_kv("📁", "File", f"<b>{html.escape(f['file_name'])}</b>"),
                ui_kv("💳", "Paid", f"<b>{paid}</b>"),
            ),
            footer="It's yours forever — find it any time in 🛍 My Purchases.",
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬇ Download Now", callback_data=f"file:dl:{file_pk}", style="success")],
            [InlineKeyboardButton("⬅ Back to Files", callback_data="files:list:0", style="primary")],
        ]),
    )


async def _deliver_file(bot, chat_id: int, f) -> None:
    """Send a stored file with the correct Telegram method for its type."""
    kind = (f.get("file_kind") or "document").lower()
    file_id = f["tg_file_id"]
    caption = f"📄 {html.escape(f.get('file_name') or 'File')}"
    senders = {
        "document": bot.send_document, "video": bot.send_video, "audio": bot.send_audio,
        "photo": bot.send_photo, "voice": bot.send_voice, "animation": bot.send_animation,
    }
    sender = senders.get(kind, bot.send_document)
    try:
        await sender(chat_id, file_id, caption=caption, parse_mode=ParseMode.HTML)
    except BadRequest:
        if sender is bot.send_document:
            raise
        await bot.send_document(chat_id, file_id, caption=caption, parse_mode=ParseMode.HTML)


async def _record_downloads(user_id: int, file_pks: list[int]) -> None:
    if not file_pks:
        return
    try:
        async with _db_lock:
            start = await _next_seq("downloads", "id")
            now = datetime.utcnow().isoformat()
            await _sqlite_db.downloads.insert_many([
                {"id": start + i, "user_id": user_id, "file_pk": pk, "timestamp": now}
                for i, pk in enumerate(file_pks)
            ])
        await _sqlite_db.files.update_many({"file_pk": {"$in": file_pks}}, {"$inc": {"downloads_count": 1}})
    except Exception:
        log.exception("Could not record downloads for %s", user_id)


async def cb_file_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    file_pk = int(query.data.split(":")[2])
    user = update.effective_user
    f = await _get_file(file_pk)
    if not f:
        await query.answer("❌ File not found.", show_alert=True)
        return
    if int(f.get("price") or 0) > 0 and not await _owns_file(user.id, file_pk):
        await query.answer("❌ You need to purchase this file first.", show_alert=True)
        return
    await query.answer("📤 Sending file…")
    if not await guard_user(update, context):
        return
    try:
        await _deliver_file(context.bot, user.id, f)
    except TelegramError:
        try:
            await context.bot.send_message(user.id, "⚠️ Could not deliver file, please contact support.")
        except TelegramError:
            pass
        return
    await _record_downloads(user.id, [file_pk])


async def _owned_file_pks(user_id: int) -> list[int]:
    docs = await _sqlite_db.purchases.find(
        {"user_id": user_id}, {"_id": 0, "file_pk": 1}
    ).to_list(length=None)
    return list(dict.fromkeys(d.get("file_pk") for d in docs if d.get("file_pk") is not None))


async def cb_my_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except TelegramError:
        pass
    try:
        per_page = FILES_PER_PAGE
        page = int(query.data.split(":")[1]) if query.data and ":" in query.data else 0
        user = update.effective_user
        purchase_docs = await _sqlite_db.purchases.find(
            {"user_id": user.id},
            {"_id": 0, "file_pk": 1, "id": 1},
        ).sort("id", -1).to_list(length=None)
        file_ids = list(dict.fromkeys(
            p.get("file_pk") for p in purchase_docs if p.get("file_pk") is not None
        ))
        file_docs = await _sqlite_db.files.find(
            {"file_pk": {"$in": file_ids}, "is_deleted": 0},
            {"_id": 0, "file_pk": 1, "file_name": 1},
        ).to_list(length=None) if file_ids else []
        names = {f.get("file_pk"): f.get("file_name", "Unnamed file") for f in file_docs}
        all_rows = [{"file_pk": pk, "file_name": names[pk]} for pk in file_ids if pk in names]
        total_owned = len(all_rows)
        total_pages = max(1, (total_owned + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))
        rows = all_rows[page * per_page:(page + 1) * per_page]

        if not rows:
            text = ui_screen("🛍", "My Purchases", ui_box("📭 You haven't purchased any files yet.", "<i>Browse 📁 Buy Files to get started!</i>"))
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data="files:list:0", style="primary")]])
        else:
            text = ui_screen(
                "🛍", "My Purchases",
                ui_box(ui_kv("📁", "Files Owned", f"<b>{total_owned}</b>")),
                footer="Tap a file to download it, or grab everything at once 👇",
            )
            buttons = [[InlineKeyboardButton(
                f"📥 Download All ({total_owned})", callback_data="claimall:ask:owned", style="success"
            )]]
            for r in rows:
                buttons.append([InlineKeyboardButton(f"⬇ {r['file_name']}", callback_data=f"file:dl:{r['file_pk']}", style="primary")])
            nav = pager_row("purchases:", page, total_pages)
            if nav:
                buttons.append(nav)
            buttons.append([InlineKeyboardButton("⬅ Back", callback_data="files:list:0", style="primary")])
            kb = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    except Exception:
        log.exception("My Purchases callback failed for user %s", getattr(update.effective_user, "id", None))
        try:
            await query.edit_message_text(
                "⚠️ <b>My Purchases temporarily unavailable.</b>\nPlease try again.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Retry", callback_data="purchases:0", style="primary")],
                    [InlineKeyboardButton("⬅ Back", callback_data="files:list:0", style="primary")],
                ]),
            )
        except TelegramError:
            pass


# ============================================================
# 📥 CLAIM ALL — deliver every file the user can access in one tap
#   scope "all"   -> all FREE files + every file the user owns
#   scope "owned" -> only purchased files (from My Purchases)
# ============================================================
async def _claimable_files(user_id: int, scope: str) -> list[dict]:
    owned = await _owned_file_pks(user_id)
    if scope == "owned":
        if not owned:
            return []
        filt = {"is_deleted": 0, "file_pk": {"$in": owned}}
    else:
        filt = {"is_deleted": 0, "$or": [{"price": 0}, {"price": None}, {"file_pk": {"$in": owned}}]}
    return await _sqlite_db.files.find(
        filt, {"_id": 0, "file_pk": 1, "file_name": 1, "file_kind": 1, "tg_file_id": 1, "price": 1},
    ).sort("file_pk", 1).limit(CLAIM_ALL_MAX).to_list(length=CLAIM_ALL_MAX)


def _claim_back_kb(scope: str) -> InlineKeyboardMarkup:
    back = "purchases:0" if scope == "owned" else "files:list:0"
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back", callback_data=back, style="primary")]])


async def cb_claimall_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await guard_user(update, context):
        return
    scope = query.data.split(":")[2]
    files = await _claimable_files(update.effective_user.id, scope)
    if not files:
        await query.edit_message_text(
            "📥 <b>Claim All</b>\n\nNothing to claim yet — no free or purchased files found.",
            parse_mode=ParseMode.HTML, reply_markup=_claim_back_kb(scope),
        )
        return
    free_count = sum(1 for f in files if int(f.get("price") or 0) == 0)
    paid_count = len(files) - free_count
    text = (
        "📥 <b>Claim All Files</b>\n\n"
        f"🆓 Free files: <b>{free_count}</b>\n"
        f"🛍 Purchased files: <b>{paid_count}</b>\n"
        f"📦 Total to send: <b>{len(files)}</b>\n\n"
        "Tap below and every file will be sent to this chat one after another."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"✅ Claim All ({len(files)})", callback_data=f"claimall:go:{scope}", style="success")],
        [InlineKeyboardButton("⬅ Back", callback_data="purchases:0" if scope == "owned" else "files:list:0", style="primary")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


def _retry_seconds(exc: RetryAfter) -> float:
    ra = exc.retry_after
    return ra.total_seconds() if hasattr(ra, "total_seconds") else float(ra)


async def cb_claimall_go(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    if user.id in _claim_all_running:
        await query.answer("⏳ Already sending your files…", show_alert=True)
        return
    _claim_all_running.add(user.id)  # before any await, so a double tap can't start twice
    try:
        await query.answer("📥 Sending…")
        if not await guard_user(update, context):
            _claim_all_running.discard(user.id)
            return
        scope = query.data.split(":")[2]
        files = await _claimable_files(user.id, scope)
    except Exception:
        _claim_all_running.discard(user.id)
        raise
    if not files:
        _claim_all_running.discard(user.id)
        await query.edit_message_text("📥 Nothing to claim.", reply_markup=_claim_back_kb(scope))
        return

    total = len(files)
    sent_pks: list[int] = []
    failed = 0
    try:
        await query.edit_message_text(
            f"📥 <b>Claiming files…</b>\n\n⏳ Sent <b>0</b> / <b>{total}</b>", parse_mode=ParseMode.HTML
        )
        for i, f in enumerate(files, start=1):
            delivered = False
            for _attempt in range(3):
                try:
                    await _deliver_file(context.bot, user.id, f)
                    delivered = True
                    break
                except RetryAfter as exc:
                    await asyncio.sleep(_retry_seconds(exc) + 0.5)
                except TelegramError as exc:
                    log.warning("Claim-all delivery failed for file %s: %s", f.get("file_pk"), exc)
                    break
            if delivered:
                sent_pks.append(f["file_pk"])
            else:
                failed += 1
            if i % 5 == 0 and i < total:
                try:
                    await query.edit_message_text(
                        f"📥 <b>Claiming files…</b>\n\n⏳ Sent <b>{len(sent_pks)}</b> / <b>{total}</b>",
                        parse_mode=ParseMode.HTML,
                    )
                except TelegramError:
                    pass
            await asyncio.sleep(0.35)  # stay well under Telegram's per-chat limit
    finally:
        _claim_all_running.discard(user.id)

    await _record_downloads(user.id, sent_pks)
    summary = f"✅ <b>Claim Complete!</b>\n\n📦 Delivered: <b>{len(sent_pks)}</b> / <b>{total}</b>"
    if failed:
        summary += f"\n⚠️ Failed: <b>{failed}</b> (contact support)"
    # Same message edit: the progress card becomes the final summary.
    await query.edit_message_text(summary, parse_mode=ParseMode.HTML, reply_markup=_claim_back_kb(scope))



async def cb_admin_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "?? <b>Upload File</b>\n\nSend me the file you want to add to the store.",
        parse_mode=ParseMode.HTML,
    )
    return UP_FILE


async def conv_upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    kind = None
    tg_file = None
    file_name = None
    file_size = 0

    if msg.document:
        kind, tg_file = "document", msg.document
        file_name, file_size = tg_file.file_name or "file", tg_file.file_size or 0
    elif msg.video:
        kind, tg_file = "video", msg.video
        file_name = tg_file.file_name or f"video_{tg_file.file_unique_id}.mp4"
        file_size = tg_file.file_size or 0
    elif msg.audio:
        kind, tg_file = "audio", msg.audio
        file_name = tg_file.file_name or f"audio_{tg_file.file_unique_id}.mp3"
        file_size = tg_file.file_size or 0
    elif msg.photo:
        tg_file = msg.photo[-1]
        kind = "photo"
        file_name = f"photo_{tg_file.file_unique_id}.jpg"
        file_size = tg_file.file_size or 0
    elif msg.voice:
        kind, tg_file = "voice", msg.voice
        file_name = f"voice_{tg_file.file_unique_id}.ogg"
        file_size = tg_file.file_size or 0
    elif msg.animation:
        kind, tg_file = "animation", msg.animation
        file_name = tg_file.file_name or f"gif_{tg_file.file_unique_id}.mp4"
        file_size = tg_file.file_size or 0
    else:
        await msg.reply_text("❌ Unsupported file type. Please send a valid file.")
        return UP_FILE

    context.user_data["up_kind"] = kind
    context.user_data["up_file_id"] = tg_file.file_id
    context.user_data["up_unique_id"] = tg_file.file_unique_id
    context.user_data["up_orig_name"] = file_name
    context.user_data["up_size"] = file_size

    await msg.reply_text(
        f"✅ File received ({fmt_size(file_size)}).\n\n📝 Enter File Name (or send - to use original filename):"
    )
    return UP_NAME


async def conv_upload_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    name = context.user_data["up_orig_name"] if text == "-" else text
    context.user_data["up_name"] = name
    await update.message.reply_text("📄 Enter Description (or send - to skip):")
    return UP_DESC


async def conv_upload_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    context.user_data["up_desc"] = "" if text == "-" else text
    await update.message.reply_text(
        "💰 Enter Price (0 = FREE):\n\nExample: 0, 50, 100, 250, 500, 1000\n"
        "Next step me choose karoge ki price 🪙 Coins me ho ya 💎 Gems me."
    )
    return UP_PRICE


async def conv_upload_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a valid number.")
        return UP_PRICE
    context.user_data["up_price"] = int(text)
    if int(text) == 0:
        context.user_data["up_currency"] = "coins"
        return await show_upload_preview(update, context)
    await update.message.reply_text(
        f"💱 <b>Select Currency</b>\n\nPrice <b>{int(text)}</b> kis currency me rakhna hai?\n\n"
        f"🪙 <b>Coins</b> — users rewards se kama sakte hain\n"
        f"{GEM_E} <b>Gems</b> — paid currency (sirf admin de sakta hai / Stars se buy)",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🪙 Coins", callback_data="up:cur:coins", style="primary"),
             InlineKeyboardButton("💎 Gems", callback_data="up:cur:gems", style="success")],
            [InlineKeyboardButton("❌ Cancel", callback_data="up:cancel", style="danger")],
        ]),
    )
    return UP_CURRENCY


async def cb_upload_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["up_currency"] = "gems" if query.data.endswith("gems") else "coins"
    return await show_upload_preview(update, context)


async def show_upload_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    d = context.user_data
    currency = d.get("up_currency", "coins")
    text = (
        "👀 <b>Preview</b>\n\n"
        f"📁 File Name: {html.escape(d['up_name'])}\n"
        f"📦 File Size: {fmt_size(d['up_size'])}\n"
        f"📄 Description: {html.escape(d['up_desc']) if d['up_desc'] else '—'}\n"
        f"💰 Price: {price_text(d['up_price'], currency)}\n"
        f"📅 Upload Date: {fmt_date(datetime.utcnow().isoformat())}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Publish", callback_data="up:publish", style="primary"),
         InlineKeyboardButton("✏ Edit", callback_data="up:edit", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="up:cancel", style="primary")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    return UP_PREVIEW


async def cb_upload_publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    d = context.user_data
    user = update.effective_user
    async with db_conn() as db:
        # Telegram can deliver the publish callback twice, and admins can
        # accidentally upload the same Telegram file again.  Do not create
        # duplicate store records for the same underlying file.
        existing = None
        if d.get("up_unique_id"):
            cur = await db.execute(
                "SELECT file_pk FROM files WHERE tg_file_unique_id=? AND is_deleted=0",
                (d["up_unique_id"],),
            )
            existing = await cur.fetchone()
        if existing:
            await query.edit_message_text(
                f"⚠️ This Telegram file is already in the store (File #{existing[0]}).",
            )
            return ConversationHandler.END
        await db.execute(
            "INSERT INTO files (tg_file_id, tg_file_unique_id, file_kind, file_name, file_size, "
            "description, price, upload_date, uploaded_by, currency) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (d["up_file_id"], d["up_unique_id"], d["up_kind"], d["up_name"], d["up_size"],
             d["up_desc"], d["up_price"], datetime.utcnow().isoformat(), user.id,
             d.get("up_currency", "coins")),
        )
        await db.commit()
    await query.edit_message_text(
        f"✅ <b>File Published Successfully!</b>\n\n💰 Price: {price_text(d['up_price'], d.get('up_currency', 'coins'))}",
        parse_mode=ParseMode.HTML,
    )
    for key in ["up_kind", "up_file_id", "up_unique_id", "up_orig_name", "up_size", "up_name", "up_desc", "up_price", "up_currency"]:
        context.user_data.pop(key, None)
    return ConversationHandler.END


async def cb_upload_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📝 Enter File Name (or send - to use original filename):")
    return UP_NAME


async def cb_upload_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Upload cancelled.")
    for key in ["up_kind", "up_file_id", "up_unique_id", "up_orig_name", "up_size", "up_name", "up_desc", "up_price", "up_currency"]:
        context.user_data.pop(key, None)
    return ConversationHandler.END



async def cb_admin_managefiles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    if update.callback_query:
        await update.callback_query.answer()
    await send_manage_files_list(update, context, page=0)


async def send_manage_files_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    viewer_id = update.effective_user.id
    is_owner = viewer_id == OWNER_ID
    per_page = FILES_PER_PAGE
    count_filter = {"is_deleted": 0} if is_owner else {"is_deleted": 0, "uploaded_by": viewer_id}
    total = await _sqlite_db.files.count_documents(count_filter)
    total_pages = max(1, (total + per_page - 1) // per_page)
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        if is_owner:
            cur = await db.execute(
                "SELECT file_pk, file_name, price, downloads_count, currency FROM files WHERE is_deleted=0 "
                "ORDER BY file_pk DESC LIMIT ? OFFSET ?",
                (per_page, page * per_page),
            )
        else:
            cur = await db.execute(
                "SELECT file_pk, file_name, price, downloads_count, currency FROM files WHERE is_deleted=0 AND uploaded_by=? "
                "ORDER BY file_pk DESC LIMIT ? OFFSET ?",
                (viewer_id, per_page, page * per_page),
            )
        rows = await cur.fetchall()

    text = ui_screen(
        "📂", "Manage Files",
        ui_box(ui_kv("📁", "Total Files", f"<b>{total}</b>")),
        footer="Select a file to edit or delete:" if is_owner else "Files you've uploaded — select one to edit or delete:",
    )
    buttons = []
    for r in rows:
        buttons.append([InlineKeyboardButton(
            f"📄 {r['file_name']} · {'💎' if file_currency(r) == 'gems' else '🪙'}{r['price']} ({r['downloads_count']}⬇)", callback_data=f"mf:view:{r['file_pk']}:{page}"
        , style="primary")])
    nav = pager_row("mf:list:", page, total_pages)
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("🔍 Search Files", callback_data="mf:searchstart", style="primary")])
    buttons.append([InlineKeyboardButton("⬅ Back to Admin Panel", callback_data="ad:home", style="primary")])

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_mf_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[2])
    await send_manage_files_list(update, context, page)


async def cb_mf_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("🔍 Enter a keyword to search your files by name:")
    return MF_SEARCH


async def conv_mf_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyword = update.message.text.strip()
    viewer_id = update.effective_user.id
    is_owner = viewer_id == OWNER_ID
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        if is_owner:
            cur = await db.execute(
                "SELECT file_pk, file_name FROM files WHERE is_deleted=0 AND file_name LIKE ? LIMIT 15",
                (f"%{keyword}%",),
            )
        else:
            cur = await db.execute(
                "SELECT file_pk, file_name FROM files WHERE is_deleted=0 AND uploaded_by=? AND file_name LIKE ? LIMIT 15",
                (viewer_id, f"%{keyword}%"),
            )
        rows = await cur.fetchall()

    if not rows:
        await update.message.reply_text("❌ No files matched that keyword.")
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(f"📄 {r['file_name']}", callback_data=f"mf:view:{r['file_pk']}:0", style="primary")] for r in rows]
    await update.message.reply_text(
        f"🔍 Found <b>{len(rows)}</b> matching file(s):", parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ConversationHandler.END


async def cb_mf_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, file_pk, page = query.data.split(":")
    await _render_mf_view(update, int(file_pk), int(page))


async def _render_mf_view(update: Update, file_pk: int, page: int) -> None:
    query = update.callback_query
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM files WHERE file_pk=?", (file_pk,))
        f = await cur.fetchone()
    if not f:
        await query.edit_message_text("❌ File not found.")
        return
    if update.effective_user.id != OWNER_ID and f["uploaded_by"] != update.effective_user.id:
        await query.edit_message_text("🚫 You can only manage files you uploaded.")
        return
    text = (
        f"📄 <b>{html.escape(f['file_name'])}</b>\n\n"
        f"📦 Size: {fmt_size(f['file_size'])}\n"
        f"📄 Description: {html.escape(f['description']) if f['description'] else '—'}\n"
        f"💰 Price: {price_text(f['price'], file_currency(f))}\n"
        f"💱 Currency: {'💎 Gems' if file_currency(f) == 'gems' else '🪙 Coins'}\n"
        f"⬇ Downloads: {f['downloads_count']}\n"
        f"🎁 Mystery Tier: {f['mystery_tier'] or 'None'}\n"
        f"📌 Featured: {'Yes' if f['featured'] else 'No'}\n"
        f"📅 Uploaded: {fmt_date(f['upload_date'])}"
    )
    feature_label = "📌 Unfeature" if f["featured"] else "📌 Make Featured"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Name", callback_data=f"mf:ename:{file_pk}", style="primary"),
         InlineKeyboardButton("✏️ Edit Desc", callback_data=f"mf:edesc:{file_pk}", style="primary")],
        [InlineKeyboardButton("✏️ Edit Price", callback_data=f"mf:eprice:{file_pk}", style="primary"),
         InlineKeyboardButton("🎁 Set Mystery Tier", callback_data=f"mf:etier:{file_pk}", style="primary")],
        [InlineKeyboardButton(feature_label, callback_data=f"mf:tfeat:{file_pk}:{page}", style="primary")],
        [InlineKeyboardButton(
            "🔁 Switch to 🪙 Coins" if file_currency(f) == "gems" else "🔁 Switch to 💎 Gems",
            callback_data=f"mf:tcur:{file_pk}:{page}", style="success",
        )],
        [InlineKeyboardButton("🗑 Delete File", callback_data=f"mf:delete:{file_pk}", style="primary")],
        [InlineKeyboardButton("⬅ Back", callback_data=f"mf:list:{page}", style="primary")],
    ])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_mf_toggle_featured(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, file_pk, page = query.data.split(":")
    file_pk = int(file_pk)
    if not await _can_manage_file(update.effective_user.id, file_pk):
        await query.answer("🚫 You can only manage files you uploaded.", show_alert=True)
        return
    await query.answer("⏳ Updating…")
    async with db_conn() as db:
        cur = await db.execute("SELECT featured FROM files WHERE file_pk=?", (file_pk,))
        row = await cur.fetchone()
        new_val = 0 if (row and row[0]) else 1
        await db.execute("UPDATE files SET featured=? WHERE file_pk=?", (new_val, file_pk))
        await db.commit()
    await _render_mf_view(update, file_pk, int(page))


async def cb_mf_toggle_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, _, file_pk, page = query.data.split(":")
    file_pk = int(file_pk)
    if not await _can_manage_file(update.effective_user.id, file_pk):
        await query.answer("🚫 You can only manage files you uploaded.", show_alert=True)
        return
    f = await _sqlite_db.files.find_one({"file_pk": file_pk}, {"_id": 0, "currency": 1, "file_name": 1})
    if not f:
        await query.answer("❌ File not found.", show_alert=True)
        return
    new_cur = "coins" if file_currency(f) == "gems" else "gems"
    await _sqlite_db.files.update_one({"file_pk": file_pk}, {"$set": {"currency": new_cur}})
    await query.answer(f"✅ Now priced in {'💎 Gems' if new_cur == 'gems' else '🪙 Coins'}")
    await log_admin_action(
        context.bot, update.effective_user.id,
        f"💱 File #{file_pk} ({html.escape(f.get('file_name') or '')}) currency → {new_cur}",
    )
    await _render_mf_view(update, file_pk, int(page))


async def _can_manage_file(user_id: int, file_pk: int) -> bool:
    if user_id == OWNER_ID:
        return True
    async with db_conn() as db:
        cur = await db.execute("SELECT uploaded_by FROM files WHERE file_pk=?", (file_pk,))
        row = await cur.fetchone()
        return bool(row and row[0] == user_id)


async def cb_mf_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    _, field, file_pk = query.data.split(":")
    file_pk = int(file_pk)
    if not await _can_manage_file(update.effective_user.id, file_pk):
        await query.answer("🚫 You can only manage files you uploaded.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["ef_file_pk"] = file_pk
    context.user_data["ef_field"] = field
    prompts = {
        "ename": "📝 Enter new File Name:",
        "edesc": "📄 Enter new Description:",
        "eprice": "💰 Enter new Price (currency stays the same — use 🔁 Switch button to change it):",
        "etier": "🎁 Enter Mystery Tier — <code>random</code>, <code>rare</code>, <code>premium</code>, or <code>none</code>:",
    }
    await query.message.reply_text(prompts[field], parse_mode=ParseMode.HTML)
    return EF_FIELD


async def conv_edit_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = context.user_data.pop("ef_field")
    file_pk = context.user_data.pop("ef_file_pk")
    value = update.message.text.strip()

    column_map = {"ename": "file_name", "edesc": "description", "eprice": "price", "etier": "mystery_tier"}
    column = column_map[field]

    if field == "eprice":
        if not value.isdigit():
            await update.message.reply_text("❌ Please enter a valid number.")
            context.user_data["ef_field"] = field
            context.user_data["ef_file_pk"] = file_pk
            return EF_FIELD
        value = int(value)
    elif field == "etier":
        value = value.lower()
        if value not in ("random", "rare", "premium", "none"):
            await update.message.reply_text("❌ Must be one of: random, rare, premium, none.")
            context.user_data["ef_field"] = field
            context.user_data["ef_file_pk"] = file_pk
            return EF_FIELD
        value = None if value == "none" else value

    async with db_conn() as db:
        await db.execute(f"UPDATE files SET {column}=? WHERE file_pk=?", (value, file_pk))
        await db.commit()

    await update.message.reply_text("✅ File updated successfully.")
    return ConversationHandler.END


async def cb_mf_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    file_pk = int(query.data.split(":")[2])
    if not await _can_manage_file(update.effective_user.id, file_pk):
        await query.answer("🚫 You can only manage files you uploaded.", show_alert=True)
        return
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"mf:delconfirm:{file_pk}", style="primary"),
         InlineKeyboardButton("❌ No", callback_data=f"mf:view:{file_pk}:0", style="primary")],
    ])
    await query.edit_message_text("⚠️ Are you sure you want to delete this file?", reply_markup=kb)


async def cb_mf_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    file_pk = int(query.data.split(":")[2])
    if not await _can_manage_file(update.effective_user.id, file_pk):
        await query.answer("🚫 You can only manage files you uploaded.", show_alert=True)
        return
    await query.answer("⏳ Deleting…")
    async with db_conn() as db:
        await db.execute("UPDATE files SET is_deleted=1 WHERE file_pk=?", (file_pk,))
        await db.commit()
    await query.edit_message_text("🗑 <b>File deleted successfully.</b>", parse_mode=ParseMode.HTML)



async def cb_admin_fcmgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update):
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Channel", callback_data="fc:add", style="primary"),
         InlineKeyboardButton("➖ Remove Channel", callback_data="fc:remove", style="primary")],
        [InlineKeyboardButton("📋 Channel List", callback_data="fc:list", style="primary")],
        [InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")],
    ])
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("📡 <b>Force Channel Manager</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text("📡 <b>Force Channel Manager</b>", parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_fc_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await require_owner(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "➕ <b>Add Force-Join Channel/Group</b>\n\n"
        "Send either:\n"
        "• A public <b>@username</b>\n"
        "• Or a <b>https://t.me/username</b> link\n"
        "• Private chat: <b>-1001234567890</b>\n"
        "• Private + invite: <b>-1001234567890 | https://t.me/+InviteCode</b>\n\n"
        "I need to already be a <b>member</b> of it. For automatic approval "
        "of pending requests, give me admin rights with invite-user permission.",
        parse_mode=ParseMode.HTML,
    )
    return FC_ADD


async def conv_fc_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    try:
        text = (msg.text or "").strip()
        username = None
        invite_link = None
        chat_ref = None

        if text.startswith("@") and re.match(r"^@[A-Za-z0-9_]{5,32}$", text):
            username = text
            chat_ref = username
        else:
            m = re.match(r"^https?://t\.me/([A-Za-z0-9_]{5,32})/?$", text)
            if m:
                username = f"@{m.group(1)}"
                chat_ref = username

        # Private channels/groups do not have a public @username. Accept a
        # numeric Telegram chat id, optionally followed by its invite link:
        #   -1001234567890 | https://t.me/+AbCdEf
        private_m = re.match(
            r"^(-100\d+)(?:\s*(?:\||,)\s*(https?://t\.me/(?:\+|joinchat/)[A-Za-z0-9_-]+))?$",
            text,
            re.I,
        )
        if private_m:
            chat_ref = int(private_m.group(1))
            invite_link = private_m.group(2)

        if not chat_ref:
            await msg.reply_text(
                "❌ Send a public @username/link, or a private chat ID like "
                "<code>-1001234567890</code> (optionally: <code>ID | invite link</code>).",
                parse_mode=ParseMode.HTML,
            )
            return FC_ADD

        try:
            chat = await context.bot.get_chat(chat_ref)
        except TelegramError as e:
            await msg.reply_text(
                f"❌ Couldn't find that channel/group ({html.escape(str(e))}).\n"
                "For a private chat, send its numeric ID and make sure I've already been added to it.",
                parse_mode=ParseMode.HTML,
            )
            return FC_ADD

        try:
            me = await context.bot.get_me()
            member = await context.bot.get_chat_member(chat.id, me.id)
            if member.status in ("left", "kicked"):
                await msg.reply_text("❌ I'm not currently a member of that chat. Please add me first, then try again.")
                return FC_ADD
        except TelegramError as e:
            await msg.reply_text(
                f"❌ I can't access that chat's member list ({html.escape(str(e))}).\n"
                "Please make sure I've been added to it.",
                parse_mode=ParseMode.HTML,
            )
            return FC_ADD

        # A private chat has no username, so use its stable numeric id as the
        # deduplication key. Keep the invite link separately for the prompt.
        resolved_username = f"@{chat.username}" if chat.username else str(chat.id)
        await _save_force_channel(chat.id, resolved_username, chat.title, str(chat.type), invite_link)
        await msg.reply_text(f"✅ Added: <b>{html.escape(chat.title)}</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    except Exception as e:
        log.exception("Unexpected error in conv_fc_add")
        await msg.reply_text(
            f"⚠️ <b>Something went wrong adding this channel.</b>\n<code>{html.escape(str(e))}</code>\n\n"
            "This has been logged — please share this exact message so it can be fixed.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END


async def _save_force_channel(
    chat_id: int, username: str, title: str, chat_type: str, invite_link: str | None = None
) -> None:
    async with db_conn() as db:
        await db.execute(
            "INSERT INTO force_channels (username, chat_id, title, chat_type, invite_link, added_date) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO UPDATE SET "
            "chat_id=excluded.chat_id, title=excluded.title, chat_type=excluded.chat_type, invite_link=excluded.invite_link",
            (username, chat_id, title, chat_type, invite_link, datetime.utcnow().isoformat()),
        )
        await db.commit()
    # A newly added channel should be enforced immediately, not after the
    # pass-cache TTL expires for everyone who was already checked.
    _force_join_pass_cache.clear()
    _invalidate_force_channels_cache()


async def cb_fc_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_owner(update):
        return
    await query.answer()
    channels = await list_force_channels()
    if not channels:
        text = "📋 <b>Channel List</b>\n\nNo channels added yet."
    else:
        lines = ["📋 <b>Channel List</b>\n"]
        for ch in channels:
            lines.append(f"• <b>{html.escape(ch['title'])}</b> — added {fmt_date(ch['added_date'])}")
        text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_button("ad:fcmgr"))


async def cb_fc_remove_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, answered: bool = False) -> None:
    query = update.callback_query
    if not answered:
        if not await require_owner(update):
            return
        await query.answer()
    channels = await list_force_channels()
    if not channels:
        await query.edit_message_text("No channels to remove.", reply_markup=back_button("ad:fcmgr"))
        return
    buttons = [[InlineKeyboardButton(f"➖ {ch['title']}", callback_data=f"fc:rm:{ch['id']}", style="primary")] for ch in channels]
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:fcmgr", style="primary")])
    await query.edit_message_text("➖ Select a channel to remove:", reply_markup=InlineKeyboardMarkup(buttons))


async def cb_fc_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_owner(update):
        return
    ch_id = int(query.data.split(":")[2])
    async with db_conn() as db:
        await db.execute("DELETE FROM force_channels WHERE id=?", (ch_id,))
        await db.commit()
    _force_join_pass_cache.clear()
    _invalidate_force_channels_cache()
    await query.answer("➖ Removed")
    await cb_fc_remove_menu(update, context, answered=True)



async def cb_admin_walletmgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    is_owner = update.effective_user.id == OWNER_ID
    rows = [
        [InlineKeyboardButton("➕ Add Coins", callback_data="wm:add", style="primary"),
         InlineKeyboardButton("➖ Remove Coins", callback_data="wm:remove", style="primary")],
        [InlineKeyboardButton("💎 Add Gems", callback_data="wm:addg", style="success"),
         InlineKeyboardButton("💎 Remove Gems", callback_data="wm:remg", style="danger")],
        [InlineKeyboardButton("♻ Reset Coins", callback_data="wm:reset", style="primary")],
    ]
    if is_owner:
        rows.append([InlineKeyboardButton("🎯 Set Exact Balance", callback_data="wm:setbal", style="primary"),
                     InlineKeyboardButton("💎 Set Exact Gems", callback_data="wm:setgem", style="primary")])
        rows.append([InlineKeyboardButton("👥 Bulk Manage Users", callback_data="wm:bulk", style="primary")])
        rows.append([InlineKeyboardButton("📋 Pending Payments", callback_data="pp:list:0", style="primary")])
    rows.append([InlineKeyboardButton("📜 Wallet History", callback_data="wm:history", style="primary")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    kb = InlineKeyboardMarkup(rows)
    text = (
        "💰 <b>Wallet Manager</b>\n\nEnter a User ID to manage their wallet, or view recent history.\n\n"
        f"{GEM_E} <b>Gems</b> = paid currency. Users can only get Gems from an admin or by buying with ⭐ Stars."
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_wm_action_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    action = query.data.split(":")[1]
    if not await require_admin(update):
        return ConversationHandler.END
    if action in ("setbal", "setgem") and not await require_owner(update):
        return ConversationHandler.END
    await query.answer()
    context.user_data["wm_action"] = action
    await query.message.reply_text("👤 Enter the target User ID:")
    return UM_SEARCH


async def conv_wm_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please send a valid numeric User ID.")
        return UM_SEARCH
    target_id = int(text)
    row = await get_user_row(target_id)
    if not row:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    context.user_data["wm_target"] = target_id
    action = context.user_data["wm_action"]
    if action == "reset":
        async with db_conn() as db:
            await db.execute("UPDATE wallet SET coins=0 WHERE user_id=?", (target_id,))
            await db.execute(
                "INSERT INTO transactions (user_id, tx_type, amount, description, timestamp) VALUES (?, ?, ?, ?, ?)",
                (target_id, "admin_reset", 0, "Admin reset wallet to 0", datetime.utcnow().isoformat()),
            )
            await db.commit()
        await update.message.reply_text(f"♻ Wallet reset to 0 for user {target_id}.")
        await log_admin_action(context.bot, update.effective_user.id, f"♻ Reset wallet to 0 for user {target_id}")
        return ConversationHandler.END

    if action == "setbal":
        await update.message.reply_text("🎯 Enter the exact balance to set:")
        return UM_AMOUNT
    if action == "setgem":
        current = await get_gems(target_id)
        await update.message.reply_text(f"💎 Current gems: {current}\n🎯 Enter the exact gems amount to set:")
        return UM_AMOUNT
    if action in ("addg", "remg"):
        current = await get_gems(target_id)
        await update.message.reply_text(f"💎 Current gems: {current}\n💎 Enter the gems amount:")
        return UM_AMOUNT

    await update.message.reply_text("🪙 Enter the amount:")
    return UM_AMOUNT


async def conv_wm_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    action = context.user_data.get("wm_action")
    min_ok = 0 if action in ("setbal", "setgem") else 1
    if not text.isdigit() or int(text) < min_ok:
        await update.message.reply_text("❌ Please enter a valid number." if action in ("setbal", "setgem") else "❌ Please enter a valid positive number.")
        return UM_AMOUNT
    amount = int(text)
    target_id = context.user_data.pop("wm_target")
    action = context.user_data.pop("wm_action")

    if action in ("addg", "remg", "setgem"):
        await _admin_gems_apply(update, context, target_id, action, amount)
        return ConversationHandler.END

    if action == "setbal":
        async with db_conn() as db:
            await db.execute(
                "INSERT INTO wallet (user_id, coins) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET coins=excluded.coins",
                (target_id, amount),
            )
            await db.execute(
                "INSERT INTO transactions (user_id, tx_type, amount, description, timestamp) VALUES (?, ?, ?, ?, ?)",
                (target_id, "admin_setbal", amount, f"Admin set exact balance to {amount}", datetime.utcnow().isoformat()),
            )
            await db.commit()
        await update.message.reply_text(f"🎯 Balance for user {target_id} set to {amount} coins.")
        await log_admin_action(context.bot, update.effective_user.id, f"🎯 Set exact balance for user {target_id} to {amount} coins")
        return ConversationHandler.END

    if action == "add":
        new_bal = await add_coins(target_id, amount, "admin_gift", f"Admin added {amount} coins")
        await update.message.reply_text(f"✅ Added {amount} coins. New balance: {new_bal}")
        await log_admin_action(context.bot, update.effective_user.id, f"➕ Added {amount} coins to user {target_id}")
        try:
            await context.bot.send_message(target_id, f"🎁 <b>{amount} Coins</b> have been added to your wallet by admin!", parse_mode=ParseMode.HTML)
        except TelegramError:
            pass
    else:
        ok = await remove_coins(target_id, amount, "admin_deduct", f"Admin removed {amount} coins")
        if ok:
            await update.message.reply_text(f"✅ Removed {amount} coins.")
            await log_admin_action(context.bot, update.effective_user.id, f"➖ Removed {amount} coins from user {target_id}")
        else:
            await update.message.reply_text("❌ User doesn't have enough coins to remove that amount.")
    return ConversationHandler.END


async def _admin_gems_apply(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            target_id: int, action: str, amount: int) -> None:
    """Shared by Wallet Manager and User Manager — the ONLY way gems are given."""
    admin_id = update.effective_user.id
    if action == "setgem":
        await set_gems(target_id, amount, f"Admin {admin_id} set gems to {amount}")
        await update.message.reply_text(f"🎯 Gems for user {target_id} set to 💎 {amount}.")
        await log_admin_action(context.bot, admin_id, f"💎 Set exact gems for user {target_id} to {amount}")
        return
    if action == "addg":
        new_bal = await add_gems(target_id, amount, "admin_gift", f"Admin added {amount} gems")
        await update.message.reply_text(f"✅ Added 💎 {amount} gems. New gems: {new_bal}")
        await log_admin_action(context.bot, admin_id, f"💎 Added {amount} gems to user {target_id}")
        try:
            await context.bot.send_message(
                target_id, f"🎁 {GEM_E} <b>{amount} Gems</b> have been added to your wallet by admin!",
                parse_mode=ParseMode.HTML,
            )
        except TelegramError:
            pass
        return
    ok = await remove_gems(target_id, amount, "admin_deduct", f"Admin removed {amount} gems")
    if ok:
        await update.message.reply_text(f"✅ Removed 💎 {amount} gems from user {target_id}.")
        await log_admin_action(context.bot, admin_id, f"💎 Removed {amount} gems from user {target_id}")
    else:
        await update.message.reply_text("❌ User doesn't have enough gems to remove that amount.")


async def cb_wm_bulk_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await require_owner(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "👥 <b>Bulk Manage Users</b>\n\n"
        "Send the target users separated by space, comma, or a new line — "
        "numeric User IDs, @usernames, or a mix of both:\n"
        "<code>111 222 @alice @bob</code>",
        parse_mode=ParseMode.HTML,
    )
    return WB_IDS


async def conv_wm_bulk_ids(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()
    tokens = [tok for tok in re.split(r"[\s,]+", raw) if tok]
    if not tokens:
        await update.message.reply_text("❌ Please send at least one User ID or @username.")
        return WB_IDS

    resolved: list[int] = []
    not_found: list[str] = []

    async with db_conn() as db:
        for tok in tokens:
            if tok.startswith("@"):
                uname = tok.lstrip("@")
                cur = await db.execute("SELECT user_id FROM users WHERE username=?", (uname,))
                row = await cur.fetchone()
                if row:
                    resolved.append(row[0])
                else:
                    not_found.append(tok)
            elif tok.isdigit():
                resolved.append(int(tok))
            else:
                not_found.append(tok)

    if not resolved:
        await update.message.reply_text(
            "❌ None of those could be resolved to a real user. Check the IDs/usernames and try again."
        )
        return WB_IDS

    context.user_data["wb_ids"] = resolved
    msg = f"✅ Resolved <b>{len(resolved)}</b> users.\n\nWhat should be applied to all of them?"
    if not_found:
        msg += f"\n\n⚠️ Not found (skipped): {', '.join(not_found[:15])}"
        if len(not_found) > 15:
            msg += f" (+{len(not_found) - 15} more)"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Coins", callback_data="wb:add", style="primary"),
         InlineKeyboardButton("➖ Remove Coins", callback_data="wb:remove", style="primary")],
        [InlineKeyboardButton("🚫 Ban All", callback_data="wb:ban", style="primary"),
         InlineKeyboardButton("✅ Unban All", callback_data="wb:unban", style="primary")],
        [InlineKeyboardButton("👑 Give Premium", callback_data="wb:premium", style="primary")],
        [InlineKeyboardButton("❌ Cancel", callback_data="wb:cancel", style="primary")],
    ])
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=kb)
    return WB_ACTION


async def cb_wb_action_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["wb_coin_action"] = "add" if query.data == "wb:add" else "remove"
    verb = "add to" if query.data == "wb:add" else "remove from"
    await query.message.reply_text(f"🪙 Enter the coin amount to {verb} all {len(context.user_data['wb_ids'])} users:")
    return WB_AMOUNT


async def conv_wm_bulk_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Please enter a valid positive number.")
        return WB_AMOUNT
    amount = int(text)
    target_ids = context.user_data.pop("wb_ids")
    action = context.user_data.pop("wb_coin_action")
    is_add = action == "add"

    verb = "Adding" if is_add else "Removing"
    status_msg = await update.message.reply_text(f"⏳ {verb} {amount} coins for {len(target_ids)} users...")
    ok_list: list[int] = []
    skipped: list[int] = []

    async def process_one(uid: int) -> None:
        row = await get_user_row(uid)
        if not row:
            skipped.append(uid)
            return
        if is_add:
            await add_coins(uid, amount, "admin_gift", f"Bulk admin gift: {amount} coins")
            success = True
        else:
            success = await remove_coins(uid, amount, "admin_deduct", f"Bulk admin deduct: {amount} coins")
        if not success:
            skipped.append(uid)
            return
        ok_list.append(uid)
        await TELEGRAM_SEND_LIMITER.acquire()
        try:
            verb_msg = f"🎁 <b>{amount} Coins</b> have been added to your wallet by admin!" if is_add \
                else f"⚠️ <b>{amount} Coins</b> have been deducted from your wallet by admin."
            await context.bot.send_message(uid, verb_msg, parse_mode=ParseMode.HTML)
        except TelegramError:
            pass

    await asyncio.gather(*(process_one(uid) for uid in target_ids))

    past_verb = "Added" if is_add else "Removed"
    result = f"✅ <b>Bulk {past_verb} Complete</b>\n\n🪙 {past_verb} {amount} coins for <b>{len(ok_list)}</b> users."
    if skipped:
        result += f"\n⚠️ Skipped (not found or insufficient balance): {', '.join(str(u) for u in skipped[:20])}"
        if len(skipped) > 20:
            result += f" (+{len(skipped) - 20} more)"
    await status_msg.edit_text(result, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cb_wb_action_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    target_ids = context.user_data.pop("wb_ids")
    banned = 1 if query.data == "wb:ban" else 0
    async with db_conn() as db:
        for uid in target_ids:
            await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (banned, uid))
            _guard_auth_cache.pop(uid, None)
        await db.commit()
    action_word = "Banned" if banned else "Unbanned"
    await query.message.reply_text(f"✅ <b>{action_word}</b> {len(target_ids)} users.", parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cb_wb_action_premium_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("7 Days", callback_data="wb:pset:7", style="primary"),
         InlineKeyboardButton("30 Days", callback_data="wb:pset:30", style="primary")],
        [InlineKeyboardButton("90 Days", callback_data="wb:pset:90", style="primary"),
         InlineKeyboardButton("Lifetime", callback_data="wb:pset:0", style="primary")],
    ])
    await query.message.reply_text("👑 Select Premium duration to grant to all selected users:", reply_markup=kb)
    return WB_PREMIUM


async def cb_wb_action_premium_set(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    days = int(query.data.split(":")[2])
    target_ids = context.user_data.pop("wb_ids")
    for uid in target_ids:
        await grant_premium(uid, None if days == 0 else days, update.effective_user.id)
        await TELEGRAM_SEND_LIMITER.acquire()
        try:
            label = "Lifetime" if days == 0 else f"{days} days"
            await context.bot.send_message(
                uid, f"👑 <b>You've been granted Premium!</b>\nDuration: {label}", parse_mode=ParseMode.HTML
            )
        except TelegramError:
            pass
    label = "Lifetime" if days == 0 else f"{days} Days"
    await query.message.reply_text(f"✅ Granted <b>{label}</b> Premium to {len(target_ids)} users.", parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cb_wb_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.pop("wb_ids", None)
    context.user_data.pop("wb_coin_action", None)
    await query.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END



async def cb_pending_payments_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_owner(update):
        return
    await query.answer()
    page = int(query.data.split(":")[2])
    per_page = 10
    async with db_conn() as db:
        total = (await (await db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'")).fetchone())[0]
        cur = await db.execute(
            "SELECT * FROM payments WHERE status='pending' ORDER BY payment_id ASC LIMIT ? OFFSET ?",
            (per_page, page * per_page),
        )
        rows = await cur.fetchall()

    if not rows and page == 0:
        text = "📋 <b>Pending Payments</b>\n\nNothing pending right now — all caught up! ✅"
        buttons = [[InlineKeyboardButton("⬅ Back", callback_data="ad:walletmgr", style="primary")]]
    else:
        text = f"📋 <b>Pending Payments</b>  —  Total: <b>{total}</b>\n\nTap Accept/Reject on any request below:\n"
        buttons = []
        for r in rows:
            urow = await get_user_row(r["user_id"])
            uname = f"@{urow['username']}" if urow and urow["username"] else (urow["first_name"] if urow else f"ID {r['user_id']}")
            got = f"💎{r['gems']}" if r["currency"] == "gems" else f"🪙{r['coins']}"
            text += f"\n👤 <b>{html.escape(uname or str(r['user_id']))}</b> — ⭐{r['stars']} → {got} <i>({fmt_date(r['timestamp'])})</i>"
            buttons.append([
                InlineKeyboardButton(f"✅ Accept #{r['payment_id']}", callback_data=f"pay:accept:{r['payment_id']}", style="primary"),
                InlineKeyboardButton(f"❌ Reject #{r['payment_id']}", callback_data=f"pay:reject:{r['payment_id']}", style="primary"),
            ])
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"pp:list:{page-1}", style="primary"))
        if (page + 1) * per_page < total:
            nav.append(InlineKeyboardButton("Next ➡", callback_data=f"pp:list:{page+1}", style="primary"))
        if nav:
            buttons.append(nav)
        buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:walletmgr", style="primary")])

    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_wm_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM transactions ORDER BY tx_id DESC LIMIT 15")
        rows = await cur.fetchall()
    if not rows:
        text = "📜 No transactions yet."
    else:
        lines = ["📜 <b>Recent Wallet History</b>\n"]
        for r in rows:
            cur_icon = "💎" if r["currency"] == "gems" else "🪙"
            lines.append(f"👤 <code>{r['user_id']}</code> {'+' if r['amount']>=0 else ''}{r['amount']} {cur_icon} — {html.escape(r['tx_type'])}")
        text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_button("ad:walletmgr"))



async def cb_admin_redeemmgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    is_owner = update.effective_user.id == OWNER_ID
    rows = [
        [InlineKeyboardButton("➕ Create Code", callback_data="rm:create", style="primary")],
        [InlineKeyboardButton("📋 List Codes", callback_data="rm:list", style="primary")],
        [InlineKeyboardButton("🗑 Delete Code", callback_data="rm:delstart", style="primary")],
    ]
    if is_owner:
        rows.append([InlineKeyboardButton("🗑 Delete ALL Codes", callback_data="rm:delall", style="primary")])
    rows.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    kb = InlineKeyboardMarkup(rows)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("🎟 <b>Redeem Manager</b>", parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text("🎟 <b>Redeem Manager</b>", parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_rm_create_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not await require_admin(update):
        return ConversationHandler.END
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        async with db_conn() as db:
            cur = await db.execute(
                "SELECT COUNT(*) FROM redeems WHERE created_by=? AND created_at >= ?",
                (user_id, today_start),
            )
            count_today = (await cur.fetchone())[0]
        if count_today >= ADMIN_DAILY_REDEEM_LIMIT:
            await query.answer(
                f"🚫 Daily limit reached — admins can create up to {ADMIN_DAILY_REDEEM_LIMIT} redeem codes per day.",
                show_alert=True,
            )
            return ConversationHandler.END
    await query.answer()
    await query.message.reply_text("🎟 Enter the redeem code (e.g. WELCOME500):")
    return RM_CODE


async def conv_rm_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip().upper()
    if not re.match(r"^[A-Z0-9_\-]{3,32}$", code):
        await update.message.reply_text("❌ Invalid code format. Use letters/numbers only (3-32 chars).")
        return RM_CODE
    async with db_conn() as db:
        cur = await db.execute("SELECT 1 FROM redeems WHERE code=?", (code,))
        if await cur.fetchone():
            await update.message.reply_text("❌ This code already exists. Try another.")
            return RM_CODE
    context.user_data["rm_code"] = code
    await update.message.reply_text("💰 Enter Coin Reward (e.g. 500):")
    return RM_COINS


async def conv_rm_coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a valid number.")
        return RM_COINS
    amount = int(text)
    if update.effective_user.id != OWNER_ID:
        if amount > ADMIN_MAX_REDEEM_COINS or amount < ADMIN_MIN_REDEEM_COINS:
            await update.message.reply_text(
                f"🚫 Admins can only create codes worth between {ADMIN_MIN_REDEEM_COINS}–{ADMIN_MAX_REDEEM_COINS} coins."
            )
            return RM_COINS
    context.user_data["rm_coins"] = amount
    await update.message.reply_text("⭐ Enter Premium Reward in days (0 for none):")
    return RM_PREMIUM


async def conv_rm_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a valid number.")
        return RM_PREMIUM
    context.user_data["rm_premium"] = int(text)
    await update.message.reply_text("🔢 Enter Usage Limit (0 for unlimited):")
    return RM_LIMIT


async def conv_rm_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ Please enter a valid number.")
        return RM_LIMIT
    context.user_data["rm_limit"] = int(text)
    await update.message.reply_text("📅 Enter Expiry Date (DD-MM-YYYY) or send - for no expiry:")
    return RM_EXPIRY


async def conv_rm_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    expiry_iso = None
    if text != "-":
        try:
            expiry_iso = datetime.strptime(text, "%d-%m-%Y").replace(hour=23, minute=59, second=59).isoformat()
        except ValueError:
            await update.message.reply_text("❌ Invalid date format. Use DD-MM-YYYY or send -.")
            return RM_EXPIRY

    d = context.user_data
    async with db_conn() as db:
        await db.execute(
            "INSERT INTO redeems (code, coin_reward, premium_days, usage_limit, expiry_date, status, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'active', ?, ?)",
            (d["rm_code"], d["rm_coins"], d["rm_premium"], d["rm_limit"], expiry_iso,
             update.effective_user.id, datetime.utcnow().isoformat()),
        )
        await db.commit()

    await update.message.reply_text(
        f"✅ <b>Redeem Code Created!</b>\n\n🎟 Code: <code>{d['rm_code']}</code>\n💰 Coins: {d['rm_coins']}\n"
        f"⭐ Premium Days: {d['rm_premium']}\n🔢 Usage Limit: {d['rm_limit'] or 'Unlimited'}\n"
        f"📅 Expiry: {text if text != '-' else 'Never'}",
        parse_mode=ParseMode.HTML,
    )
    await log_admin_action(
        context.bot, update.effective_user.id,
        f"🎟 Created redeem code <code>{d['rm_code']}</code> — {d['rm_coins']} coins"
    )
    for k in ["rm_code", "rm_coins", "rm_premium", "rm_limit"]:
        context.user_data.pop(k, None)
    return ConversationHandler.END


async def cb_rm_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM redeems ORDER BY created_at DESC LIMIT 15")
        rows = await cur.fetchall()
    if not rows:
        text = "📋 No redeem codes yet."
    else:
        lines = ["📋 <b>Redeem Codes</b>\n"]
        for r in rows:
            lines.append(
                f"🎟 <code>{r['code']}</code> — {r['coin_reward']}🪙 | "
                f"{r['used_count']}/{r['usage_limit'] or '∞'} used | {r['status']}"
            )
        text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_button("ad:redeemmgr"))


async def cb_rm_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not await require_admin(update):
        return ConversationHandler.END
    await query.answer()
    await query.message.reply_text(
        "🗑 Enter the exact redeem code to delete:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="rm:delcancel", style="primary")]]),
    )
    return RM_DELETE


async def conv_rm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip().upper()
    async with db_conn() as db:
        cur = await db.execute("SELECT 1 FROM redeems WHERE code=?", (code,))
        if not await cur.fetchone():
            await update.message.reply_text("❌ No such code found. Please check and try again, or /cancel.")
            return RM_DELETE
        await db.execute("DELETE FROM redeems WHERE code=?", (code,))
        await db.execute("DELETE FROM redeem_uses WHERE code=?", (code,))
        await db.commit()
    await update.message.reply_text(f"✅ Deleted code: <code>{html.escape(code)}</code>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cb_rm_delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END


async def cb_rm_delete_all_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update):
        return
    query = update.callback_query
    await query.answer()
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM redeems")
        count = (await cur.fetchone())[0]
    if count == 0:
        await query.edit_message_text("No redeem codes to delete.", reply_markup=back_button("ad:redeemmgr"))
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Yes, Delete ALL", callback_data="rm:delallconfirm", style="primary"),
         InlineKeyboardButton("❌ No", callback_data="ad:redeemmgr", style="primary")],
    ])
    await query.edit_message_text(
        f"⚠️ <b>Delete ALL {count} Redeem Codes?</b>\n\nThis cannot be undone.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )


async def cb_rm_delete_all_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update):
        return
    query = update.callback_query
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM redeems")
        count = (await cur.fetchone())[0]
        await db.execute("DELETE FROM redeems")
        await db.execute("DELETE FROM redeem_uses")
        await db.commit()
    await query.answer("🗑 Deleted all codes")
    await query.edit_message_text(f"🗑 <b>Deleted {count} redeem codes.</b>", parse_mode=ParseMode.HTML)
    await log_admin_action(context.bot, update.effective_user.id, f"🗑 Deleted ALL {count} redeem codes")



async def cb_admin_usermgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text("🔍 Enter User ID or @username to search:")
    return UM_SEARCH


async def conv_um_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        if text.isdigit():
            cur = await db.execute("SELECT * FROM users WHERE user_id=?", (int(text),))
        else:
            uname = text.lstrip("@")
            cur = await db.execute("SELECT * FROM users WHERE username=?", (uname,))
        row = await cur.fetchone()

    if not row:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END

    await send_user_profile(update.message, row["user_id"])
    return ConversationHandler.END


async def send_user_profile(message_or_query, target_id: int, edit: bool = False):
    row = await get_user_row(target_id)
    if not row:
        return
    balance = await get_balance(target_id)
    gems = await get_gems(target_id)
    async with db_conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=?", (target_id,))
        refs = (await cur.fetchone())[0]
    premium = "⭐ Active" if await is_premium_active(target_id) else "❌ None"
    banned = "🚫 Banned" if row["is_banned"] else "✅ Active"

    text = (
        f"👤 <b>User Profile</b>\n\n"
        f"🆔 ID: <code>{target_id}</code>\n"
        f"📛 Name: {html.escape(row['first_name'] or '—')}\n"
        f"🔗 Username: @{html.escape(row['username']) if row['username'] else '—'}\n"
        f"📅 Joined: {fmt_date(row['join_date'])}\n"
        f"🪙 Wallet: {balance}\n"
        f"💎 Gems: {gems}\n"
        f"👥 Referrals: {refs}\n"
        f"⭐ Premium: {premium}\n"
        f"🔒 Status: {banned}"
    )
    is_owner = message_or_query.from_user.id == OWNER_ID
    rows = [
        [InlineKeyboardButton("➕ Add Coins", callback_data=f"um:addc:{target_id}", style="primary"),
         InlineKeyboardButton("➖ Remove Coins", callback_data=f"um:remc:{target_id}", style="primary")],
        [InlineKeyboardButton("💎 Add Gems", callback_data=f"um:addg:{target_id}", style="success"),
         InlineKeyboardButton("💎 Remove Gems", callback_data=f"um:remg:{target_id}", style="danger")],
    ]
    if is_owner:
        rows.append([InlineKeyboardButton("🚫 Ban", callback_data=f"um:ban:{target_id}", style="primary"),
                     InlineKeyboardButton("✅ Unban", callback_data=f"um:unban:{target_id}", style="primary")])
    rows.append([InlineKeyboardButton("👑 Give Premium", callback_data=f"um:givep:{target_id}", style="primary"),
                 InlineKeyboardButton("❌ Remove Premium", callback_data=f"um:remp:{target_id}", style="primary")])
    kb = InlineKeyboardMarkup(rows)
    if hasattr(message_or_query, "edit_message_text") and edit:
        await message_or_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await message_or_query.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)



async def cb_admin_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    if update.callback_query:
        await update.callback_query.answer()
    await send_all_users_list(update, context, page=0)


async def send_all_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    per_page = 10
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        total = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        cur = await db.execute(
            "SELECT user_id, username, first_name, is_banned FROM users "
            "ORDER BY join_date DESC LIMIT ? OFFSET ?",
            (per_page, page * per_page),
        )
        rows = await cur.fetchall()

    text = f"👤 <b>All Users</b>\n\n👥 Total Registered: <b>{total}</b>\n\nTap a user to view or manage their profile:"
    buttons = []
    for r in rows:
        label = f"@{r['username']}" if r["username"] else (r["first_name"] or f"ID {r['user_id']}")
        tag = "🚫 " if r["is_banned"] else "👤 "
        buttons.append([InlineKeyboardButton(f"{tag}{label}", callback_data=f"au:view:{r['user_id']}:{page}", style="primary")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"au:list:{page-1}", style="primary"))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"au:list:{page+1}", style="primary"))
    if nav:
        buttons.append(nav)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_au_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    page = int(query.data.split(":")[2])
    await send_all_users_list(update, context, page)


async def cb_au_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    await query.answer()
    target_id = int(query.data.split(":")[2])
    await send_user_profile(query, target_id, edit=True)


async def cb_um_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update):
        return
    query = update.callback_query
    action, target_id = query.data.split(":")[1], int(query.data.split(":")[2])
    banned = 1 if action == "ban" else 0
    async with db_conn() as db:
        await db.execute("UPDATE users SET is_banned=? WHERE user_id=?", (banned, target_id))
        await db.commit()
    _guard_auth_cache.pop(target_id, None)
    await query.answer("✅ Updated")
    await log_admin_action(context.bot, update.effective_user.id, f"{'🚫 Banned' if banned else '✅ Unbanned'} user {target_id}")
    await send_user_profile(query, target_id, edit=True)


async def cb_um_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    action, target_id = query.data.split(":")[1], int(query.data.split(":")[2])
    if action == "remp":
        await remove_premium(target_id)
        await query.answer("✅ Premium removed")
        await send_user_profile(query, target_id, edit=True)
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("7 Days", callback_data=f"um:pset:{target_id}:7", style="primary"),
         InlineKeyboardButton("30 Days", callback_data=f"um:pset:{target_id}:30", style="primary")],
        [InlineKeyboardButton("90 Days", callback_data=f"um:pset:{target_id}:90", style="primary"),
         InlineKeyboardButton("Lifetime", callback_data=f"um:pset:{target_id}:0", style="primary")],
        [InlineKeyboardButton("⬅ Back", callback_data=f"um:back:{target_id}", style="primary")],
    ])
    await query.answer()
    await query.edit_message_text("👑 Select Premium Duration:", reply_markup=kb)


async def cb_um_pset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    _, _, target_id, days = query.data.split(":")
    target_id, days = int(target_id), int(days)
    await grant_premium(target_id, None if days == 0 else days, update.effective_user.id)
    await query.answer("✅ Premium granted")
    try:
        await context.bot.send_message(
            target_id,
            f"👑 <b>You've been granted Premium!</b>\nDuration: {'Lifetime' if days==0 else f'{days} days'}",
            parse_mode=ParseMode.HTML,
        )
    except TelegramError:
        pass
    await log_admin_action(
        context.bot, update.effective_user.id,
        f"👑 Granted {'Lifetime' if days == 0 else f'{days} days'} Premium to user {target_id}"
    )
    await send_user_profile(query, target_id, edit=True)


async def cb_um_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_admin(update):
        return
    target_id = int(query.data.split(":")[2])
    await query.answer()
    await send_user_profile(query, target_id, edit=True)


async def cb_um_coins_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    action, target_id = query.data.split(":")[1], int(query.data.split(":")[2])
    if not await is_admin(update.effective_user.id):
        await query.answer(ADMIN_ONLY_MSG, show_alert=True)
        return ConversationHandler.END
    await query.answer()
    context.user_data["um_action"] = {"addc": "add", "remc": "remove", "addg": "addg", "remg": "remg"}[action]
    context.user_data["um_target"] = target_id
    if action in ("addg", "remg"):
        current = await get_gems(target_id)
        await query.message.reply_text(f"💎 Current gems: {current}\n💎 Enter the gems amount:")
    else:
        await query.message.reply_text("🪙 Enter the coin amount:")
    return UM_AMOUNT


async def conv_um_coins_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Please enter a valid positive number.")
        return UM_AMOUNT
    amount = int(text)
    target_id = context.user_data.pop("um_target")
    action = context.user_data.pop("um_action")
    if action in ("addg", "remg"):
        await _admin_gems_apply(update, context, target_id, action, amount)
        return ConversationHandler.END
    if action == "add":
        await add_coins(target_id, amount, "admin_gift", "Admin added coins via User Manager")
        await update.message.reply_text(f"✅ Added {amount} coins to user {target_id}.")
    else:
        ok = await remove_coins(target_id, amount, "admin_deduct", "Admin removed coins via User Manager")
        await update.message.reply_text(
            f"✅ Removed {amount} coins from user {target_id}." if ok else "❌ Insufficient balance to remove that amount."
        )
    return ConversationHandler.END



async def cb_admin_premiummgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    if update.callback_query:
        await update.callback_query.answer()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM premium ORDER BY granted_at DESC LIMIT 20")
        rows = await cur.fetchall()
    if not rows:
        text = "👑 <b>Premium Manager</b>\n\nNo premium users yet.\n\nUse 👥 User Manager to grant premium to a specific user."
    else:
        lines = ["👑 <b>Premium Users</b>\n"]
        for r in rows:
            status = "Lifetime" if r["is_lifetime"] else fmt_date(r["expiry_date"])
            lines.append(f"🆔 <code>{r['user_id']}</code> — {status}")
        text = "\n".join(lines)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_button("ad:home"))
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)



async def cb_admin_adminmgr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    if update.callback_query:
        await update.callback_query.answer()

    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM admins ORDER BY added_date")
        rows = await cur.fetchall()

    lines = ["🛡 <b>Admin Manager</b>\n"]
    lines.append(f"👑 Owner: <code>{OWNER_ID}</code>")
    for r in rows:
        if r["user_id"] == OWNER_ID:
            continue
        u = await get_user_row(r["user_id"])
        label = f"@{u['username']}" if u and u["username"] else (u["first_name"] if u else "Unknown")
        role_tag = "🥇 Senior" if r["role"] == "senior" else "🥈 Junior"
        lines.append(f"🛡 <code>{r['user_id']}</code> — {html.escape(label or '—')} ({role_tag})")
    text = "\n".join(lines)

    buttons = []
    is_owner = update.effective_user.id == OWNER_ID
    if is_owner:
        buttons.append([InlineKeyboardButton("➕ Add Admin", callback_data="am:add", style="primary"),
                         InlineKeyboardButton("➖ Remove Admin", callback_data="am:remove", style="primary")])
        buttons.append([InlineKeyboardButton("📜 Action Log", callback_data="am:log:0", style="primary")])
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    kb = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_am_log_view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_owner(update):
        return
    await query.answer()
    page = int(query.data.split(":")[2])
    per_page = 10
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM admin_logs ORDER BY log_id DESC LIMIT ? OFFSET ?", (per_page, page * per_page)
        )
        rows = await cur.fetchall()

    if not rows and page == 0:
        text = "📜 <b>Admin Action Log</b>\n\nNo actions recorded yet."
    else:
        lines = ["📜 <b>Admin Action Log</b>\n"]
        for r in rows:
            u = await get_user_row(r["actor_id"])
            label = f"@{u['username']}" if u and u["username"] else str(r["actor_id"])
            lines.append(f"👤 {html.escape(label)} — {r['action_text']}\n<i>{fmt_date(r['timestamp'])}</i>")
        text = "\n\n".join(lines)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅ Prev", callback_data=f"am:log:{page-1}", style="primary"))
    if len(rows) == per_page:
        nav.append(InlineKeyboardButton("Next ➡", callback_data=f"am:log:{page+1}", style="primary"))
    buttons = [nav] if nav else []
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:adminmgr", style="primary")])
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_am_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        await query.answer("🚫 Only the owner can add admins.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    await query.message.reply_text("👤 Send the User ID or @username to promote to admin:")
    return AM_ADD_USER


async def conv_am_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    target_id = None
    async with db_conn() as db:
        if text.startswith("@"):
            cur = await db.execute("SELECT user_id FROM users WHERE username=?", (text.lstrip("@"),))
            row = await cur.fetchone()
            if row:
                target_id = row[0]
        elif text.isdigit():
            target_id = int(text)

    if target_id is None:
        await update.message.reply_text(
            "❌ Couldn't find that user. They need to have started the bot at least once. Try again, or /cancel."
        )
        return AM_ADD_USER

    context.user_data["am_target_id"] = target_id
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🥇 Senior Admin", callback_data="am:role:senior", style="primary"),
         InlineKeyboardButton("🥈 Junior Admin", callback_data="am:role:junior", style="primary")],
    ])
    await update.message.reply_text(
        "🛡 Choose their role:\n\n"
        "🥇 <b>Senior</b> — their actions are only reported to you (the Owner).\n"
        "🥈 <b>Junior</b> — their actions are reported to you AND all Senior admins.",
        parse_mode=ParseMode.HTML, reply_markup=kb,
    )
    return AM_ADD_ROLE


async def cb_am_add_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data.split(":")[2]
    target_id = context.user_data.pop("am_target_id", None)
    if target_id is None:
        await query.message.reply_text("❌ Something went wrong — please start again.")
        return ConversationHandler.END

    async with db_conn() as db:
        await db.execute(
            "INSERT INTO admins (user_id, added_date, role) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role",
            (target_id, datetime.utcnow().isoformat(), role),
        )
        await db.commit()
    _guard_auth_cache.pop(target_id, None)

    role_label = "Senior Admin 🥇" if role == "senior" else "Junior Admin 🥈"
    await query.message.reply_text(
        f"✅ User <code>{target_id}</code> is now a <b>{role_label}</b>.", parse_mode=ParseMode.HTML
    )
    try:
        await context.bot.send_message(
            target_id, f"🛡 <b>You've been made a {role_label} of this bot!</b>", parse_mode=ParseMode.HTML
        )
    except TelegramError:
        pass
    return ConversationHandler.END


async def cb_am_remove_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        await query.answer("🚫 Only the owner can remove admins.", show_alert=True)
        return
    await query.answer()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM admins WHERE user_id != ? ORDER BY added_date", (OWNER_ID,))
        rows = await cur.fetchall()
    if not rows:
        await query.edit_message_text("No sub-admins to remove.", reply_markup=back_button("ad:adminmgr"))
        return
    buttons = []
    for r in rows:
        u = await get_user_row(r["user_id"])
        label = f"@{u['username']}" if u and u["username"] else str(r["user_id"])
        buttons.append([InlineKeyboardButton(f"➖ {label}", callback_data=f"am:rm:{r['user_id']}", style="primary")])
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:adminmgr", style="primary")])
    await query.edit_message_text("➖ Select an admin to remove:", reply_markup=InlineKeyboardMarkup(buttons))


async def cb_am_remove_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if update.effective_user.id != OWNER_ID:
        await query.answer("🚫 Only the owner can remove admins.", show_alert=True)
        return
    target_id = int(query.data.split(":")[2])
    if target_id == OWNER_ID:
        await query.answer("🚫 Can't remove the owner.", show_alert=True)
        return
    async with db_conn() as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (target_id,))
        await db.commit()
    _guard_auth_cache.pop(target_id, None)
    await query.answer("✅ Removed")
    await cb_am_remove_menu(update, context)



async def cb_admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return ConversationHandler.END
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text(
        "📢 Send the message you want to broadcast (text, photo, video, animation, sticker, document, voice, or audio).\n\n"
        "Send /cancel to abort."
    )
    return BR_CONTENT


async def conv_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message
    async with db_conn() as db:
        cur = await db.execute("SELECT user_id FROM users")
        all_users = [r[0] for r in await cur.fetchall()]

    status_msg = await msg.reply_text(f"📢 Broadcasting to {len(all_users)} users...")
    counters = {"done": 0, "failed": 0}
    counters_lock = asyncio.Lock()

    async def send_one(uid: int) -> None:
        await TELEGRAM_SEND_LIMITER.acquire()
        try:
            await context.bot.copy_message(chat_id=uid, from_chat_id=msg.chat_id, message_id=msg.message_id)
            async with counters_lock:
                counters["done"] += 1
        except RetryAfter as e:
            await asyncio.sleep(_retry_seconds(e) + 0.5)
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=msg.chat_id, message_id=msg.message_id)
                async with counters_lock:
                    counters["done"] += 1
            except TelegramError:
                async with counters_lock:
                    counters["failed"] += 1
        except TelegramError:
            async with counters_lock:
                counters["failed"] += 1

    await asyncio.gather(*(send_one(uid) for uid in all_users))

    await status_msg.edit_text(
        f"✅ <b>Broadcast Complete</b>\n\n✅ Sent: {counters['done']}\n❌ Failed: {counters['failed']}",
        parse_mode=ParseMode.HTML,
    )
    await log_admin_action(
        context.bot, update.effective_user.id,
        f"📢 Sent a broadcast — reached {counters['done']}, failed {counters['failed']}"
    )
    return ConversationHandler.END


_cancel_handled_updates: set[int] = set()


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Registered both as a conversation fallback and in group 1; reply once.
    if update.update_id in _cancel_handled_updates:
        return ConversationHandler.END
    _cancel_handled_updates.add(update.update_id)
    if len(_cancel_handled_updates) > 1000:
        _cancel_handled_updates.clear()
        _cancel_handled_updates.add(update.update_id)
    admin = await is_admin(update.effective_user.id)
    await update.message.reply_text("❌ Cancelled.", reply_markup=user_reply_keyboard(admin))
    context.user_data.clear()
    return ConversationHandler.END


# Escape hatch: any reply-keyboard menu button pressed while a ConversationHandler
# is active (upload, broadcast, user manager, redeem manager, etc.) must be able to
# break out of that conversation instead of being silently swallowed. Without this,
# PTB keeps routing the user's text to the active conversation's state handlers,
# none of which match a menu button, so the tap appears to do nothing.
_MENU_ESCAPE_REGEX = (
    "^(⬅️ Back to Main|📤 Upload File|📂 Manage Files|💰 Wallet Manager|"
    "🎟 Redeem Manager|📡 Force Channels|👥 User Manager|👤 All Users|"
    "👑 Premium Manager|🛡 Admin Manager|📋 Admin List|📊 Statistics|"
    "🛠 Maintenance|⚙ Settings|📢 Broadcast|👑 Admin Panel|"
    "🖼 Buy Files Media|🖼 Set Buy Files Media|"
    "Buy Files|My Wallet|Mystery Box|Daily Bonus|"
    "Refer & Earn|My Stats|Leaderboard|Support|🎟️ Redeem Code)$"
)


async def cmd_menu_escape(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fallback used by every ConversationHandler so menu buttons always work,
    even mid-conversation. Ends the current conversation, then re-dispatches
    the tapped button through the normal text router / TEXT_ROUTES dict."""
    context.user_data.clear()
    await text_router(update, context)
    return ConversationHandler.END



async def cb_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    if update.callback_query:
        await update.callback_query.answer()

    async with db_conn() as db:
        total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        active_users = (await (await db.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen > ?",
            ((datetime.utcnow() - timedelta(days=7)).isoformat(),)
        )).fetchone())[0]
        premium_users = (await (await db.execute(
            "SELECT COUNT(*) FROM premium WHERE is_lifetime=1 OR expiry_date > ?",
            (datetime.utcnow().isoformat(),)
        )).fetchone())[0]
        total_files = (await (await db.execute("SELECT COUNT(*) FROM files WHERE is_deleted=0")).fetchone())[0]
        total_downloads = (await (await db.execute("SELECT COUNT(*) FROM downloads")).fetchone())[0]
        coins_distributed = (await (await db.execute(
            "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE amount > 0 AND currency != 'gems'"
        )).fetchone())[0]
        redeem_count = (await (await db.execute("SELECT COUNT(*) FROM redeem_uses")).fetchone())[0]
        referral_count = (await (await db.execute("SELECT COUNT(*) FROM referrals")).fetchone())[0]
        revenue_stars = (await (await db.execute(
            "SELECT COALESCE(SUM(stars),0) FROM payments WHERE status='accepted'"
        )).fetchone())[0]
        pending_payments = (await (await db.execute(
            "SELECT COUNT(*) FROM payments WHERE status='pending'"
        )).fetchone())[0]

    gem_agg = await _sqlite_db.wallet.aggregate([
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$gems", 0]}}}}
    ]).to_list(length=1)
    gems_in_wallets = int(gem_agg[0]["total"]) if gem_agg else 0
    gem_files = await _sqlite_db.files.count_documents({"is_deleted": 0, "currency": "gems"})
    gem_sales = await _sqlite_db.payments.count_documents({"status": "accepted", "currency": "gems"})
    text = (
        "📊 <b>Statistics</b>\n\n"
        f"👥 Total Users: <b>{total_users}</b>\n"
        f"🟢 Active (7d): <b>{active_users}</b>\n"
        f"⭐ Premium Users: <b>{premium_users}</b>\n"
        f"📁 Total Files: <b>{total_files}</b>\n"
        f"⬇ Downloads: <b>{total_downloads}</b>\n"
        f"🪙 Coins Distributed: <b>{coins_distributed}</b>\n"
        f"💎 Gems in Wallets: <b>{gems_in_wallets}</b>\n"
        f"💎 Gem Files: <b>{gem_files}</b>  ·  Gem Sales: <b>{gem_sales}</b>\n"
        f"🎟 Redeem Count: <b>{redeem_count}</b>\n"
        f"🚀 Referral Count: <b>{referral_count}</b>\n"
        f"💰 Revenue: <b>{revenue_stars} ⭐</b>\n"
        f"⏳ Pending Payments: <b>{pending_payments}</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 Top Downloaded Files", callback_data="stats:topfiles", style="primary")],
        [InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")],
    ])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_stats_top_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await is_admin(update.effective_user.id):
        await query.answer(ADMIN_ONLY_MSG, show_alert=True)
        return
    await query.answer()
    async with db_conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT file_name, downloads_count, price, currency FROM files WHERE is_deleted=0 "
            "ORDER BY downloads_count DESC LIMIT 10"
        )
        rows = await cur.fetchall()

    if not rows:
        text = "📈 <b>Top Downloaded Files</b>\n\nNo files yet."
    else:
        medals = ["🥇", "🥈", "🥉"]
        lines = ["📈 <b>Top 10 Downloaded Files</b>\n"]
        for i, r in enumerate(rows):
            rank = medals[i] if i < 3 else f"{i+1}."
            tag = "FREE" if r["price"] == 0 else f"{r['price']} {'gems' if file_currency(r) == 'gems' else 'coins'}"
            lines.append(f"{rank} {html.escape(r['file_name'])} — <b>{r['downloads_count']}</b> downloads ({tag})")
        text = "\n".join(lines)
    await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_button("ad:stats"))



async def cb_admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        if update.callback_query:
            await update.callback_query.answer(ADMIN_ONLY_MSG, show_alert=True)
        else:
            await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    current = await get_setting("maintenance", "0")
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Enable", callback_data="mt:on", style="primary"),
         InlineKeyboardButton("❌ Disable", callback_data="mt:off", style="primary")],
        [InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")],
    ])
    status = "🚧 ENABLED" if current == "1" else "✅ DISABLED"
    text = f"🛠 <b>Maintenance Mode</b>\n\nCurrent status: <b>{status}</b>"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def cb_mt_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await require_owner(update):
        return
    val = "1" if query.data == "mt:on" else "0"
    await set_setting("maintenance", val)
    await query.answer("✅ Updated")
    await log_admin_action(context.bot, update.effective_user.id, f"🛠 Maintenance mode turned {'ON' if val == '1' else 'OFF'}")
    await cb_admin_maintenance(update, context)



SETTINGS_FIELDS = {
    "referral_reward": "🚀 Referral Reward (coins)",
    "daily_bonus": "🎁 Daily Bonus (coins)",
    "premium_daily_bonus": "👑 Premium Daily Bonus (coins)",
    "coin_packages": "🪙 Coin Packages (JSON list)",
    "gem_packages": "💎 Gem Packages (JSON list)",
    "premium_pricing": "👑 Premium Pricing (JSON list)",
    "coin_rate_bdt": "💵 Coins per 1 Taka",
    "bdt_payment_details": "💵 BDT Payment Details (bKash/Nagad)",
    "mystery_box_pricing": "🎁 Mystery Box Pricing (JSON)",
    "referral_milestones": "🚀 Referral Milestone Rewards (JSON)",
    "streak_rewards": "🔥 Login Streak Rewards (JSON)",
    "star_rate": "⭐ Star Rate",
    "support_username": "💬 Support Username",
    "payment_username": "💰 Payment Username (Stars)",
    "bot_name": "🏷 Bot Name",
    "force_join": "📡 Force Join (1/0)",
}


async def cb_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await require_owner(update):
        return
    buttons = [[InlineKeyboardButton(label, callback_data=f"set:{key}", style="primary")] for key, label in SETTINGS_FIELDS.items()]
    buttons.append([InlineKeyboardButton("⬅ Back", callback_data="ad:home", style="primary")])
    text = "⚙ <b>Settings</b>\n\nSelect a setting to edit:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))


async def cb_settings_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not await require_owner(update):
        return ConversationHandler.END
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    current = await get_setting(key, "")
    context.user_data["st_key"] = key
    await query.message.reply_text(
        f"✏️ Current value of <b>{SETTINGS_FIELDS.get(key, key)}</b>:\n<code>{html.escape(current)}</code>\n\n"
        f"Send the new value:",
        parse_mode=ParseMode.HTML,
    )
    return ST_VALUE


async def conv_settings_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    key = context.user_data.pop("st_key")
    value = update.message.text.strip()
    if key in _JSON_SETTING_KEYS:
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError
        except Exception:
            await update.message.reply_text(
                "❌ Invalid JSON. Please send a valid JSON list."
            )
            context.user_data["st_key"] = key
            return ST_VALUE
    elif key in _NUMERIC_SETTING_KEYS:
        try:
            float(value)
        except (TypeError, ValueError):
            await update.message.reply_text("❌ Please enter a valid number.")
            context.user_data["st_key"] = key
            return ST_VALUE
    await set_setting(key, value)
    await update.message.reply_text("✅ Setting updated successfully.")
    return ConversationHandler.END



async def handle_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        await update.effective_message.reply_text(ADMIN_ONLY_MSG)
        return
    is_owner = update.effective_user.id == OWNER_ID
    await update.effective_message.reply_text(
        (await admin_dashboard_text())
        + "\n<i>All admin controls are on your keyboard. Tap ⬅️ Back to Main to return.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_reply_keyboard(is_owner),
    )


async def handle_admin_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_admin(update.effective_user.id):
        return
    await update.effective_message.reply_text(
        "🏠 <b>Main Menu</b>", parse_mode=ParseMode.HTML, reply_markup=user_reply_keyboard(True)
    )


async def admin_dashboard_text() -> str:
    since = (datetime.utcnow() - timedelta(days=1)).isoformat()
    users, new_users, files, gem_files, pending = await asyncio.gather(
        _sqlite_db.users.count_documents({}),
        _sqlite_db.users.count_documents({"join_date": {"$gt": since}}),
        _sqlite_db.files.count_documents({"is_deleted": 0}),
        _sqlite_db.files.count_documents({"is_deleted": 0, "currency": "gems"}),
        _sqlite_db.payments.count_documents({"status": "pending"}),
    )
    return ui_screen(
        "👑", "Admin Panel",
        ui_box(
            ui_kv("👥", "Users", f"<b>{users}</b>  (+{new_users} today)"),
            ui_kv("📁", "Files", f"<b>{files}</b>  ·  💎 {gem_files} gem files"),
            ui_kv("⏳", "Pending Payments", f"<b>{pending}</b>" + ("  ⚠️" if pending else "  ✅")),
        ),
        subtitle=BOT_VERSION,
        footer="Select an option below 👇",
    )


async def cb_admin_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not await is_admin(update.effective_user.id):
        await query.answer(ADMIN_ONLY_MSG, show_alert=True)
        return
    await query.answer()
    await query.edit_message_text(await admin_dashboard_text(), parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())



async def job_expire_premium(context: ContextTypes.DEFAULT_TYPE) -> None:
    async with db_conn() as db:
        await db.execute(
            "DELETE FROM premium WHERE is_lifetime=0 AND expiry_date IS NOT NULL AND expiry_date < ?",
            (datetime.utcnow().isoformat(),),
        )
        await db.commit()


async def job_expire_redeem_codes(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-deletes redeem codes past their expiry_date, along with their
    usage records, so admins never have to clean these up manually."""
    now = datetime.utcnow().isoformat()
    async with db_conn() as db:
        cur = await db.execute(
            "SELECT code FROM redeems WHERE expiry_date IS NOT NULL AND expiry_date < ?", (now,)
        )
        expired = [r[0] for r in await cur.fetchall()]
        if expired:
            placeholders = ",".join("?" * len(expired))
            await db.execute(f"DELETE FROM redeems WHERE code IN ({placeholders})", expired)
            await db.execute(f"DELETE FROM redeem_uses WHERE code IN ({placeholders})", expired)
            await db.commit()
            log.info("Auto-deleted %d expired redeem code(s)", len(expired))


_last_error_report: dict[str, float] = {}


async def _report_error_to_owner(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """DM the owner the real exception, so "Something went wrong" is never a
    mystery again. The same error is reported at most once per minute."""
    err = context.error
    if err is None:
        return
    sig = f"{type(err).__name__}:{str(err)[:120]}"
    now = time.monotonic()
    last = _last_error_report.get(sig)
    if last is not None and now - last < 60:
        return
    _last_error_report[sig] = now
    if len(_last_error_report) > 500:
        _last_error_report.clear()
    action, uid = "unknown", "—"
    if isinstance(update, Update):
        if update.effective_user:
            uid = update.effective_user.id
        if update.callback_query:
            action = f"button: {update.callback_query.data}"
        elif update.effective_message and update.effective_message.text:
            action = f"text: {update.effective_message.text[:60]}"
    tb = "".join(traceback.format_exception(type(err), err, err.__traceback__))[-2500:]
    await context.bot.send_message(
        OWNER_ID,
        f"🐞 <b>Bot Error</b>\n"
        f"User: <code>{uid}</code>\n"
        f"Action: <code>{html.escape(str(action))}</code>\n"
        f"Error: <code>{html.escape(sig)}</code>\n"
        f"<pre>{html.escape(tb)}</pre>",
        parse_mode=ParseMode.HTML,
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Exception while handling update:", exc_info=context.error)
    try:
        await _report_error_to_owner(update, context)
    except Exception:
        log.exception("Could not send the error report to the owner")
    # Previously this only logged — if a handler crashed after deducting
    # coins/creating a code/etc, the user got dead silence and no idea
    # anything went wrong. Now we also try to notify them.
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong processing that. If coins were deducted "
                "and you didn't get a result, please contact support with what you did."
            )
    except Exception:
        pass



TEXT_ROUTES = {
    "Buy Files": handle_buy_files,
    "My Wallet": handle_my_wallet,
    "Daily Bonus": handle_daily_bonus,
    "Mystery Box": handle_mystery_box,
    "Refer & Earn": handle_invite_friends,
    "My Stats": handle_my_stats,
    "Leaderboard": handle_leaderboard,
    "Support": handle_support,
    "👑 Admin Panel": handle_admin_panel,
    "📂 Manage Files": cb_admin_managefiles,
    "💰 Wallet Manager": cb_admin_walletmgr,
    "🎟 Redeem Manager": cb_admin_redeemmgr,
    "📡 Force Channels": cb_admin_fcmgr,
    "👤 All Users": cb_admin_all_users,
    "👑 Premium Manager": cb_admin_premiummgr,
    "🛡 Admin Manager": cb_admin_adminmgr,
    "📋 Admin List": cb_admin_adminmgr,
    "📊 Statistics": cb_admin_stats,
    "🛠 Maintenance": cb_admin_maintenance,
    "⚙ Settings": cb_admin_settings,
    "⬅️ Back to Main": handle_admin_back_to_main,
    "📤 Upload File": cb_admin_upload_start,
    "📢 Broadcast": cb_admin_broadcast_start,
    "🎟️ Redeem Code": handle_redeem_prompt,
    "🖼 Buy Files Media": cb_admin_bfmedia_panel,
    "🖼 Set Buy Files Media": cb_admin_bfmedia_panel,
}


async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user is None or update.message is None or update.message.text is None:
        return
    if context.user_data is not None and context.user_data.get("awaiting_reject_reason"):
        if update.message.text in TEXT_ROUTES:
            # Owner tapped a menu button instead of typing a reason: cancel
            # the pending rejection rather than rejecting with "My Stats".
            context.user_data.pop("awaiting_reject_reason", None)
            context.user_data.pop("reject_payment_id", None)
            context.user_data.pop("reject_chat_msg", None)
            await update.message.reply_text("ℹ️ Payment rejection cancelled — the payment is still pending.")
        else:
            await handle_reject_reason(update, context)
            return
    text = update.message.text
    handler = TEXT_ROUTES.get(text)
    if handler:
        await handler(update, context)



def build_application() -> Application:
    concurrent_updates = CONCURRENT_UPDATES
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(concurrent_updates)
        .request(HTTPXRequest(
            connection_pool_size=concurrent_updates,
            pool_timeout=20.0,
            connect_timeout=15.0,
            read_timeout=20.0,
            write_timeout=20.0,
        ))
        .get_updates_request(HTTPXRequest(connection_pool_size=64, pool_timeout=20.0))
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # PTB runs only the FIRST matching handler per group. The catch-all
    # TypeHandler used to share group -1 with flood_guard, so flood_guard
    # never ran. Normalisation now has its own earlier group.
    app.add_handler(TypeHandler(Update, _normalize_incoming), group=-3)
    app.add_handler(MessageHandler(filters.ALL, group_restriction_guard), group=-2)
    app.add_handler(CallbackQueryHandler(group_restriction_guard), group=-2)

    app.add_handler(MessageHandler(filters.ALL, flood_guard), group=-1)
    app.add_handler(CallbackQueryHandler(flood_guard), group=-1)

    # Capture private-channel join requests. Telegram has no API for listing
    # pending requests later, so this update must be persisted when it arrives.
    # A pending request will pass force-join verification without being
    # auto-approved by the bot.
    app.add_handler(ChatJoinRequestHandler(record_force_join_request))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))

    app.add_handler(CallbackQueryHandler(cb_verify_join, pattern="^verify_join$"))

    app.add_handler(CallbackQueryHandler(cb_wallet_home, pattern="^wallet:home$"))
    app.add_handler(CallbackQueryHandler(cb_wallet_refer, pattern="^wallet:refer$"))
    app.add_handler(CallbackQueryHandler(cb_refer_home, pattern="^refer:home$"))
    app.add_handler(CallbackQueryHandler(cb_ui_noop, pattern="^ui:noop$"))
    app.add_handler(CallbackQueryHandler(cb_mystery_home, pattern="^mystery:home$"))
    app.add_handler(CallbackQueryHandler(cb_wallet_tx, pattern="^wallet:tx:"))
    app.add_handler(CallbackQueryHandler(cb_wallet_buy_premium, pattern="^wallet:buypremium$"))
    app.add_handler(CallbackQueryHandler(handle_buy_coins_bdt, pattern="^wallet:buybdt$"))

    app.add_handler(CallbackQueryHandler(cb_mystery_open, pattern=r"^mystery:open:\w+:\d+$"))

    app.add_handler(CallbackQueryHandler(cb_premium_purchase, pattern=r"^premium:buy:\d+:\d+$"))

    app.add_handler(CallbackQueryHandler(cb_buycoins_paid, pattern="^buycoins:paid$"))
    buycoins_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_buycoins_pkg, pattern=r"^buycoins:pkg:\d+$"),
            CallbackQueryHandler(cb_buycoins_custom, pattern="^buycoins:custom$"),
        ],
        states={
            BC_STARS: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_buycoins_stars)],
            BC_SCREENSHOT: [MessageHandler((filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND, conv_buycoins_screenshot)],
        },
        fallbacks=[CallbackQueryHandler(cb_buycoins_cancel, pattern="^buycoins:cancel$"), CommandHandler("cancel", cmd_cancel), MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape)],
        per_message=False,
    )
    app.add_handler(CallbackQueryHandler(cb_buycoins_start, pattern="^wallet:buycoins$"))
    app.add_handler(buycoins_conv)
    app.add_handler(CallbackQueryHandler(cb_buycoins_cancel, pattern="^buycoins:cancel$"))
    # ---- 💎 Buy Gems (manual star payment, same-message flow) ----
    app.add_handler(CallbackQueryHandler(cb_buygems_start, pattern="^gems:buy$"))
    app.add_handler(CallbackQueryHandler(cb_buygems_paid, pattern="^gems:paid$"))
    buygems_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_buygems_pkg, pattern=r"^gems:pkg:\d+$")],
        states={
            GM_SHOT: [MessageHandler(
                (filters.PHOTO | filters.Document.ALL | filters.TEXT) & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX),
                conv_buygems_screenshot,
            )],
        },
        fallbacks=[
            CallbackQueryHandler(cb_buygems_cancel, pattern="^gems:cancel$"),
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(buygems_conv)
    app.add_handler(CallbackQueryHandler(cb_buygems_cancel, pattern="^gems:cancel$"))

    app.add_handler(CallbackQueryHandler(cb_payment_accept, pattern=r"^pay:accept:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_payment_reject, pattern=r"^pay:reject:\d+$"))

    buybdt_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_buybdt_paid, pattern="^buybdt:paid$")],
        states={
            BDT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_buybdt_amount)],
            BDT_PROOF: [MessageHandler((filters.PHOTO | filters.Document.ALL | filters.TEXT) & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_buybdt_proof)],
        },
        fallbacks=[CallbackQueryHandler(cb_buybdt_cancel, pattern="^buybdt:cancel$"), CommandHandler("cancel", cmd_cancel), MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape)],
        per_message=False,
    )
    app.add_handler(buybdt_conv)

    app.add_handler(MessageHandler(filters.Regex("^🎟️ Redeem Code$"), handle_redeem_prompt))
    app.add_handler(CallbackQueryHandler(cb_redeem_cancel, pattern="^redeem:cancel$"))

    redeem_enter_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_redeem_enter_start, pattern="^redeem:enter$")],
        states={RD_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), handle_redeem_code)]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(redeem_enter_conv)

    redeem_gift_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_redeem_gift_start, pattern="^redeem:gift$")],
        states={GC_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_gift_amount)]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(redeem_gift_conv)

    app.add_handler(CallbackQueryHandler(cb_files_list, pattern=r"^files:list:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_file_view, pattern=r"^file:view:\d+(:\d+)?$"))
    app.add_handler(CallbackQueryHandler(cb_claimall_ask, pattern=r"^claimall:ask:(all|owned)$"))
    app.add_handler(CallbackQueryHandler(cb_claimall_go, pattern=r"^claimall:go:(all|owned)$"))
    app.add_handler(CallbackQueryHandler(cb_file_buy, pattern=r"^file:buy:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_file_download, pattern=r"^file:dl:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_my_purchases, pattern=r"^purchases:\d+$"))
    # These buttons were rendered by the handlers but had no application
    # route, so Telegram clicks appeared to do nothing.
    app.add_handler(CallbackQueryHandler(cb_file_request_done, pattern=r"^freq:done:\d+$"))

    app.add_handler(CallbackQueryHandler(cb_admin_home, pattern="^ad:home$"))
    app.add_handler(CallbackQueryHandler(cb_admin_managefiles, pattern="^ad:managefiles$"))
    app.add_handler(CallbackQueryHandler(cb_admin_walletmgr, pattern="^ad:walletmgr$"))
    app.add_handler(CallbackQueryHandler(cb_admin_redeemmgr, pattern="^ad:redeemmgr$"))
    app.add_handler(CallbackQueryHandler(cb_admin_fcmgr, pattern="^ad:fcmgr$"))
    app.add_handler(CallbackQueryHandler(cb_admin_premiummgr, pattern="^ad:premiummgr$"))
    app.add_handler(CallbackQueryHandler(cb_admin_adminmgr, pattern="^ad:adminmgr$"))
    app.add_handler(CallbackQueryHandler(cb_am_remove_menu, pattern="^am:remove$"))
    app.add_handler(CallbackQueryHandler(cb_am_log_view, pattern=r"^am:log:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_am_remove_confirm, pattern=r"^am:rm:\d+$"))

    am_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_am_add_start, pattern="^am:add$")],
        states={
            AM_ADD_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_am_add_user)],
            AM_ADD_ROLE: [CallbackQueryHandler(cb_am_add_role, pattern=r"^am:role:(senior|junior)$")],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(am_add_conv)
    app.add_handler(CallbackQueryHandler(cb_admin_stats, pattern="^ad:stats$"))
    app.add_handler(CallbackQueryHandler(cb_stats_top_files, pattern="^stats:topfiles$"))
    app.add_handler(CallbackQueryHandler(cb_admin_maintenance, pattern="^ad:maintenance$"))
    app.add_handler(CallbackQueryHandler(cb_mt_toggle, pattern="^mt:(on|off)$"))
    app.add_handler(CallbackQueryHandler(cb_admin_settings, pattern="^ad:settings$"))

    upload_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_admin_upload_start, pattern="^ad:upload$"),
            MessageHandler(filters.Regex("^📤 Upload File$"), cb_admin_upload_start),
        ],
        states={
            UP_FILE: [MessageHandler(
                (filters.Document.ALL | filters.VIDEO | filters.AUDIO | filters.PHOTO | filters.VOICE | filters.ANIMATION) & ~filters.COMMAND,
                conv_upload_file
            )],
            UP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_upload_name)],
            UP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_upload_desc)],
            UP_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_upload_price)],
            UP_CURRENCY: [
                CallbackQueryHandler(cb_upload_currency, pattern="^up:cur:(coins|gems)$"),
                CallbackQueryHandler(cb_upload_cancel, pattern="^up:cancel$"),
            ],
            UP_PREVIEW: [
                CallbackQueryHandler(cb_upload_publish, pattern="^up:publish$"),
                CallbackQueryHandler(cb_upload_edit, pattern="^up:edit$"),
                CallbackQueryHandler(cb_upload_cancel, pattern="^up:cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(upload_conv)

    app.add_handler(CallbackQueryHandler(cb_admin_bfmedia_panel, pattern="^ad:bfmedia$"))
    app.add_handler(CallbackQueryHandler(cb_bfmedia_preview, pattern="^bfm:preview$"))
    app.add_handler(CallbackQueryHandler(cb_bfmedia_remove_ask, pattern="^bfm:remove$"))
    app.add_handler(CallbackQueryHandler(cb_bfmedia_remove_confirm, pattern="^bfm:removeyes$"))

    bfmedia_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_admin_bfmedia_start, pattern="^bfm:set$"),
        ],
        states={
            BF_MEDIA: [
                MessageHandler(
                    (filters.PHOTO | filters.VIDEO | filters.ANIMATION) & ~filters.COMMAND,
                    conv_bfmedia_receive,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(bfmedia_conv)

    app.add_handler(CallbackQueryHandler(cb_admin_wslides_panel, pattern="^ad:wslides$"))
    app.add_handler(CallbackQueryHandler(cb_wslides_preview, pattern="^ws:preview$"))
    app.add_handler(CallbackQueryHandler(cb_wslides_clear_ask, pattern="^ws:clearask$"))
    app.add_handler(CallbackQueryHandler(cb_wslides_clear_confirm, pattern="^ws:clearyes$"))

    wslides_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_wslides_add_start, pattern="^ws:addstart$"),
        ],
        states={
            WS_COLLECT: [
                MessageHandler(
                    (filters.PHOTO | filters.VIDEO | filters.ANIMATION) & ~filters.COMMAND,
                    conv_wslides_receive,
                ),
                CallbackQueryHandler(cb_wslides_save, pattern="^ws:save$"),
                CallbackQueryHandler(cb_wslides_cancel, pattern="^ws:cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(wslides_conv)

    # --- previously dead buttons now wired up ---
    app.add_handler(CallbackQueryHandler(cb_my_referrals, pattern=r"^myrefs:\d+$"))

    mf_search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_mf_search_start, pattern="^mf:searchstart$")],
        states={MF_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_mf_search)]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(mf_search_conv)

    file_request_conv = ConversationHandler(
        entry_points=[CommandHandler("request", handle_file_request_prompt)],
        states={FR_TEXT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_file_request_text),
            CallbackQueryHandler(cb_file_request_cancel, pattern="^freq:cancel$"),
        ]},
        fallbacks=[
            CallbackQueryHandler(cb_file_request_cancel, pattern="^freq:cancel$"),
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(file_request_conv)

    app.add_handler(CallbackQueryHandler(cb_mf_list, pattern=r"^mf:list:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_mf_view, pattern=r"^mf:view:\d+:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_mf_delete, pattern=r"^mf:delete:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_mf_delete_confirm, pattern=r"^mf:delconfirm:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_mf_toggle_featured, pattern=r"^mf:tfeat:\d+:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_mf_toggle_currency, pattern=r"^mf:tcur:\d+:\d+$"))

    edit_field_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_mf_edit_field, pattern=r"^mf:(ename|edesc|eprice|etier):\d+$")],
        states={EF_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_edit_field_value)]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(edit_field_conv)

    fc_add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_fc_add_start, pattern="^fc:add$")],
        states={
            FC_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_fc_add)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(fc_add_conv)
    app.add_handler(CallbackQueryHandler(cb_fc_list, pattern="^fc:list$"))
    app.add_handler(CallbackQueryHandler(cb_fc_remove_menu, pattern="^fc:remove$"))
    app.add_handler(CallbackQueryHandler(cb_fc_remove_confirm, pattern=r"^fc:rm:\d+$"))

    wm_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_wm_action_start, pattern="^wm:(add|remove|reset|setbal|addg|remg|setgem)$")],
        states={
            UM_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_wm_user_id)],
            UM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_wm_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(wm_conv)
    app.add_handler(CallbackQueryHandler(cb_wm_history, pattern="^wm:history$"))

    wb_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_wm_bulk_start, pattern="^wm:bulk$")],
        states={
            WB_IDS: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_wm_bulk_ids)],
            WB_ACTION: [
                CallbackQueryHandler(cb_wb_action_coins, pattern="^wb:(add|remove)$"),
                CallbackQueryHandler(cb_wb_action_ban, pattern="^wb:(ban|unban)$"),
                CallbackQueryHandler(cb_wb_action_premium_menu, pattern="^wb:premium$"),
                CallbackQueryHandler(cb_wb_cancel, pattern="^wb:cancel$"),
            ],
            WB_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_wm_bulk_amount)],
            WB_PREMIUM: [CallbackQueryHandler(cb_wb_action_premium_set, pattern=r"^wb:pset:\d+$")],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(wb_conv)

    app.add_handler(CallbackQueryHandler(cb_pending_payments_list, pattern=r"^pp:list:\d+$"))

    rm_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_rm_create_start, pattern="^rm:create$")],
        states={
            RM_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_code)],
            RM_COINS: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_coins)],
            RM_PREMIUM: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_premium)],
            RM_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_limit)],
            RM_EXPIRY: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_expiry)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(rm_conv)
    app.add_handler(CallbackQueryHandler(cb_rm_list, pattern="^rm:list$"))
    app.add_handler(CallbackQueryHandler(cb_rm_delete_all_confirm, pattern="^rm:delall$"))
    app.add_handler(CallbackQueryHandler(cb_rm_delete_all_execute, pattern="^rm:delallconfirm$"))

    rm_delete_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_rm_delete_start, pattern="^rm:delstart$")],
        states={RM_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_rm_delete)]},
        fallbacks=[CallbackQueryHandler(cb_rm_delete_cancel, pattern="^rm:delcancel$"), CommandHandler("cancel", cmd_cancel), MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape)],
        per_message=False,
    )
    app.add_handler(rm_delete_conv)

    um_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_admin_usermgr, pattern="^ad:usermgr$"),
            MessageHandler(filters.Regex("^👥 User Manager$"), cb_admin_usermgr),
            CallbackQueryHandler(cb_um_coins_start, pattern=r"^um:(addc|remc|addg|remg):\d+$"),
        ],
        states={
            UM_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_um_search)],
            UM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_um_coins_amount)],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(um_conv)
    app.add_handler(CallbackQueryHandler(cb_um_ban, pattern=r"^um:(ban|unban):\d+$"))
    app.add_handler(CallbackQueryHandler(cb_um_premium, pattern=r"^um:(givep|remp):\d+$"))
    app.add_handler(CallbackQueryHandler(cb_um_pset, pattern=r"^um:pset:\d+:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_um_back, pattern=r"^um:back:\d+$"))

    app.add_handler(CallbackQueryHandler(cb_au_list, pattern=r"^au:list:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_au_view, pattern=r"^au:view:\d+:\d+$"))

    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_admin_broadcast_start, pattern="^ad:broadcast$"),
            MessageHandler(filters.Regex("^📢 Broadcast$"), cb_admin_broadcast_start),
        ],
        states={BR_CONTENT: [MessageHandler(
            (filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Sticker.ALL |
             filters.Document.ALL | filters.VOICE | filters.AUDIO) & ~filters.COMMAND,
            conv_broadcast_content
        )]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(broadcast_conv)

    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_settings_field, pattern=r"^set:\w+$")],
        states={ST_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex(_MENU_ESCAPE_REGEX), conv_settings_value)]},
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
            MessageHandler(filters.Regex(_MENU_ESCAPE_REGEX), cmd_menu_escape),
        ],
        per_message=False,
    )
    app.add_handler(settings_conv)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    app.add_handler(CommandHandler("cancel", cmd_cancel), group=1)

    app.add_error_handler(error_handler)
    return app


async def post_init(app: Application) -> None:
    global _BOT_INSTANCE, BOT_USERNAME
    _BOT_INSTANCE = app.bot
    try:
        me = await app.bot.get_me()
        if me.username:
            BOT_USERNAME = me.username
            log.info(f"Auto-detected BOT_USERNAME: @{BOT_USERNAME}")
    except Exception as e:
        log.warning(f"Could not auto-detect bot username, using fallback '{BOT_USERNAME}': {e}")
    try:
        await app.bot.set_my_name(name=APP_NAME)
        log.info("Telegram display name set to %s", APP_NAME)
    except Exception as e:
        log.warning("Could not set Telegram display name: %s", e)
    await init_db()
    await init_db_pool()
    if app.job_queue:
        app.job_queue.run_repeating(job_expire_premium, interval=3600, first=10)
        app.job_queue.run_repeating(job_expire_redeem_codes, interval=3600, first=15)
    log.info("Bot initialized and ready.")


async def post_shutdown(app: Application) -> None:
    await close_db_pool()


def _start_dummy_webserver() -> None:
    """Run a tiny fixed-port health server for hosting-service health checks."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    port = HEALTH_CHECK_PORT

    class _Health(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):
            pass  # silence default request logging

    def _serve():
        HTTPServer(("0.0.0.0", port), _Health).serve_forever()

    threading.Thread(target=_serve, daemon=True).start()
    log.info(f"Dummy health server listening on port {port} (for Render).")


def main() -> None:
    _validate_config()
    _start_dummy_webserver()
    app = build_application()
    log.info("Starting %s...", APP_NAME)
    app.run_polling(
        allowed_updates=["message", "callback_query", "chat_join_request"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
