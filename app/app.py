"""
BlogMaker v2 - 네이버 상위 블로그 패턴 학습 AI 블로그 자동 생성기
@author: CashMaker (cashmaker.co.kr)
@version: 2.0.0
"""

import streamlit as st
import anthropic
from pathlib import Path
import json
import re
import io
from datetime import datetime

# ============================================================
# 설정
# ============================================================

PAGE_CONFIG = {
    "page_title": "BlogMaker v2",
    "page_icon": "📝",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

st.set_page_config(**PAGE_CONFIG)

MODEL_NAME = "claude-sonnet-4-6"  # 2026년 2월 출시, 균형형 추천 모델
# 다른 옵션:
#   claude-opus-4-7         (2026년 4월 출시, 최고 성능 - 비용 더 큼)
#   claude-haiku-4-5-20251001  (저비용 빠른 응답)
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

# ============================================================
# 유틸리티 함수
# ============================================================

def load_skill(filename: str) -> str:
    """SKILL.md 파일 로드"""
    path = SKILL_DIR / filename
    if not path.exists():
        st.error(f"SKILL 파일을 찾을 수 없습니다: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def get_api_client():
    """Anthropic API 클라이언트 생성"""
    api_key = st.session_state.get("api_key") or st.secrets.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        st.error("⚠️ Anthropic API 키가 설정되지 않았습니다. '설정' 탭에서 입력해주세요.")
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
# 5단 골격 단계별 생성 함수
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
- 카테고리별 시각 패턴 적용 (이미지 첨부 위치를 [📷 직접 촬영 사진] 같이 표시)
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
    
    return call_claude(client, system_prompt, stage_prompts[stage], max_tokens=2500 if stage == 3 else 1000)


# ============================================================
# 전자책 분해 함수
# ============================================================

def split_ebook_to_posts(client, ebook_text: str, num_posts: int, category: str) -> list[dict]:
    """전자책 텍스트를 N편의 블로그 글 주제로 분해"""
    
    system = """당신은 한국 디지털 콘텐츠 기획 전문가다.
전자책의 핵심 내용을 추출해 네이버 블로그 시리즈로 분해하는 일을 한다."""
    
    prompt = f"""다음 전자책 내용을 분석해 **{num_posts}편의 블로그 글 주제**로 분해해라.

전자책 카테고리: {category}

전자책 내용:
---
{ebook_text[:15000]}
---

출력 형식 (JSON 배열만 출력, 다른 설명 금지):
[
  {{
    "번호": 1,
    "제목": "구체적인 블로그 글 제목",
    "핵심메시지": "이 글에서 다룰 한 가지 핵심",
    "주요키워드": ["키워드1", "키워드2", "키워드3"]
  }},
  ...
]

규칙:
- {num_posts}편 정확히 생성
- 각 글이 독립적으로 읽혀도 가치가 있어야 함
- 시리즈 흐름 유지 (난이도/주제 점진적 심화)
- 제목은 클릭하고 싶게, 구체적으로
"""
    
    response = call_claude(client, system, prompt, max_tokens=4000)
    
    # JSON 추출
    json_match = re.search(r'\[.*\]', response, re.DOTALL)
    if not json_match:
        st.error("JSON 형식으로 응답이 오지 않았습니다. 다시 시도해주세요.")
        return []
    
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError as e:
        st.error(f"JSON 파싱 실패: {e}")
        return []


def extract_text_from_upload(uploaded_file) -> str:
    """업로드된 파일에서 텍스트 추출 (txt, md만 기본 지원. pdf/docx는 별도 라이브러리 필요)"""
    
    name = uploaded_file.name.lower()
    
    if name.endswith(".txt") or name.endswith(".md"):
        return uploaded_file.read().decode("utf-8", errors="ignore")
    
    elif name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            return "\n".join(page.extract_text() for page in reader.pages)
        except ImportError:
            st.error("PDF 처리를 위해 `pip install pypdf` 가 필요합니다.")
            return ""
    
    elif name.endswith(".docx"):
        try:
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.read()))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            st.error("DOCX 처리를 위해 `pip install python-docx` 가 필요합니다.")
            return ""
    
    else:
        st.error(f"지원하지 않는 파일 형식입니다: {name}")
        return ""


# ============================================================
# UI - 탭 1: 블로그 작성
# ============================================================

def tab_blog_writer():
    st.header("📝 블로그 글 자동 생성")
    st.caption("네이버 상위 블로그 9편 분석 기반 · 5단 골격 단계별 생성")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        category = st.selectbox(
            "카테고리 선택",
            list(CATEGORY_MAP.keys()),
            help="카테고리에 따라 어미/후킹/시각 패턴이 자동 분기됩니다.",
        )
        
        st.divider()
        
        st.markdown(f"**선택된 카테고리: `{category}`**")
        skill_content = load_skill(CATEGORY_MAP[category])
        with st.expander("📖 적용되는 SKILL 미리보기"):
            st.markdown(skill_content)
    
    with col2:
        topic = st.text_input(
            "블로그 주제",
            placeholder="예: 27인치 모니터 LG 32GP750 3개월 사용 후기",
            help="구체적일수록 글이 좋아집니다.",
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
            help="구체적 사실이 많을수록 AI 회피 효과가 큽니다. 최소 3개 권장.",
        )
        
        st.divider()
        
        if st.button("✨ 5단 골격 단계별 생성", type="primary", use_container_width=True):
            if not topic.strip():
                st.warning("주제를 입력해주세요.")
                return
            
            client = get_api_client()
            if not client:
                return
            
            system_prompt = build_system_prompt(category, user_facts)
            context = {
                "topic": topic,
                "user_facts": user_facts,
                "previous_stages": "",
            }
            
            all_stages = []
            progress = st.progress(0, text="시작...")
            
            for i, stage_name in enumerate(STAGE_NAMES, 1):
                progress.progress((i - 1) / 5, text=f"생성 중: {stage_name}")
                
                stage_output = generate_stage(client, system_prompt, i, context)
                all_stages.append((stage_name, stage_output))
                
                # 다음 단계에 이전 단계 누적
                context["previous_stages"] += f"\n\n{stage_output}"
                
                # 실시간 표시
                st.markdown(f"### {stage_name}")
                st.markdown(stage_output)
                st.divider()
            
            progress.progress(1.0, text="완료!")
            
            # 전체 합본
            full_post = "\n\n".join(out for _, out in all_stages)
            
            st.success("✅ 생성 완료!")
            
            with st.expander("📋 전체 글 합본 (복사용)", expanded=True):
                st.text_area(
                    "복사해서 네이버 블로그에 붙여넣으세요",
                    value=full_post,
                    height=400,
                )
            
            # 다운로드
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                "💾 .md 파일로 다운로드",
                data=full_post,
                file_name=f"blogpost_{category.replace('/', '_')}_{timestamp}.md",
                mime="text/markdown",
            )


# ============================================================
# UI - 탭 2: 전자책 분해
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
        )
        
        category = st.selectbox(
            "전자책 카테고리",
            list(CATEGORY_MAP.keys()),
            key="ebook_category",
        )
        
        num_posts = st.slider(
            "분해할 글 편수",
            min_value=10,
            max_value=100,
            value=50,
            step=5,
            help="Writey 기본값: 50편",
        )
    
    with col2:
        st.info(
            """
            **사용 방법**
            
            1. 전자책 파일을 업로드 (txt/md/pdf/docx)
            2. 카테고리와 편수 선택
            3. '분해 시작' 클릭
            4. 생성된 주제 리스트 다운로드
            5. 각 주제는 탭 1에서 본문 생성에 사용
            
            **권장 분량**
            - 200페이지 전자책 → 50편
            - 100페이지 전자책 → 25편
            """
        )
    
    if st.button("🔪 분해 시작", type="primary"):
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
        
        st.info(f"추출된 텍스트: {len(text):,}자 (앞 15,000자만 분석에 사용)")
        
        with st.spinner(f"{num_posts}편으로 분해 중..."):
            posts = split_ebook_to_posts(client, text, num_posts, category)
        
        if not posts:
            return
        
        st.success(f"✅ {len(posts)}편 분해 완료!")
        
        # 표로 표시
        st.markdown("### 📋 분해 결과")
        for post in posts:
            with st.expander(f"#{post.get('번호', '?')} {post.get('제목', '?')}"):
                st.markdown(f"**핵심 메시지**: {post.get('핵심메시지', '?')}")
                kw = post.get('주요키워드', [])
                if kw:
                    st.markdown(f"**키워드**: {', '.join(kw)}")
        
        # JSON 다운로드
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            "💾 분해 결과 JSON 다운로드",
            data=json.dumps(posts, ensure_ascii=False, indent=2),
            file_name=f"ebook_split_{timestamp}.json",
            mime="application/json",
        )


# ============================================================
# UI - 탭 3: 설정
# ============================================================

def tab_settings():
    st.header("⚙️ 설정")
    
    st.subheader("API 키 설정")
    st.caption("Anthropic API 키를 입력하세요. 한 세션에만 저장됩니다.")
    
    current_key = st.session_state.get("api_key", "")
    masked = "*" * (len(current_key) - 4) + current_key[-4:] if current_key else ""
    
    st.text_input(
        "현재 키 (마스킹)",
        value=masked,
        disabled=True,
    )
    
    new_key = st.text_input(
        "새 API 키",
        type="password",
        placeholder="sk-ant-...",
    )
    
    if st.button("저장"):
        if new_key.strip():
            st.session_state["api_key"] = new_key.strip()
            st.success("✅ API 키 저장 완료")
            st.rerun()
        else:
            st.warning("키를 입력해주세요.")
    
    st.divider()
    
    st.subheader("배포 시 권장 (Streamlit Cloud)")
    st.code("""
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-..."
    """, language="toml")
    
    st.divider()
    
    st.subheader("모델 정보")
    st.code(f"현재 모델: {MODEL_NAME}", language="text")
    st.caption("사용 가능한 최신 Claude 모델로 교체 가능합니다. (api.anthropic.com/v1/models 확인)")
    
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
    st.title("📝 BlogMaker v2")
    st.caption("네이버 상위 블로그 패턴 학습 · 5단 골격 단계별 자동 생성 · Writey 연동")
    
    tab1, tab2, tab3 = st.tabs(["✍️ 블로그 작성", "📚 전자책 분해", "⚙️ 설정"])
    
    with tab1:
        tab_blog_writer()
    
    with tab2:
        tab_ebook_splitter()
    
    with tab3:
        tab_settings()


if __name__ == "__main__":
    main()
