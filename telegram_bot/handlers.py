"""
Telegram Bot Handler - Sportwetten Analyse (Mehrsprachig)
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram_bot.sheets_service import (
    list_available_dates,
    list_tabs_in_sheet,
    read_sheet_tab,
    get_todays_sheet_id,
)
from telegram_bot.translations import t, get_risk_label, get_bet_type

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# SPRACHE
# ─────────────────────────────────────────────

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "de")


# ─────────────────────────────────────────────
# HILFSFUNKTIONEN
# ─────────────────────────────────────────────

def _run_analysis(spreadsheet_id: str, tab_name: str) -> Optional[dict]:
    try:
        from data.parser import DataParser
        from analysis.match_analysis import analyze_match_v47_ml
        from app import choose_consistent_predicted_score

        raw_text = read_sheet_tab(spreadsheet_id, tab_name)
        if not raw_text.strip():
            return None

        parser = DataParser()
        match_data = parser.parse(raw_text)
        result = analyze_match_v47_ml(match_data)
        result = choose_consistent_predicted_score(result)
        return result
    except Exception as e:
        logger.error(f"Analyse-Fehler für Tab '{tab_name}': {e}", exc_info=True)
        return None


def _format_analysis(result: dict, lang: str = "de") -> str:
    info = result.get("match_info", {})
    probs = result.get("probabilities", {})
    mu = result.get("mu", {})
    risk_score = result.get("risk_score", 0)
    ext_risk = result.get("extended_risk", {})
    score = result.get("predicted_score", "?-?")
    tki = result.get("tki", {})

    home = info.get("home", info.get("home_team", "Heim"))
    away = info.get("away", info.get("away_team", "Gast"))
    competition = info.get("competition", "")
    kickoff = info.get("kickoff", "")

    _overall = ext_risk.get("overall", risk_score) if ext_risk else risk_score
    if isinstance(_overall, dict):
        overall_risk = _overall.get("score", _overall.get("value", risk_score))
    else:
        overall_risk = _overall
    try:
        overall_risk = int(overall_risk)
    except Exception:
        overall_risk = int(risk_score)

    empfehlung = get_risk_label(overall_risk, lang)
    risk_emoji = ["🟢", "🟢", "🟡", "🟡", "🔴", "🔴"][min(overall_risk, 5)]

    tki_h = tki.get("home", 0)
    tki_a = tki.get("away", 0)
    tki_note = ""
    if tki_h > 2.5:
        tki_note += f"\n{t('tki_krise', lang, team=home, val=tki_h)}"
    if tki_a > 2.5:
        tki_note += f"\n{t('tki_krise', lang, team=away, val=tki_a)}"

    # Gelbe Punkte bei erfüllten Kriterien (identisch mit Streamlit)
    def dot(prob, threshold):
        return "🟡 " if prob >= threshold else "     "

    hw = probs.get("home_win", 0)
    dr = probs.get("draw", 0)
    aw = probs.get("away_win", 0)
    ov = probs.get("over_25", 0)
    un = probs.get("under_25", 0)
    by = probs.get("btts_yes", 0)
    bn = probs.get("btts_no", 0)

    text = (
        f"⚽ <b>{home} vs {away}</b>\n"
        f"🏆 {competition}  |  ⏰ {kickoff}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 <b>{t('prognose', lang)}: {score}</b>\n\n"
        f"{t('wahrscheinlichkeiten', lang)}\n"
        f"  {dot(hw,50)}{t('heimsieg', lang)}:      <b>{hw:.1f}%</b>\n"
        f"  {dot(dr,50)}{t('unentschieden', lang)}: <b>{dr:.1f}%</b>\n"
        f"  {dot(aw,50)}{t('auswaertssieg', lang)}: <b>{aw:.1f}%</b>\n\n"
        f"  {dot(ov,60)}{t('ueber', lang)}:  <b>{ov:.1f}%</b>\n"
        f"  {dot(un,60)}{t('unter', lang)}: <b>{un:.1f}%</b>\n"
        f"  {dot(by,60)}{t('btts_ja', lang)}:   <b>{by:.1f}%</b>\n"
        f"  {dot(bn,60)}{t('btts_nein', lang)}: <b>{bn:.1f}%</b>\n"
        f"{tki_note}\n"
        f"{t('mu_label', lang, home=mu.get('home', 0), away=mu.get('away', 0))}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{risk_emoji} <b>{t('risiko', lang)}: {overall_risk}/5</b>  {empfehlung}\n"
    )
    return text


def _format_match_list(matches: list, title: str, lang: str = "de") -> str:
    text = f"📅 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, m in enumerate(matches, 1):
        text += f"{i}. {m['home']} vs {m['away']}\n"
    text += f"\n{t('click_number', lang)}"
    return text


# ─────────────────────────────────────────────
# COMMAND HANDLERS
# ─────────────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    keyboard = [
        [
            InlineKeyboardButton(t("btn_today", lang), callback_data="cmd_today"),
            InlineKeyboardButton(t("btn_bet", lang), callback_data="cmd_bet"),
        ],
        [InlineKeyboardButton(t("btn_all_dates", lang), callback_data="cmd_dates")],
    ]
    await update.message.reply_html(
        t("start_welcome", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def lang_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    keyboard = [
        [
            InlineKeyboardButton(t("btn_de", lang), callback_data="lang_de"),
            InlineKeyboardButton(t("btn_tr", lang), callback_data="lang_tr"),
            InlineKeyboardButton(t("btn_en", lang), callback_data="lang_en"),
        ]
    ]
    await update.message.reply_html(
        t("lang_current", lang),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    msg = update.message or update.callback_query.message
    loading = await msg.reply_html(t("loading_today", lang))

    result = get_todays_sheet_id()
    if not result:
        await loading.edit_text(t("no_matches_today", lang))
        return

    date_str, sheet_id = result
    tabs = list_tabs_in_sheet(sheet_id)
    skip = {"overview", "übersicht", "zusammenfassung", "tracking", "results"}
    match_tabs = [t_ for t_ in tabs if t_.lower() not in skip]

    if not match_tabs:
        await loading.edit_text(t("no_tabs_today", lang))
        return

    matches = [
        {"home": t_.split(" vs ")[0].strip() if " vs " in t_ else t_,
         "away": t_.split(" vs ")[1].strip() if " vs " in t_ else "",
         "tab": t_, "sheet_id": sheet_id}
        for t_ in match_tabs
    ]
    context.bot_data[f"matches_{date_str}"] = matches

    text = _format_match_list(
        [{"home": m["home"], "away": m["away"]} for m in matches],
        t("title_today", lang, date=date_str),
        lang
    )

    keyboard = []
    row = []
    for i in range(1, len(match_tabs) + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"analyze_{date_str}_{i-1}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await loading.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def dates_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    msg = update.message or update.callback_query.message
    loading = await msg.reply_html(t("loading_dates", lang))

    dates = list_available_dates()
    if not dates:
        await loading.edit_text(t("no_dates", lang))
        return

    sorted_dates = sorted(dates.keys(), reverse=True)
    text = t("title_dates", lang, count=len(sorted_dates))

    by_month: dict = {}
    for d in sorted_dates:
        month = d[3:]
        by_month.setdefault(month, []).append(d)

    for month in sorted(by_month.keys(), reverse=True)[:4]:
        text += f"<b>{month}</b>\n"
        for d in by_month[month][:10]:
            text += f"  • {d}\n"
        text += "\n"

    text += t("hint_date", lang)
    await loading.edit_text(text, parse_mode="HTML")


async def date_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    if not context.args:
        await update.message.reply_html(t("format_date", lang))
        return

    date_str = context.args[0]
    loading = await update.message.reply_html(t("loading_date", lang, date=date_str))

    dates = list_available_dates()
    if date_str not in dates:
        await loading.edit_text(t("no_data_date", lang, date=date_str))
        return

    sheet_id = dates[date_str]
    tabs = list_tabs_in_sheet(sheet_id)
    skip = {"overview", "übersicht", "zusammenfassung", "tracking", "results"}
    match_tabs = [t_ for t_ in tabs if t_.lower() not in skip]

    if not match_tabs:
        await loading.edit_text(t("no_tabs_date", lang, date=date_str))
        return

    matches = [
        {"home": t_.split(" vs ")[0].strip() if " vs " in t_ else t_,
         "away": t_.split(" vs ")[1].strip() if " vs " in t_ else "",
         "tab": t_, "sheet_id": sheet_id}
        for t_ in match_tabs
    ]
    context.bot_data[f"matches_{date_str}"] = matches

    text = _format_match_list(
        [{"home": m["home"], "away": m["away"]} for m in matches],
        t("title_date", lang, date=date_str),
        lang
    )

    keyboard = []
    row = []
    for i in range(1, len(match_tabs) + 1):
        row.append(InlineKeyboardButton(str(i), callback_data=f"analyze_{date_str}_{i-1}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    await loading.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def bet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    msg = update.message or update.callback_query.message
    loading = await msg.reply_html(t("loading_bet", lang))

    result = get_todays_sheet_id()
    if not result:
        await loading.edit_text(t("no_matches_bet", lang))
        return

    date_str, sheet_id = result
    tabs = list_tabs_in_sheet(sheet_id)
    skip = {"overview", "übersicht", "zusammenfassung", "tracking", "results"}
    match_tabs = [t_ for t_ in tabs if t_.lower() not in skip]

    if not match_tabs:
        await loading.edit_text(t("no_tabs_today", lang))
        return

    await loading.edit_text(t("analyzing", lang, count=len(match_tabs)))

    recommendations = []
    for tab in match_tabs:
        analysis = _run_analysis(sheet_id, tab)
        if not analysis:
            continue

        probs = analysis.get("probabilities", {})
        odds = analysis.get("odds", {})
        ext_risk = analysis.get("extended_risk", {})
        _ov = ext_risk.get("overall", analysis.get("risk_score", 5)) if ext_risk else analysis.get("risk_score", 5)
        if isinstance(_ov, dict):
            _ov = _ov.get("score", _ov.get("value", analysis.get("risk_score", 5)))
        try:
            overall_risk = int(_ov)
        except Exception:
            overall_risk = int(analysis.get("risk_score", 5))

        info = analysis.get("match_info", {})

        def implied(o):
            try: return 1 / float(o) * 100
            except: return 100

        odds_1x2 = odds.get("1x2", (0, 0, 0))
        odds_ou = odds.get("ou25", (0, 0))
        odds_btts = odds.get("btts", (0, 0))

        checks = [
            ("Heimsieg", probs.get("home_win", 0), implied(odds_1x2[0]), odds_1x2[0]),
            ("Unentschieden", probs.get("draw", 0), implied(odds_1x2[1]), odds_1x2[1]),
            ("Auswärtssieg", probs.get("away_win", 0), implied(odds_1x2[2]), odds_1x2[2]),
            ("Über 2.5", probs.get("over_25", 0), implied(odds_ou[0]), odds_ou[0]),
            ("Unter 2.5", probs.get("under_25", 0), implied(odds_ou[1]), odds_ou[1]),
            ("BTTS Ja", probs.get("btts_yes", 0), implied(odds_btts[0]), odds_btts[0]),
            ("BTTS Nein", probs.get("btts_no", 0), implied(odds_btts[1]), odds_btts[1]),
        ]

        for bet_type, our_prob, imp_prob, odd in checks:
            edge = our_prob - imp_prob
            if edge >= 5 and overall_risk <= 3 and odd:
                recommendations.append({
                    "home": info.get("home", info.get("home_team", "?")),
                    "away": info.get("away", info.get("away_team", "?")),
                    "bet_type": bet_type,
                    "prob": our_prob,
                    "odd": odd,
                    "edge": edge,
                    "risk": overall_risk,
                })

    if not recommendations:
        await loading.edit_text(t("no_value_bets", lang), parse_mode="HTML")
        return

    recommendations.sort(key=lambda x: x["edge"], reverse=True)

    text = t("title_bet", lang, date=date_str)
    for i, rec in enumerate(recommendations[:5], 1):
        risk_emoji = "🟢" if rec["risk"] <= 2 else "🟡"
        bet_label = get_bet_type(rec["bet_type"], lang)
        text += (
            f"<b>{i}. {rec['home']} vs {rec['away']}</b>\n"
            f"   {t('bet_tip', lang)}: <b>{bet_label}</b>\n"
            f"   {t('bet_quote', lang)}: {rec['odd']}  |  {t('bet_prob', lang)}: {rec['prob']:.1f}%\n"
            f"   {t('bet_edge', lang)}: +{rec['edge']:.1f}%  {risk_emoji} {t('bet_risk', lang)} {rec['risk']}/5\n\n"
        )

    await loading.edit_text(text, parse_mode="HTML")


# ─────────────────────────────────────────────
# CALLBACK HANDLER
# ─────────────────────────────────────────────

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    lang = get_lang(context)

    if data == "cmd_today":
        await today_handler(update, context)
    elif data == "cmd_bet":
        await bet_handler(update, context)
    elif data == "cmd_dates":
        await dates_handler(update, context)

    elif data.startswith("lang_"):
        new_lang = data.split("_")[1]
        if new_lang in ("de", "tr", "en"):
            context.user_data["lang"] = new_lang
            await query.edit_message_text(
                t("lang_changed", new_lang),
                parse_mode="HTML"
            )

    elif data.startswith("analyze_"):
        parts = data.split("_", 2)
        if len(parts) == 3:
            _, date_str, idx_str = parts
            try:
                idx = int(idx_str)
            except ValueError:
                await query.edit_message_text(t("unknown_action", lang))
                return

            matches = context.bot_data.get(f"matches_{date_str}")
            if not matches or idx >= len(matches):
                await query.edit_message_text(t("cache_miss", lang))
                return

            match = matches[idx]
            await query.edit_message_text(
                t("analyzing_match", lang, home=match["home"], away=match["away"])
            )

            result = _run_analysis(match["sheet_id"], match["tab"])
            if not result:
                await query.edit_message_text(t("analysis_failed", lang))
                return

            text = _format_analysis(result, lang)

            # Bankroll: alle erfüllten Wettarten als Toggle-Buttons
            from telegram_bot.bankroll import get_bankroll
            keyboard = None
            if get_bankroll(query.from_user.id) > 0:
                probs = result.get("probabilities", {})
                odds = result.get("odds", {})
                info = result.get("match_info", {})
                match_name = f"{info.get('home', '?')[:12]} vs {info.get('away', '?')[:12]}"

                ext = result.get("extended_risk", {})

                def _rs(d):
                    """Extrahiert risk_score als int aus dict oder int"""
                    if isinstance(d, dict):
                        return int(d.get("risk_score", d.get("score", 3)))
                    try:
                        return int(d)
                    except Exception:
                        return 3

                all_options = [
                    ("Heimsieg",      probs.get("home_win", 0),  50, odds.get("1x2", [0,0,0])[0], _rs(ext.get("1x2", 3))),
                    ("Unentschieden", probs.get("draw", 0),       50, odds.get("1x2", [0,0,0])[1], _rs(ext.get("1x2", 3))),
                    ("Auswärtssieg",  probs.get("away_win", 0),   50, odds.get("1x2", [0,0,0])[2], _rs(ext.get("1x2", 3))),
                    ("Über 2.5",      probs.get("over_25", 0),    60, odds.get("ou25", [0,0])[0],  _rs(ext.get("over_under", {}).get("over", 3))),
                    ("Unter 2.5",     probs.get("under_25", 0),   60, odds.get("ou25", [0,0])[1],  _rs(ext.get("over_under", {}).get("under", 3))),
                    ("BTTS Ja",       probs.get("btts_yes", 0),   60, odds.get("btts", [0,0])[0],  _rs(ext.get("btts", {}).get("yes", 3))),
                    ("BTTS Nein",     probs.get("btts_no", 0),    60, odds.get("btts", [0,0])[1],  _rs(ext.get("btts", {}).get("no", 3))),
                ]
                qualified = [(bt, prob, odd, rs) for bt, prob, thr, odd, rs in all_options if prob >= thr and odd > 0]

                if qualified:
                    uid = query.from_user.id
                    sess_key = f"bsess_{uid}"
                    context.bot_data[sess_key] = {
                        "match": match_name,
                        "date_str": date_str,
                        "qualified": [{"bet_type": bt, "prob": prob, "odds": odd, "risk_score": rs} for bt, prob, odd, rs in qualified],
                        "selected": [],  # ausgewählte Indizes
                    }
                    # Toggle-Buttons: alle unausgewählt
                    btn_rows = []
                    row = []
                    for i, (bt, prob, odd, rs) in enumerate(qualified):
                        row.append(InlineKeyboardButton(
                            f"⬜ {bt} @ {odd}",
                            callback_data=f"btog_{uid}_{i}"
                        ))
                        if len(row) == 2:
                            btn_rows.append(row)
                            row = []
                    if row:
                        btn_rows.append(row)
                    btn_rows.append([InlineKeyboardButton("✅ Weiter mit Auswahl", callback_data=f"bconf_{uid}")])
                    keyboard = InlineKeyboardMarkup(btn_rows)

            await query.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)
    elif data == "bank_open":
        await open_bets_handler(update, context)
    elif data == "bank_stats":
        await stats_handler(update, context)
    elif data == "bank_cancel":
        await query.edit_message_text("❌ Abgebrochen.")
    elif data == "bank_reset_confirm":
        keyboard = [[
            InlineKeyboardButton("✅ Ja, reset", callback_data="bank_reset_do"),
            InlineKeyboardButton("❌ Nein", callback_data="bank_cancel"),
        ]]
        await query.edit_message_text(
            "⚠️ Bankroll wirklich zurücksetzen? Alle Daten werden gelöscht.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "bank_reset_do":
        from telegram_bot.bankroll import set_bankroll, get_user_data
        init = get_user_data(query.from_user.id)["initial"]
        set_bankroll(query.from_user.id, init)
        await query.edit_message_text(f"✅ Bankroll zurückgesetzt auf {init:.2f} €")

    elif data.startswith("close_"):
        parts = data.split("_")
        bet_id = int(parts[1])
        won = parts[2] == "won"
        from telegram_bot.bankroll import close_bet
        result = close_bet(query.from_user.id, bet_id, won)
        if "error" in result:
            await query.answer("❌ Wette nicht gefunden", show_alert=True)
        else:
            emoji = "✅" if won else "❌"
            profit_str = f"+{result['profit']:.2f}" if result['profit'] >= 0 else f"{result['profit']:.2f}"
            await query.edit_message_text(
                "{} <b>Wette abgeschlossen!</b>\n\nErgebnis: <b>{}</b>\nP&L: <b>{} €</b>\n💼 Bankroll: <b>{:.2f} €</b>".format(
                    emoji,
                    "Gewonnen" if won else "Verloren",
                    profit_str,
                    result["bankroll"]
                ),
                parse_mode="HTML"
            )
    elif data.startswith("profil_"):
        key = data[len("profil_"):]
        from telegram_bot.bankroll import set_risk_profile, RISK_PROFILES
        if set_risk_profile(query.from_user.id, key):
            prof = RISK_PROFILES[key]
            keyboard = []
            for k, p in RISK_PROFILES.items():
                mark = "✅ " if k == key else ""
                keyboard.append([InlineKeyboardButton(
                    f"{mark}{p['name']} (max {p['max_stake_percent']}%)",
                    callback_data=f"profil_{k}"
                )])
            await query.edit_message_text(
                f"✅ Profil geändert: <b>{prof['name']}</b>\n\n"
                f"Adjustment: {prof['adjustment']}x\n"
                f"Max Einsatz: {prof['max_stake_percent']}% der Bankroll",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("btog_"):
        # Toggle Wettart an/aus
        parts = data.split("_")
        uid, idx = int(parts[1]), int(parts[2])
        sess_key = f"bsess_{uid}"
        sess = context.bot_data.get(sess_key)
        if not sess:
            await query.answer("❌ Session abgelaufen. Analyse erneut starten.", show_alert=True)
            return
        selected = sess["selected"]
        if idx in selected:
            selected.remove(idx)
        else:
            selected.append(idx)
        sess["selected"] = selected
        # Keyboard neu aufbauen mit Toggle-Status
        qualified = sess["qualified"]
        btn_rows = []
        row = []
        for i, opt in enumerate(qualified):
            is_sel = i in selected
            label = f"{'✅' if is_sel else '⬜'} {opt['bet_type']} @ {opt['odds']}"
            row.append(InlineKeyboardButton(label, callback_data=f"btog_{uid}_{i}"))
            if len(row) == 2:
                btn_rows.append(row)
                row = []
        if row:
            btn_rows.append(row)
        conf_label = f"✅ Weiter ({len(selected)} ausgewählt)" if selected else "✅ Weiter mit Auswahl"
        btn_rows.append([InlineKeyboardButton(conf_label, callback_data=f"bconf_{uid}")])
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn_rows))
        except Exception:
            pass

    elif data.startswith("bconf_"):
        # Bestätigung: Einsatz für erste ausgewählte Wette wählen
        uid = int(data.split("_")[1])
        sess_key = f"bsess_{uid}"
        sess = context.bot_data.get(sess_key)
        if not sess or not sess.get("selected"):
            await query.answer("❌ Keine Wettart ausgewählt!", show_alert=True)
            return
        # Starte mit erster ausgewählten Wette
        sess["pending"] = list(sess["selected"])  # noch zu verarbeitende
        sess["placed"] = []  # bereits platzierte
        context.bot_data[sess_key] = sess
        await _ask_stake(query, context, uid, sess_key)

    elif data.startswith("bstake_"):
        parts = data.split("_")
        uid, idx, choice = int(parts[1]), int(parts[2]), parts[3]
        sess_key = f"bsess_{uid}"
        sess = context.bot_data.get(sess_key)
        if not sess:
            await query.answer("Session abgelaufen.", show_alert=True)
            return
        from telegram_bot.bankroll import place_bet, calculate_stake
        opt = sess["qualified"][idx]
        if choice == "s":
            sess["pending"].pop(0)
            context.bot_data[sess_key] = sess
            if sess["pending"]:
                await _ask_stake(query, context, uid, sess_key)
            else:
                await _show_placed_summary(query, context, uid, sess_key)
            return
        stake_info = calculate_stake(uid, opt.get("risk_score", 3), float(opt["odds"]))
        stake = {"h": stake_info["half"], "r": stake_info["recommended"], "d": stake_info["double"]}.get(choice, stake_info["recommended"])
        result = place_bet(uid, sess["match"], opt["bet_type"], float(opt["odds"]), stake, float(opt["prob"]))
        if "error" in result:
            await query.answer(f"Fehler: {result['error']}", show_alert=True)
            return
        sess["placed"].append(result["bet"])
        sess["pending"].pop(0)
        context.bot_data[sess_key] = sess
        if sess["pending"]:
            await _ask_stake(query, context, uid, sess_key)
        else:
            await _show_placed_summary(query, context, uid, sess_key)

    elif data.startswith("bclose_"):
        # Ergebnis eintragen: bclose_{uid}_{bet_id}_{won/lost}
        parts = data.split("_")
        uid, bet_id, outcome = int(parts[1]), int(parts[2]), parts[3]
        from telegram_bot.bankroll import close_bet
        result = close_bet(uid, bet_id, outcome == "won")
        if "error" in result:
            await query.answer("❌ Wette nicht gefunden", show_alert=True)
            return
        # Update message mit neuem Keyboard (entferne diese Zeile)
        try:
            current_text = query.message.text or query.message.caption or ""
            profit_str = f"+{result['profit']:.2f}" if result['profit'] >= 0 else f"{result['profit']:.2f}"
            emoji = "✅" if outcome == "won" else "❌"
            new_text = current_text + f"\n{emoji} #{bet_id}: {profit_str} €"
            # Keyboard neu bauen ohne diese Wette
            old_kb = query.message.reply_markup.inline_keyboard if query.message.reply_markup else []
            new_kb = [row for row in old_kb if not any(f"bclose_{uid}_{bet_id}_" in btn.callback_data for btn in row if btn.callback_data)]
            if not any("bclose_" in str(row) for row in new_kb):
                profit_total = sum(b.get("profit", 0) for b in [result["bet"]])
                new_text += f"\n\n💼 Bankroll: <b>{result['bankroll']:.2f} €</b>"
                await query.edit_message_text(new_text, parse_mode="HTML")
            else:
                await query.edit_message_text(new_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(new_kb))
        except Exception:
            await query.answer(f"{'✅ Gewonnen' if outcome == 'won' else '❌ Verloren'}: {profit_str} €", show_alert=True)

    else:
        await query.edit_message_text(t("unknown_action", lang))



# ─────────────────────────────────────────────
# HELPER: Einsatz abfragen
# ─────────────────────────────────────────────

async def _ask_stake(query, context, uid: int, sess_key: str):
    sess = context.bot_data[sess_key]
    pending = sess["pending"]
    idx = pending[0]
    opt = sess["qualified"][idx]
    from telegram_bot.bankroll import calculate_stake
    risk_score = opt.get("risk_score", 3)
    stake_info = calculate_stake(uid, risk_score, float(opt["odds"]))
    done = len(sess["placed"])
    total = len(sess["selected"])
    text = (
        f"💰 <b>Wette {done+1}/{total}</b>\n\n"
        f"Match: <b>{sess['match']}</b>\n"
        f"Tipp: <b>{opt['bet_type']}</b> @ {opt['odds']}\n"
        f"Wahrsch.: <b>{opt['prob']:.1f}%</b>\n\n"
        f"💼 Bankroll: <b>{stake_info['bankroll']:.2f} €</b>\n"
        f"⚙️ Profil: <b>{stake_info['profile_name']}</b>\n\n"
        f"📐 Empfohlen: <b>{stake_info['recommended']:.2f} €</b> ({stake_info['percentage']}%)\n"
        f"🏆 Potentieller Gewinn: <b>+{stake_info['potential_win']:.2f} €</b>\n\n"
        "Wähle deinen Einsatz:"
    )
    keyboard = [
        [
            InlineKeyboardButton(f"½ ({stake_info['half']:.2f}€)",        callback_data=f"bstake_{uid}_{idx}_h"),
            InlineKeyboardButton(f"✅ Empfohlen ({stake_info['recommended']:.2f}€)", callback_data=f"bstake_{uid}_{idx}_r"),
        ],
        [
            InlineKeyboardButton(f"2× ({stake_info['double']:.2f}€)",     callback_data=f"bstake_{uid}_{idx}_d"),
            InlineKeyboardButton("❌ Überspringen",                         callback_data=f"bstake_{uid}_{idx}_s"),
        ],
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


async def _show_placed_summary(query, context, uid: int, sess_key: str):
    sess = context.bot_data[sess_key]
    placed = sess["placed"]
    from datetime import datetime
    today = datetime.now().strftime("%d.%m.%Y")
    is_today = sess.get("date_str", today) == today
    total_stake = sum(b["stake"] for b in placed)
    text = f"✅ <b>{len(placed)} Wette(n) platziert!</b>\n\n"
    for b in placed:
        text += f"• {b['bet_type']} @ {b['odds']} — {b['stake']:.2f} € → {b['potential_win']:.2f} €\n"
    text += f"\nGesamteinsatz: <b>{total_stake:.2f} €</b>"
    if is_today:
        text += "\n\nErgebnisse über /open eintragen wenn das Spiel beendet ist."
        await query.edit_message_text(text, parse_mode="HTML")
    else:
        # Sofort Gewonnen/Verloren abfragen
        text += "\n\nTrag die Ergebnisse direkt ein:"
        keyboard = []
        for b in placed:
            keyboard.append([
                InlineKeyboardButton(f"✅ #{b['id']} {b['bet_type']} Gewonnen", callback_data=f"bclose_{uid}_{b['id']}_won"),
                InlineKeyboardButton(f"❌ #{b['id']} Verloren", callback_data=f"bclose_{uid}_{b['id']}_lost"),
            ])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Fehler: {context.error}", exc_info=context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text(
            f"❌ Fehler: {str(context.error)[:200]}"
        )


# ─────────────────────────────────────────────
# BANKROLL HANDLERS
# ─────────────────────────────────────────────

async def bankroll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from telegram_bot.bankroll import get_user_data, get_stats
    data = get_user_data(user_id)
    stats = get_stats(user_id)

    if data["initial"] == 0:
        await update.message.reply_html(
            "💼 <b>Demo Bankroll</b>\n\n"
            "Noch kein Startkapital gesetzt.\n\n"
            "Nutze /setbank [Betrag] um zu starten.\n"
            "Beispiel: /setbank 1000"
        )
        return

    profit = data["bankroll"] - data["initial"]
    profit_emoji = "📈" if profit >= 0 else "📉"
    profit_str = f"+{profit:.2f}" if profit >= 0 else f"{profit:.2f}"

    text = (
        f"💼 <b>Demo Bankroll</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 Aktuell:     <b>{data['bankroll']:.2f} €</b>\n"
        f"🏦 Start:       <b>{data['initial']:.2f} €</b>\n"
        f"{profit_emoji} Gesamt P&L: <b>{profit_str} €</b>\n\n"
        f"📊 <b>Statistiken</b>\n"
        f"  Wetten:    {stats['total']} ({stats['won']}W / {stats['lost']}L)\n"
        f"  Win Rate:  {stats['win_rate']:.1f}%\n"
        f"  ROI:       {stats['roi']:+.1f}%\n"
        f"  Offen:     {stats['open']} Wetten\n"
    )
    keyboard = [
        [
            InlineKeyboardButton("📋 Offene Wetten", callback_data="bank_open"),
            InlineKeyboardButton("📈 Details", callback_data="bank_stats"),
        ],
        [InlineKeyboardButton("🔄 Reset", callback_data="bank_reset_confirm")],
    ]
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def setbank_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_html("❌ Format: /setbank [Betrag]\nBeispiel: /setbank 1000")
        return
    try:
        amount = float(context.args[0].replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_html("❌ Ungültiger Betrag. Beispiel: /setbank 1000")
        return

    from telegram_bot.bankroll import set_bankroll
    set_bankroll(user_id, amount)
    await update.message.reply_html(
        f"✅ <b>Bankroll gesetzt!</b>\n\n"
        f"💰 Startkapital: <b>{amount:.2f} €</b>\n\n"
        f"Nach einer Analyse kannst du direkt Wetten platzieren.\n"
        f"Nutze /bankroll für die Übersicht."
    )


async def open_bets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from telegram_bot.bankroll import get_open_bets, get_bankroll
    bets = get_open_bets(user_id)
    bankroll = get_bankroll(user_id)
    msg = update.message or update.callback_query.message

    if not bets:
        await msg.reply_html(
            f"📋 <b>Offene Wetten</b>\n\nKeine offenen Wetten.\n\n"
            f"💰 Verfügbar: <b>{bankroll:.2f} €</b>"
        )
        return

    text = f"📋 <b>Offene Wetten ({len(bets)})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n"
    keyboard = []
    for bet in bets:
        text += (
            f"<b>#{bet['id']} {bet['match']}</b>\n"
            f"  {bet['bet_type']} @ {bet['odds']}\n"
            f"  Einsatz: {bet['stake']:.2f} € → Gewinn: {bet['potential_win']:.2f} €\n"
            f"  📅 {bet['date']}\n\n"
        )
        keyboard.append([
            InlineKeyboardButton(f"✅ #{bet['id']} Gewonnen", callback_data=f"close_{bet['id']}_won"),
            InlineKeyboardButton(f"❌ #{bet['id']} Verloren", callback_data=f"close_{bet['id']}_lost"),
        ])
    text += f"💰 Verfügbar: <b>{bankroll:.2f} €</b>"
    await msg.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from telegram_bot.bankroll import get_stats
    stats = get_stats(user_id)
    msg = update.message or update.callback_query.message

    if stats["initial"] == 0 or stats["total"] == 0:
        await msg.reply_html("📈 <b>Statistiken</b>\n\nNoch keine abgeschlossenen Wetten.")
        return

    roi_emoji = "📈" if stats["roi"] >= 0 else "📉"
    profit_str = f"+{stats['total_profit']:.2f}" if stats["total_profit"] >= 0 else f"{stats['total_profit']:.2f}"

    text = (
        f"📈 <b>Statistiken</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 Wetten gesamt: <b>{stats['total']}</b>\n"
        f"✅ Gewonnen:      <b>{stats['won']}</b>\n"
        f"❌ Verloren:      <b>{stats['lost']}</b>\n"
        f"🎯 Win Rate:      <b>{stats['win_rate']:.1f}%</b>\n\n"
        f"💶 Einsatz gesamt: <b>{stats['total_staked']:.2f} €</b>\n"
        f"💰 Profit:         <b>{profit_str} €</b>\n"
        f"{roi_emoji} ROI:            <b>{stats['roi']:+.1f}%</b>\n\n"
        f"🏦 Start:   <b>{stats['initial']:.2f} €</b>\n"
        f"💼 Aktuell: <b>{stats['bankroll']:.2f} €</b>\n"
    )
    if stats.get("best_win"):
        text += f"\n🏆 Bester Gewinn: <b>+{stats['best_win']['profit']:.2f} €</b> ({stats['best_win']['match']})\n"
    if stats.get("worst_loss"):
        text += f"💔 Größter Verlust: <b>{stats['worst_loss']['profit']:.2f} €</b> ({stats['worst_loss']['match']})\n"

    await msg.reply_html(text)


async def profil_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    from telegram_bot.bankroll import RISK_PROFILES, get_risk_profile
    current = get_risk_profile(user_id)
    current_name = RISK_PROFILES[current]["name"]

    text = (
        f"⚙️ <b>Risikoprofil</b>\n\n"
        f"Aktuell: <b>{current_name}</b>\n\n"
        f"Das Profil bestimmt die Einsatzhöhe\n"
        f"basierend auf dem Risiko-Score des Spiels."
    )
    keyboard = []
    for key, prof in RISK_PROFILES.items():
        mark = "✅ " if key == current else ""
        keyboard.append([InlineKeyboardButton(
            f"{mark}{prof['name']} (max {prof['max_stake_percent']}%)",
            callback_data=f"profil_{key}"
        )])
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))
