# BlogMaker

네이버 블로그 자동 작성 도구. Claude API를 써서 5단 골격(도입→전환→본론→강조→클로징)으로 자연스러운 한국어 블로그 글을 만들어요. 카테고리별 맞춤 톤(IT 리뷰, 맛집, 금융 등 9종)과 Openverse 무료 사진 자동 삽입까지 포함.

## 1. 폴더 위치 (중요)

**반드시 홈 디렉터리에 두세요.** `~/Downloads`나 `~/Desktop`은 macOS 권한 문제로 Python이 작동 안 할 수 있어요.

```bash
# Downloads에 있다면 옮기기
mv ~/Downloads/blogmaker ~/blogmaker
cd ~/blogmaker
```

`pwd` 입력했을 때 `/Users/<본인이름>/blogmaker` 로 나오면 OK.

## 2. 설치 + 실행 (처음 한 번)

```bash
bash setup.sh
```

이게 하는 일:

- Downloads 폴더에 있으면 경고 (옮기라고 안내)
- 시스템에 있는 Python 3 중 안정 버전 자동 탐색 (3.12 → 3.11 → 3.10 → 3.9 순)
- `venv/` 가상환경 자동 생성
- `requirements.txt` 의존성 설치
- Streamlit 자동 실행 (브라우저 자동 열림)

1~2분 정도 걸려요. 끝나면 `http://localhost:8501` 이 자동으로 열립니다.

## 3. 두 번째 실행부터

```bash
bash run.sh
```

설치 단계 건너뛰고 바로 실행돼요. 또는 macOS Finder에서 `run.sh` 우클릭 → "다음으로 열기" → "터미널".

## 4. 첫 사용 흐름

1. **설정 탭** 열기
2. **Anthropic API 키** 발급 → 저장
   - [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) → "Create Key" → 복사 (`sk-ant-...`로 시작) → 앱에 붙여넣고 "키 저장"
   - 키는 `.config.json`에 로컬로만 저장됨 (외부 전송 X)
3. **블로그 작성 탭**으로 이동
4. 카테고리 선택 → 주제 입력 → **본인 경험/팁** 최대한 구체적으로 입력
5. **"🚀 5단 골격 단계별 생성"** 클릭
6. 5단계가 순서대로 스트리밍으로 떠요
7. 다 끝나면 자동으로 합본 + 사진 삽입 → 복사 또는 .md 다운로드

## 5. 비용 안내

- 기본 모델: **Haiku 4.5** (가장 저렴, 빠름)
- 본문 1편당 대략 **5~15원** 정도
- Sonnet/Opus는 더 비싸지만 문장 품질↑

설정 탭에서 모델 변경 가능.

## 6. 카테고리

| 카테고리 | 톤 특징 |
|---|---|
| 💻 IT/디지털 리뷰 | 실사용 후기 톤, 장단점 균형 |
| 💰 금융/재테크 | 검증 톤 + 면책 한 줄 자동 |
| 🍜 맛집/여행 | 오감 표현, 솔직한 단점 포함 |
| 🌿 건강/감정 | 부드러운 공감 톤, 진단 단정 회피 |
| 📚 교육/학습 | 친근한 학습자 톤, 비유 풍부 |
| 💼 취업/이직 | 실전 경험 톤, 단정 표현 회피 |
| 📋 행정/법률/생활 | 정확한 안내 톤, 출처 표기 |
| 🏠 가전/생활용품 | 일상 시나리오, 솔직한 단점 |
| 📈 마케팅/창업/부업 | 시행착오 톤, 과장 표현 회피 |

각 카테고리의 세부 프롬프트는 `skills/` 폴더 안에 .md 파일로 있어요. 직접 수정해서 톤을 본인 스타일로 바꿔도 됩니다.

## 7. 트러블슈팅

| 증상 | 해결 |
|---|---|
| `streamlit: command not found` | venv 활성화 안 됨. `source venv/bin/activate` 먼저 |
| `Operation not permitted` | Downloads 폴더에 있는 거예요. `~/blogmaker`로 옮기세요 |
| `model_not_found` | 설정 탭에서 다른 모델 선택 (Haiku 4.5가 가장 안전) |
| 사진이 안 나옴 | Openverse API가 일시적으로 다운됐을 수 있어요. 잠시 후 재시도 |
| 생성 중 끊김 | Anthropic API 일시 오류일 가능성. "다음 단계" 버튼으로 재개 |

## 8. 파일 구조

```
blogmaker/
├── app.py              # 메인 Streamlit 앱
├── requirements.txt    # 의존성
├── setup.sh           # 자동 설치 + 첫 실행
├── run.sh             # 두 번째 실행부터
├── .streamlit/config.toml  # Streamlit 테마/설정
├── .config.json       # API 키 저장 (자동 생성)
├── skills/
│   ├── _master.md            # 공통 작성 원칙
│   ├── it_review.md          # 카테고리별 톤 가이드
│   ├── finance.md
│   ├── food_travel.md
│   ├── health_emotion.md
│   ├── education.md
│   ├── career.md
│   ├── admin_legal.md
│   ├── home_appliance.md
│   └── marketing.md
└── README.md          # 이 파일
```

`skills/` 안의 .md 파일을 수정하면 즉시 다음 생성부터 반영돼요. 본인 블로그 스타일에 맞춰 톤을 조정하세요.
