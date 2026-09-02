"""
Übersetzungen für den Telegram Bot
Unterstützte Sprachen: de (Deutsch), tr (Türkisch), en (Englisch)
"""

TEXTS = {
    "de": {
        # Start
        "start_welcome": "👋 <b>Sportwetten-Analyse Bot</b>\n\n📋 <b>Befehle:</b>\n/today – Heutige Matches\n/date 15.02.2025 – Matches an einem Datum\n/dates – Alle verfügbaren Daten\n/bet – Wett-Empfehlungen für heute\n/lang – Sprache ändern\n\nPowered by SMART-PRECISION v4.7+ ⚽",
        "btn_today": "📅 Heute",
        "btn_bet": "💰 Empfehlungen",
        "btn_all_dates": "📆 Alle Daten",

        # Today
        "loading_today": "🔄 Lade heutige Matches...",
        "no_matches_today": "📭 Keine Matches für heute gefunden.",
        "no_tabs_today": "📭 Keine Match-Tabs gefunden.",
        "title_today": "HEUTE – {date}",
        "click_number": "💡 Klicke eine Zahl für die Analyse",

        # Dates
        "loading_dates": "🔄 Lade verfügbare Daten...",
        "no_dates": "📭 Keine Daten verfügbar.",
        "title_dates": "📆 <b>VERFÜGBARE DATEN</b> ({count} Tage)\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "hint_date": "💡 Nutze /date DD.MM.YYYY",

        # Date
        "format_date": "❌ Format: /date DD.MM.YYYY\nBeispiel: /date 15.02.2025",
        "loading_date": "🔄 Lade Matches für {date}...",
        "no_data_date": "❌ Keine Daten für {date} gefunden.",
        "no_tabs_date": "📭 Keine Match-Tabs für {date}.",
        "title_date": "MATCHES – {date}",

        # Bet
        "loading_bet": "💰 Berechne Wett-Empfehlungen...",
        "no_matches_bet": "📭 Keine heutigen Matches vorhanden.",
        "analyzing": "⏳ Analysiere {count} Matches...",
        "no_value_bets": "📭 <b>Keine klaren Value Bets heute</b>\n\nKein ausreichendes Value (Edge < 5%) oder zu hohes Risiko.\n\nNutze /today für manuelle Analyse.",
        "title_bet": "💰 <b>VALUE BETS – {date}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "bet_tip": "Tipp",
        "bet_quote": "Quote",
        "bet_prob": "Prob",
        "bet_edge": "Edge",
        "bet_risk": "Risiko",

        # Analysis
        "analyzing_match": "⏳ Analysiere {home} vs {away}...",
        "analysis_failed": "❌ Analyse fehlgeschlagen – Tab-Daten unvollständig?",
        "cache_miss": "❌ Match nicht mehr im Cache. Nutze /today erneut.",
        "prognose": "Prognose",
        "wahrscheinlichkeiten": "📊 <b>Wahrscheinlichkeiten</b>",
        "heimsieg": "Heimsieg",
        "unentschieden": "Unentschieden",
        "auswaertssieg": "Auswärtssieg",
        "ueber": "Über 2.5",
        "unter": "Unter 2.5",
        "btts_ja": "BTTS Ja",
        "btts_nein": "BTTS Nein",
        "mu_label": "🔢 μ: Heim {home} | Gast {away}",
        "tki_krise": "⚠️ TKI-Krise: {team} ({val})",
        "risiko": "Risiko",
        "risk_labels": {
            0: "Sehr niedrig",
            1: "Gute Basis",
            2: "Solide",
            3: "Standard-Risiko",
            4: "Vorsicht",
            5: "Sehr spekulativ",
        },

        # Bet types
        "bet_types": {
            "Heimsieg": "Heimsieg",
            "Unentschieden": "Unentschieden",
            "Auswärtssieg": "Auswärtssieg",
            "Über 2.5": "Über 2.5",
            "Unter 2.5": "Unter 2.5",
            "BTTS Ja": "BTTS Ja",
            "BTTS Nein": "BTTS Nein",
        },

        # Lang
        "lang_current": "🌍 <b>Sprache / Language / Dil</b>\n\nAktuelle Sprache: <b>Deutsch 🇩🇪</b>",
        "lang_changed": "✅ Sprache auf <b>Deutsch 🇩🇪</b> geändert.",
        "btn_de": "🇩🇪 Deutsch",
        "btn_tr": "🇹🇷 Türkçe",
        "btn_en": "🇬🇧 English",

        # Errors
        "error": "❌ Fehler: {msg}",
        "unknown_action": "⚠️ Unbekannte Aktion",
        "folder_not_configured": "❌ GOOGLE_DRIVE_FOLDER_ID nicht konfiguriert.",
    },

    "tr": {
        "start_welcome": "👋 <b>Spor Bahis Analiz Botu</b>\n\n📋 <b>Komutlar:</b>\n/today – Bugünün maçları\n/date 15.02.2025 – Belirli tarihin maçları\n/dates – Tüm mevcut tarihler\n/bet – Bugünün bahis önerileri\n/lang – Dil değiştir\n\nSMART-PRECISION v4.7+ ⚽ ile güçlendirildi",
        "btn_today": "📅 Bugün",
        "btn_bet": "💰 Öneriler",
        "btn_all_dates": "📆 Tüm Tarihler",

        "loading_today": "🔄 Bugünün maçları yükleniyor...",
        "no_matches_today": "📭 Bugün için maç bulunamadı.",
        "no_tabs_today": "📭 Maç sekmesi bulunamadı.",
        "title_today": "BUGÜN – {date}",
        "click_number": "💡 Analiz için bir numara tıkla",

        "loading_dates": "🔄 Mevcut tarihler yükleniyor...",
        "no_dates": "📭 Mevcut veri yok.",
        "title_dates": "📆 <b>MEVCUT TARİHLER</b> ({count} gün)\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "hint_date": "💡 /date GG.AA.YYYY kullan",

        "format_date": "❌ Format: /date GG.AA.YYYY\nÖrnek: /date 15.02.2025",
        "loading_date": "🔄 {date} için maçlar yükleniyor...",
        "no_data_date": "❌ {date} için veri bulunamadı.",
        "no_tabs_date": "📭 {date} için maç sekmesi yok.",
        "title_date": "MAÇLAR – {date}",

        "loading_bet": "💰 Bahis önerileri hesaplanıyor...",
        "no_matches_bet": "📭 Bugün maç yok.",
        "analyzing": "⏳ {count} maç analiz ediliyor...",
        "no_value_bets": "📭 <b>Bugün net value bahis yok</b>\n\nYeterli value yok (Edge < %5) veya risk çok yüksek.\n\nManuel analiz için /today kullan.",
        "title_bet": "💰 <b>VALUE BAHİSLER – {date}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "bet_tip": "Tahmin",
        "bet_quote": "Oran",
        "bet_prob": "Olasılık",
        "bet_edge": "Edge",
        "bet_risk": "Risk",

        "analyzing_match": "⏳ {home} vs {away} analiz ediliyor...",
        "analysis_failed": "❌ Analiz başarısız – Sekme verisi eksik?",
        "cache_miss": "❌ Maç önbellekte yok. /today komutunu tekrar kullan.",
        "prognose": "Tahmin",
        "wahrscheinlichkeiten": "📊 <b>Olasılıklar</b>",
        "heimsieg": "Ev Sahibi Galibiyeti",
        "unentschieden": "Beraberlik",
        "auswaertssieg": "Deplasman Galibiyeti",
        "ueber": "2.5 Üst",
        "unter": "2.5 Alt",
        "btts_ja": "KG Var",
        "btts_nein": "KG Yok",
        "mu_label": "🔢 μ: Ev {home} | Deplasman {away}",
        "tki_krise": "⚠️ TKI Krizi: {team} ({val})",
        "risiko": "Risk",
        "risk_labels": {
            0: "Çok düşük",
            1: "İyi temel",
            2: "Sağlam",
            3: "Standart risk",
            4: "Dikkatli ol",
            5: "Çok spekülatif",
        },

        "bet_types": {
            "Heimsieg": "Ev Sahibi",
            "Unentschieden": "Beraberlik",
            "Auswärtssieg": "Deplasman",
            "Über 2.5": "2.5 Üst",
            "Unter 2.5": "2.5 Alt",
            "BTTS Ja": "KG Var",
            "BTTS Nein": "KG Yok",
        },

        "lang_current": "🌍 <b>Sprache / Language / Dil</b>\n\nMevcut dil: <b>Türkçe 🇹🇷</b>",
        "lang_changed": "✅ Dil <b>Türkçe 🇹🇷</b> olarak değiştirildi.",
        "btn_de": "🇩🇪 Deutsch",
        "btn_tr": "🇹🇷 Türkçe",
        "btn_en": "🇬🇧 English",

        "error": "❌ Hata: {msg}",
        "unknown_action": "⚠️ Bilinmeyen işlem",
        "folder_not_configured": "❌ GOOGLE_DRIVE_FOLDER_ID yapılandırılmamış.",
    },

    "en": {
        "start_welcome": "👋 <b>Sports Betting Analysis Bot</b>\n\n📋 <b>Commands:</b>\n/today – Today's matches\n/date 15.02.2025 – Matches on a date\n/dates – All available dates\n/bet – Betting recommendations for today\n/lang – Change language\n\nPowered by SMART-PRECISION v4.7+ ⚽",
        "btn_today": "📅 Today",
        "btn_bet": "💰 Recommendations",
        "btn_all_dates": "📆 All Dates",

        "loading_today": "🔄 Loading today's matches...",
        "no_matches_today": "📭 No matches found for today.",
        "no_tabs_today": "📭 No match tabs found.",
        "title_today": "TODAY – {date}",
        "click_number": "💡 Click a number to analyse",

        "loading_dates": "🔄 Loading available dates...",
        "no_dates": "📭 No data available.",
        "title_dates": "📆 <b>AVAILABLE DATES</b> ({count} days)\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "hint_date": "💡 Use /date DD.MM.YYYY",

        "format_date": "❌ Format: /date DD.MM.YYYY\nExample: /date 15.02.2025",
        "loading_date": "🔄 Loading matches for {date}...",
        "no_data_date": "❌ No data found for {date}.",
        "no_tabs_date": "📭 No match tabs for {date}.",
        "title_date": "MATCHES – {date}",

        "loading_bet": "💰 Calculating betting recommendations...",
        "no_matches_bet": "📭 No matches today.",
        "analyzing": "⏳ Analysing {count} matches...",
        "no_value_bets": "📭 <b>No clear value bets today</b>\n\nInsufficient value (Edge < 5%) or risk too high.\n\nUse /today for manual analysis.",
        "title_bet": "💰 <b>VALUE BETS – {date}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n",
        "bet_tip": "Tip",
        "bet_quote": "Odds",
        "bet_prob": "Prob",
        "bet_edge": "Edge",
        "bet_risk": "Risk",

        "analyzing_match": "⏳ Analysing {home} vs {away}...",
        "analysis_failed": "❌ Analysis failed – Tab data incomplete?",
        "cache_miss": "❌ Match no longer in cache. Use /today again.",
        "prognose": "Prediction",
        "wahrscheinlichkeiten": "📊 <b>Probabilities</b>",
        "heimsieg": "Home Win",
        "unentschieden": "Draw",
        "auswaertssieg": "Away Win",
        "ueber": "Over 2.5",
        "unter": "Under 2.5",
        "btts_ja": "BTTS Yes",
        "btts_nein": "BTTS No",
        "mu_label": "🔢 μ: Home {home} | Away {away}",
        "tki_krise": "⚠️ TKI Crisis: {team} ({val})",
        "risiko": "Risk",
        "risk_labels": {
            0: "Very low",
            1: "Good base",
            2: "Solid",
            3: "Standard risk",
            4: "Caution",
            5: "Very speculative",
        },

        "bet_types": {
            "Heimsieg": "Home Win",
            "Unentschieden": "Draw",
            "Auswärtssieg": "Away Win",
            "Über 2.5": "Over 2.5",
            "Unter 2.5": "Under 2.5",
            "BTTS Ja": "BTTS Yes",
            "BTTS Nein": "BTTS No",
        },

        "lang_current": "🌍 <b>Sprache / Language / Dil</b>\n\nCurrent language: <b>English 🇬🇧</b>",
        "lang_changed": "✅ Language changed to <b>English 🇬🇧</b>.",
        "btn_de": "🇩🇪 Deutsch",
        "btn_tr": "🇹🇷 Türkçe",
        "btn_en": "🇬🇧 English",

        "error": "❌ Error: {msg}",
        "unknown_action": "⚠️ Unknown action",
        "folder_not_configured": "❌ GOOGLE_DRIVE_FOLDER_ID not configured.",
    },
}

DEFAULT_LANG = "de"


def t(key: str, lang: str = "de", **kwargs) -> str:
    """Gibt übersetzten Text zurück"""
    lang = lang if lang in TEXTS else DEFAULT_LANG
    text = TEXTS[lang].get(key, TEXTS[DEFAULT_LANG].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except Exception:
            pass
    return text


def get_risk_label(risk: int, lang: str = "de") -> str:
    lang = lang if lang in TEXTS else DEFAULT_LANG
    return TEXTS[lang]["risk_labels"].get(risk, "")


def get_bet_type(bet_type: str, lang: str = "de") -> str:
    lang = lang if lang in TEXTS else DEFAULT_LANG
    return TEXTS[lang]["bet_types"].get(bet_type, bet_type)
