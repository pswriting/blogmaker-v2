"""
BlogMaker - 네이버 블로그 자동 작성 도구
Streamlit + Claude API + Openverse(무료 사진)

실행:
    streamlit run app.py
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Iterator

import requests
import streamlit as st

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None  # type: ignore


# ────────────────────────────────────────────────────────────────────
# 경로 / 상수
# ────────────────────────────────────────────────────────────────────

APP_DIR = Path(__file__).parent.resolve()
SKILLS_DIR = APP_DIR / "skills"
CONFIG_PATH = APP_DIR / ".config.json"

CATEGORIES = {
    "it_review": "💻 IT/디지털 리뷰",
    "finance": "💰 금융/재테크",
    "food_travel": "🍜 맛집/여행",
    "health_emotion": "🌿 건강/감정",
    "education": "📚 교육/학습",
    "career": "💼 취업/이직",
    "admin_legal": "📋 행정/법률/생활",
    "home_appliance": "🏠 가전/생활용품",
    "marketing": "📈 마케팅/창업/부업",
}

STAGES = [
    ("intro", "🌱 도입 — 공감·문제 제기"),
    ("transition", "🔄 전환 — 본인 경험으로 연결"),
    ("body", "📖 본론 — 핵심 정보·팁 (가장 비중 큼)"),
    ("emphasis", "⭐ 강조 — 핵심 포인트 재강조"),
    ("closing", "🤗 클로징 — 따뜻한 마무리 + 해시태그"),
]

MODELS = {
    "claude-haiku-4-5-20251001": "Haiku 4.5 (빠르고 저렴 · 추천)",
    "claude-sonnet-4-6": "Sonnet 4.6 (균형)",
    "claude-opus-4-6": "Opus 4.6 (최고 품질, 느림)",
}

OPENVERSE_ENDPOINTS = [
    "https://api.openverse.org/v1/images/",
    "https://api.openverse.engineering/v1/images/",
]


# ────────────────────────────────────────────────────────────────────
# 설정 저장 / 로드 (로컬 파일)
# ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_skill(category_key: str) -> str:
    """마스터 + 카테고리 SKILL을 합쳐서 반환."""
    master = (SKILLS_DIR / "_master.md").read_text(encoding="utf-8")
    cat_path = SKILLS_DIR / f"{category_key}.md"
    if cat_path.exists():
        cat = cat_path.read_text(encoding="utf-8")
    else:
        cat = ""
    return master + "\n\n---\n\n" + cat


# ────────────────────────────────────────────────────────────────────
# 프롬프트 빌더
# ────────────────────────────────────────────────────────────────────

STAGE_INSTRUCTIONS = {
    "intro": (
        "지금부터 [도입] 단계만 작성해. 3~5문단. "
        "독자의 공감을 끌어내는 질문 후킹 또는 본인 상황 묘사로 시작. "
        "메인 키워드를 자연스럽게 1~2회 포함. "
        "도입 마무리에 사진 마커 1개 박기: [[IMG: 영문 검색어]]"
    ),
    "transition": (
        "이어서 [전환] 단계만 작성해. 2~4문단. "
        "도입에서 제기한 문제와 본론을 잇는 다리 역할. "
        "'그래서 제가 ~해봤어요' 같은 본인 행동/경험으로 연결. "
        "앞에서 작성한 도입과 자연스럽게 이어져야 함."
    ),
    "body": (
        "[본론] 단계 작성. 5~8문단. 전체 글에서 가장 비중 큰 부분. "
        "사용자가 제공한 경험·정보·팁을 곳곳에 녹여 풀어쓰기. "
        "본론 중간쯤에 사진 마커 1개: [[IMG: 영문 검색어]]"
    ),
    "emphasis": (
        "[강조] 단계 작성. 2~3문단. "
        "본론에서 가장 중요한 포인트 1~2개를 다시 짚으면서 강조. "
        "'특히 이건 꼭 기억하세요', '제가 가장 강조하고 싶은 건' 같은 톤."
    ),
    "closing": (
        "[클로징] 단계 작성. 2~3문단. "
        "따뜻한 마무리. 댓글·공감 유도. 본인의 다음 계획 살짝 언급해도 OK. "
        "클로징 직전에 사진 마커 1개: [[IMG: 영문 검색어]] "
        "마지막 줄에 해시태그 5~8개를 '#키워드' 형식, 한 줄로, 띄어쓰기로 구분해서 첨부."
    ),
}


def build_system_prompt(category_key: str) -> list:
    """캐싱 가능한 system 프롬프트 (skill 부분만 캐시)."""
    skill = load_skill(category_key)
    return [
        {
            "type": "text",
            "text": skill,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def build_user_message(
    stage: str,
    topic: str,
    keyword: str,
    user_experience: str,
    previous_text: str,
) -> str:
    parts = [
        f"## 주제\n{topic}",
        f"## 메인 키워드\n{keyword}" if keyword else "",
        f"## 본인 경험·정보·팁\n{user_experience}" if user_experience else "",
    ]
    if previous_text:
        parts.append(f"## 지금까지 작성된 글\n{previous_text}")
    parts.append(f"## 이번 단계 지시\n{STAGE_INSTRUCTIONS[stage]}")
    parts.append(
        "**중요**: 단계 제목(예: '도입', '본론')은 본문에 쓰지 마. "
        "본문만 자연스럽게 이어 써. 마크다운 헤더(#, ##)도 쓰지 마."
    )
    return "\n\n".join(p for p in parts if p)


# ────────────────────────────────────────────────────────────────────
# Anthropic 호출 (스트리밍)
# ────────────────────────────────────────────────────────────────────

def stream_stage(
    client: Anthropic,
    model: str,
    category_key: str,
    stage: str,
    topic: str,
    keyword: str,
    user_experience: str,
    previous_text: str,
) -> Iterator[str]:
    system = build_system_prompt(category_key)
    user_msg = build_user_message(stage, topic, keyword, user_experience, previous_text)

    with client.messages.stream(
        model=model,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ────────────────────────────────────────────────────────────────────
# Openverse 사진 검색
# ────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=3600)
def search_openverse(query: str) -> dict | None:
    """첫 번째 사진 결과를 반환. 실패하면 None."""
    if not query:
        return None
    headers = {"User-Agent": "BlogMaker/1.0 (personal)"}
    params = {
        "q": query,
        "page_size": 5,
        "license_type": "all-cc",
        "mature": "false",
    }
    for endpoint in OPENVERSE_ENDPOINTS:
        try:
            r = requests.get(endpoint, params=params, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            results = data.get("results", [])
            if not results:
                continue
            first = results[0]
            return {
                "url": first.get("url") or first.get("thumbnail"),
                "thumb": first.get("thumbnail") or first.get("url"),
                "creator": first.get("creator") or "Unknown",
                "source": first.get("source") or "Openverse",
                "license": first.get("license") or "cc",
                "foreign_url": first.get("foreign_landing_url") or "",
            }
        except Exception:
            continue
    return None


# ────────────────────────────────────────────────────────────────────
# 본문 후처리: 사진 마커를 실제 이미지 마크다운으로 치환
# ────────────────────────────────────────────────────────────────────

IMG_MARKER_RE = re.compile(r"\[\[IMG:\s*([^\]]+?)\s*\]\]")


def replace_image_markers(text: str) -> tuple[str, list[dict]]:
    """[[IMG: query]] 마커를 마크다운 이미지로 치환. 사용된 사진 메타 리스트도 반환."""
    used = []

    def repl(match: re.Match) -> str:
        query = match.group(1).strip()
        photo = search_openverse(query)
        if not photo:
            return f"\n\n> 📷 *이미지 자리: {query} (검색 결과 없음)*\n\n"
        used.append({"query": query, **photo})
        credit = f"Photo by {photo['creator']} via {photo['source']} (CC)"
        return (
            f"\n\n![{query}]({photo['url']})\n"
            f"*{credit}*\n\n"
        )

    return IMG_MARKER_RE.sub(repl, text), used


# ────────────────────────────────────────────────────────────────────
# Streamlit UI
# ────────────────────────────────────────────────────────────────────

def init_state() -> None:
    if "stages_text" not in st.session_state:
        st.session_state.stages_text = {key: "" for key, _ in STAGES}
    if "current_stage_idx" not in st.session_state:
        st.session_state.current_stage_idx = 0
    if "final_text" not in st.session_state:
        st.session_state.final_text = ""
    if "used_photos" not in st.session_state:
        st.session_state.used_photos = []


def reset_stages() -> None:
    st.session_state.stages_text = {key: "" for key, _ in STAGES}
    st.session_state.current_stage_idx = 0
    st.session_state.final_text = ""
    st.session_state.used_photos = []


def assemble_text() -> str:
    return "\n\n".join(st.session_state.stages_text[key].strip() for key, _ in STAGES).strip()


def page_settings() -> None:
    st.header("⚙️ 설정")
    cfg = load_config()

    st.subheader("1) Anthropic API 키")
    current_key = cfg.get("anthropic_api_key", "")
    display_key = (
        f"✅ 저장됨 (`...{current_key[-4:]}`)" if current_key else "⚠️ 미설정"
    )
    st.markdown(f"**현재 상태:** {display_key}")
    st.markdown(
        "키 발급: [console.anthropic.com/settings/keys]"
        "(https://console.anthropic.com/settings/keys)"
    )

    new_key = st.text_input(
        "새 API 키 (sk-ant-...)",
        value="",
        type="password",
        placeholder="sk-ant-...",
    )
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("키 저장", type="primary", use_container_width=True):
            if new_key.startswith("sk-ant-"):
                cfg["anthropic_api_key"] = new_key
                save_config(cfg)
                st.success("저장 완료. 다른 탭으로 이동하세요.")
                st.rerun()
            else:
                st.error("올바른 키 형식이 아니에요 (sk-ant-...로 시작해야 함)")
    with col2:
        if st.button("키 삭제", use_container_width=True):
            cfg.pop("anthropic_api_key", None)
            save_config(cfg)
            st.success("삭제됨.")
            st.rerun()

    st.divider()

    st.subheader("2) 모델 선택")
    current_model = cfg.get("model", "claude-haiku-4-5-20251001")
    model = st.selectbox(
        "사용할 Claude 모델",
        options=list(MODELS.keys()),
        format_func=lambda k: MODELS[k],
        index=list(MODELS.keys()).index(current_model)
        if current_model in MODELS
        else 0,
    )
    if model != current_model:
        cfg["model"] = model
        save_config(cfg)
        st.success(f"모델 변경: {MODELS[model]}")

    st.divider()

    st.subheader("3) 사진 옵션")
    use_photos = st.checkbox(
        "Openverse 사진 자동 삽입 (무료, API 키 불필요)",
        value=cfg.get("use_photos", True),
    )
    if use_photos != cfg.get("use_photos", True):
        cfg["use_photos"] = use_photos
        save_config(cfg)


def page_blog_writer() -> None:
    cfg = load_config()
    api_key = cfg.get("anthropic_api_key", "")
    model = cfg.get("model", "claude-haiku-4-5-20251001")

    if not api_key:
        st.warning("⚠️ 먼저 **설정** 탭에서 Anthropic API 키를 저장해주세요.")
        return

    if Anthropic is None:
        st.error("anthropic 패키지가 설치되지 않았어요. `pip install anthropic` 실행하세요.")
        return

    client = Anthropic(api_key=api_key)

    # 입력 영역
    st.header("✍️ 블로그 작성")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        category_key = st.selectbox(
            "카테고리",
            options=list(CATEGORIES.keys()),
            format_func=lambda k: CATEGORIES[k],
        )
    with col_b:
        keyword = st.text_input(
            "메인 키워드 (검색 노출용)",
            placeholder="예: 무지출 챌린지, 갤럭시 S25 후기",
        )

    topic = st.text_input(
        "주제 (한 줄)",
        placeholder="예: 한 달 무지출 챌린지 도전 후기와 실패한 이유",
    )
    user_experience = st.text_area(
        "본인 경험 / 정보 / 팁 (최대한 구체적으로)",
        height=160,
        placeholder=(
            "여기 적은 내용이 본문 곳곳에 녹아 들어가요.\n"
            "예: 4주 동안 외식 0회 / 첫 주는 의외로 쉬웠는데 둘째 주부터 폭발 / "
            "결국 친구 생일에 무너짐 / 통장에 17만원 모임 / 다시 도전한다면 주말은 예외 두기"
        ),
    )

    # 액션 버튼
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        gen_button = st.button(
            "🚀 5단 골격 단계별 생성",
            type="primary",
            use_container_width=True,
            disabled=not (topic and user_experience),
        )
    with col2:
        if st.button("🔄 초기화", use_container_width=True):
            reset_stages()
            st.rerun()
    with col3:
        next_stage = st.button(
            "▶️ 다음 단계",
            use_container_width=True,
            disabled=st.session_state.current_stage_idx >= len(STAGES),
        )

    # 단계별 표시
    st.divider()

    if gen_button:
        reset_stages()
        _run_stage(client, model, category_key, topic, keyword, user_experience, 0)
        st.rerun()

    if next_stage:
        idx = st.session_state.current_stage_idx
        if idx < len(STAGES):
            _run_stage(
                client, model, category_key, topic, keyword, user_experience, idx
            )
            st.rerun()

    # 단계별 결과 표시
    for i, (key, label) in enumerate(STAGES):
        text = st.session_state.stages_text[key]
        if text:
            with st.expander(label, expanded=(i == st.session_state.current_stage_idx - 1)):
                st.markdown(text)

    # 합본 + 사진 삽입
    if all(st.session_state.stages_text[k] for k, _ in STAGES):
        st.divider()
        st.subheader("📄 최종 합본")

        use_photos = cfg.get("use_photos", True)
        combined = assemble_text()

        if use_photos and "[[IMG:" in combined and not st.session_state.final_text:
            with st.spinner("🖼 Openverse에서 사진 검색 중..."):
                final, used = replace_image_markers(combined)
                st.session_state.final_text = final
                st.session_state.used_photos = used
        elif not st.session_state.final_text:
            # 사진 안 쓸 때는 마커 그대로 두거나 제거
            st.session_state.final_text = IMG_MARKER_RE.sub("", combined)

        st.markdown(st.session_state.final_text)

        col_x, col_y = st.columns([1, 1])
        with col_x:
            st.download_button(
                "💾 .md 파일로 다운로드",
                data=st.session_state.final_text,
                file_name=f"blog_{int(time.time())}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with col_y:
            st.code(st.session_state.final_text, language="markdown")

        if st.session_state.used_photos:
            with st.expander(f"🖼 사용된 사진 크레딧 ({len(st.session_state.used_photos)}개)"):
                for p in st.session_state.used_photos:
                    st.markdown(
                        f"- **{p['query']}** — by {p['creator']} via "
                        f"[{p['source']}]({p.get('foreign_url', '')}) (CC {p['license']})"
                    )


def _run_stage(
    client: Anthropic,
    model: str,
    category_key: str,
    topic: str,
    keyword: str,
    user_experience: str,
    idx: int,
) -> None:
    """idx번째 단계 생성. 스트리밍으로 화면에 띄우면서 session_state에 저장."""
    if idx >= len(STAGES):
        return

    stage_key, stage_label = STAGES[idx]
    previous_text = "\n\n".join(
        st.session_state.stages_text[k]
        for k, _ in STAGES[:idx]
        if st.session_state.stages_text[k]
    )

    placeholder = st.empty()
    placeholder.info(f"⏳ {stage_label} 생성 중...")

    box = st.empty()
    accumulated = ""
    try:
        for chunk in stream_stage(
            client,
            model,
            category_key,
            stage_key,
            topic,
            keyword,
            user_experience,
            previous_text,
        ):
            accumulated += chunk
            box.markdown(accumulated + "▌")
    except Exception as e:
        placeholder.error(f"❌ 오류: {e}")
        return

    box.markdown(accumulated)
    placeholder.success(f"✅ {stage_label} 완료")
    st.session_state.stages_text[stage_key] = accumulated.strip()
    st.session_state.current_stage_idx = idx + 1
    # 단계 사이에 살짝 쉼
    time.sleep(0.3)


# ────────────────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────────────────

def main() -> None:
    st.set_page_config(
        page_title="BlogMaker — 네이버 블로그 자동 작성",
        page_icon="📝",
        layout="wide",
    )
    init_state()

    st.title("📝 BlogMaker")
    st.caption("Claude API로 네이버 블로그 스타일 글을 자동 생성합니다 · 5단 골격 + 카테고리 SKILL + 무료 사진")

    tab1, tab2 = st.tabs(["✍️ 블로그 작성", "⚙️ 설정"])
    with tab1:
        page_blog_writer()
    with tab2:
        page_settings()


if __name__ == "__main__":
    main()
