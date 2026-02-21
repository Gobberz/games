"""
BlackJack Trainer — Monte Carlo Simulation
"""

import streamlit as st
from ui.styles import COLORS
from ml.simulation import run_all_simulations


def render_simulation(gs):
    st.markdown(
        '<h2 style="text-align:center;letter-spacing:0.15em">🔬 SIMULATION</h2>',
        unsafe_allow_html=True
    )
    muted = COLORS["text_muted"]
    st.markdown(
        f'<p style="text-align:center;color:{muted};'
        f'font-family:\'Cinzel\',serif;font-size:11px;letter-spacing:0.2em">'
        f'MONTE-CARLO &nbsp;·&nbsp; STRATEGY COMPARISON &nbsp;·&nbsp; EV ANALYSIS</p>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        n_rounds = st.select_slider(
            "Rounds",
            options=[1000, 2500, 5000, 10000, 25000],
            value=5000,
        )
    with col2:
        num_decks = st.selectbox("Decks in shoe", [1, 2, 4, 6, 8], index=3)
    with col3:
        bet = st.number_input("Bet ($)", min_value=1, max_value=1000, value=10, step=1)

    st.markdown("<br>", unsafe_allow_html=True)
    run_col, _ = st.columns([1, 3])
    with run_col:
        run_sim = st.button("▶ Run Simulation", type="primary", use_container_width=True)

    if run_sim or st.session_state.get("sim_results"):
        if run_sim:
            with st.spinner("Running simulation..."):
                results = run_all_simulations(n_rounds, num_decks, bet)
            st.session_state["sim_results"] = results
        else:
            results = st.session_state["sim_results"]
        _render_results(results)


def _render_results(results: dict):
    try:
        import plotly.graph_objects as go
        _plotly_results(results, go)
    except ImportError:
        for key in ("basic", "player", "random"):
            r = results[key]
            st.write(f"**{key}**: balance ${r['balance']:.0f}, win rate {r['win_rate']*100:.1f}%")


def _plotly_results(results: dict, go):
    st.markdown('<div class="gold-divider" style="margin:20px 0"></div>', unsafe_allow_html=True)

    strategies = [
        ("basic",  "📐 Basic Strategy", COLORS["gold"]),
        ("player", "🧑 Beginner",        COLORS["success"]),
        ("random", "🎲 Random",      COLORS["error"]),
    ]

    cols = st.columns(3)
    for i, (key, label, color) in enumerate(strategies):
        r    = results[key]
        ev   = r["ev_per_round"]
        wr   = r["win_rate"] * 100
        bal  = r["balance"]
        sign = "+" if bal >= 0 else ""
        bal_color = "#27ae60" if bal >= 0 else "#e74c3c"

        with cols[i]:
            surf = COLORS["surface"]
            bord = COLORS["border"]
            tm   = COLORS["text_muted"]
            tp   = COLORS["text_primary"]
            st.markdown(
                f'<div style="background:{surf};border:1px solid {color}44;'
                f'border-top:3px solid {color};border-radius:8px;padding:16px;text-align:center">'
                f'<div style="font-family:\'Cinzel\',serif;color:{color};font-size:13px;'
                f'font-weight:600;letter-spacing:0.1em;margin-bottom:12px">{label}</div>'
                f'<div style="color:{tm};font-size:11px;font-family:\'Cinzel\',serif;letter-spacing:0.08em">BALANCE</div>'
                f'<div style="font-family:\'Cinzel\',serif;color:{bal_color};'
                f'font-size:22px;font-weight:700">{sign}${bal:,.0f}</div>'
                f'<div style="color:{tm};font-size:11px;margin-top:8px;font-family:\'Cinzel\',serif;letter-spacing:0.08em">WIN RATE</div>'
                f'<div style="color:{tp};font-family:\'Cinzel\',serif;font-size:16px">{wr:.1f}%</div>'
                f'<div style="color:{tm};font-size:11px;margin-top:4px;font-family:\'Cinzel\',serif;letter-spacing:0.08em">EV/ROUND</div>'
                f'<div style="color:{tm};font-family:\'Cinzel\',serif;font-size:14px">{sign}${ev:.2f}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)
    fig = go.Figure()
    for key, label, color in strategies:
        hist = results[key]["balance_history"]
        fig.add_trace(go.Scatter(
            x=list(range(len(hist))), y=hist,
            name=label,
            mode="lines",
            line=dict(color=color, width=2),
        ))

    fig.add_hline(y=0, line_dash="dot", line_color=COLORS["border"], opacity=0.7)
    n   = results["n_rounds"]
    bet = results["bet"]
    fig.update_layout(
        title=dict(
            text=f"Balance over time ({n:,} rounds, ${bet}/hand)",
            font=dict(family="Cinzel", color=COLORS["gold"], size=13), x=0.5,
        ),
        xaxis=dict(
            title="Round (sampled)",
            tickfont=dict(color=COLORS["text_muted"], family="Cinzel", size=10),
            gridcolor=COLORS["border"], gridwidth=0.5,
        ),
        yaxis=dict(
            title="Balance ($)", tickprefix="$",
            tickfont=dict(color=COLORS["text_muted"], family="Cinzel", size=10),
            gridcolor=COLORS["border"], gridwidth=0.5,
        ),
        legend=dict(font=dict(color=COLORS["text_muted"], family="Cinzel", size=11),
                    bgcolor=COLORS["surface"], bordercolor=COLORS["border"]),
        paper_bgcolor=COLORS["felt_dark"],
        plot_bgcolor=COLORS["felt"],
        margin=dict(l=70, r=40, t=50, b=60),
        height=360,
    )
    st.plotly_chart(fig, use_container_width=True)

    basic_ev  = results["basic"]["ev_per_round"]
    player_ev = results["player"]["ev_per_round"]
    edge  = abs(basic_ev - player_ev)
    surf  = COLORS["surface"]
    gold  = COLORS["gold"]
    tp    = COLORS["text_primary"]
    st.markdown(
        f'<div style="background:{surf};border:1px solid {gold}44;'
        f'border-left:3px solid {gold};border-radius:0 8px 8px 0;padding:14px 18px;'
        f'font-family:\'Crimson Pro\',serif;color:{tp};font-size:15px">'
        f'💡 <strong>Takeaway:</strong> Over {n:,} rounds Basic Strategy saves <strong>${edge*n:,.0f}</strong> vs a beginner (${edge:.2f}/round). '
        f'The house always wins — the goal is to <em>lose less</em>.</div>',
        unsafe_allow_html=True
    )
