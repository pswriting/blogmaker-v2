"""
BlogMaker v2 - 네이버 상위 블로그 패턴 학습 AI 블로그 자동 생성기
@author: CashMaker (cashmaker.co.kr)
@version: 2.1.0 - Premium UI
"""

import streamlit as st
import anthropic
from pathlib import Path
import json
import re
import io
from datetime import datetime

# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="BlogMaker v2 | CashMaker",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MODEL_NAME = "claude-sonnet-4-6"

SKILL_DIR = Path(__file__).parent.parent / "skills"

CATEGORY_MAP = {
    "IT / 리뷰": "it_review.md",
    "행정 / 법무": "admin_legal.md",
    "교육 / 육아": "education.md",
    "재테크 / 투자": "finance.md",
    "취업 / 커리어": "career.md",
    "맛집 / 여행": "food_travel.md",
    "가전 / 리빙": "home_appliance.md",
    "건강 / 감성": "health_emotion.md",
    "마케팅 / 1인사업": "marketing.md",
}

STAGE_NAMES = ["도입", "전환", "본론", "강조", "클로징"]

# ============================================================
# 프리미엄 디자인 시스템 (CSS 주입)
# ============================================================

PREMIUM_CSS = """
<style>
/* ─────────────────────────────────────────
   Pretendard 폰트 로드 (한글 산세리프 최고급)
   ───────────────────────────────────────── */
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');

:root {
    --color-ink: #0F1419;
    --color-ink-soft: #1B1F2A;
    --color-ink-mute: #4A5060;
    --color-gold: #B8985A;
    --color-gold-soft: #D4B87E;
    --color-gold-faint: #EBE0C8;
    --color-ivory: #FAF7F0;
    --color-ivory-soft: #F5F1E8;
    --color-line: #E5DFD2;
    --color-line-soft: #EFEAE0;
    --color-white: #FFFFFF;
    --color-error: #8B3A3A;
    --color-success: #4A6B47;
    
    --font-body: 'Pretendard Variable', Pretendard, -apple-system, sans-serif;
    --font-display: 'Pretendard Variable', Pretendard, -apple-system, sans-serif;
    
    --shadow-soft: 0 1px 2px rgba(15, 20, 25, 0.04);
    --shadow-card: 0 1px 3px rgba(15, 20, 25, 0.06), 0 4px 12px rgba(15, 20, 25, 0.03);
}

/* ─────────────────────────────────────────
   전역 리셋 & 베이스
   ───────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: var(--font-body) !important;
    font-feature-settings: "tnum", "ss01";
    letter-spacing: -0.01em;
}

.stApp {
    background: var(--color-ivory) !important;
}

/* Streamlit 기본 헤더/푸터 숨기기 */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 0 !important;
}

footer { display: none !important; }
.stDeployButton { display: none !important; }
#MainMenu { visibility: hidden !important; }

/* 메인 컨테이너 */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 4rem !important;
    max-width: 1200px !important;
}

/* ─────────────────────────────────────────
   타이포그래피
   ───────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-display) !important;
    color: var(--color-ink) !important;
    letter-spacing: -0.025em !important;
    font-weight: 700 !important;
}

h1 { font-size: 2rem !important; line-height: 1.2 !important; }
h2 { font-size: 1.5rem !important; line-height: 1.3 !important; font-weight: 600 !important; }
h3 { font-size: 1.15rem !important; line-height: 1.4 !important; font-weight: 600 !important; }

p, div, span, label {
    color: var(--color-ink-soft) !important;
}

.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--color-ink-mute) !important;
    font-size: 0.875rem !important;
    letter-spacing: -0.005em !important;
}

/* ─────────────────────────────────────────
   탭 (가장 눈에 띄는 부분)
   ───────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent !important;
    border-bottom: 1px solid var(--color-line) !important;
    gap: 0 !important;
    padding: 0 !important;
}

.stTabs [data-baseweb="tab"] {
    height: 52px !important;
    padding: 0 28px !important;
    background: transparent !important;
    border: none !important;
    color: var(--color-ink-mute) !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    letter-spacing: -0.01em !important;
    transition: all 0.2s ease !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--color-ink) !important;
    background: transparent !important;
}

.stTabs [aria-selected="true"] {
    color: var(--color-ink) !important;
    font-weight: 600 !important;
    border-bottom: 2px solid var(--color-gold) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
    background: var(--color-gold) !important;
    height: 2px !important;
}

.stTabs [data-baseweb="tab-panel"] {
    padding-top: 2.5rem !important;
}

/* ─────────────────────────────────────────
   입력 컨트롤 (텍스트, 셀렉트, 슬라이더)
   ───────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--color-white) !important;
    border: 1px solid var(--color-line) !important;
    border-radius: 4px !important;
    color: var(--color-ink) !important;
    font-family: var(--font-body) !important;
    font-size: 0.95rem !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--color-gold) !important;
    box-shadow: 0 0 0 3px rgba(184, 152, 90, 0.08) !important;
    outline: none !important;
}

.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #A8A89A !important;
}

/* Select box */
.stSelectbox > div > div {
    background: var(--color-white) !important;
    border: 1px solid var(--color-line) !important;
    border-radius: 4px !important;
}

.stSelectbox > div > div:hover {
    border-color: var(--color-gold) !important;
}

/* Slider */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background: var(--color-gold) !important;
    border: 2px solid var(--color-white) !important;
    box-shadow: 0 0 0 1px var(--color-gold) !important;
}

.stSlider [data-baseweb="slider"] > div > div > div {
    background: var(--color-gold) !important;
}

.stSlider [data-baseweb="slider"] > div {
    background: var(--color-line) !important;
}

/* Labels */
.stTextInput label, .stTextArea label, .stSelectbox label, .stSlider label,
.stFileUploader label {
    color: var(--color-ink) !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    letter-spacing: -0.005em !important;
    margin-bottom: 6px !important;
}

/* ─────────────────────────────────────────
   버튼 - 골드 프라이머리
   ───────────────────────────────────────── */
.stButton > button,
.stDownloadButton > button {
    background: var(--color-ink) !important;
    color: var(--color-ivory) !important;
    border: 1px solid var(--color-ink) !important;
    border-radius: 4px !important;
    padding: 12px 28px !important;
    font-family: var(--font-body) !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    letter-spacing: -0.005em !important;
    transition: all 0.2s ease !important;
    box-shadow: none !important;
    height: auto !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background: var(--color-gold) !important;
    color: var(--color-white) !important;
    border-color: var(--color-gold) !important;
    transform: translateY(-1px);
}

.stButton > button:active,
.stDownloadButton > button:active {
    transform: translateY(0);
}

/* Primary 버튼 (CTA) - 골드 */
.stButton > button[kind="primary"] {
    background: var(--color-gold) !important;
    border-color: var(--color-gold) !important;
    color: var(--color-white) !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--color-ink) !important;
    border-color: var(--color-ink) !important;
    color: var(--color-ivory) !important;
}

/* ─────────────────────────────────────────
   알림 박스 (info, warning, error, success)
   ───────────────────────────────────────── */
.stAlert {
    background: var(--color-white) !important;
    border-radius: 4px !important;
    padding: 16px 20px !important;
    border: 1px solid var(--color-line) !important;
    border-left: 3px solid var(--color-gold) !important;
    box-shadow: var(--shadow-soft) !important;
}

.stAlert [data-testid="stMarkdownContainer"] p,
.stAlert div {
    color: var(--color-ink-soft) !important;
    font-size: 0.9rem !important;
}

/* ─────────────────────────────────────────
   Expander
   ───────────────────────────────────────── */
.streamlit-expanderHeader,
[data-testid="stExpander"] details summary {
    background: var(--color-white) !important;
    border: 1px solid var(--color-line) !important;
    border-radius: 4px !important;
    color: var(--color-ink) !important;
    font-weight: 500 !important;
    padding: 14px 18px !important;
}

[data-testid="stExpander"] details summary:hover {
    border-color: var(--color-gold-soft) !important;
}

[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid var(--color-line-soft) !important;
    border-radius: 4px 4px 0 0 !important;
}

[data-testid="stExpander"] details[open] {
    background: var(--color-white) !important;
    border-radius: 4px !important;
}

/* ─────────────────────────────────────────
   파일 업로더
   ───────────────────────────────────────── */
[data-testid="stFileUploader"] section {
    background: var(--color-white) !important;
    border: 1.5px dashed var(--color-line) !important;
    border-radius: 4px !important;
    padding: 24px !important;
}

[data-testid="stFileUploader"] section:hover {
    border-color: var(--color-gold-soft) !important;
    background: var(--color-ivory-soft) !important;
}

/* ─────────────────────────────────────────
   진행바
   ───────────────────────────────────────── */
.stProgress > div > div > div {
    background: var(--color-gold) !important;
}

.stProgress > div > div {
    background: var(--color-line) !important;
}

/* ─────────────────────────────────────────
   커스텀 컴포넌트 클래스
   ───────────────────────────────────────── */

/* 상단 브랜드 영역 */
.brand-header {
    display: flex;
    flex-direction: column;
    padding-bottom: 24px;
    margin-bottom: 8px;
    border-bottom: 1px solid var(--color-line);
}

.brand-wordmark {
    font-family: var(--font-display);
    font-size: 1.75rem;
    font-weight: 700;
    color: var(--color-ink);
    letter-spacing: -0.03em;
    line-height: 1;
    margin: 0;
}

.brand-wordmark .accent {
    color: var(--color-gold);
    font-weight: 600;
}

.brand-tagline {
    margin-top: 10px;
    color: var(--color-ink-mute);
    font-size: 0.875rem;
    letter-spacing: -0.005em;
}

.brand-meta {
    margin-top: 4px;
    color: var(--color-ink-mute);
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
}

/* 섹션 헤더 */
.section-header {
    margin-bottom: 28px;
}

.section-eyebrow {
    color: var(--color-gold);
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 8px;
    display: block;
}

.section-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-ink);
    letter-spacing: -0.025em;
    line-height: 1.3;
    margin: 0 0 10px 0;
}

.section-description {
    color: var(--color-ink-mute);
    font-size: 0.9rem;
    line-height: 1.5;
    max-width: 640px;
}

/* 카드 컨테이너 */
.premium-card {
    background: var(--color-white);
    border: 1px solid var(--color-line);
    border-radius: 6px;
    padding: 28px;
    box-shadow: var(--shadow-card);
    margin-bottom: 20px;
}

.premium-card-header {
    border-bottom: 1px solid var(--color-line-soft);
    padding-bottom: 16px;
    margin-bottom: 20px;
}

.premium-card-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--color-ink);
    margin: 0;
    letter-spacing: -0.015em;
}

.premium-card-subtitle {
    font-size: 0.8rem;
    color: var(--color-ink-mute);
    margin-top: 4px;
}

/* 안내 사이드 박스 */
.info-panel {
    background: var(--color-ivory-soft);
    border: 1px solid var(--color-line-soft);
    border-left: 3px solid var(--color-gold);
    border-radius: 4px;
    padding: 24px;
}

.info-panel h4 {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-gold);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0 0 14px 0;
}

.info-panel ol, .info-panel ul {
    margin: 0;
    padding-left: 18px;
}

.info-panel li {
    color: var(--color-ink-soft);
    font-size: 0.875rem;
    line-height: 1.7;
    letter-spacing: -0.005em;
}

.info-panel li + li {
    margin-top: 4px;
}

/* 5단 골격 단계 표시 */
.stage-marker {
    display: inline-flex;
    align-items: center;
    gap: 14px;
    padding: 6px 0;
    margin-bottom: 14px;
}

.stage-number {
    width: 28px;
    height: 28px;
    border: 1.5px solid var(--color-gold);
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--color-gold);
    font-size: 0.85rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.stage-label {
    font-size: 0.7rem;
    font-weight: 600;
    color: var(--color-gold);
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.stage-title {
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--color-ink);
    letter-spacing: -0.02em;
    margin: 0;
}

/* 작은 메타 정보 */
.meta-row {
    display: flex;
    gap: 20px;
    padding: 12px 0;
    border-top: 1px solid var(--color-line-soft);
    border-bottom: 1px solid var(--color-line-soft);
    margin: 16px 0;
}

.meta-item {
    display: flex;
    flex-direction: column;
}

.meta-label {
    font-size: 0.7rem;
    color: var(--color-ink-mute);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 500;
}

.meta-value {
    font-size: 0.95rem;
    color: var(--color-ink);
    font-weight: 600;
    margin-top: 2px;
    letter-spacing: -0.01em;
}

/* 골드 구분선 */
.gold-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, var(--color-gold), transparent);
    margin: 32px 0;
    border: none;
}

/* 결과 컨테이너 */
.result-container {
    background: var(--color-white);
    border: 1px solid var(--color-line);
    border-radius: 6px;
    padding: 32px;
    margin-top: 20px;
    box-shadow: var(--shadow-card);
}

.result-content {
    font-family: var(--font-body);
    line-height: 1.8;
    color: var(--color-ink-soft);
    white-space: pre-wrap;
    font-size: 0.95rem;
}

/* 페이지 진입 페이드 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}

.block-container > div {
    animation: fadeIn 0.4s ease-out;
}

/* 사이드 디테일 */
.kbd {
    font-family: ui-monospace, monospace;
    background: var(--color-ivory-soft);
    border: 1px solid var(--color-line);
    border-radius: 3px;
    padding: 2px 6px;
    font-size: 0.8rem;
    color: var(--color-ink);
}
</style>
"""


# ============================================================
# 유틸리티 함수
# ============================================================

def inject_css():
    """프리미엄 CSS 주입"""
    st.markdown(PREMIUM_CSS, unsafe_allow_html=True)


def render_brand_header():
    """상단 브랜드 영역"""
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-meta">CashMaker Studio</div>
            <h1 class="brand-wordmark">BlogMaker <span class="accent">v2</span></h1>
            <p class="brand-tagline">네이버 상위 블로그 패턴 학습 AI · 5단 골격 단계별 생성 · Writey 연동</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(eyebrow: str, title: str, description: str = ""):
    """탭 안의 섹션 헤더"""
    desc_html = f'<p class="section-description">{description}</p>' if description else ""
    st.markdown(
        f"""
        <div class="section-header">
            <span class="section-eyebrow">{eyebrow}</span>
            <h2 class="section-title">{title}</h2>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stage_marker(number: int, title: str):
    """5단계 생성 시 단계 마커"""
    st.markdown(
        f"""
        <div class="stage-marker">
            <span class="stage-number">{number:02d}</span>
            <div>
                <div class="stage-label">Stage {number}</div>
                <h3 class="stage-title">{title}</h3>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_gold_divider():
    st.markdown('<hr class="gold-divider">', unsafe_allow_html=True)


def load_skill(filename: str) -> str:
    """SKILL.md 파일 로드"""
    path = SKILL_DIR / filename
    if not path.exists():
        st.error(f"SKILL 파일을 찾을 수 없습니다: {path.name}")
        return ""
    return path.read_text(encoding="utf-8")


def get_api_client():
    """Anthropic API 클라이언트 생성"""
    api_key = st.session_state.get("api_key", "")
    
    if not api_key:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            api_key = ""
    
    if not api_key:
        st.error("API 키가 필요합니다. **설정** 탭에서 Anthropic API 키를 입력해주세요.")
        st.markdown(
            '<p style="font-size:0.85rem; color:var(--color-ink-mute); margin-top:8px;">'
            '키 발급 → <a href="https://console.anthropic.com" target="_blank" '
            'style="color:var(--color-gold); text-decoration:none; border-bottom:1px solid var(--color-gold);">'
            'console.anthropic.com</a></p>',
            unsafe_allow_html=True,
        )
        return None
    
    return anthropic.Anthropic(api_key=api_key)


def build_system_prompt(category: str, user_facts: str = "") -> str:
    """카테고리에 맞는 시스템 프롬프트 구성"""
    master = load_skill("_master.md")
    category_skill = load_skill(CATEGORY_MAP[category])
    facts_section = f"\n\n## 사용자 제공 사실/경험\n{user_facts}\n" if user_facts.strip() else ""
    
    return f"""{master}

---

# 현재 카테고리: {category}

{category_skill}
{facts_section}

---

위 모든 규칙을 엄수하여 한국어 네이버 블로그 글을 작성한다.
"""


def call_claude(client, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
    """Claude API 호출"""
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text
    except anthropic.APIError as e:
        st.error(f"API 오류: {e}")
        return ""
    except Exception as e:
        st.error(f"알 수 없는 오류: {e}")
        return ""


# ============================================================
# 5단 골격 단계별 생성
# ============================================================

def generate_stage(client, system_prompt: str, stage: int, context: dict) -> str:
    """5단 골격 중 특정 단계만 생성"""
    topic = context.get("topic", "")
    user_facts = context.get("user_facts", "")
    previous = context.get("previous_stages", "")
    
    stage_prompts = {
        1: f"""주제: {topic}

위 주제로 네이버 블로그 글의 **1단계 (도입)**만 작성한다.
- 1~3문장
- 카테고리에 맞는 후킹 패턴 선택
- 도입만! 본문이나 결론은 절대 쓰지 말 것
""",
        2: f"""주제: {topic}

이전 단계 (도입):
{previous}

위 도입에 이어 **2단계 (전환)**만 작성한다.
- 1문장
- "오늘은 ~"으로 시작 권장
- 글의 주제와 약속을 명확히
- 전환만! 다른 단계는 쓰지 말 것
""",
        3: f"""주제: {topic}

이전 단계 (도입+전환):
{previous}

사용자 제공 사실: {user_facts}

위에 이어 **3단계 (본론)**을 작성한다.
- 전체 글의 60~70% 분량 (1000~1500자)
- 소제목 4~6개
- 넘버링 또는 박스 구조 강제
- 카테고리별 시각 패턴 적용 (이미지 첨부 위치를 [사진: 직접 촬영] 같이 표시)
- 구체 숫자/날짜/제품명 최소 3개 이상 포함
- 본론만! 도입/전환/강조/클로징 다시 쓰지 말 것
""",
        4: f"""주제: {topic}

이전 단계 (도입+전환+본론):
{previous}

위 본론의 핵심을 **4단계 (강조)**로 한 번 더 짚는다.
- 1~3문장
- 핵심 한 줄을 굵은 글씨 또는 인용 박스로 표현 (마크업 사용: **굵은글씨** 또는 > 인용)
- 강조만! 다른 단계는 쓰지 말 것
""",
        5: f"""주제: {topic}

이전 단계 (도입~강조):
{previous}

마지막 **5단계 (클로징)**을 작성한다.
- 권유형 마무리 (1~3문장)
- 카테고리에 맞는 CTA
- 책임 회피/면책 문구 (해당 카테고리만)
- 마지막에 해시태그 생성: 메인 3~5개 + 서브 15~20개 (#으로 시작)
- 클로징만! 다른 단계는 쓰지 말 것
""",
    }
    
    return call_claude(client, system_prompt, stage_prompts[stage], max_tokens=2500 if stage == 3 else 1000)


# ============================================================
# 전자책 분해
# ============================================================

def split_ebook_to_posts(client, ebook_text: str, num_posts: int, category: str) -> list[dict]:
    """전자책 텍스트를 N편의 블로그 글 주제로 분해 (배치 처리)"""
    
    system = """당신은 한국 디지털 콘텐츠 기획 전문가다.
전자책의 핵심 내용을 추출해 네이버 블로그 시리즈로 분해하는 일을 한다.
JSON 형식만 출력하며, 마크다운이나 설명을 절대 추가하지 않는다."""
    
    BATCH_SIZE = 15
    all_posts = []
    text_sample = ebook_text[:15000]
    
    progress_placeholder = st.empty()
    
    for batch_start in range(0, num_posts, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, num_posts)
        batch_count = batch_end - batch_start
        
        progress_placeholder.info(
            f"배치 생성 중: {batch_start + 1}~{batch_end}편 / 총 {num_posts}편"
        )
        
        prompt = f"""다음 전자책 내용을 분석해 **블로그 글 주제 {batch_count}편**을 생성하라.
(이번 배치: {batch_start + 1}번부터 {batch_end}번까지)

전자책 카테고리: {category}

전자책 내용:
---
{text_sample}
---

출력 규칙 (엄수):
1. JSON 배열만 출력. 다른 텍스트/설명/마크다운 코드블록 금지.
2. 문자열 안의 따옴표는 반드시 백슬래시로 이스케이프 (예: "그는 \\"안녕\\"이라 말했다")
3. 정확히 {batch_count}개 객체 생성
4. 각 객체는 아래 4개 필드 필수

[
  {{
    "번호": {batch_start + 1},
    "제목": "구체적인 글 제목 (따옴표 사용 금지)",
    "핵심메시지": "이 글의 한 가지 핵심 (따옴표 사용 금지)",
    "주요키워드": ["키워드1", "키워드2", "키워드3"]
  }}
]

규칙:
- 번호는 {batch_start + 1}부터 시작
- 시리즈 흐름 유지 (점진적 심화)
- 제목과 핵심메시지에는 따옴표(" ')를 사용하지 말 것
"""
        
        response = call_claude(client, system, prompt, max_tokens=6000)
        
        if not response:
            st.error(f"배치 {batch_start + 1}~{batch_end} 응답 없음. 중단합니다.")
            break
        
        cleaned = response.strip()
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        start_idx = cleaned.find('[')
        end_idx = cleaned.rfind(']')
        
        if start_idx == -1 or end_idx == -1:
            st.warning(f"배치 {batch_start + 1}~{batch_end}: JSON 배열을 찾을 수 없음.")
            continue
        
        json_text = cleaned[start_idx:end_idx + 1]
        
        try:
            batch_posts = json.loads(json_text)
            all_posts.extend(batch_posts)
        except json.JSONDecodeError:
            try:
                fixed = re.sub(r',(\s*[}\]])', r'\1', json_text)
                fixed = fixed.replace('\u201c', '"').replace('\u201d', '"')
                fixed = fixed.replace('\u2018', "'").replace('\u2019', "'")
                batch_posts = json.loads(fixed)
                all_posts.extend(batch_posts)
            except json.JSONDecodeError as e2:
                st.warning(f"배치 {batch_start + 1}~{batch_end} 파싱 실패: {str(e2)[:80]}")
                continue
    
    progress_placeholder.empty()
    return all_posts


def extract_text_from_upload(uploaded_file) -> str:
    """업로드된 파일에서 텍스트 추출"""
    name = uploaded_file.name.lower()
    
    if name.endswith(".txt") or name.endswith(".md"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    
    elif name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            return "\n".join(page.extract_text() for page in reader.pages)
        except ImportError:
            st.error("PDF 처리에는 `pypdf` 패키지가 필요합니다.")
            return ""
    
    elif name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            st.error("DOCX 처리에는 `python-docx` 패키지가 필요합니다.")
            return ""
    
    else:
        st.error(f"지원하지 않는 파일 형식입니다: {name}")
        return ""


# ============================================================
# 탭 1: 블로그 작성
# ============================================================

def tab_blog_writer():
    render_section_header(
        eyebrow="WRITE",
        title="블로그 글 자동 생성",
        description="카테고리 선택 후 주제와 본인 경험을 입력하면 도입 → 전환 → 본론 → 강조 → 클로징의 5단 골격으로 순차 생성됩니다.",
    )
    
    col_left, col_right = st.columns([1, 1.6], gap="large")
    
    with col_left:
        category = st.selectbox(
            "카테고리",
            list(CATEGORY_MAP.keys()),
            help="카테고리에 따라 어미, 후킹, 시각 패턴이 자동 분기됩니다.",
        )
        
        with st.expander("이 카테고리의 SKILL 미리보기"):
            skill_content = load_skill(CATEGORY_MAP[category])
            st.markdown(skill_content)
    
    with col_right:
        topic = st.text_input(
            "블로그 주제",
            placeholder="예: 27인치 모니터 LG 32GP750 3개월 사용 후기",
            help="구체적일수록 결과 품질이 높아집니다.",
        )
        
        user_facts = st.text_area(
            "본인 경험 · 구체 사실 (선택, 권장)",
            placeholder="""예시
· 2026년 1월 구매, 정가 35만원 → 28만원에 구매
· 이전 사용: 24인치 삼성 (5년 사용)
· 사용 환경: 듀얼 모니터, 영상편집 작업 위주
· 단점: 스피커 음질이 아쉬움""",
            height=180,
            help="숫자, 날짜, 제품명 등 구체적 사실이 많을수록 AI 회피 효과가 큽니다. 최소 3개 권장.",
        )
    
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
    
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        generate_clicked = st.button(
            "5단 골격으로 생성",
            type="primary",
            use_container_width=True,
            key="generate_blog",
        )
    
    if generate_clicked:
        if not topic.strip():
            st.warning("주제를 입력해주세요.")
            return
        
        client = get_api_client()
        if not client:
            return
        
        render_gold_divider()
        
        system_prompt = build_system_prompt(category, user_facts)
        context = {"topic": topic, "user_facts": user_facts, "previous_stages": ""}
        all_stages = []
        
        for i, stage_name in enumerate(STAGE_NAMES, 1):
            render_stage_marker(i, stage_name)
            
            with st.spinner(f"Stage {i:02d} · {stage_name} 생성 중…"):
                stage_output = generate_stage(client, system_prompt, i, context)
            
            all_stages.append((stage_name, stage_output))
            context["previous_stages"] += f"\n\n{stage_output}"
            
            st.markdown(
                f'<div class="result-content">{stage_output}</div>',
                unsafe_allow_html=True,
            )
            st.markdown('<div style="margin: 32px 0;"></div>', unsafe_allow_html=True)
        
        render_gold_divider()
        
        full_post = "\n\n".join(out for _, out in all_stages)
        
        st.markdown(
            '<span class="section-eyebrow">RESULT</span>'
            '<h2 class="section-title" style="margin-bottom:20px;">완성된 글</h2>',
            unsafe_allow_html=True,
        )
        
        st.text_area(
            "복사용 전체 글",
            value=full_post,
            height=400,
            label_visibility="collapsed",
        )
        
        col_dl, _ = st.columns([1, 3])
        with col_dl:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "Markdown 파일로 저장",
                data=full_post,
                file_name=f"blogpost_{category.replace(' / ', '_')}_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True,
            )


# ============================================================
# 탭 2: 전자책 분해
# ============================================================

def tab_ebook_splitter():
    render_section_header(
        eyebrow="SPLIT",
        title="전자책 → 블로그 시리즈 분해",
        description="Writey로 만든 전자책 1권을 자동으로 N편의 블로그 글 주제 리스트로 분해합니다. 각 주제는 블로그 작성 탭에서 본문으로 확장할 수 있습니다.",
    )
    
    col_input, col_guide = st.columns([1.5, 1], gap="large")
    
    with col_input:
        uploaded_file = st.file_uploader(
            "전자책 파일",
            type=["txt", "md", "pdf", "docx"],
            help="지원 형식: TXT, MD, PDF, DOCX",
        )
        
        category = st.selectbox(
            "카테고리",
            list(CATEGORY_MAP.keys()),
            key="ebook_category",
        )
        
        num_posts = st.slider(
            "분해할 글 편수",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            help="15편씩 배치로 처리됩니다.",
        )
    
    with col_guide:
        st.markdown(
            """
            <div class="info-panel">
                <h4>WORKFLOW</h4>
                <ol>
                    <li>전자책 파일 업로드</li>
                    <li>카테고리 및 편수 선택</li>
                    <li>분해 시작 클릭</li>
                    <li>생성된 주제 리스트 다운로드</li>
                    <li>각 주제를 블로그 작성 탭에서 확장</li>
                </ol>
                <h4 style="margin-top:24px;">권장 분량</h4>
                <ul>
                    <li>200페이지 전자책 → 50편</li>
                    <li>100페이지 전자책 → 25편</li>
                    <li>50페이지 전자책 → 15편</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown('<div style="margin-top: 28px;"></div>', unsafe_allow_html=True)
    
    col_btn, _ = st.columns([1, 3])
    with col_btn:
        split_clicked = st.button(
            "분해 시작",
            type="primary",
            use_container_width=True,
            key="split_ebook",
        )
    
    if split_clicked:
        if not uploaded_file:
            st.warning("전자책 파일을 업로드해주세요.")
            return
        
        client = get_api_client()
        if not client:
            return
        
        render_gold_divider()
        
        with st.spinner("전자책 텍스트 추출 중…"):
            text = extract_text_from_upload(uploaded_file)
        
        if not text.strip():
            st.error("텍스트를 추출할 수 없습니다.")
            return
        
        st.info(f"추출된 텍스트: **{len(text):,}자** (앞 15,000자만 분석에 사용)")
        
        posts = split_ebook_to_posts(client, text, num_posts, category)
        
        if not posts:
            st.error("분해 결과가 없습니다. 다시 시도해주세요.")
            return
        
        st.success(f"총 **{len(posts)}편** 분해 완료")
        
        st.markdown(
            '<div style="margin-top:32px;"></div>'
            '<span class="section-eyebrow">RESULT</span>'
            '<h2 class="section-title" style="margin-bottom:20px;">분해된 시리즈</h2>',
            unsafe_allow_html=True,
        )
        
        for post in posts:
            num = post.get("번호", "?")
            title = post.get("제목", "(제목 없음)")
            msg = post.get("핵심메시지", "")
            kw = post.get("주요키워드", [])
            
            with st.expander(f"#{num:02d}  {title}" if isinstance(num, int) else f"#{num}  {title}"):
                if msg:
                    st.markdown(f"**핵심 메시지** · {msg}")
                if kw:
                    st.markdown(f"**키워드** · {' · '.join(kw)}")
        
        col_dl, _ = st.columns([1, 3])
        with col_dl:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "JSON으로 저장",
                data=json.dumps(posts, ensure_ascii=False, indent=2),
                file_name=f"ebook_split_{timestamp}.json",
                mime="application/json",
                use_container_width=True,
            )


# ============================================================
# 탭 3: 설정
# ============================================================

def tab_settings():
    render_section_header(
        eyebrow="CONFIG",
        title="설정",
        description="API 키 및 모델 정보를 관리합니다. 입력한 키는 본인의 브라우저 세션에만 저장되며 운영자나 다른 사용자가 접근할 수 없습니다.",
    )
    
    col_left, col_right = st.columns([1.5, 1], gap="large")
    
    with col_left:
        st.markdown(
            '<div class="premium-card">'
            '<div class="premium-card-header">'
            '<h3 class="premium-card-title">Anthropic API 키</h3>'
            '<p class="premium-card-subtitle">본인의 키를 직접 사용해주세요</p>'
            '</div>',
            unsafe_allow_html=True,
        )
        
        current_key = st.session_state.get("api_key", "")
        masked = ("•" * 16 + current_key[-4:]) if len(current_key) >= 4 else ""
        
        if masked:
            st.markdown(
                f'<div class="meta-row">'
                f'<div class="meta-item">'
                f'<span class="meta-label">CURRENT KEY</span>'
                f'<span class="meta-value" style="font-family:ui-monospace,monospace;">{masked}</span>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        
        new_key = st.text_input(
            "새 API 키 입력",
            type="password",
            placeholder="sk-ant-...",
            help="키는 브라우저 세션에만 저장됩니다.",
        )
        
        col_save, _ = st.columns([1, 2])
        with col_save:
            if st.button("저장", type="primary", use_container_width=True, key="save_key"):
                if new_key.strip():
                    st.session_state["api_key"] = new_key.strip()
                    st.success("API 키가 저장되었습니다.")
                    st.rerun()
                else:
                    st.warning("키를 입력해주세요.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown(
            '<div class="premium-card">'
            '<div class="premium-card-header">'
            '<h3 class="premium-card-title">API 키 발급 안내</h3>'
            '</div>'
            '<ol style="padding-left:20px; line-height:1.8; color:var(--color-ink-soft); font-size:0.9rem; margin:0;">'
            '<li><a href="https://console.anthropic.com" target="_blank" '
            'style="color:var(--color-gold); text-decoration:none; border-bottom:1px solid var(--color-gold);">console.anthropic.com</a> 접속 후 로그인</li>'
            '<li>좌측 메뉴 <strong>API Keys</strong> 클릭</li>'
            '<li><strong>Create Key</strong> 클릭 후 이름 입력</li>'
            '<li>발급된 키 (sk-ant-...) 복사 후 위에 붙여넣기</li>'
            '<li><strong>Plans & Billing</strong>에서 결제 카드 등록 필수</li>'
            '</ol>'
            '</div>',
            unsafe_allow_html=True,
        )
    
    with col_right:
        st.markdown(
            f'<div class="premium-card">'
            f'<div class="premium-card-header">'
            f'<h3 class="premium-card-title">시스템 정보</h3>'
            f'</div>'
            f'<div class="meta-row" style="margin-top:0; border-top:none; padding-top:0;">'
            f'<div class="meta-item">'
            f'<span class="meta-label">MODEL</span>'
            f'<span class="meta-value">{MODEL_NAME}</span>'
            f'</div></div>'
            f'<div class="meta-row" style="border-top:none; padding-top:0;">'
            f'<div class="meta-item">'
            f'<span class="meta-label">VERSION</span>'
            f'<span class="meta-value">v2.1.0</span>'
            f'</div></div>'
            f'<div class="meta-row" style="border-top:none; border-bottom:none; padding-top:0;">'
            f'<div class="meta-item">'
            f'<span class="meta-label">BUILD</span>'
            f'<span class="meta-value">Premium UI</span>'
            f'</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        
        # 로드된 SKILL
        if SKILL_DIR.exists():
            files = sorted(f.name for f in SKILL_DIR.glob("*.md"))
            skill_list_html = "".join(
                f'<div style="font-family:ui-monospace,monospace; font-size:0.8rem; '
                f'color:var(--color-ink-soft); padding:4px 0; '
                f'border-bottom:1px solid var(--color-line-soft);">{f}</div>'
                for f in files
            )
            st.markdown(
                f'<div class="premium-card">'
                f'<div class="premium-card-header">'
                f'<h3 class="premium-card-title">로드된 SKILL</h3>'
                f'<p class="premium-card-subtitle">{len(files)}개 카테고리 패턴</p>'
                f'</div>'
                f'{skill_list_html}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ============================================================
# 메인
# ============================================================

def main():
    inject_css()
    render_brand_header()
    
    # API 키 없을 때 안내
    if not st.session_state.get("api_key"):
        try:
            has_secret = bool(st.secrets.get("ANTHROPIC_API_KEY", ""))
        except Exception:
            has_secret = False
        
        if not has_secret:
            st.markdown(
                '<div style="background:var(--color-ivory-soft); border:1px solid var(--color-line-soft);'
                'border-left:3px solid var(--color-gold); border-radius:4px; padding:16px 20px; '
                'margin:24px 0; font-size:0.9rem; color:var(--color-ink-soft);">'
                '시작하려면 <strong>설정</strong> 탭에서 본인의 Anthropic API 키를 입력해주세요. '
                '키는 본인의 브라우저 세션에만 저장됩니다.'
                '</div>',
                unsafe_allow_html=True,
            )
    
    tab1, tab2, tab3 = st.tabs(["블로그 작성", "전자책 분해", "설정"])
    
    with tab1:
        tab_blog_writer()
    
    with tab2:
        tab_ebook_splitter()
    
    with tab3:
        tab_settings()


if __name__ == "__main__":
    main()
