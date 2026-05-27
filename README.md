# 📝 BlogMaker

Claude API로 **네이버 블로그 스타일** 글을 자동 생성하는 Streamlit 도구입니다. 5단 골격(도입→전환→본론→강조→클로징)으로 자연스러운 한국어 글을 쓰고, 카테고리별 맞춤 톤(9종), 무료 사진(Openverse) 자동 삽입, 검정 배경 썸네일 생성까지 한 곳에서 됩니다.

> ⚠️ 생성된 글은 초안입니다. 발행 전 사실 확인과 본인 톤에 맞는 다듬기를 권장해요.

## ✨ 기능

- **5단 골격 단계별 생성** — 도입·전환·본론·강조·클로징을 순서대로 스트리밍 생성
- **9개 카테고리별 SKILL** — IT 리뷰 / 금융 / 맛집·여행 / 건강·감정 / 교육 / 취업 / 행정·법률 / 가전 / 마케팅. 카테고리에 따라 어미·후킹·시각 패턴이 자동으로 바뀜
- **무료 사진 자동 삽입** — 본문 속 `[[IMG: ...]]` 마커를 Openverse(CC 라이선스, API 키 불필요) 사진으로 교체. 작가 크레딧 자동 표기
- **썸네일 생성** — 검정 배경 1:1 대표 이미지. 후킹 문구는 Claude가 자동 제안, 포인트 색상 5종, PNG 다운로드
- **Prompt caching** — 카테고리 SKILL을 캐싱해 호출 비용 절감

## 🚀 설치 & 실행

> **중요:** `~/Downloads`, `~/Desktop`은 macOS 권한 문제로 Python이 막힐 수 있어요. **홈 디렉터리(`~/blogmaker`)에 두세요.**

```bash
git clone https://github.com/<your-id>/blogmaker.git ~/blogmaker
cd ~/blogmaker
bash setup.sh
```

`setup.sh`가 안정 버전 Python 탐색 → `venv` 생성 → 의존성 설치 → Streamlit 실행(`http://localhost:8501` 자동 오픈)까지 처리합니다.

두 번째 실행부터는:

```bash
bash run.sh
```

수동 설치를 선호하면:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## 🔑 첫 사용

1. **설정 탭** → Anthropic API 키 저장
   ([console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)에서 발급, `sk-ant-`로 시작)
   키는 로컬 `.config.json`에만 저장되고 `.gitignore`로 커밋에서 제외됩니다.
2. **블로그 작성 탭** → 카테고리·주제·본인 경험 입력 → 5단 골격 생성 → 합본 복사 / `.md` 다운로드
3. **썸네일 탭** → 주제 입력 → 후킹 자동 제안 → 색상 선택 → 생성 → PNG 다운로드

## 🖼 이미지 미리 보기 (선택)

`image_test.html`을 브라우저에서 더블클릭하면 Streamlit 없이도 검색어별 Openverse 사진을 미리 볼 수 있어요.

## 🔤 한글 폰트 (썸네일용)

- **macOS / Windows**: 시스템 폰트를 자동 인식합니다 (AppleSDGothicNeo / 맑은 고딕).
- **Linux 또는 인식 실패 시**: 한글 TTF를 `assets/font.ttf`로 넣어주세요. 예) [나눔고딕](https://hangeul.naver.com/font), Noto Sans KR.

## 💰 비용

기본 모델은 **Haiku 4.5**(가장 저렴). 본문 1편당 대략 5~15원. 설정 탭에서 Sonnet / Opus로 변경 가능(품질↑, 비용↑).

## 📂 구조

```
blogmaker/
├── app.py                  # Streamlit 메인 앱
├── requirements.txt
├── setup.sh / run.sh       # 설치·실행 스크립트
├── image_test.html         # 사진 미리보기 (브라우저 단독 실행)
├── .streamlit/config.toml
├── .config.example.json    # 설정 예시 (.config.json은 gitignore)
├── skills/
│   ├── _master.md          # 공통 작성 원칙
│   └── *.md                # 카테고리별 톤 가이드 9종
├── .gitignore
├── LICENSE
└── README.md
```

`skills/*.md`를 수정하면 다음 생성부터 즉시 반영돼요. 본인 블로그 스타일에 맞게 톤을 조정하세요.

## 🛠 트러블슈팅

| 증상 | 해결 |
|---|---|
| `Operation not permitted` | `~/blogmaker`로 옮기세요 (Downloads 권한 문제) |
| `streamlit: command not found` | `source venv/bin/activate` 후 실행 |
| `model_not_found` | 설정 탭에서 모델 변경 (Haiku 4.5 권장) |
| 썸네일 한글 깨짐 | `assets/font.ttf`에 한글 폰트 추가 |
| 사진 안 나옴 | Openverse 일시 장애 가능, 잠시 후 재시도 |

## 📄 라이선스

MIT — 자유롭게 사용·수정·배포하세요. 생성 사진은 각 Openverse 항목의 CC 라이선스를 따릅니다.
