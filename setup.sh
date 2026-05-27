#!/usr/bin/env bash
# BlogMaker 자동 설치 스크립트 (macOS / Linux)
# 사용법:
#   1) 이 폴더 통째로 ~/blogmaker 로 옮긴다 (Downloads 권한 문제 회피)
#   2) 터미널에서 bash setup.sh
#   3) 끝나면 자동으로 streamlit이 열림

set -e

cd "$(dirname "$0")"

# 1) 현재 위치가 Downloads면 경고
PWD_NOW="$(pwd)"
case "$PWD_NOW" in
  *Downloads*)
    echo ""
    echo "⚠️  현재 위치가 Downloads 폴더 안이에요. macOS 권한 문제로 Python이 작동 안 할 수 있어요."
    echo "   이 폴더 통째로 ~/blogmaker 로 옮긴 다음 다시 실행해주세요:"
    echo ""
    echo "       mv \"$PWD_NOW\" ~/blogmaker"
    echo "       cd ~/blogmaker"
    echo "       bash setup.sh"
    echo ""
    read -p "그래도 계속할까요? (y/N) " ans
    [[ "$ans" =~ ^[Yy]$ ]] || exit 1
    ;;
esac

# 2) Python 후보 탐색 - 시스템 Python 3.9~3.12 우선 (3.14는 일부 문제 있음)
PYTHON_CMD=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    VER=$("$candidate" -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>/dev/null || echo "")
    if [[ -n "$VER" ]]; then
      echo "✓ Python 발견: $candidate (버전 $VER)"
      PYTHON_CMD="$candidate"
      break
    fi
  fi
done

if [[ -z "$PYTHON_CMD" ]]; then
  echo "❌ Python 3을 찾을 수 없어요. https://www.python.org/downloads/ 에서 3.11 또는 3.12 설치 후 다시 실행해주세요."
  exit 1
fi

# 3) venv 생성
if [[ ! -d "venv" ]]; then
  echo "→ 가상환경 생성 중..."
  "$PYTHON_CMD" -m venv venv
fi

# 4) venv 활성화 + 의존성 설치
echo "→ 의존성 설치 중 (1~2분 소요)..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# 5) 실행
echo ""
echo "🚀 BlogMaker 시작! 브라우저가 자동으로 열려요."
echo "   종료: Ctrl+C"
echo ""
streamlit run app/app.py
