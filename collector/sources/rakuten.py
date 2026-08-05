"""라쿠텐 트래블 숙박플랜 페이지 파서.

일본 국내 재고 — 특히 료칸의 1박2식 플랜 — 은 글로벌 OTA 에 잘 안 올라오므로
네이버(=글로벌 OTA 집합)만으로는 최저가를 놓친다. 그래서 별도 소스로 둔다.

페이지는 SSR 이고 요금이 `hinfo.hotels` 인라인 JSON 에 그대로 박혀 있어
JS 실행 없이 파싱된다. (WAF 없음, 일반 UA 로 200)
"""

import html
import json
import re
import urllib.request

BASE = "https://hotel.travel.rakuten.co.jp/hotelinfo/plan/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_PLAN_BLOCK = re.compile(r'<li id="(\d+)" class="planThumb"')
_H4 = re.compile(r"<h4>\s*(.*?)\s*</h4>", re.S)
# 객실 코드에 하이픈이 들어가는 시설이 있다(예: 03-13). 플랜ID만 숫자로 고정한다.
# 플랜의 첫 객실은 rm-type-wrapper, 접힌 나머지는 hiddenTyp rm-type-wrapper 라서 둘 다 받는다.
_ROOM_BLOCK = re.compile(r"<li id='(\d+)-([^']+)'[^>]*class='(?:hiddenTyp )?rm-type-wrapper'")
_TITLE = re.compile(r'title="([^"]{2,80})"')
_HINFO = re.compile(r"hinfo\.hotels\s*=\s*(\{.*?\});", re.S)


def build_url(hotel_no, stay, adults, rooms):
    ci = stay["check_in"].split("-")
    co = stay["check_out"].split("-")
    q = {
        "f_nen1": ci[0], "f_tuki1": str(int(ci[1])), "f_hi1": str(int(ci[2])),
        "f_nen2": co[0], "f_tuki2": str(int(co[1])), "f_hi2": str(int(co[2])),
        "f_hak": str(stay["nights"]),
        "f_heya_su": str(rooms),
        "f_otona_su": str(adults),
        "f_flg": "PLAN",
        # 아동 인원. 풀세트로 넣어야 날짜 조건이 실제로 적용된다.
        "f_s1": "0", "f_s2": "0", "f_y1": "0", "f_y2": "0", "f_y3": "0", "f_y4": "0",
    }
    return f"{BASE}{hotel_no}?" + "&".join(f"{k}={v}" for k, v in q.items())


def fetch(hotel, stay, adults, rooms, timeout=40):
    url = build_url(hotel["rakuten_no"], stay, adults, rooms)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ja"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        page = res.read().decode("utf-8", "replace")

    plans = _plan_names(page)
    rooms_map = _room_names(page)
    prices = _prices(page, hotel["rakuten_no"])

    offers = []
    for (plan_id, room_code), total_jpy in prices.items():
        plan_name = plans.get(plan_id, f"플랜 {plan_id}")
        room_name = rooms_map.get(room_code) or rooms_map.get(f"{plan_id}-{room_code}") or room_code
        offers.append(
            {
                "source": "rakuten",
                "seller": "라쿠텐 트래블",
                "room": f"{room_name} / {plan_name}",
                "krw": None,  # 환율은 수집기에서 일괄 환산
                "jpy": total_jpy,
                "free_cancel": None,
                "breakfast": _has_meal(plan_name, _BREAKFAST),
                "dinner": _has_meal(plan_name, _DINNER),
                "official": False,
                "url": url,
            }
        )
    return offers


def _plan_names(page):
    out, starts = {}, [(m.group(1), m.start()) for m in _PLAN_BLOCK.finditer(page)]
    for i, (plan_id, pos) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(page)
        m = _H4.search(page, pos, end)
        if m:
            out[plan_id] = _clean(m.group(1))
    return out


def _room_names(page):
    """객실 코드(ch3t 등) → 객실명. 코드는 시설 내에서 일관되므로 전역 맵으로 충분하다."""
    out = {}
    for m in _ROOM_BLOCK.finditer(page):
        plan_id, code = m.group(1), m.group(2)
        t = _TITLE.search(page, m.end(), m.end() + 6000)
        if not t:
            continue
        name = _clean(t.group(1))
        out.setdefault(code, name)
        out[f"{plan_id}-{code}"] = name
    return out


def _prices(page, hotel_no):
    """(플랜ID, 객실코드) → 세금포함 총액(엔). 0 은 해당 조건 판매 없음."""
    m = _HINFO.search(page)
    if not m:
        return {}
    hotels = json.loads(m.group(1))
    node = hotels.get(str(hotel_no)) or {}
    out = {}
    for plan_id, plan in (node.get("plans") or {}).items():
        for code, room in (plan.get("rooms") or {}).items():
            total = room.get("sumTotalChargeTaxInclusive") or 0
            if total > 0:
                out[(plan_id, code)] = int(total)
    return out


# 「夕朝食付」처럼 한 단어에 두 끼가 붙는 표기가 흔해서 키를 따로 둔다.
_BOTH = ("夕朝食", "朝夕食", "２食付", "2食付", "２食", "1泊2食", "１泊２食")
_BREAKFAST = _BOTH + ("朝食付", "朝食あり", "朝付", "朝食込")
_DINNER = _BOTH + ("夕食付", "夕食あり", "夕付", "会席", "夕食込")
_NO_MEAL = ("素泊", "食事なし", "食事無し")


def _has_meal(plan_name, keys):
    if any(k in plan_name for k in _NO_MEAL):
        return False
    return any(k in plan_name for k in keys)


def _clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s))).strip()
