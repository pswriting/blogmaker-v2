"""
BlogMaker v2.1 - 네이버 상위 블로그 패턴 학습 AI 블로그 자동 생성기
@author: CashMaker (cashmaker.co.kr)
@version: 2.1.0

v2 → v2.1 변경점
- (P1) st.secrets 안전 처리 (secrets.toml 미존재 시 크래시 방지)
- (P1) 생성 결과 session_state 보존 (재실행 시 결과 유지)
- (P1) Anthropic prompt caching 적용 (system 토큰 재호출 비용 절감)
- (P2) 단계 실패 시 즉시 중단 + 재시도 안내
- (P2) PDF extract_text None 가드
- (P2) load_skill @st.cache_data 적용
- (P2) 본론 max_tokens 상향 + stop_reason 체크
- (P3) 설정 탭에 모델 선택 UI
- (NEW) 주제별 네이버 검색 결과 실시간 크롤링 → 패턴 컨텍스트 주입
- (NEW) Pollinations.ai 무료 이미지 자동 생성 (썸네일 + 본문 이미지)
- (NEW) 통합 워크플로우 탭: 전자책 → 분해 → 글 + 썸네일 + 이미지 한 번에
"""

from __future__ import annotations

import io
import json
import re
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import requests
import streamlit as st

# ============================================================
# 페이지 설정
# ============================================================

PAGE_CONFIG = {
    "page_title": "BlogMaker v2.1",
    "page_icon": "📝",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}
st.set_page_config(**PAGE_CONFIG)

# ============================================================
# 상수
# ============================================================

DEFAULT_MODEL = "claude-sonnet-4-6"
AVAILABLE_MODELS = {
    "claude-sonnet-4-6": "Sonnet 4.6 (균형형, 추천)",
    "claude-opus-4-7": "Opus 4.7 (최고 성능, 비용 큼)",
    "claude-haiku-4-5-20251001": "Haiku 4.5 (저비용, 빠름)",
}

SKILL_DIR = Path(__file__).parent.parent / "skills"

CATEGORY_MAP = {
    "IT/리뷰": "it_review.md",
    "행정/법무": "admin_legal.md",
    "교육/육아": "education.md",
    "재테크/투자": "finance.md",
    "취업/커리어": "career.md",
    "맛집/여행": "food_travel.md",
    "가전/리빙": "home_appliance.md",
    "건강/감성": "health_emotion.md",
    "마케팅/1인사업": "marketing.md",
}

STAGE_NAMES = ["1. 도입", "2. 전환", "3. 본론", "4. 강조", "5. 클로징"]

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

# ============================================================
# Secrets / 모델 선택
# ============================================================

def safe_secrets_get(key: str, default: str = "") -> str:
    """st.secrets 접근 안전 래퍼.
    secrets.toml 파일이 없으면 StreamlitSecretNotFoundError가 발생할 수 있음.
    """
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def get_active_model() -> str:
    return st.session_state.get("model_name", DEFAULT_MODEL)


def get_api_client() -> Optional[anthropic.Anthropic]:
    api_key = st.session_state.get("api_key") or safe_secrets_get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("⚠️ Anthropic API 키가 설정되지 않았습니다. '설정' 탭에서 입력해주세요.")
        return None
    return anthropic.Anthropic(api_key=api_key)


# ============================================================
# 스킬 로딩 (캐싱)
# ============================================================

@st.cache_data(show_spinner=False)
def load_skill(filename: str) -> str:
    path = SKILL_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_system_prompt(
    category: str,
    user_facts: str = "",
    pattern_context: str = "",
) -> str:
    master = load_skill("_master.md")
    category_skill = load_skill(CATEGORY_MAP[category])

    if not master or not category_skill:
        st.error(f"SKILL 파일을 찾을 수 없습니다: {SKILL_DIR}")
        return ""

    facts_section = f"\n\n## 사용자 제공 사실/경험\n{user_facts}\n" if user_facts.strip() else ""
    pattern_section = (
        f"\n\n## 추가 학습: 동일 주제 네이버 상위 블로그 실시간 분석\n{pattern_context}\n"
        if pattern_context.strip()
        else ""
    )

    return f"""{master}

---

# 현재 카테고리: {category}

{category_skill}
{facts_section}
{pattern_section}

---

위 모든 규칙을 엄수하여 한국어 네이버 블로그 글을 작성한다.
"""


# ============================================================
# Claude API 호출 (prompt caching 적용)
# ============================================================

def call_claude(
    client: anthropic.Anthropic,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2000,
    use_cache: bool = True,
) -> str:
    """Claude API 호출. system은 ephemeral cache 처리해 비용 절감."""
    try:
        if use_cache and system_prompt.strip():
            system_blocks = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ]
        else:
            system_blocks = system_prompt

        response = client.messages.create(
            model=get_active_model(),
            max_tokens=max_tokens,
            system=system_blocks,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")

        if response.stop_reason == "max_tokens":
            st.warning(
                f"⚠️ 응답이 max_tokens({max_tokens})에 도달해 잘렸을 수 있습니다. "
                "설정에서 max_tokens를 올리거나 본론을 분할해 다시 생성해보세요."
            )
        return text
    except anthropic.APIError as e:
        st.error(f"API 오류: {e}")
        return ""
    except Exception as e:
        st.error(f"알 수 없는 오류: {e}")
        return ""


# ============================================================
# 네이버 검색 결과 실시간 크롤링 (패턴 트레이닝)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def crawl_naver_blog_search(keyword: str, max_results: int = 5) -> list[dict]:
    """네이버 모바일 검색 결과에서 블로그 상위 글의 제목/요약/URL 추출.

    모바일 페이지(m.search.naver.com)가 데스크탑 대비 HTML이 가볍고 파싱이 안정적.
    실패 시 빈 리스트 반환 (호출 측에서 graceful fallback).
    """
    if not keyword.strip():
        return []

    encoded = urllib.parse.quote(keyword)
    url = f"https://m.search.naver.com/search.naver?where=m_blog&query={encoded}"

    try:
        resp = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                    "Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        html = resp.text
    except Exception:
        return []

    # 모바일 블로그 검색 결과 패턴: 제목 + 본문 미리보기
    # 안정적인 파싱을 위해 단순 정규식 (실패 허용)
    results: list[dict] = []

    # 제목 + 링크 추출
    title_pattern = re.compile(
        r'<a[^>]+class="[^"]*api_txt_lines[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        re.DOTALL,
    )
    desc_pattern = re.compile(
        r'<div class="[^"]*api_txt_lines\s+dsc_txt[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL,
    )

    def clean(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"&[a-zA-Z]+;", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    titles = title_pattern.findall(html)
    descs = desc_pattern.findall(html)

    for i, (href, raw_title) in enumerate(titles[:max_results]):
        title = clean(raw_title)
        desc = clean(descs[i]) if i < len(descs) else ""
        if not title:
            continue
        results.append({"title": title, "url": href, "snippet": desc})

    # Fallback: 위 패턴이 실패하면 blog.naver.com 링크를 광범위하게 수집
    if not results:
        fallback = re.findall(
            r'href="(https?://[^"]*blog\.naver\.com[^"]*)"[^>]*>([^<]{5,120})</a>',
            html,
        )
        seen = set()
        for href, raw in fallback:
            title = clean(raw)
            if not title or href in seen:
                continue
            seen.add(href)
            results.append({"title": title, "url": href, "snippet": ""})
            if len(results) >= max_results:
                break

    return results


def build_pattern_context(crawled: list[dict]) -> str:
    """크롤링 결과를 시스템 프롬프트에 주입할 컨텍스트 텍스트로 변환."""
    if not crawled:
        return ""
    lines = [
        "다음은 동일 주제로 네이버 검색 상위에 노출 중인 블로그 글들의 제목·요약이다.",
        "구조, 어미, 후킹, 키워드 배치를 참고하되 표현은 절대 복제하지 말 것.",
        "",
    ]
    for i, post in enumerate(crawled, 1):
        lines.append(f"[{i}] {post['title']}")
        if post.get("snippet"):
            lines.append(f"    요약: {post['snippet'][:200]}")
    return "\n".join(lines)


# ============================================================
# 5단 골격 단계별 생성
# ============================================================

def generate_stage(
    client: anthropic.Anthropic,
    system_prompt: str,
    stage: int,
    context: dict,
) -> str:
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
- 카테고리별 시각 패턴 적용. 이미지 자리는 정확히 다음 형식으로 표시:
  [📷 IMG: <간단한 한글 설명> | PROMPT: <영문 이미지 생성 프롬프트 (40단어 이내, 사진 스타일 명시)>]
- 본문에 위 이미지 자리 마커를 최소 2개, 최대 4개 삽입
- 구체 숫자/날짜/제품명 최소 3개 이상 포함
- 본론만! 도입/전환/강조/클로징 다시 쓰지 말 것
""",
        4: f"""주제: {topic}

이전 단계 (도입+전환+본론):
{previous}

위 본론의 핵심을 **4단계 (강조)**로 한 번 더 짚는다.
- 1~3문장
- 핵심 한 줄을 굵은 글씨 또는 컬러 박스로 표현 (마크업 사용: **굵은글씨** 또는 > 인용)
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

    max_tokens = 3500 if stage == 3 else 1000
    return call_claude(client, system_prompt, stage_prompts[stage], max_tokens=max_tokens)


def generate_full_post(
    client: anthropic.Anthropic,
    category: str,
    topic: str,
    user_facts: str,
    use_naver_crawl: bool,
    on_stage: Optional[callable] = None,
) -> dict:
    """전체 5단 글 생성. 결과 + 메타데이터 dict 반환."""
    pattern_context = ""
    crawled: list[dict] = []
    if use_naver_crawl:
        crawled = crawl_naver_blog_search(topic, max_results=5)
        if not crawled:
            st.info(
                "ℹ️ 네이버 실시간 크롤링 결과가 비어 있어 기본 SKILL만 적용해 생성합니다. "
                "(네이버 페이지 구조 변경 또는 차단 가능성)"
            )
        pattern_context = build_pattern_context(crawled)

    system_prompt = build_system_prompt(category, user_facts, pattern_context)
    if not system_prompt:
        return {}

    ctx = {"topic": topic, "user_facts": user_facts, "previous_stages": ""}
    stages: list[tuple[str, str]] = []

    for i, stage_name in enumerate(STAGE_NAMES, 1):
        output = generate_stage(client, system_prompt, i, ctx)
        if not output.strip():
            st.error(f"❌ {stage_name} 생성 실패. 중단합니다. 잠시 후 다시 시도하거나 모델을 바꿔보세요.")
            return {}
        stages.append((stage_name, output))
        ctx["previous_stages"] += f"\n\n{output}"
        if on_stage:
            on_stage(i, stage_name, output)

    full_post = "\n\n".join(o for _, o in stages)
    return {
        "category": category,
        "topic": topic,
        "user_facts": user_facts,
        "stages": stages,
        "full_post": full_post,
        "crawled": crawled,
        "pattern_context": pattern_context,
    }


# ============================================================
# 이미지 자리 마커 파싱 + Pollinations 생성
# ============================================================

IMG_MARKER_RE = re.compile(
    r"\[📷\s*IMG:\s*(?P<desc>.+?)\s*\|\s*PROMPT:\s*(?P<prompt>.+?)\]",
    re.DOTALL,
)


def extract_image_markers(body: str) -> list[dict]:
    """본문에서 이미지 자리 마커 추출."""
    markers = []
    for m in IMG_MARKER_RE.finditer(body):
        markers.append({
            "desc": m.group("desc").strip(),
            "prompt": m.group("prompt").strip(),
            "raw": m.group(0),
        })
    return markers


def pollinations_image_url(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    seed: Optional[int] = None,
    model: str = "flux",
) -> str:
    """Pollinations.ai 이미지 URL 생성."""
    encoded = urllib.parse.quote(prompt)
    params = f"width={width}&height={height}&nologo=true&model={model}"
    if seed is not None:
        params += f"&seed={seed}"
    return f"{POLLINATIONS_BASE}{encoded}?{params}"


def replace_markers_with_images(body: str, markers: list[dict], urls: list[str]) -> str:
    """본문의 마커를 마크다운 이미지 링크로 치환."""
    out = body
    for marker, url in zip(markers, urls):
        md_img = f"![{marker['desc']}]({url})"
        out = out.replace(marker["raw"], md_img, 1)
    return out


# ============================================================
# 썸네일 추천
# ============================================================

def suggest_thumbnail(
    client: anthropic.Anthropic,
    topic: str,
    category: str,
    full_post: str,
) -> dict:
    """주제·카테고리·본문 기반 썸네일 컨셉 + Pollinations 프롬프트 생성."""
    system = """당신은 네이버 블로그 썸네일 디자인 전문가다.
검색 결과에서 눈에 띄는 썸네일의 핵심 요소(텍스트 카피, 배경 컬러, 비주얼 모티프)를 잡아낸다."""

    user = f"""아래 블로그 글의 썸네일을 추천해라.

주제: {topic}
카테고리: {category}
본문 일부 (앞 800자):
---
{full_post[:800]}
---

다음 JSON만 출력 (다른 설명 금지):
{{
  "thumbnail_text": "썸네일에 들어갈 짧은 카피 (한국어 8자 이내 권장)",
  "background_color": "추천 배경 컬러 (한국어 + HEX 코드)",
  "visual_motif": "핵심 비주얼 모티프 (한국어 한 줄)",
  "image_prompt": "Pollinations.ai에 넣을 영문 이미지 생성 프롬프트 (50단어 이내, 한국 블로그 썸네일 스타일, no text in image)"
}}
"""
    raw = call_claude(client, system, user, max_tokens=600, use_cache=False)
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        return {}
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return {}


# ============================================================
# 전자책 분해
# ============================================================

def split_ebook_to_posts(
    client: anthropic.Anthropic,
    ebook_text: str,
    num_posts: int,
    category: str,
) -> list[dict]:
    system = """당신은 한국 디지털 콘텐츠 기획 전문가다.
전자책의 핵심 내용을 추출해 네이버 블로그 시리즈로 분해하는 일을 한다."""

    prompt = f"""다음 전자책 내용을 분석해 **{num_posts}편의 블로그 글 주제**로 분해해라.

전자책 카테고리: {category}

전자책 내용:
---
{ebook_text[:20000]}
---

출력 형식 (JSON 배열만 출력, 다른 설명 금지):
[
  {{
    "번호": 1,
    "제목": "구체적인 블로그 글 제목",
    "핵심메시지": "이 글에서 다룰 한 가지 핵심",
    "주요키워드": ["키워드1", "키워드2", "키워드3"]
  }}
]

규칙:
- {num_posts}편 정확히 생성
- 각 글이 독립적으로 읽혀도 가치가 있어야 함
- 시리즈 흐름 유지 (난이도/주제 점진적 심화)
- 제목은 클릭하고 싶게, 구체적으로
"""
    response = call_claude(client, system, prompt, max_tokens=4000, use_cache=False)
    json_match = re.search(r"\[.*\]", response, re.DOTALL)
    if not json_match:
        st.error("JSON 형식으로 응답이 오지 않았습니다. 다시 시도해주세요.")
        return []
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        st.error(f"JSON 파싱 실패: {e}")
        return []


def extract_text_from_upload(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="ignore")
    elif name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except ImportError:
            st.error("PDF 처리를 위해 `pip install pypdf` 가 필요합니다.")
            return ""
        except Exception as e:
            st.error(f"PDF 파싱 오류: {e}")
            return ""
    elif name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(data))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            st.error("DOCX 처리를 위해 `pip install python-docx` 가 필요합니다.")
            return ""
        except Exception as e:
            st.error(f"DOCX 파싱 오류: {e}")
            return ""
    else:
        st.error(f"지원하지 않는 파일 형식입니다: {name}")
        return ""


# ============================================================
# 결과 렌더링 헬퍼
# ============================================================

def render_post_result(post: dict, key_prefix: str = "post") -> None:
    """post dict (full_post, stages, crawled, thumbnail?, image_urls?)를 화면에 그린다."""
    if post.get("thumbnail"):
        thumb = post["thumbnail"]
        st.markdown("### 🎨 추천 썸네일")
        col_t1, col_t2 = st.columns([1, 1])
        with col_t1:
            if thumb.get("image_url"):
                st.image(thumb["image_url"], caption=thumb.get("thumbnail_text", ""), width=400)
        with col_t2:
            st.markdown(f"**카피**: {thumb.get('thumbnail_text', '')}")
            st.markdown(f"**배경 컬러**: {thumb.get('background_color', '')}")
            st.markdown(f"**비주얼 모티프**: {thumb.get('visual_motif', '')}")
            with st.expander("이미지 생성 프롬프트"):
                st.code(thumb.get("image_prompt", ""))
        st.divider()

    if post.get("crawled"):
        with st.expander(f"🔍 참고된 네이버 상위 결과 {len(post['crawled'])}편"):
            for i, c in enumerate(post["crawled"], 1):
                st.markdown(f"**[{i}] [{c['title']}]({c['url']})**")
                if c.get("snippet"):
                    st.caption(c["snippet"][:200])

    st.markdown("### 📝 본문")
    rendered_body = post.get("rendered_body", post.get("full_post", ""))
    st.markdown(rendered_body)

    if post.get("image_urls"):
        with st.expander(f"🖼 본문 이미지 {len(post['image_urls'])}개"):
            for i, (marker, url) in enumerate(zip(post.get("markers", []), post["image_urls"]), 1):
                st.markdown(f"**{i}. {marker['desc']}**")
                st.image(url, width=400)
                st.caption(f"프롬프트: {marker['prompt']}")

    with st.expander("📋 텍스트 전체 (복사용)", expanded=False):
        st.text_area(
            "복사해서 네이버 블로그에 붙여넣으세요",
            value=rendered_body,
            height=400,
            key=f"{key_prefix}_textarea",
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_cat = post.get("category", "post").replace("/", "_")
    st.download_button(
        "💾 .md 파일로 다운로드",
        data=rendered_body,
        file_name=f"blogpost_{safe_cat}_{timestamp}.md",
        mime="text/markdown",
        key=f"{key_prefix}_download",
    )


# ============================================================
# 탭 1: 단일 블로그 작성
# ============================================================

def tab_blog_writer():
    st.header("📝 블로그 글 자동 생성")
    st.caption("네이버 상위 블로그 9편 분석 + 실시간 검색 결과 학습 · 5단 골격 단계별 생성")

    col1, col2 = st.columns([1, 2])

    with col1:
        category = st.selectbox(
            "카테고리 선택",
            list(CATEGORY_MAP.keys()),
            help="카테고리에 따라 어미/후킹/시각 패턴이 자동 분기됩니다.",
            key="t1_category",
        )
        st.divider()
        st.markdown(f"**선택된 카테고리: `{category}`**")
        with st.expander("📖 적용되는 SKILL 미리보기"):
            st.markdown(load_skill(CATEGORY_MAP[category]))

    with col2:
        topic = st.text_input(
            "블로그 주제",
            placeholder="예: 27인치 모니터 LG 32GP750 3개월 사용 후기",
            help="구체적일수록 글이 좋아집니다.",
            key="t1_topic",
        )
        user_facts = st.text_area(
            "본인 경험 / 구체 사실 (선택)",
            placeholder="""예시:
- 2026년 1월 구매, 정가 35만원에서 28만원에 구매
- 이전 사용 모니터: 24인치 삼성 (5년 사용)
- 듀얼 모니터로 사용, 영상편집 작업 위주
- 단점: 스피커 음질이 아쉬움
""",
            height=180,
            key="t1_user_facts",
        )

        col_opt1, col_opt2, col_opt3 = st.columns(3)
        with col_opt1:
            use_naver = st.checkbox("🔍 네이버 상위 글 실시간 학습", value=True, key="t1_use_naver")
        with col_opt2:
            gen_thumb = st.checkbox("🎨 썸네일 추천", value=True, key="t1_gen_thumb")
        with col_opt3:
            gen_img = st.checkbox("🖼 본문 이미지 생성", value=True, key="t1_gen_img")

        st.divider()

        if st.button("✨ 5단 골격 단계별 생성", type="primary", use_container_width=True, key="t1_generate"):
            if not topic.strip():
                st.warning("주제를 입력해주세요.")
                return

            client = get_api_client()
            if not client:
                return

            progress = st.progress(0, text="시작...")
            stage_placeholders = {}

            def on_stage(i, name, output):
                progress.progress(i / 5, text=f"완료: {name}")
                stage_placeholders[i] = (name, output)

            post = generate_full_post(
                client, category, topic, user_facts, use_naver, on_stage=on_stage
            )
            if not post:
                progress.empty()
                return

            # 이미지 마커 추출 + Pollinations URL 생성
            markers: list[dict] = []
            urls: list[str] = []
            if gen_img:
                # 본론(stage 3)에서 마커가 주로 생성됨
                markers = extract_image_markers(post["full_post"])
                urls = [
                    pollinations_image_url(m["prompt"], width=1024, height=768, seed=i)
                    for i, m in enumerate(markers)
                ]

            rendered = (
                replace_markers_with_images(post["full_post"], markers, urls)
                if markers and urls
                else post["full_post"]
            )

            thumb = {}
            if gen_thumb:
                progress.progress(1.0, text="썸네일 추천 중...")
                thumb = suggest_thumbnail(client, topic, category, post["full_post"])
                if thumb and thumb.get("image_prompt"):
                    thumb["image_url"] = pollinations_image_url(
                        thumb["image_prompt"], width=1200, height=900, seed=42
                    )

            progress.progress(1.0, text="완료!")

            post["markers"] = markers
            post["image_urls"] = urls
            post["rendered_body"] = rendered
            post["thumbnail"] = thumb
            st.session_state["t1_last_post"] = post

    # 결과 표시 (session_state 보존)
    if st.session_state.get("t1_last_post"):
        st.divider()
        st.success("✅ 생성 완료")
        render_post_result(st.session_state["t1_last_post"], key_prefix="t1")


# ============================================================
# 탭 2: 전자책 분해
# ============================================================

def tab_ebook_splitter():
    st.header("📚 전자책 → 블로그 시리즈 분해")
    st.caption("Writey 연동 · 전자책 1권을 N편의 블로그 글 주제로 자동 분해")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "전자책 파일 업로드",
            type=["txt", "md", "pdf", "docx"],
            help="PDF/DOCX는 pypdf/python-docx 패키지가 필요합니다.",
            key="t2_uploader",
        )
        category = st.selectbox(
            "전자책 카테고리", list(CATEGORY_MAP.keys()), key="t2_category"
        )
        num_posts = st.slider(
            "분해할 글 편수",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            key="t2_num_posts",
        )

    with col2:
        st.info(
            """
            **사용 방법**

            1. 전자책 파일을 업로드 (txt/md/pdf/docx)
            2. 카테고리와 편수 선택
            3. '분해 시작' 클릭
            4. 생성된 주제 리스트 다운로드
            5. 각 주제는 탭 1 또는 탭 3에서 본문 생성에 사용
            """
        )

    if st.button("🔪 분해 시작", type="primary", key="t2_split"):
        if not uploaded_file:
            st.warning("파일을 업로드해주세요.")
            return
        client = get_api_client()
        if not client:
            return

        with st.spinner("전자책 텍스트 추출 중..."):
            text = extract_text_from_upload(uploaded_file)
        if not text.strip():
            st.error("텍스트를 추출할 수 없습니다.")
            return

        st.info(f"추출된 텍스트: {len(text):,}자 (앞 20,000자만 분석에 사용)")

        with st.spinner(f"{num_posts}편으로 분해 중..."):
            posts = split_ebook_to_posts(client, text, num_posts, category)
        if not posts:
            return

        st.session_state["t2_posts"] = posts
        st.session_state["t2_category"] = category

    if st.session_state.get("t2_posts"):
        posts = st.session_state["t2_posts"]
        st.success(f"✅ {len(posts)}편 분해 완료!")
        st.markdown("### 📋 분해 결과")
        for post in posts:
            with st.expander(f"#{post.get('번호', '?')} {post.get('제목', '?')}"):
                st.markdown(f"**핵심 메시지**: {post.get('핵심메시지', '?')}")
                kw = post.get("주요키워드", [])
                if kw:
                    st.markdown(f"**키워드**: {', '.join(kw)}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "💾 분해 결과 JSON 다운로드",
            data=json.dumps(posts, ensure_ascii=False, indent=2),
            file_name=f"ebook_split_{timestamp}.json",
            mime="application/json",
            key="t2_download",
        )


# ============================================================
# 탭 3: 통합 워크플로우 (전자책 → 자동 글 + 썸네일 + 이미지)
# ============================================================

def tab_integrated_workflow():
    st.header("🚀 통합 워크플로우")
    st.caption("전자책 업로드 → 50편 분해 → 글 선택 → 5단 본문 + 썸네일 + 이미지까지 한 번에")

    st.markdown("### 1️⃣ 전자책 업로드 + 분해")

    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_a:
        uploaded_file = st.file_uploader(
            "전자책 파일",
            type=["txt", "md", "pdf", "docx"],
            key="t3_uploader",
        )
    with col_b:
        category = st.selectbox("카테고리", list(CATEGORY_MAP.keys()), key="t3_category")
    with col_c:
        num_posts = st.number_input(
            "편수", min_value=5, max_value=100, value=30, step=5, key="t3_num_posts"
        )

    if st.button("📚 전자책 분해", key="t3_split"):
        if not uploaded_file:
            st.warning("파일을 업로드해주세요.")
        else:
            client = get_api_client()
            if client:
                with st.spinner("전자책 분해 중..."):
                    text = extract_text_from_upload(uploaded_file)
                    if text.strip():
                        posts = split_ebook_to_posts(client, text, num_posts, category)
                        if posts:
                            st.session_state["t3_split_posts"] = posts
                            st.session_state["t3_split_category"] = category
                            st.success(f"✅ {len(posts)}편 분해 완료")

    st.divider()
    st.markdown("### 2️⃣ 생성할 글 선택")

    split_posts = st.session_state.get("t3_split_posts", [])
    if not split_posts:
        st.info("👆 위에서 먼저 전자책을 분해하세요.")
        return

    titles = [f"#{p.get('번호', '?')} {p.get('제목', '?')}" for p in split_posts]
    selected_idx = st.selectbox(
        "생성할 글",
        range(len(titles)),
        format_func=lambda i: titles[i],
        key="t3_selected_idx",
    )
    selected = split_posts[selected_idx]

    with st.expander("선택된 글 상세"):
        st.markdown(f"**핵심 메시지**: {selected.get('핵심메시지', '')}")
        kw = selected.get("주요키워드", [])
        if kw:
            st.markdown(f"**키워드**: {', '.join(kw)}")

    extra_facts = st.text_area(
        "본인 경험 / 구체 사실 추가 (선택)",
        placeholder="이 편에만 추가로 넣고 싶은 구체 사실/경험",
        height=120,
        key="t3_extra_facts",
    )

    col_o1, col_o2, col_o3 = st.columns(3)
    with col_o1:
        use_naver = st.checkbox("🔍 네이버 실시간 학습", value=True, key="t3_use_naver")
    with col_o2:
        gen_thumb = st.checkbox("🎨 썸네일", value=True, key="t3_gen_thumb")
    with col_o3:
        gen_img = st.checkbox("🖼 본문 이미지", value=True, key="t3_gen_img")

    st.divider()
    st.markdown("### 3️⃣ 생성")

    if st.button("🚀 이 글 통합 생성", type="primary", key="t3_run"):
        client = get_api_client()
        if not client:
            return

        topic = selected.get("제목", "")
        cat = st.session_state.get("t3_split_category", category)
        # 키워드를 user_facts 보강 재료로 추가
        facts_combined = extra_facts
        if selected.get("핵심메시지"):
            facts_combined = f"이 글의 핵심: {selected['핵심메시지']}\n\n{facts_combined}"
        if kw:
            facts_combined += f"\n주요 키워드: {', '.join(kw)}"

        progress = st.progress(0, text="시작...")

        def on_stage(i, name, output):
            progress.progress(i / 6, text=f"완료: {name}")

        post = generate_full_post(
            client, cat, topic, facts_combined, use_naver, on_stage=on_stage
        )
        if not post:
            progress.empty()
            return

        markers, urls = [], []
        if gen_img:
            markers = extract_image_markers(post["full_post"])
            urls = [
                pollinations_image_url(m["prompt"], width=1024, height=768, seed=i)
                for i, m in enumerate(markers)
            ]
        rendered = (
            replace_markers_with_images(post["full_post"], markers, urls)
            if markers and urls
            else post["full_post"]
        )

        thumb = {}
        if gen_thumb:
            progress.progress(5 / 6, text="썸네일 추천 중...")
            thumb = suggest_thumbnail(client, topic, cat, post["full_post"])
            if thumb and thumb.get("image_prompt"):
                thumb["image_url"] = pollinations_image_url(
                    thumb["image_prompt"], width=1200, height=900, seed=42
                )

        progress.progress(1.0, text="완료!")

        post["markers"] = markers
        post["image_urls"] = urls
        post["rendered_body"] = rendered
        post["thumbnail"] = thumb
        st.session_state["t3_last_post"] = post

    if st.session_state.get("t3_last_post"):
        st.divider()
        st.success("✅ 통합 생성 완료")
        render_post_result(st.session_state["t3_last_post"], key_prefix="t3")


# ============================================================
# 탭 4: 설정
# ============================================================

def tab_settings():
    st.header("⚙️ 설정")

    st.subheader("API 키 설정")
    st.caption("Anthropic API 키. 한 세션에만 저장됩니다.")
    current_key = st.session_state.get("api_key", "")
    if current_key:
        masked = "*" * max(0, len(current_key) - 4) + current_key[-4:]
        st.text_input("현재 키 (마스킹)", value=masked, disabled=True)
    new_key = st.text_input("새 API 키", type="password", placeholder="sk-ant-...")
    if st.button("저장", key="settings_save_key"):
        if new_key.strip():
            st.session_state["api_key"] = new_key.strip()
            st.success("✅ API 키 저장 완료")
            st.rerun()
        else:
            st.warning("키를 입력해주세요.")

    st.divider()

    st.subheader("모델 선택")
    current_model = get_active_model()
    new_model = st.selectbox(
        "사용할 Claude 모델",
        list(AVAILABLE_MODELS.keys()),
        format_func=lambda k: f"{k} — {AVAILABLE_MODELS[k]}",
        index=list(AVAILABLE_MODELS.keys()).index(current_model)
        if current_model in AVAILABLE_MODELS
        else 0,
        key="settings_model",
    )
    if st.button("모델 적용", key="settings_save_model"):
        st.session_state["model_name"] = new_model
        st.success(f"✅ 모델 변경: {new_model}")

    st.divider()

    st.subheader("배포 시 권장 (Streamlit Cloud)")
    st.code(
        """# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-..."
""",
        language="toml",
    )

    st.divider()

    st.subheader("SKILL 파일 위치")
    st.code(str(SKILL_DIR), language="text")
    if SKILL_DIR.exists():
        files = sorted(f.name for f in SKILL_DIR.glob("*.md"))
        st.markdown(f"**현재 로드된 SKILL: {len(files)}개**")
        for f in files:
            st.markdown(f"- `{f}`")


# ============================================================
# 메인
# ============================================================

def main():
    st.title("📝 BlogMaker v2.1")
    st.caption("네이버 패턴 학습 · 5단 골격 단계별 생성 · 실시간 트레이닝 · 무료 이미지 자동 생성")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["✍️ 블로그 작성", "📚 전자책 분해", "🚀 통합 워크플로우", "⚙️ 설정"]
    )
    with tab1:
        tab_blog_writer()
    with tab2:
        tab_ebook_splitter()
    with tab3:
        tab_integrated_workflow()
    with tab4:
        tab_settings()


if __name__ == "__main__":
    main()
