#!/bin/bash
# 맥에서 1시간마다 수집해 push 한다 (launchd 가 호출).
#
# GitHub Actions 만으로는 네이버가 데이터센터 IP 차단에 걸려 대부분 실패한다.
# 로컬(한국 가정용 IP)에서는 100% 성공하므로, 맥이 켜져 있는 동안은 여기서 채운다.
# 맥이 자거나 꺼져 있으면 GitHub Actions 가 나머지 3개 소스로 시간을 메운다.

set -uo pipefail

REPO="/Users/glen/Documents/japan-hotel-watch"
# launchd 는 로그인 셸 PATH 를 물려받지 않는다. 직접 지정해야 git·gh·python 을 찾는다.
export PATH="/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

cd "$REPO" || exit 1

LOG="$REPO/.local-run.log"
# 로그가 무한정 커지지 않게 1MB 넘으면 뒤쪽만 남긴다.
if [ -f "$LOG" ] && [ "$(stat -f%z "$LOG")" -gt 1048576 ]; then
  tail -n 300 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
fi
exec >>"$LOG" 2>&1

STAMP=$(date '+%Y-%m-%d %H:%M')
echo "─── $STAMP 시작"

# 네트워크가 없으면 조용히 끝낸다 (외출·기내 등)
if ! curl -sf --max-time 10 -o /dev/null https://github.com; then
  echo "네트워크 없음 — 건너뜀"
  exit 0
fi

git pull -q --rebase --autostash origin main || echo "pull 실패 — 그대로 진행"

if ! python3 collector/collect.py; then
  echo "수집 실패"
  exit 1
fi

git add docs/data
if git diff --staged --quiet; then
  echo "변경 없음 — 커밋 생략"
  exit 0
fi

MSG="요금 갱신(로컬) $STAMP KST"
git commit -q -m "$MSG"

# GitHub Actions 실행과 겹치면 push 가 밀린다.
# history.jsonl 은 append-only 라 합집합, latest.json 은 방금 값이 이긴다.
for i in 1 2 3; do
  if git push -q origin main; then
    echo "push 완료"
    exit 0
  fi
  echo "push 경합 — 재시도 $i"
  git fetch -q origin main
  git show origin/main:docs/data/history.jsonl > /tmp/jhw_theirs.jsonl 2>/dev/null \
    || : > /tmp/jhw_theirs.jsonl
  git reset -q --soft origin/main
  sort -u /tmp/jhw_theirs.jsonl docs/data/history.jsonl > /tmp/jhw_merged.jsonl \
    && mv /tmp/jhw_merged.jsonl docs/data/history.jsonl
  git add docs/data
  git commit -q -m "$MSG"
  sleep 5
done

echo "3회 재시도 후에도 push 실패"
exit 1
