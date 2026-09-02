"""
Erweiterte Visualisierungs-Komponenten
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List
from models.tracking import load_historical_matches_from_sheets


def show_poisson_heatmap(result: Dict):
    """
    Zeigt Poisson-Verteilung als Heatmap mit wahrscheinlichsten Ergebnissen

    Args:
        result: Analyse-Ergebnis Dictionary
    """
    st.subheader("📊 Wahrscheinlichste Ergebnisse (Poisson-Verteilung)")

    # Hole Scorelines aus Result
    scorelines = result.get("scorelines", [])

    if not scorelines:
        st.warning("⚠️ Keine Scoreline-Daten verfügbar")
        return

    # Top 10 wahrscheinlichste Ergebnisse
    top_scorelines = scorelines[:10]

    # Erstelle DataFrame mit KORRIGIERTER Datenverarbeitung
    data = []
    for score, prob in top_scorelines:
        # Sicherstellen, dass der Score ein String ist
        score_str = str(score)
        # Sicherstellen, dass die Wahrscheinlichkeit eine Zahl ist
        try:
            prob_float = float(prob)
        except:
            prob_float = 0.0

        data.append(
            {
                "Ergebnis": score_str,
                "Wahrscheinlichkeit": f"{prob_float:.1f}%",
                "Wahrscheinlichkeit_Raw": prob_float,
            }
        )

    df = pd.DataFrame(data)
    styled_df = df[["Ergebnis", "Wahrscheinlichkeit"]].style.set_properties(
        **{
            "font-weight": "bold",
            "font-size": "20px",
            "color": "white",
            "background-color": "#0e1117",
        }
    )

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # KORRIGIERT: Sortiere nach Wahrscheinlichkeit absteigend
    df = df.sort_values("Wahrscheinlichkeit_Raw", ascending=False).reset_index(
        drop=True
    )

    # OPTIMIERTES Bar Chart mit größerer Schrift und grünen Balken
    fig = go.Figure(
        data=[
            go.Bar(
                x=df["Ergebnis"],
                y=df["Wahrscheinlichkeit_Raw"],
                text=df["Wahrscheinlichkeit"],
                textposition="auto",
                marker_color="darkgreen",
                textfont=dict(size=15, color="white", family="Arial"),
                marker=dict(line=dict(color="darkgreen", width=1)),
                hovertemplate="<b>%{x}</b><br>Wahrscheinlichkeit: %{text}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=dict(
            text="Top 10 Wahrscheinlichste Ergebnisse",
            font=dict(size=18, color="white"),
        ),
        xaxis=dict(
            title="Ergebnis",
            title_font=dict(size=16, color="white"),
            tickfont=dict(
                size=18,
            ),
        ),
        yaxis=dict(
            title="Wahrscheinlichkeit (%)",
            title_font=dict(size=16, color="white"),
            tickfont=dict(
                size=18,
            ),
        ),
        height=450,
        plot_bgcolor="rgba(14, 17, 23)",
        paper_bgcolor="rgba(14, 17, 23)",
        hoverlabel=dict(
            font_size=18,
            font_family="Arial",
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="darkgreen",
            font_color="black",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabelle mit Details - mit besserer Formatierung
    with st.expander("📋 Detaillierte Wahrscheinlichkeiten", expanded=True):
        # Füge Formatierung für die Tabelle hinzu
        styled_df = df[["Ergebnis", "Wahrscheinlichkeit"]].copy()

        # Highlight die Top 3 Ergebnisse
        def highlight_top(row):
            styles = [""] * len(row)
            try:
                idx = row.name
                if idx < 3:  # Top 3 Ergebnisse
                    styles = [
                        "background-color: #0e1117; font-weight: bold; font-size: 20px;"
                    ] * len(row)
                elif idx < 5:  # Top 4-5
                    styles = [
                        "background-color: #0e1117; font-weight: bold; font-size: 20px;"
                    ] * len(row)
                else:  # Rest
                    styles = [
                        "background-color: #0e1117; font-weight: bold; font-size: 20px;"
                    ] * len(row)
            except:
                pass
            return styles

        # Zeige formatierte Tabelle
        st.dataframe(
            styled_df.style.apply(highlight_top, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ergebnis": st.column_config.TextColumn(
                    "Ergebnis", help="Vorhergesagtes Spielergebnis"
                ),
                "Wahrscheinlichkeit": st.column_config.TextColumn(
                    "Wahrscheinlichkeit", help="Wahrscheinlichkeit in Prozent"
                ),
            },
        )

        # Zusammenfassung der Top Ergebnisse
        if len(df) >= 3:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    label=f"🏆 {df.iloc[0]['Ergebnis']}",
                    value=f"{df.iloc[0]['Wahrscheinlichkeit']}",
                    delta="Wahrscheinlichstes",
                )
            with col2:
                st.metric(
                    label=f"🥈 {df.iloc[1]['Ergebnis']}",
                    value=f"{df.iloc[1]['Wahrscheinlichkeit']}",
                    delta="Zweitwahrscheinlichstes",
                )
            with col3:
                st.metric(
                    label=f"🥉 {df.iloc[2]['Ergebnis']}",
                    value=f"{df.iloc[2]['Wahrscheinlichkeit']}",
                    delta="Drittwahrscheinlichstes",
                )


def show_historical_performance():
    """
    Zeigt historische ML-Performance (nur wenn Daten vorhanden)
    """
    st.subheader("📈 Historische ML-Performance")

    historical_matches = load_historical_matches_from_sheets()

    if len(historical_matches) < 5:
        st.info(
            "📊 Noch nicht genug historische Daten verfügbar (mindestens 5 Matches benötigt)"
        )
        return

    st.success(f"✅ {len(historical_matches)} historische Matches analysiert")

    # Berechne Accuracy
    home_errors = []
    away_errors = []

    for match in historical_matches:
        pred_home = match.get("predicted_mu_home", 0)
        pred_away = match.get("predicted_mu_away", 0)
        actual_home = match.get("actual_mu_home", 0)
        actual_away = match.get("actual_mu_away", 0)

        home_errors.append(abs(pred_home - actual_home))
        away_errors.append(abs(pred_away - actual_away))

    avg_home_error = sum(home_errors) / len(home_errors) if home_errors else 0
    avg_away_error = sum(away_errors) / len(away_errors) if away_errors else 0
    avg_total_error = (avg_home_error + avg_away_error) / 2

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø Abweichung Heimtore", f"{avg_home_error:.2f}")
    col2.metric("Ø Abweichung Auswärtstore", f"{avg_away_error:.2f}")
    col3.metric("Ø Gesamt-Abweichung", f"{avg_total_error:.2f}")

    # Scatter Plot: Predicted vs Actual
    fig = go.Figure()

    # Heimtore
    pred_home_values = [m.get("predicted_mu_home", 0) for m in historical_matches]
    actual_home_values = [m.get("actual_mu_home", 0) for m in historical_matches]

    fig.add_trace(
        go.Scatter(
            x=pred_home_values,
            y=actual_home_values,
            mode="markers",
            name="Heimtore",
            marker=dict(size=10, color="blue", opacity=0.6),
        )
    )

    # Auswärtstore
    pred_away_values = [m.get("predicted_mu_away", 0) for m in historical_matches]
    actual_away_values = [m.get("actual_mu_away", 0) for m in historical_matches]

    fig.add_trace(
        go.Scatter(
            x=pred_away_values,
            y=actual_away_values,
            mode="markers",
            name="Auswärtstore",
            marker=dict(size=10, color="orange", opacity=0.6),
        )
    )

    # Perfekte Linie (x=y)
    max_val = max(
        max(pred_home_values + pred_away_values),
        max(actual_home_values + actual_away_values),
    )
    fig.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Perfekte Vorhersage",
            line=dict(color="green", dash="dash"),
        )
    )

    fig.update_layout(
        title="Vorhergesagte vs. Tatsächliche Tore",
        xaxis_title="Vorhergesagte μ-Werte",
        yaxis_title="Tatsächliche Tore",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)


def show_confidence_gauge(result: Dict):
    """
    Zeigt Confidence-Level für die Vorhersage

    Args:
        result: Analyse-Ergebnis Dictionary
    """
    st.subheader("🎲 Vorhersage-Konfidenz")

    # Berechne Confidence basierend auf verschiedenen Faktoren
    confidence_factors = []

    # Faktor 1: Daten-Vollständigkeit (aus Validierung)
    # (Wenn alle Felder vorhanden: +30 Punkte)
    confidence_factors.append(("Daten-Vollständigkeit", 30))

    # Faktor 2: Wahrscheinlichkeits-Dominanz
    # Je höher die beste Wahrscheinlichkeit, desto höher Confidence
    probs = result["probabilities"]
    best_1x2 = max(probs["home_win"], probs["draw"], probs["away_win"])

    if best_1x2 >= 70:
        prob_score = 30
    elif best_1x2 >= 60:
        prob_score = 25
    elif best_1x2 >= 50:
        prob_score = 20
    else:
        prob_score = 10

    confidence_factors.append(("Wahrscheinlichkeits-Klarheit", prob_score))

    # Faktor 3: ML-Modell Confidence
    ml_correction = result.get("ml_position_correction", {})
    if ml_correction.get("applied", False):
        ml_conf = ml_correction.get("confidence", 0.5) * 20
        confidence_factors.append(("ML-Modell", ml_conf))
    else:
        confidence_factors.append(("ML-Modell", 10))

    # Faktor 4: H2H Daten-Qualität
    h2h = result["h2h"]
    total_h2h_matches = h2h["home_wins"] + h2h["draws"] + h2h["away_wins"]

    if total_h2h_matches >= 5:
        h2h_score = 20
    elif total_h2h_matches >= 3:
        h2h_score = 15
    else:
        h2h_score = 5

    confidence_factors.append(("H2H Daten", h2h_score))

    # Gesamt-Confidence
    total_confidence = sum(score for _, score in confidence_factors)

    # Gauge Chart
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=total_confidence,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Gesamt-Konfidenz"},
            delta={"reference": 70},
            gauge={
                "axis": {"range": [None, 100], "tickwidth": 1},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 40], "color": "lightcoral"},
                    {"range": [40, 70], "color": "lightyellow"},
                    {"range": [70, 100], "color": "lightgreen"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 70,
                },
            },
        )
    )

    fig.update_layout(height=300)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 Konfidenz-Faktoren")
        for factor, score in confidence_factors:
            st.progress(score / 30, text=f"{factor}: {score:.0f}/30")

        st.markdown("---")
        if total_confidence >= 80:
            st.success(
                "✅ **Sehr hohe Konfidenz** - Starke Datenbasis und klare Signale"
            )
        elif total_confidence >= 60:
            st.info("ℹ️ **Gute Konfidenz** - Solide Vorhersage möglich")
        else:
            st.warning("⚠️ **Moderate Konfidenz** - Vorsicht bei Einsätzen")


def show_team_radar(result: Dict):
    """
    Zeigt Team-Vergleich als Radar/Netzdiagramm

    Args:
        result: Analyse-Ergebnis Dictionary
    """
    st.subheader("🕸️ Team-Vergleich (Radar)")
    
    # Safety Check
    if "match_data" not in result:
        st.warning("⚠️ Radar-Chart nicht verfügbar (fehlende Match-Daten)")
        return

    home_team = result["match_data"].home_team
    away_team = result["match_data"].away_team

    # Berechne normalisierte Werte für 8 Achsen (0-100 Skala)

    # 1. Offensive Stärke (xG + Tore/Spiel kombiniert)
    home_offense = min(
        100, ((home_team.xg_for_ha + home_team.goals_scored_per_match_ha) / 4) * 100
    )
    away_offense = min(
        100, ((away_team.xg_for_ha + away_team.goals_scored_per_match_ha) / 4) * 100
    )

    # 2. Defensive Stabilität (Clean Sheets + xG Against invertiert)
    home_defense = min(
        100,
        (home_team.cs_yes_ha * 100 + (1 - min(1, home_team.xg_against_ha / 2)) * 50),
    )
    away_defense = min(
        100,
        (away_team.cs_yes_ha * 100 + (1 - min(1, away_team.xg_against_ha / 2)) * 50),
    )

    # 3. Form (PPG Form normalisiert)
    home_form = min(100, (home_team.ppg_ha / 3) * 100)
    away_form = min(100, (away_team.ppg_ha / 3) * 100)

    # 4. Ballbesitz/Kontrolle
    home_possession = min(100, home_team.possession)
    away_possession = min(100, away_team.possession)

    # 5. Conversion Rate
    home_conversion = min(100, home_team.conversion_rate * 100)
    away_conversion = min(100, away_team.conversion_rate * 100)

    # 6. Tabellenposition (invertiert: 1. Platz = 100, 18. Platz = 0)
    home_position_score = max(0, 100 - ((home_team.position - 1) / 17) * 100)
    away_position_score = max(0, 100 - ((away_team.position - 1) / 17) * 100)

    # 7. Heim/Auswärts-Stärke (PPG H/A)
    home_ha_strength = min(100, (home_team.ppg_ha / 3) * 100)
    away_ha_strength = min(100, (away_team.ppg_ha / 3) * 100)

    # 8. Failed to Score Rate (invertiert: niedrig = besser)
    home_fts_score = max(0, 100 - (home_team.fts_yes_ha * 100))
    away_fts_score = max(0, 100 - (away_team.fts_yes_ha * 100))

    # Radar Chart
    categories = [
        "Offensive",
        "Defensive",
        "Form",
        "Ballbesitz",
        "Conversion",
        "Tabellenplatz",
        "H/A Stärke",
        "Scoring Rate",
    ]

    fig = go.Figure()

    # Heimteam
    fig.add_trace(
        go.Scatterpolar(
            r=[
                home_offense,
                home_defense,
                home_form,
                home_possession,
                home_conversion,
                home_position_score,
                home_ha_strength,
                home_fts_score,
            ],
            theta=categories,
            fill="toself",
            name=home_team.name,
            line_color="blue",
        )
    )

    # Auswärtsteam
    fig.add_trace(
        go.Scatterpolar(
            r=[
                away_offense,
                away_defense,
                away_form,
                away_possession,
                away_conversion,
                away_position_score,
                away_ha_strength,
                away_fts_score,
            ],
            theta=categories,
            fill="toself",
            name=away_team.name,
            line_color="orange",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detail-Tabelle
    with st.expander("📋 Detaillierte Werte"):
        comparison_data = {
            "Kategorie": categories,
            home_team.name: [
                f"{home_offense:.1f}",
                f"{home_defense:.1f}",
                f"{home_form:.1f}",
                f"{home_possession:.1f}",
                f"{home_conversion:.1f}",
                f"{home_position_score:.1f}",
                f"{home_ha_strength:.1f}",
                f"{home_fts_score:.1f}",
            ],
            away_team.name: [
                f"{away_offense:.1f}",
                f"{away_defense:.1f}",
                f"{away_form:.1f}",
                f"{away_possession:.1f}",
                f"{away_conversion:.1f}",
                f"{away_position_score:.1f}",
                f"{away_ha_strength:.1f}",
                f"{away_fts_score:.1f}",
            ],
        }

        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
