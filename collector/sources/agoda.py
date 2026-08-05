"""아고다 직접 조회. 표준 라이브러리만 쓴다(Playwright 불필요).

네이버도 아고다 요금을 주지만 **일부 공급 채널을 빠뜨린다.**
블러썸 기준 네이버-아고다는 918,596원인데 직접 조회하면 채널 21 로 825,613원이다.
9만원 차이라 이 소스를 따로 두는 값어치가 있다.

동작 원리
 1) 아고다 '호텔 상세' 페이지를 1회 GET → agoda.user.03 쿠키의 UserId 확보
    (홈으로 워밍업하면 저가 채널이 응답에서 빠진다)
 2) x-gate-meta = base64("<epoch_ms>|<UserId>|<API 경로>")
    여기 UUID 가 쿠키의 UserId 와 일치해야 저가 채널까지 내려온다
 3) GetSecondaryData 로 요금 JSON 수신
"""

import base64
import http.cookiejar
import json
import re
import time
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
API_PATH = "/api/cronos/property/BelowFoldParams/GetSecondaryData"
WARMUP = "https://www.agoda.com/ko-kr/the-basics-fukuoka/hotel/fukuoka-jp.html"

_session = None  # (opener, user_id) — 호텔마다 새로 만들 필요 없다


def _get_session(timeout):
    global _session
    if _session is None:
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        req = urllib.request.Request(
            WARMUP, headers={"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
        opener.open(req, timeout=timeout).read()
        raw = urllib.parse.unquote(
            next((c.value for c in jar if c.name == "agoda.user.03"), ""))
        m = re.search(r"UserId=([0-9a-f-]{36})", raw)
        if not m:
            raise RuntimeError("agoda.user.03 UserId 확보 실패")
        _session = (opener, m.group(1))
    return _session


def fetch(hotel, stay, adults, rooms=1, timeout=90):
    hotel_id = hotel.get("agoda_id")
    if not hotel_id:
        return []
    opener, user_id = _get_session(timeout)

    qs = urllib.parse.urlencode({
        "checkIn": stay["check_in"], "los": stay["nights"], "adults": adults,
        "rooms": rooms, "currency": "KRW", "hotel_id": hotel_id, "all": "false",
        "isHostPropertiesEnabled": "false", "price_view": 0,
        "sessionid": "", "pagetypeid": 7, "attributionInfos": "32|-1",
    })
    gate = base64.b64encode(
        f"{int(time.time() * 1000)}|{user_id}|{API_PATH}".encode()).decode()
    req = urllib.request.Request(
        f"https://www.agoda.com{API_PATH}?{qs}",
        headers={
            "User-Agent": UA, "Accept": "application/json",
            "Accept-Language": "ko-KR", "ag-language-locale": "ko-kr",
            "ag-language-id": "9", "cr-currency-code": "KRW",
            "cr-currency-id": "26", "x-gate-meta": gate,
        },
    )
    with opener.open(req, timeout=timeout) as res:
        data = json.load(res)

    # 응답이 요청 조건을 그대로 되돌려주므로 매 요청 자체 검증이 된다.
    crit = data.get("hotelSearchCriteria") or {}
    if crit.get("adults") != adults or not str(crit.get("checkInDate", "")).startswith(stay["check_in"]):
        raise RuntimeError(f"조회 조건 불일치: {crit.get('checkInDate')} adults={crit.get('adults')}")

    offers = []
    for master in (data.get("roomGridData") or {}).get("masterRooms") or []:
        for room in master.get("rooms") or []:
            # isFit 을 안 보면 성인 1명짜리 플랜이 최저가로 잡힌다.
            if not room.get("isFit") or (room.get("numberOfGuests") or 0) < adults:
                continue
            total = (room.get("totalPrice") or {}).get("display")
            if not total:
                continue
            offers.append({
                "source": "agoda",
                "seller": "아고다 직접",
                "room": f"{master.get('name') or ''} / {room.get('name') or ''}".strip(" /"),
                "krw": int(total),  # 전 숙박일 총액, 세금·봉사료 포함
                "jpy": None,
                "free_cancel": bool(room.get("isFreeCancellation")),
                "breakfast": bool(room.get("isBreakfastIncluded")),
                "dinner": False,
                "official": False,
                "channel": room.get("channelId"),
                "url": _page_url(hotel, stay, adults, rooms),
            })
    return offers


def _page_url(hotel, stay, adults, rooms):
    q = urllib.parse.urlencode({
        "checkIn": stay["check_in"], "los": stay["nights"],
        "adults": adults, "rooms": rooms, "currency": "KRW",
    })
    return f"https://www.agoda.com/ko-kr/hotel/{hotel['agoda_id']}.html?{q}"
