import streamlit as st
from ui.styles import (
    COLORS, card_html, hand_html, value_badge,
    feedback_html, RESULT_EMOJI, RESULT_COLORS,
    ACTION_LABELS, ACTION_COLORS,
)
from game.engine import Action


def _bust_span():
    c = COLORS["error"]
    return f'&nbsp;&nbsp;<span style="color:{c}">BUST</span>'


def _bj_span():
    c = COLORS["success"]
    return f'&nbsp;&nbsp;<span style="color:{c};font-family:Cinzel,serif;font-size:12px">BLACKJACK</span>'


def render_game(gs):
    _init_round_if_needed(gs)
    state = gs.state

    st.markdown(
        '<h2 style="text-align:center;letter-spacing:0.15em;margin-bottom:4px">'
        '♠ BLACKJACK TRAINER ♠</h2>',
        unsafe_allow_html=True
    )
    muted = COLORS["text_muted"]
    st.markdown(
        f'<p style="text-align:center;color:{muted};'
        f'font-family:\'Cinzel\',serif;font-size:12px;letter-spacing:0.2em;">'
        f'ROUND {state["round_num"]} &nbsp;·&nbsp; '
        f'6 DECKS &nbsp;·&nbsp; DEALER STANDS ON SOFT 17</p>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="gold-divider"></div>', unsafe_allow_html=True)

    if state["is_blackjack"] and state["round_active"]:
        _handle_instant_blackjack(gs)
        return

    if state["round_active"] or st.session_state.get("round_result"):
        _render_table(gs, state)
    else:
        _render_new_round_prompt()


def _init_round_if_needed(gs):
    if "round_started" not in st.session_state:
        gs.new_round()
        st.session_state["round_started"] = True
        st.session_state["round_result"]  = None
        st.session_state["feedbacks"]     = []


def _handle_instant_blackjack(gs):
    result_data = gs.finish_round()
    st.session_state["round_result"]  = result_data
    st.session_state["round_started"] = False
    _show_result(gs, result_data, gs.state)
    _render_next_button()


def _render_table(gs, state):
    show_dealer_full = not state["round_active"] or bool(st.session_state.get("round_result"))

    muted = COLORS["text_muted"]
    st.markdown(
        f'<p style="color:{muted};font-family:\'Cinzel\',serif;'
        f'font-size:11px;letter-spacing:0.2em;text-align:center;margin-bottom:4px">'
        f'DEALER</p>',
        unsafe_allow_html=True
    )

    if show_dealer_full:
        final_cards     = st.session_state.get("dealer_final_cards") or [state["dealer_upcard"]]
        dv              = st.session_state.get("dealer_final_value") or 0
        dealer_html_str = hand_html(final_cards, show_all=True)
    else:
        dealer_html_str = card_html(state["dealer_upcard"]) + " " + card_html("hidden", hidden=True)
        dv = None

    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            f'<div style="text-align:center;padding:12px 0">{dealer_html_str}</div>',
            unsafe_allow_html=True
        )
        if dv is not None:
            bust_info  = dv > 21
            bust_extra = _bust_span() if bust_info else ""
            badge      = value_badge(dv, is_bust=bust_info)
            st.markdown(
                f'<div style="text-align:center;margin-top:4px">{badge}{bust_extra}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div style="text-align:center;margin-top:4px">'
                f'<span style="color:{muted};font-size:13px;'
                f'font-family:\'Cinzel\',serif;letter-spacing:0.1em">'
                f'upcard: {state["dealer_upcard"]}</span></div>',
                unsafe_allow_html=True
            )

    st.markdown('<div class="gold-divider" style="margin:16px 0"></div>', unsafe_allow_html=True)

    st.markdown(
        f'<p style="color:{muted};font-family:\'Cinzel\',serif;'
        f'font-size:11px;letter-spacing:0.2em;text-align:center;margin-bottom:4px">'
        f'PLAYER</p>',
        unsafe_allow_html=True
    )

    col_l, col_c, col_r = st.columns([1, 3, 1])
    with col_c:
        st.markdown(
            f'<div style="text-align:center;padding:12px 0">'
            f'{hand_html(state["player_cards"])}</div>',
            unsafe_allow_html=True
        )
        bj_extra = _bj_span() if state["is_blackjack"] else ""
        badge    = value_badge(state["player_value"], state["is_soft"], state["is_bust"])
        st.markdown(
            f'<div style="text-align:center;margin-top:4px">{badge}{bj_extra}</div>',
            unsafe_allow_html=True
        )

    st.markdown("", unsafe_allow_html=True)

    result_data = st.session_state.get("round_result")
    if result_data:
        _show_result(gs, result_data, state)
        _render_next_button()
    elif state["round_active"]:
        _render_action_buttons(gs, state)


def _render_action_buttons(gs, state):
    st.markdown('<div class="gold-divider" style="margin:12px 0 16px"></div>', unsafe_allow_html=True)

    warning = gs.ml_warning()
    if warning:
        warn_color = COLORS.get("warning", "#f39c12")
        st.markdown(
            f'<div style="background:rgba(243,156,18,0.12);border:1px solid {warn_color}40;'
            f'border-left:4px solid {warn_color};border-radius:6px;'
            f'padding:10px 14px;margin-bottom:12px;font-family:\'Crimson Pro\',serif;'
            f'font-size:14px;color:{warn_color}">{warning}</div>',
            unsafe_allow_html=True
        )

    cols    = st.columns(4)
    actions = [
        (Action.HIT,    "hit",    True,                cols[0]),
        (Action.STAND,  "stand",  True,                cols[1]),
        (Action.DOUBLE, "double", state["can_double"],  cols[2]),
        (Action.SPLIT,  "split",  state["can_split"],   cols[3]),
    ]

    for action_enum, key, enabled, col in actions:
        label_txt = ACTION_LABELS[key]
        with col:
            if enabled:
                if st.button(label_txt, key=f"btn_{key}", use_container_width=True):
                    _process_action(gs, action_enum)
            else:
                st.button(label_txt, key=f"btn_{key}", disabled=True, use_container_width=True)

    if gs.last_correct is not None:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(
            feedback_html(gs.last_correct, gs.last_action.value, gs.last_optimal.value),
            unsafe_allow_html=True,
        )


def _process_action(gs, action_enum: Action):
    gs.act(action_enum)
    if not gs.round_active:
        result_data = gs.finish_round()
        st.session_state["round_result"] = result_data
        _persist_dealer_info(gs)
    st.rerun()


def _persist_dealer_info(gs):
    dh = gs._engine.dealer_hand
    if dh:
        st.session_state["dealer_final_cards"] = [str(c) for c in dh.cards]
        st.session_state["dealer_final_value"] = dh.value


def _show_result(gs, result_data: dict, state: dict):
    result     = result_data["result"]
    result_key = result.value if hasattr(result, "value") else str(result)

    label     = RESULT_EMOJI.get(result_key, result_key)
    css_class = "result-win"  if result_key in ("win", "blackjack") else \
                "result-lose" if result_key in ("lose", "bust")     else "result-push"

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown(f'<div class="{css_class}">{label}</div>', unsafe_allow_html=True)

        acc       = result_data.get("accuracy", 1.0)
        acc_color = COLORS["success"] if acc >= 0.8 else \
                    COLORS["warning"] if acc >= 0.5 else COLORS["error"]
        muted     = COLORS["text_muted"]
        st.markdown(
            f'<div style="text-align:center;margin-top:8px">'
            f'<span style="color:{muted};font-family:\'Cinzel\',serif;'
            f'font-size:11px;letter-spacing:0.1em">ROUND ACCURACY &nbsp;</span>'
            f'<span style="color:{acc_color};font-family:\'Cinzel\',serif;'
            f'font-size:16px;font-weight:600">{acc*100:.0f}%</span></div>',
            unsafe_allow_html=True
        )

        if gs.last_correct is not None:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                feedback_html(gs.last_correct, gs.last_action.value, gs.last_optimal.value),
                unsafe_allow_html=True,
            )


def _render_new_round_prompt():
    col_l, col_c, col_r = st.columns([2, 1, 2])
    with col_c:
        if st.button("🃏 New Round", use_container_width=True, type="primary"):
            _start_new_round()


def _render_next_button():
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([2, 1, 2])
    with col_c:
        if st.button("▶ Next Round", use_container_width=True, type="primary"):
            _start_new_round()


def _start_new_round():
    gs = st.session_state.get("gs")
    if gs:
        gs.new_round()
    st.session_state["round_result"]       = None
    st.session_state["dealer_final_cards"] = None
    st.session_state["dealer_final_value"] = None
    st.rerun()
