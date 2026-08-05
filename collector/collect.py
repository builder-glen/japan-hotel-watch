"""6개 호텔 × 2개 소스 요금을 수집해 docs/data 로 떨군다.

산출물
  docs/data/latest.json   — 현재 스냅샷 (웹페이지가 읽는 파일)
  docs/data/history.jsonl — 호텔별 최저가 시계열 (append only, 차트용)
"""

import json
import statistics
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import ADULTS, ROOMS, STAYS
from sources import naver, rakuten

KST = timezone(timedelta(hours=9))
DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
LATEST = DATA / "latest.json"
HISTORY = DATA / "history.jsonl"

MAX_OFFERS = 8  # 호텔당 페이지에 노출할 최저가 상위 건수
FX_FALLBACK = 9.1  # 네이버 응답에서 환율을 못 뽑았을 때의 최후 보루 (KRW/JPY)


def main():
    now = datetime.now(KST).replace(microsecond=0)
    prev = _load_json(LATEST) or {}

    raw = []  # (stay, hotel, offers, errors)
    for stay in STAYS:
        for hotel in stay["hotels"]:
            offers, errors = [], {}
            for name, fn in (
                ("naver", lambda: naver.fetch(hotel, stay, ADULTS)),
                ("rakuten", lambda: rakuten.fetch(hotel, stay, ADULTS, ROOMS)),
            ):
                try:
                    offers += fn()
                except Exception as exc:
                    errors[name] = f"{type(exc).__name__}: {exc}"
                time.sleep(1.5)  # 라쿠텐 권고 간격에 맞춘 예의상 딜레이
            raw.append((stay, hotel, offers, errors))

    fx = _fx_rate([o for _, _, offs, _ in raw for o in offs], prev.get("fx_jpy_krw"))
    lows = _history_lows()

    stays_out, history_lines = [], []
    for stay in STAYS:
        hotels_out = []
        for stay_ref, hotel, offers, errors in raw:
            if stay_ref["id"] != stay["id"]:
                continue

            for o in offers:
                # 라쿠텐은 엔화만 주므로 환산해서 비교 축을 원화로 통일한다.
                if o["krw"] is None and o["jpy"] is not None:
                    o["krw"] = round(o["jpy"] * fx)
                    o["krw_estimated"] = True
                if o["jpy"] is None and o["krw"] is not None:
                    o["jpy"] = round(o["krw"] / fx)
                    o["jpy_estimated"] = True

            offers = [o for o in offers if o.get("krw")]
            offers.sort(key=lambda o: o["krw"])
            best = offers[0] if offers else None

            key = f"{stay['id']}/{hotel['key']}"
            prior_low = lows.get(key)
            record_low = bool(best and (prior_low is None or best["krw"] < prior_low))

            hotels_out.append(
                {
                    **{k: hotel[k] for k in ("key", "name_ko", "name_ja", "official")},
                    "naver_url": naver._detail_url(hotel, stay, ADULTS),
                    "rakuten_url": rakuten.build_url(hotel["rakuten_no"], stay, ADULTS, ROOMS),
                    "best": best,
                    "offers": offers[:MAX_OFFERS],
                    "offer_count": len(offers),
                    "prior_low_krw": prior_low,
                    "record_low": record_low,
                    "errors": errors,
                }
            )

            if best:
                history_lines.append(
                    json.dumps(
                        {
                            "t": now.isoformat(),
                            "stay": stay["id"],
                            "hotel": hotel["key"],
                            "krw": best["krw"],
                            "jpy": best["jpy"],
                            "src": best["source"],
                            "seller": best["seller"],
                        },
                        ensure_ascii=False,
                    )
                )

        stays_out.append(
            {
                **{k: stay[k] for k in ("id", "label", "check_in", "check_out", "nights")},
                "hotels": hotels_out,
            }
        )

    DATA.mkdir(parents=True, exist_ok=True)
    if history_lines:
        with HISTORY.open("a", encoding="utf-8") as f:
            f.write("\n".join(history_lines) + "\n")

    LATEST.write_text(
        json.dumps(
            {
                "collected_at": now.isoformat(),
                "adults": ADULTS,
                "rooms": ROOMS,
                "fx_jpy_krw": round(fx, 4),
                "stays": stays_out,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    ok = sum(1 for s in stays_out for h in s["hotels"] if h["best"])
    total = sum(len(s["hotels"]) for s in stays_out)
    print(f"[{now.isoformat()}] {ok}/{total} 호텔 수집, 환율 {fx:.3f} KRW/JPY")
    for s in stays_out:
        for h in s["hotels"]:
            b = h["best"]
            mark = " ★신규최저" if h["record_low"] else ""
            line = f"  {s['label']} {h['name_ko']:<22}"
            print(f"{line} {b['krw']:>9,}원 ({b['seller']}){mark}" if b else f"{line} 수집 실패 {h['errors']}")

    # 전 호텔 실패는 소스가 죽었다는 뜻이므로 워크플로를 실패시킨다.
    return 0 if ok else 1


def _fx_rate(offers, previous):
    """네이버가 같은 상품의 원화·엔화를 동시에 주므로 거기서 환율을 역산한다."""
    pairs = [o["krw"] / o["jpy"] for o in offers if o.get("krw") and o.get("jpy")]
    if pairs:
        return statistics.median(pairs)
    return previous or FX_FALLBACK


def _history_lows():
    """호텔별 과거 최저가. 지금 값이 신기록인지 판정하는 기준."""
    lows = {}
    if not HISTORY.exists():
        return lows
    for line in HISTORY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        k = f"{r['stay']}/{r['hotel']}"
        if r.get("krw") and (k not in lows or r["krw"] < lows[k]):
            lows[k] = r["krw"]
    return lows


def _load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


if __name__ == "__main__":
    sys.exit(main())
