#!/usr/bin/env bash
# 두 번째 실행부터는 이것만 쓰면 됨 (의존성 설치 건너뜀)
set -e
cd "$(dirname "$0")"

if [[ ! -d "venv" ]]; then
  echo "venv가 없어요. 먼저 bash setup.sh 를 실행해주세요."
  exit 1
fi

# shellcheck disable=SC1091
source venv/bin/activate
streamlit run app.py
