"""네이버 호텔 GraphQL — 국내외 OTA 10여 곳의 요금을 원화로 한 번에 가져온다.

인증·쿠키 불필요. adultCnt=3 으로 질의하므로 3인 수용 불가 객실은 응답에 아예 없다.
"""

import json
import urllib.request

ENDPOINT = "https://hermes-hotel-svc-api.naver.com/graphql"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

QUERY = (
    "query hotelRates($adultCnt:Int!,$checkIn:String!,$checkOut:String!,$id:String!,"
    "$includeTax:Boolean!,$impArea:SingleImpArea!,$childrenAges:[Int]){"
    "hotelRates(adultCnt:$adultCnt,checkIn:$checkIn,checkOut:$checkOut,id:$id,"
    "includeTax:$includeTax,childrenAges:$childrenAges,impArea:$impArea){"
    "totalCount rates{roomId roomName ota{code npay isOfficialSite} "
    "productFeatures{isFreeCancel isPayLater freeBreakfast freeDinner} "
    "rate{userRate original localRate{currencyCode rate}}} "
    "rateFilter{otas{key name}}}}"
)


def fetch(hotel, stay, adults, timeout=30):
    """호텔 1곳의 전 OTA 요금을 조회해 offer 리스트로 반환."""
    payload = {
        "operationName": "hotelRates",
        "variables": {
            "id": hotel["naver_id"],
            "checkIn": stay["check_in"],
            "checkOut": stay["check_out"],
            "adultCnt": adults,
            "childrenAges": [],
            "includeTax": True,
            # 네이버 상세페이지용 enum. non-null 이라 생략 불가.
            "impArea": "renewalSingle",
        },
        "query": QUERY,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        body = json.load(res)

    if body.get("errors"):
        raise RuntimeError(f"naver graphql error: {body['errors'][:1]}")

    data = (body.get("data") or {}).get("hotelRates")
    if not data:
        return []

    ota_names = {o["key"]: o["name"] for o in (data.get("rateFilter") or {}).get("otas") or []}
    offers = []
    for r in data.get("rates") or []:
        rate = r.get("rate") or {}
        krw = _int(rate.get("userRate"))
        if not krw:
            continue
        local = rate.get("localRate") or {}
        feat = r.get("productFeatures") or {}
        ota = r.get("ota") or {}
        offers.append(
            {
                "source": "naver",
                "seller": ota_names.get(ota.get("code")) or ota.get("code") or "?",
                "room": (r.get("roomName") or "").strip(),
                "krw": krw,
                # localRate 는 OTA 에 따라 null 이므로 없을 수 있다.
                "jpy": _int(local.get("rate")) if local.get("currencyCode") == "JPY" else None,
                "free_cancel": bool(feat.get("isFreeCancel")),
                "breakfast": bool(feat.get("freeBreakfast")),
                "dinner": bool(feat.get("freeDinner")),
                "official": bool(ota.get("isOfficialSite")),
                "url": _detail_url(hotel, stay, adults),
            }
        )
    return offers


def _detail_url(hotel, stay, adults):
    return (
        f"https://hotels.naver.com/accommodation/detail/hotels/{hotel['naver_id']}/rates"
        f"?checkIn={stay['check_in']}&checkOut={stay['check_out']}&adultCnt={adults}"
    )


def _int(v):
    try:
        return int(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None
