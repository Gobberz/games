import streamlit as st


st.set_page_config(
    page_title="BlackJack Trainer",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui.styles import GLOBAL_CSS, COLORS
from ui.game_view import render_game
from ui.analytics_view import render_analytics
from ui.simulation_view import render_simulation
from data.game_session import GameSession
from data.database import Database


st.markdown(GLOBAL_CSS, unsafe_allow_html=True)



@st.cache_resource
def get_database():
    """Single DB instance shared across the whole app."""
    return Database()


def get_game_session() -> GameSession:
    """GameSession persists in session_state across Streamlit reruns."""
    if "gs" not in st.session_state:
        db = get_database()
        st.session_state["gs"] = GameSession(db=db)
    return st.session_state["gs"]



with st.sidebar:
    st.markdown(
        f'<div style="text-align:center;padding:16px 0 8px">'
        f'<span style="font-family:\'Cinzel\',serif;color:{COLORS["gold"]};'
        f'font-size:22px;font-weight:700;letter-spacing:0.1em">🃏 BJ TRAINER</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown(
        f'<div style="text-align:center;margin-bottom:16px">'
        f'<span style="font-family:\'Cinzel\',serif;color:{COLORS["text_muted"]};'
        f'font-size:10px;letter-spacing:0.2em">BASIC STRATEGY TRAINER</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

    page = st.radio(
        "NAVIGATION",
        options=["🎮 Game", "📊 Analytics", "🔬 Simulation"],
        label_visibility="visible",
    )

    st.markdown('<div class="gold-divider" style="margin-top:auto"></div>', unsafe_allow_html=True)

    
    gs = get_game_session()
    from data.repository import AnalyticsRepo
    try:
        stats = AnalyticsRepo(gs.db).overall_stats(gs.player_id)
        if stats and stats.get("total_rounds", 0) > 0:
            total = stats["total_rounds"]
            wins  = stats["total_wins"]
            acc   = stats.get("avg_accuracy", 0) * 100
            st.markdown(
                f'<div style="padding:12px 0">'
                f'<div style="font-family:\'Cinzel\',serif;color:{COLORS["text_muted"]};'
                f'font-size:10px;letter-spacing:0.15em;margin-bottom:8px">STATS</div>'
                f'<div style="display:flex;justify-content:space-between;margin:4px 0">'
                f'<span style="color:{COLORS["text_muted"]};font-size:12px">Rounds</span>'
                f'<span style="color:{COLORS["gold"]};font-family:\'Cinzel\',serif;font-size:13px">{total}</span>'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;margin:4px 0">'
                f'<span style="color:{COLORS["text_muted"]};font-size:12px">Win rate</span>'
                f'<span style="color:{COLORS["success"]};font-family:\'Cinzel\',serif;font-size:13px">'
                f'{wins/total*100:.0f}%</span>'
                f'</div>'
                f'<div style="display:flex;justify-content:space-between;margin:4px 0">'
                f'<span style="color:{COLORS["text_muted"]};font-size:12px">Accuracy</span>'
                f'<span style="color:{COLORS["gold"]};font-family:\'Cinzel\',serif;font-size:13px">'
                f'{acc:.0f}%</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True
            )
    except Exception:
        pass

    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 New Session", use_container_width=True):
        gs.end_session()
        del st.session_state["gs"]
        
        for key in ["round_started", "round_result", "dealer_final_cards",
                    "dealer_final_value", "sim_results"]:
            st.session_state.pop(key, None)
        st.rerun()

    st.markdown(
        f'<div style="margin-top:16px;text-align:center">'
        f'<span style="color:{COLORS["text_muted"]};font-size:10px;'
        f'font-family:\'Cinzel\',serif;letter-spacing:0.1em">'
        f'6 DECKS · SOFT 17 STANDS</span></div>',
        unsafe_allow_html=True
    )

    
    try:
        ml_status = "🧠 ML ON" if gs._trainer.is_trained else "🧠 ML training..."
        ml_color  = COLORS["success"] if gs._trainer.is_trained else COLORS["text_muted"]
        st.markdown(
            f'<div style="text-align:center;margin-top:4px">'
            f'<span style="color:{ml_color};font-size:10px;'
            f'font-family:\'Cinzel\',serif;letter-spacing:0.1em">{ml_status}</span></div>',
            unsafe_allow_html=True
        )
    except Exception:
        pass



gs = get_game_session()

if page == "🎮 Game":
    render_game(gs)
elif page == "📊 Analytics":
    render_analytics(gs)
elif page == "🔬 Simulation":
    render_simulation(gs)
