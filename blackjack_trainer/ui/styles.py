"""
BlackJack Trainer — UI styles and theme
Casino aesthetic: dark green felt, gold accents
"""


COLORS = {
    "felt_dark":    "#0a1f0f",
    "felt":         "#0f2d16",
    "felt_mid":     "#1a4225",
    "felt_light":   "#245c33",
    "gold":         "#c9a227",
    "gold_light":   "#e8c547",
    "gold_pale":    "#f5e6b2",
    "card_bg":      "#fdf6e3",
    "card_red":     "#c0392b",
    "card_black":   "#1a1a2e",
    "success":      "#27ae60",
    "error":        "#e74c3c",
    "warning":      "#f39c12",
    "text_primary": "#f5e6b2",
    "text_muted":   "#8faa94",
    "surface":      "#122d18",
    "border":       "#2d5a3d",
}

SUIT_COLORS = {
    "♠": COLORS["card_black"],
    "♣": COLORS["card_black"],
    "♥": COLORS["card_red"],
    "♦": COLORS["card_red"],
}


SUIT_EMOJI = {"♠": "♠", "♣": "♣", "♥": "♥", "♦": "♦"}

ACTION_LABELS = {
    "hit":    "🎯 Hit",
    "stand":  "✋ Stand",
    "double": "⚡ Double",
    "split":  "✂️ Split",
}

ACTION_COLORS = {
    "hit":    "#3498db",
    "stand":  "#e67e22",
    "double": "#9b59b6",
    "split":  "#1abc9c",
}

RESULT_EMOJI = {
    "win":       "🏆 Win!",
    "blackjack": "💎 Blackjack!",
    "lose":      "💀 Loss",
    "bust":      "💥 Bust!",
    "push":      "🤝 Push",
}

RESULT_COLORS = {
    "win":       "#27ae60",
    "blackjack": "#c9a227",
    "lose":      "#e74c3c",
    "bust":      "#e74c3c",
    "push":      "#7f8c8d",
}


GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&display=swap');

/* ── Reset & Base ── */
.stApp {{
    background-color: {COLORS['felt_dark']};
    background-image:
        radial-gradient(ellipse at 20% 20%, rgba(36, 92, 51, 0.4) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 80%, rgba(10, 31, 15, 0.6) 0%, transparent 60%);
    font-family: 'Crimson Pro', Georgia, serif;
    color: {COLORS['text_primary']};
}}


h1, h2, h3 {{
    font-family: 'Cinzel', serif !important;
    color: {COLORS['gold']} !important;
    letter-spacing: 0.05em;
}}


.stSidebar {{
    background: linear-gradient(180deg, {COLORS['felt']} 0%, {COLORS['felt_dark']} 100%) !important;
    border-right: 1px solid {COLORS['border']} !important;
}}
.stSidebar .stRadio label {{
    color: {COLORS['text_primary']} !important;
    font-family: 'Cinzel', serif;
    font-size: 14px;
    letter-spacing: 0.1em;
    padding: 6px 0;
}}

/* Buttons */
.stButton > button {{
    font-family: 'Cinzel', serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    border-radius: 4px !important;
    border: 1px solid {COLORS['gold']}44 !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase;
    font-size: 13px !important;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(201, 162, 39, 0.3) !important;
    border-color: {COLORS['gold']} !important;
}}

/* Metrics */
[data-testid="metric-container"] {{
    background: {COLORS['surface']} !important;
    border: 1px solid {COLORS['border']} !important;
    border-radius: 8px !important;
    padding: 16px !important;
}}
[data-testid="metric-container"] label {{
    color: {COLORS['text_muted']} !important;
    font-family: 'Cinzel', serif !important;
    font-size: 11px !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {COLORS['gold']} !important;
    font-family: 'Cinzel', serif !important;
    font-size: 28px !important;
}}

/* Dividers */
hr {{
    border-color: {COLORS['border']} !important;
    margin: 24px 0 !important;
}}

/* Cards */
.bj-card {{
    display: inline-block;
    background: {COLORS['card_bg']};
    border-radius: 8px;
    padding: 10px 14px;
    margin: 4px;
    min-width: 52px;
    text-align: center;
    font-family: 'Cinzel', serif;
    font-size: 20px;
    font-weight: 700;
    box-shadow: 2px 3px 8px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.8);
    border: 1px solid #d4c5a0;
    line-height: 1.2;
    vertical-align: top;
}}
.bj-card-hidden {{
    background: linear-gradient(135deg, {COLORS['felt']} 25%, {COLORS['felt_mid']} 50%, {COLORS['felt']} 75%);
    color: {COLORS['gold']}88;
    border: 1px solid {COLORS['border']};
    font-size: 28px;
}}
.bj-card-red {{ color: {COLORS['card_red']}; }}
.bj-card-black {{ color: {COLORS['card_black']}; }}

/* Table panel */
.felt-panel {{
    background: radial-gradient(ellipse at center, {COLORS['felt_mid']} 0%, {COLORS['felt']} 100%);
    border: 2px solid {COLORS['border']};
    border-radius: 16px;
    padding: 24px;
    margin: 8px 0;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
}}

/* Feedback block */
.feedback-correct {{
    background: linear-gradient(135deg, #0d3320, #1a5c35);
    border: 1px solid {COLORS['success']};
    border-left: 4px solid {COLORS['success']};
    border-radius: 8px;
    padding: 12px 16px;
    color: #aff0c5;
    font-family: 'Crimson Pro', serif;
    font-size: 16px;
}}
.feedback-wrong {{
    background: linear-gradient(135deg, #3d0d0d, #6b1515);
    border: 1px solid {COLORS['error']};
    border-left: 4px solid {COLORS['error']};
    border-radius: 8px;
    padding: 12px 16px;
    color: #f5a5a5;
    font-family: 'Crimson Pro', serif;
    font-size: 16px;
}}

/* Round result */
.result-win {{
    text-align: center;
    font-family: 'Cinzel', serif;
    font-size: 32px;
    font-weight: 700;
    color: {COLORS['gold']};
    text-shadow: 0 0 20px rgba(201,162,39,0.5);
    padding: 20px;
    animation: pulse 1s ease-in-out;
}}
.result-lose {{
    text-align: center;
    font-family: 'Cinzel', serif;
    font-size: 32px;
    font-weight: 700;
    color: {COLORS['error']};
    padding: 20px;
}}
.result-push {{
    text-align: center;
    font-family: 'Cinzel', serif;
    font-size: 28px;
    color: {COLORS['text_muted']};
    padding: 20px;
}}

/* Gold divider */
.gold-divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, {COLORS['gold']}88, transparent);
    margin: 20px 0;
}}

/* Accuracy badge */
.accuracy-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'Cinzel', serif;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.05em;
}}

/* Strategy table */
.strategy-hint {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['gold']}44;
    border-radius: 8px;
    padding: 10px 16px;
    font-family: 'Cinzel', serif;
    font-size: 13px;
    color: {COLORS['gold_pale']};
    letter-spacing: 0.05em;
}}

/* ── Streamlit overrides ── */
.stMarkdown p {{
    font-family: 'Crimson Pro', serif;
    font-size: 16px;
    color: {COLORS['text_primary']};
}}
div[data-testid="stVerticalBlock"] {{
    gap: 0.5rem;
}}
.stSelectbox label, .stSlider label, .stNumberInput label {{
    color: {COLORS['text_muted']} !important;
    font-family: 'Cinzel', serif !important;
    font-size: 12px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}}
</style>
"""


def card_html(card_str: str, hidden: bool = False) -> str:
    """Render a single card as an HTML block."""
    if hidden:
        return '<span class="bj-card bj-card-hidden">🂠</span>'

    
    suit = card_str[-1] if card_str and card_str[-1] in "♠♣♥♦" else ""
    rank = card_str[:-1] if suit else card_str

    color_class = "bj-card-red" if suit in ("♥", "♦") else "bj-card-black"
    suit_line = f"<br><span style='font-size:14px'>{suit}</span>" if suit else ""

    return f'<span class="bj-card {color_class}">{rank}{suit_line}</span>'


def hand_html(cards: list[str], show_all: bool = True) -> str:
    """Render a hand as a row of card HTML blocks."""
    parts = []
    for i, c in enumerate(cards):
        hidden = not show_all and i == 1
        parts.append(card_html(c, hidden=hidden))
    return " ".join(parts)


def value_badge(value: int, is_soft: bool = False, is_bust: bool = False) -> str:
    """Hand value badge."""
    label = f"{'Soft ' if is_soft else ''}{value}"
    if is_bust:
        color = COLORS["error"]
        bg = "#3d0d0d"
    elif value == 21:
        color = COLORS["gold"]
        bg = "#2d2000"
    elif value >= 17:
        color = COLORS["success"]
        bg = "#0d2d1a"
    else:
        color = COLORS["text_primary"]
        bg = COLORS["surface"]

    return (
        f'<span style="background:{bg};color:{color};border:1px solid {color}44;'
        f'padding:3px 10px;border-radius:12px;font-family:\'Cinzel\',serif;'
        f'font-size:14px;font-weight:600;">{label}</span>'
    )


def feedback_html(correct: bool, action: str, optimal: str) -> str:
    """Feedback block shown after a move."""
    from ui.styles import ACTION_LABELS
    act_lbl = ACTION_LABELS.get(action, action)
    opt_lbl = ACTION_LABELS.get(optimal, optimal)

    if correct:
        return (
            f'<div class="feedback-correct">'
            f'✅ <strong>Correct!</strong> {act_lbl} was the right play'
            f'</div>'
        )
    else:
        return (
            f'<div class="feedback-wrong">'
            f'❌ <strong>Mistake.</strong> You chose {act_lbl}, '
            f'but the right move here is: <strong>{opt_lbl}</strong>'
            f'</div>'
        )
