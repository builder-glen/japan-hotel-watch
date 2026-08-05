"""호텔 공식 홈페이지 예약엔진 직접 조회.

OTA 집계 사이트(네이버)에도, 일본 내수 사이트(라쿠텐)에도 안 잡히는 값이다.
실제로 크로스라이프·블러썸은 공식이 OTA보다 4~5만원 싸다.
반대로 공식이 훨씬 비싼 곳도 있어서, 크롤링 없이는 방향조차 예측이 안 된다.

엔진은 두 종류:
  reservation_jp — 호텔 3곳이 공유하는 Laravel+Livewire 엔진
  tripla         — 바이엔이 쓰는 Tripla 예약 위젯 (REST JSON)
"""

import html as html_mod
import json
import re
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_NO_MEAL = ("素泊", "食事なし", "食事無し")
_BREAKFAST = ("朝食", "朝付")
_DINNER = ("夕食", "夕付", "会席", "２食", "2食")


def fetch(hotel, stay, adults, rooms=1, timeout=60):
    cfg = hotel.get("official_engine")
    if not cfg:
        return []
    if cfg["engine"] == "reservation_jp":
        return _reservation_jp(cfg, stay, adults, rooms, timeout)
    if cfg["engine"] == "tripla":
        return _tripla(cfg, stay, adults, timeout)
    raise ValueError(f"unknown engine: {cfg['engine']}")


# ── reservation.jp ────────────────────────────────────────────────────────
def _reservation_jp(cfg, stay, adults, rooms, timeout):
    """1회차 GET 은 껍데기만 주고 쿠키를 심는다. 같은 쿠키로 한 번 더 GET 해야
    요금이 박힌 SSR 페이지가 온다. 3회차부터는 다시 껍데기라 매번 새 쿠키로 시작."""
    q = urllib.parse.urlencode({
        "checkin_date": stay["check_in"].replace("-", ""),
        "checkout_date": stay["check_out"].replace("-", ""),
        "adults": adults,
        "child1": 0, "child2": 0, "child3": 0, "child4": 0, "child5": 0,
        "children": 0, "rooms": rooms, "dayuseFlg": 0, "sort": 1,
        "dateUndecidedFlg": 0,
    })
    url = f"{cfg['base'].rstrip('/')}/ja/hotels/{cfg['code']}/plans?{q}"

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar()))
    opener.addheaders = [
        ("User-Agent", UA),
        ("Accept", "text/html,application/xhtml+xml"),
        ("Accept-Language", "ja,en;q=0.8"),
    ]
    page = ""
    for _ in range(2):
        with opener.open(url, timeout=timeout) as res:
            page = res.read().decode("utf-8", "replace")

    offers = []
    for snap in re.findall(r'wire:snapshot="([^"]*)"', page):
        try:
            node = json.loads(html_mod.unescape(snap))
        except json.JSONDecodeError:
            continue
        if (node.get("memo") or {}).get("name") != "modal-button-reservation":
            continue
        data = node.get("data") or {}
        try:
            plan, room, sub = data["plan"][0], data["room"][0], data["subItem"][0]
        except (KeyError, IndexError, TypeError):
            continue
        total = sub.get("totalPrice")
        if not total:
            continue
        name = plan.get("planName") or ""
        offers.append(_offer(
            room=f"{room.get('roomName') or ''} / {name}".strip(" /"),
            jpy=int(total),
            breakfast=_has(name, _BREAKFAST),
            dinner=_has(name, _DINNER),
            url=url,
        ))
    return offers


# ── Tripla ────────────────────────────────────────────────────────────────
def _tripla(cfg, stay, adults, timeout):
    """위젯 JS 에 평문으로 박혀 있는 key/secret 으로 세션 토큰을 받아 조회한다."""
    token_req = urllib.request.Request(
        "https://idp.tripla.ai/book/api/client_sessions",
        data=json.dumps({"key": cfg["key"], "secret": cfg["secret"]}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(token_req, timeout=timeout) as res:
        token = json.load(res)["data"]["client_session"]

    q = urllib.parse.urlencode({
        "rooms[][checkin_date]": stay["check_in"],
        "rooms[][checkout_date]": stay["check_out"],
        "rooms[][adults]": adults,
        "rooms[][children]": 0,
        "order": "recommended", "is_day_use": "false",
        "is_including_occupied": "false", "bookable": "true",
        "type": "plan", "mcp_locale": "ja-JP",
    })
    req = urllib.request.Request(
        f"{cfg['api']}/book/hotels/{cfg['hotel_id']}/rooms?{q}",
        headers={
            "client-session": token,
            "app-version": "tripla-booking-widget/1.0",
            "tripla-locale": "ja",
            "x-tripla-tier": "basic",
            "content-type": "application/json",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.load(res)

    offers = []
    for plan in body.get("plans") or []:
        meal = plan.get("meal_status") or ""
        for room in plan.get("rooms") or []:
            if room.get("availability") not in (None, "available"):
                continue
            # total_price 는 세금 제외다. 화면 표시 총액은 여기에 tax 를 더한 값.
            base, tax = room.get("total_price"), room.get("tax") or 0
            if not base:
                continue
            offers.append(_offer(
                room=f"{room.get('room_type_name') or ''} / {plan.get('name') or ''}".strip(" /"),
                jpy=int(base) + int(tax),
                breakfast="朝食" in meal,
                dinner="夕食" in meal,
                url=cfg["book_url"],
            ))
    return offers


# 나이·거주지·신분 조건이 붙은 플랜. 30대 여성 3인에는 해당이 없는데
# 값이 싸서 최저가 자리를 차지해 버리므로 따로 표시하고 대표가에서 뺀다.
_CONDITIONAL = ("歳以上", "才以上", "県民", "市民", "在住", "学生", "シニア", "会員限定")


def _offer(room, jpy, breakfast, dinner, url):
    return {
        "source": "official",
        "seller": "공식 홈페이지",
        "room": room,
        "krw": None,  # 환율은 수집기에서 일괄 환산
        "jpy": jpy,
        "free_cancel": None,
        "breakfast": breakfast,
        "dinner": dinner,
        "official": True,
        "conditional": any(k in room for k in _CONDITIONAL),
        "url": url,
    }


def _has(name, keys):
    if any(k in name for k in _NO_MEAL):
        return False
    return any(k in name for k in keys)
