"""
BlackJack Trainer — Analytics Dashboard
"""

import streamlit as st
from ui.styles import COLORS
from data.repository import AnalyticsRepo


def render_analytics(gs):
    """Analytics page: heatmap, progress, player profile."""
    analytics = AnalyticsRepo(gs.db)
    pid = gs.player_id

    st.markdown(
        '<h2 style="text-align:center;letter-spacing:0.15em">📊 ANALYTICS</h2>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<p style="text-align:center;color:{COLORS["text_muted"]};'
        f'font-family:\'Cinzel\',serif;font-size:11px;letter-spacing:0.2em">'
        f'ERROR ANALYSIS &nbsp;·&nbsp; PROGRESS &nbsp;·&nbsp; PLAYER PROFILE</p>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

    stats = analytics.overall_stats(pid)

    
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        total = stats.get("total_rounds", 0)
        wins  = stats.get("total_wins", 0)
        acc   = stats.get("avg_accuracy", 0)
        sess  = stats.get("sessions_count", 0)
        wr    = (wins / total * 100) if total > 0 else 0

        c1.metric("🃏 Rounds",  f"{total}")
        c2.metric("🏆 Wins",    f"{wins}")
        c3.metric("📈 Win Rate", f"{wr:.1f}%")
        c4.metric("🎯 Accuracy", f"{acc*100:.1f}%")

        st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

    
    if not stats or stats.get("total_rounds", 0) < 5:
        st.markdown(
            f'<div style="text-align:center;padding:60px 20px;'
            f'color:{COLORS["text_muted"]};font-family:\'Cinzel\',serif;'
            f'font-size:14px;letter-spacing:0.1em">'
            f'🃏 Play at least 5 rounds<br>'
            f'<span style="font-size:11px">for analytics to appear</span></div>',
            unsafe_allow_html=True
        )
        return

    tab1, tab2, tab3 = st.tabs(["🔥 Error Map", "📈 Progress", "🧠 Profile"])

    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        _render_heatmap(analytics, pid)

    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        _render_progress(analytics, pid)

    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        _render_profile(gs, analytics, stats, pid)


def _render_heatmap(analytics, pid):
    """Error heatmap — player_total × dealer_upcard grid."""
    try:
        import plotly.graph_objects as go
        import pandas as pd
        _plotly_heatmap(analytics, pid)
    except ImportError:
        _fallback_heatmap(analytics, pid)


def _plotly_heatmap(analytics, pid):
    import plotly.graph_objects as go
    import pandas as pd

    hm_data = analytics.error_heatmap(pid)
    if not hm_data:
        st.info("Not enough data for the error map.")
        return

    df = pd.DataFrame(hm_data)
    df_hard = df[df["is_soft"] == 0]

    dealer_labels  = ["2","3","4","5","6","7","8","9","10","A"]
    dealer_vals    = [2,3,4,5,6,7,8,9,10,11]
    player_totals  = list(range(8, 18))

    
    z = []
    text = []
    for pt in player_totals:
        row_z = []
        row_t = []
        for dv in dealer_vals:
            match = df_hard[(df_hard.player_total == pt) & (df_hard.dealer_upcard_val == dv)]
            if not match.empty:
                er = float(match.iloc[0]["error_rate"])
                nm = int(match.iloc[0]["total_moves"])
                row_z.append(er)
                row_t.append(f"{er*100:.0f}%<br>({nm} moves)")
            else:
                row_z.append(None)
                row_t.append("–")
        z.append(row_z)
        text.append(row_t)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=dealer_labels,
        y=[str(t) for t in player_totals],
        text=text,
        hovertemplate="Hand: %{y}<br>Dealer: %{x}<br>%{text}<extra></extra>",
        colorscale=[
            [0.0,  "#0d3320"],
            [0.3,  "#1a5c35"],
            [0.5,  "#c9a227"],
            [0.75, "#c0392b"],
            [1.0,  "#7b0000"],
        ],
        zmin=0, zmax=1,
        showscale=True,
        colorbar=dict(
            title="Errors",
            tickformat=".0%",
            tickfont=dict(color=COLORS["text_muted"], size=11),
            titlefont=dict(color=COLORS["text_muted"], size=11),
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
        ),
    ))

    fig.update_layout(
        title=dict(
            text="Hard Hands: error %",
            font=dict(family="Cinzel", color=COLORS["gold"], size=14),
            x=0.5,
        ),
        xaxis=dict(
            title="Dealer Card",
            tickfont=dict(color=COLORS["text_primary"], family="Cinzel", size=12),
            titlefont=dict(color=COLORS["text_muted"], family="Cinzel", size=11),
            gridcolor=COLORS["border"],
        ),
        yaxis=dict(
            title="Hand Total",
            tickfont=dict(color=COLORS["text_primary"], family="Cinzel", size=12),
            titlefont=dict(color=COLORS["text_muted"], family="Cinzel", size=11),
            gridcolor=COLORS["border"],
        ),
        paper_bgcolor=COLORS["felt_dark"],
        plot_bgcolor=COLORS["felt"],
        margin=dict(l=60, r=60, t=50, b=60),
        height=380,
    )

    st.plotly_chart(fig, use_container_width=True)

    
    st.markdown(
        f'<p style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
        f'font-size:13px;letter-spacing:0.1em;margin-top:20px">'
        f'TOP PROBLEM SPOTS</p>',
        unsafe_allow_html=True
    )
    top = sorted(hm_data, key=lambda x: x["error_rate"] or 0, reverse=True)[:5]
    for i, row in enumerate(top):
        if row["error_rate"] and row["error_rate"] > 0:
            soft_label = "Soft " if row["is_soft"] else ""
            pair_label = " (pair)" if row["is_pair"] else ""
            d_label    = "A" if row["dealer_upcard_val"] == 11 else str(row["dealer_upcard_val"])
            er_pct     = row["error_rate"] * 100
            bar_w      = int(er_pct)
            color = COLORS["error"] if er_pct > 60 else \
                    COLORS["warning"] if er_pct > 30 else COLORS["success"]
            st.markdown(
                f'<div style="margin:6px 0;display:flex;align-items:center;gap:12px">'
                f'<span style="color:{COLORS["text_muted"]};font-family:\'Cinzel\',serif;'
                f'font-size:11px;min-width:160px">'
                f'{soft_label}{row["player_total"]}{pair_label} vs {d_label}</span>'
                f'<div style="flex:1;background:{COLORS["border"]};border-radius:3px;height:8px">'
                f'<div style="width:{bar_w}%;background:{color};height:100%;border-radius:3px;'
                f'transition:width 0.3s"></div></div>'
                f'<span style="color:{color};font-family:\'Cinzel\',serif;font-size:13px;'
                f'font-weight:600;min-width:40px;text-align:right">{er_pct:.0f}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )


def _fallback_heatmap(analytics, pid):
    """Fallback table when plotly is not installed."""
    hm = analytics.error_heatmap(pid)
    st.subheader("Top Mistakes")
    for row in hm[:10]:
        d = "A" if row["dealer_upcard_val"] == 11 else str(row["dealer_upcard_val"])
        soft = "Soft " if row["is_soft"] else ""
        st.write(f"{soft}{row['player_total']} vs {d}: {row['error_rate']*100:.0f}% errors")


def _render_progress(analytics, pid):
    """Accuracy progress chart by session."""
    try:
        import plotly.graph_objects as go
        _plotly_progress(analytics, pid, go)
    except ImportError:
        hist = analytics.accuracy_by_session(pid)
        for s in hist:
            st.write(f"Session {s['session_id']}: accuracy {s['accuracy']*100:.0f}%")


def _plotly_progress(analytics, pid, go):
    hist = analytics.accuracy_by_session(pid)
    if not hist:
        st.info("Finish at least one session to see the progress chart.")
        return

    sessions  = [f"#{s['session_id']}" for s in hist]
    accuracy  = [s["accuracy"] * 100 for s in hist]
    win_rate  = [s["win_rate"]  * 100 for s in hist]

    
    def moving_avg(vals, window=3):
        result = []
        for i in range(len(vals)):
            start = max(0, i - window + 1)
            result.append(sum(vals[start:i+1]) / (i - start + 1))
        return result

    ma = moving_avg(accuracy)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sessions, y=accuracy,
        name="Accuracy (%)",
        mode="lines+markers",
        line=dict(color=COLORS["gold"], width=2),
        marker=dict(size=7, color=COLORS["gold_light"]),
        fill="tozeroy",
        fillcolor=f"rgba(201,162,39,0.1)",
    ))
    fig.add_trace(go.Scatter(
        x=sessions, y=win_rate,
        name="Win Rate (%)",
        mode="lines+markers",
        line=dict(color=COLORS["success"], width=2, dash="dot"),
        marker=dict(size=6, color=COLORS["success"]),
    ))
    fig.add_trace(go.Scatter(
        x=sessions, y=ma,
        name="Rolling avg",
        mode="lines",
        line=dict(color=COLORS["gold_pale"], width=1, dash="dash"),
    ))
    fig.add_hline(
        y=80, line_dash="dot",
        line_color=COLORS["success"], opacity=0.4,
        annotation_text="Target 80%",
        annotation_font_color=COLORS["success"],
    )

    fig.update_layout(
        title=dict(
            text="Progress by session",
            font=dict(family="Cinzel", color=COLORS["gold"], size=14),
            x=0.5,
        ),
        xaxis=dict(
            title="Session",
            tickfont=dict(color=COLORS["text_primary"], family="Cinzel", size=11),
            gridcolor=COLORS["border"], gridwidth=0.5,
        ),
        yaxis=dict(
            title="Percent (%)",
            range=[0, 105],
            tickfont=dict(color=COLORS["text_primary"], family="Cinzel", size=11),
            gridcolor=COLORS["border"], gridwidth=0.5,
        ),
        legend=dict(
            font=dict(color=COLORS["text_muted"], family="Cinzel", size=11),
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
        ),
        paper_bgcolor=COLORS["felt_dark"],
        plot_bgcolor=COLORS["felt"],
        margin=dict(l=60, r=40, t=50, b=60),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    
    breakdown = analytics.action_breakdown(pid)
    if breakdown:
        st.markdown(
            f'<p style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
            f'font-size:13px;letter-spacing:0.1em;margin-top:20px">'
            f'ACCURACY BY ACTION TYPE</p>',
            unsafe_allow_html=True
        )
        cols = st.columns(len(breakdown))
        for i, row in enumerate(breakdown):
            action = row.get("action", "?")
            acc    = (row.get("accuracy") or 0) * 100
            total  = row.get("total", 0)
            color  = COLORS["success"] if acc >= 75 else \
                     COLORS["warning"] if acc >= 50 else COLORS["error"]
            emoji  = {"hit":"🎯","stand":"✋","double":"⚡","split":"✂️"}.get(action,"•")
            with cols[i]:
                st.markdown(
                    f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
                    f'border-radius:8px;padding:14px;text-align:center">'
                    f'<div style="font-size:24px">{emoji}</div>'
                    f'<div style="font-family:\'Cinzel\',serif;color:{COLORS["text_muted"]};'
                    f'font-size:10px;letter-spacing:0.1em;text-transform:uppercase;'
                    f'margin:4px 0">{action}</div>'
                    f'<div style="font-family:\'Cinzel\',serif;color:{color};font-size:22px;'
                    f'font-weight:600">{acc:.0f}%</div>'
                    f'<div style="color:{COLORS["text_muted"]};font-size:11px">{total} ходов</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )


def _render_profile(gs, analytics, stats, pid):
    """Player profile: ML cluster and personal tips."""

    
    ml_cluster = gs.ml_cluster()
    if ml_cluster:
        cluster_name = ml_cluster["cluster_name"]
    else:
        cluster_name = stats.get("cluster_name") or "Beginner"

    CLUSTER_INFO = {
        "expert": {
            "emoji": "🏆", "color": COLORS["gold"],
            "title": "EXPERT",
            "desc": "You make near-optimal decisions. Accuracy above 85%.",
            "tips": [
                "Keep practicing soft hands",
                "Explore advanced spots (surrender, late double)",
                "Try card counting as the next step",
            ]
        },
        "cautious": {
            "emoji": "🛡️", "color": "#3498db",
            "title": "CAUTIOUS",
            "desc": "You play too conservatively and miss good double-down spots.",
            "tips": [
                "Hard 9 vs dealer 3–6 → always Double Down",
                "Soft 17 (A+6) → Double vs 3–6, not Stand",
                "Hard 11 → Double is almost always better than Hit",
            ]
        },
        "impulsive": {
            "emoji": "🔥", "color": COLORS["error"],
            "title": "IMPULSIVE",
            "desc": "You hit too often on 15–16. High bust rate.",
            "tips": [
                "Hard 15–16 vs dealer 2–6 → always Stand",
                "Never hit 17+, wait for the dealer",
                "Always split 8-8, never hit",
            ]
        },
        "chaotic": {
            "emoji": "🎲", "color": COLORS["warning"],
            "title": "CHAOTIC",
            "desc": "Decisions are unpredictable. Focus on memorizing basic strategy.",
            "tips": [
                "Start by memorizing hard hands (8–17)",
                "Learn 3 rules: always split A-A and 8-8, never split 10-10",
                "Check the analytics screen every 20 rounds",
            ]
        },
        "Beginner": {
            "emoji": "🃏", "color": COLORS["text_muted"],
            "title": "BEGINNER",
            "desc": "Just getting started. Play more rounds for an accurate profile.",
            "tips": [
                "Hard 17+ → always Stand",
                "Hard 11 → Double vs dealer 2–10, Hit vs Ace",
                "A-A and 8-8 → always Split",
            ]
        },
    }

    info = CLUSTER_INFO.get(cluster_name, CLUSTER_INFO["Beginner"])

    
    st.markdown(
        f'<div style="background:linear-gradient(135deg,{COLORS["surface"]},{COLORS["felt"]});'
        f'border:2px solid {info["color"]}44;border-radius:12px;padding:24px;text-align:center;'
        f'margin-bottom:20px">'
        f'<div style="font-size:48px;margin-bottom:8px">{info["emoji"]}</div>'
        f'<div style="font-family:\'Cinzel\',serif;color:{info["color"]};font-size:20px;'
        f'font-weight:700;letter-spacing:0.15em">{info["title"]}</div>'
        f'<div style="color:{COLORS["text_muted"]};font-family:\'Crimson Pro\',serif;'
        f'font-size:15px;margin-top:8px">{info["desc"]}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # personal tips
    st.markdown(
        f'<p style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
        f'font-size:13px;letter-spacing:0.1em">PERSONAL TIPS</p>',
        unsafe_allow_html=True
    )
    for tip in info["tips"]:
        st.markdown(
            f'<div style="background:{COLORS["surface"]};border-left:3px solid {info["color"]};'
            f'border-radius:0 6px 6px 0;padding:10px 16px;margin:6px 0;'
            f'color:{COLORS["text_primary"]};font-family:\'Crimson Pro\',serif;font-size:15px">'
            f'→ {tip}</div>',
            unsafe_allow_html=True
        )

    
    ml_top = gs.ml_top_mistakes(n=5)
    if ml_top:
        st.markdown('<div class="gold-divider" style="margin:20px 0"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
            f'font-size:13px;letter-spacing:0.1em">🧠 ML: HIGH-RISK SPOTS</p>',
            unsafe_allow_html=True
        )
        for m in ml_top:
            d_label = "A" if m["dealer_upcard"] == 11 else str(m["dealer_upcard"])
            soft = "Soft " if m.get("is_soft") else ""
            prob_pct = int(m["error_prob"] * 100)
            bar_w = max(4, prob_pct)
            warn_color = COLORS.get("error") if prob_pct >= 75 else COLORS.get("warning", "#f39c12")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;'
                f'padding:8px 12px;margin:4px 0;background:{COLORS["surface"]};'
                f'border-radius:6px;border:1px solid {COLORS["border"]}">'
                f'<span style="color:{COLORS["text_muted"]};font-family:\'Cinzel\',serif;'
                f'font-size:12px;min-width:110px">{soft}{m["player_total"]} vs {d_label}</span>'
                f'<div style="flex:1;background:{COLORS["border"]};height:6px;border-radius:3px">'
                f'<div style="width:{bar_w}%;height:100%;background:{warn_color};border-radius:3px"></div>'
                f'</div>'
                f'<span style="color:{warn_color};font-family:\'Cinzel\',serif;'
                f'font-size:12px;min-width:36px;text-align:right">{prob_pct}%</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # recent mistakes from DB
    st.markdown('<div class="gold-divider" style="margin:20px 0"></div>', unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
        f'font-size:13px;letter-spacing:0.1em">RECENT MISTAKES</p>',
        unsafe_allow_html=True
    )
    mistakes = analytics.recent_mistakes(pid, limit=8)
    if mistakes:
        for m in mistakes:
            d_label = "A" if m["dealer_upcard_val"] == 11 else str(m["dealer_upcard_val"])
            soft = "Soft " if m["is_soft"] else ""
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:7px 12px;margin:3px 0;background:{COLORS["surface"]};border-radius:6px;'
                f'border:1px solid {COLORS["border"]}">'
                f'<span style="color:{COLORS["text_muted"]};font-family:\'Cinzel\',serif;font-size:12px">'
                f'{soft}{m["player_total"]} vs {d_label}</span>'
                f'<span style="color:{COLORS["error"]};font-size:13px">→ {m["action_taken"]}</span>'
                f'<span style="color:{COLORS["success"]};font-size:13px">✓ {m["optimal_action"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.markdown(
            f'<p style="color:{COLORS["text_muted"]};font-family:\'Cinzel\',serif;'
            f'font-size:12px">No mistakes yet — great work!</p>',
            unsafe_allow_html=True
        )
