# BlogMaker v2

> 네이버 상위 블로그 9편의 실측 패턴을 학습한 AI 블로그 자동 생성기
> Writey 연동 · 5단 골격 단계별 생성 · 9개 카테고리별 톤 자동 분기

CashMaker (cashmaker.co.kr) 자체 개발 도구.

---

## 🎯 v1 대비 변경점

| 항목 | v1 | v2 |
|---|---|---|
| 생성 방식 | 한 번에 1편 | **5단 골격 단계별 생성** |
| 카테고리 분기 | 없음 | **9개 카테고리별 SKILL.md 자동 로드** |
| 패턴 학습 | 일반 LLM | **네이버 상위 블로그 9편 실측 패턴 적용** |
| 해시태그 | 수동 | **자동 (메인 3~5 + 서브 15~20)** |
| 전자책 연동 | 없음 | **PDF/DOCX/MD/TXT 업로드 → 50편 분해** |
| 책임 회피 표현 | 없음 | **재테크/건강 카테고리 자동 면책 문구** |

---

## 📁 디렉토리 구조

```
blogmaker_v2/
├── app/
│   ├── app.py              # Streamlit 메인 앱
│   └── requirements.txt    # 의존성
├── skills/
│   ├── _master.md          # 공통 시스템 프롬프트
│   ├── it_review.md
│   ├── admin_legal.md
│   ├── education.md
│   ├── finance.md
│   ├── career.md
│   ├── food_travel.md
│   ├── home_appliance.md
│   ├── health_emotion.md
│   └── marketing.md
├── docs/
│   └── blog_pattern_analysis_v2.md   # 9편 분석 보고서
├── README.md
└── .gitignore
```

---

## 🚀 빠른 시작

### 1. 로컬 실행

```bash
# 클론
git clone https://github.com/[YOUR_USERNAME]/blogmaker-v2.git
cd blogmaker-v2

# 가상환경 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r app/requirements.txt

# 앱 실행
streamlit run app/app.py
```

브라우저에서 자동으로 `http://localhost:8501` 열림.
설정 탭에서 Anthropic API 키 입력 후 사용.

### 2. Streamlit Cloud 배포

1. 이 레포를 GitHub에 푸시
2. [share.streamlit.io](https://share.streamlit.io) 로그인
3. New app → 레포 선택 → main 파일: `app/app.py`
4. Advanced settings → Secrets에 입력:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
5. Deploy 클릭

---

## 📝 사용 흐름

### 단일 블로그 글 생성
1. **카테고리 선택** (예: 재테크/투자)
2. **주제 입력** (예: "QQQ 5년 적립식 매수 후기")
3. **본인 경험/구체 사실 입력** (선택, 권장)
4. **생성 버튼** → 5단계 순차 실시간 표시
5. **합본 복사** 또는 **.md 다운로드**

### 전자책 → 시리즈 분해 (Writey 연동)
1. **전자책 업로드** (txt/md/pdf/docx)
2. **카테고리 + 편수 선택** (기본 50편)
3. **분해 시작** → JSON 형식으로 50개 주제 산출
4. **각 주제를 탭 1에서 본문 생성**

---

## 🧠 학습된 패턴 (9편 실측 데이터 기반)

### 5단 골격 (전 카테고리 공통)
도입 → 전환 → 본론 → 강조 → 클로징

### 어미 3대 스펙트럼
- `~ㅂ니다`: IT, 행정, 교육, 마케팅
- `~이다 (반말)`: 재테크, 취업
- `~에요/~어요`: 맛집, 가전, 건강

### 후킹 패턴 4종
1. 부정→긍정형 ("X도 아니다 / Y도 아니다 / 바로 Z다")
2. 핵심 단축형 ("사실 핵심은 단 하나")
3. 정체성 선언형 ("○○인 ○○이다")
4. 의문 던지기형 ("정말 ○○일까요?")

### 시각 패턴 5종
- 직접 촬영 / 캡처 화면 / 표 정리 / 워터마크 / 손그림 일러스트

자세한 내용은 [`docs/blog_pattern_analysis_v2.md`](docs/blog_pattern_analysis_v2.md) 참고.

---

## ⚠️ 알려진 한계

- **마케팅/1인사업 카테고리**: 9편 실측 데이터에 미포함. 본인 Brunch 글로 보완 학습 권장.
- **자동 발행 (네이버 Open API)**: v2에서는 제외. 생성/복사까지만.
- **이미지 자동 생성**: 시각 패턴 *가이드*만 제공. 실제 이미지는 사용자가 첨부.
- **다국어**: 한국어 전용.

---

## 🛠️ 트러블슈팅

### "SKILL 파일을 찾을 수 없습니다" 오류
`app.py` 위치 기준 `../skills/` 경로에 SKILL 파일이 있어야 함.
디렉토리 구조 확인.

### "anthropic.APIError: model_not_found"
`app.py` 상단의 `MODEL_NAME` 변수를 사용 가능한 모델로 교체.
사용 가능 모델 확인: https://docs.claude.com/en/docs/about-claude/models

### PDF/DOCX 업로드 실패
```bash
pip install pypdf python-docx
```

---

## 📜 라이선스

CashMaker 내부 사용. 외부 배포/판매 금지.

---

## 📞 문의

- 사이트: [cashmaker.co.kr](https://cashmaker.co.kr)
- Kmong: 최상위 2% 컨설턴트 (4.9★, 760+ 거래)

---

*Built for solo entrepreneurs who write daily.*
