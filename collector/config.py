"""여행 일정과 모니터링 대상 호텔 정의. 일정·숙소는 변경 없음."""

ADULTS = 3  # 성인 3인 1객실 고정. 2인실은 조회 자체가 안 되도록 이 값으로 필터링된다.
ROOMS = 1

STAYS = [
    {
        "id": "fukuoka",
        "label": "후쿠오카",
        "check_in": "2026-08-20",
        "check_out": "2026-08-22",
        "nights": 2,
        # 라쿠텐 플랜 안내문에서 확인한 현지 별도 징수 세금.
        # 후쿠오카현·시 조례: 1인 1박당, 숙박료 2만엔 미만 200엔 / 2만엔 이상 500엔.
        "local_tax": "숙박세 1인 1박 200엔 별도 (현지 결제) · 3명 2박이면 약 1,200엔",
        "hotels": [
            {
                "key": "basics",
                "name_ko": "더 베이직스 후쿠오카",
                "name_ja": "THE BASICS FUKUOKA",
                "naver_id": "N5041269",
                "rakuten_no": "177662",
                "agoda_id": 9115847,
                "official": "https://www.thebasics.jp/fukuoka/",
            },
            {
                "key": "blossom",
                "name_ko": "더 블러썸 하카타 프리미어",
                "name_ja": "THE BLOSSOM HAKATA Premier",
                "naver_id": "N4849822",
                "rakuten_no": "172876",
                "agoda_id": 16216159,
                "official": "https://www.jrk-hotels.co.jp/Hakata_premier/",
                "official_engine": {
                    "engine": "reservation_jp",
                    "base": "https://go-jrhotel-m.reservation.jp",
                    "code": "blossom-hakatapremier",
                },
            },
            {
                "key": "mitsui",
                "name_ko": "미쓰이 가든 호텔 후쿠오카 나카스",
                "name_ja": "三井ガーデンホテル福岡中洲",
                "naver_id": "N5007190",
                "rakuten_no": "178294",
                "agoda_id": 10560831,
                "official": "https://www.gardenhotels.co.jp/fukuoka-nakasu/",
                "official_engine": {
                    "engine": "reservation_jp",
                    "base": "https://go-gardenhotels.reservation.jp",
                    "code": "mgh033",
                },
            },
            {
                "key": "crosslife",
                "name_ko": "크로스 라이프 하카타 텐진",
                "name_ja": "クロスライフ博多天神",
                "naver_id": "N5303716",
                "rakuten_no": "184507",
                "agoda_id": 33587784,
                "official": "https://crosslife-hakatatenjin.orixhotelsandresorts.com/",
                "official_engine": {
                    "engine": "reservation_jp",
                    "base": "https://go-ohr.reservation.jp",
                    "code": "ohr-cltenjin",
                },
            },
        ],
    },
    {
        "id": "yufuin",
        "label": "유후인",
        "check_in": "2026-08-22",
        "check_out": "2026-08-24",
        "nights": 2,
        # 온천지라 입탕세가 붙는다. 무소우엔 안내문 기준 성인 1인 250엔.
        "local_tax": "입탕세 성인 1인 250엔 별도 (현지 결제)",
        "hotels": [
            {
                "key": "musouen",
                "name_ko": "야마노호텔 무소우엔",
                "name_ja": "由布院温泉 山のホテル 夢想園",
                "naver_id": "KYK1070636135",
                "rakuten_no": "44815",
                "agoda_id": 5646412,
                "official": "https://www.musouen.co.jp/",
            },
            {
                "key": "baien",
                "name_ko": "바이엔",
                "name_ja": "由布院 梅園 GARDEN RESORT",
                "naver_id": "N1736235",
                "rakuten_no": "39494",
                "agoda_id": 1155918,
                "official": "https://www.yufuin-baien.com/",
                # key/secret 은 위젯 JS 에 평문으로 공개돼 있는 값이라 비밀이 아니다.
                "official_engine": {
                    "engine": "tripla",
                    "api": "https://api.guest-relations.com",
                    "hotel_id": "2904",
                    "key": "c8c604a2d81f7b2fe901",
                    "secret": "1882351c176e635f5c64",
                    "book_url": "https://booking.guest-relations.com/booking/result?code=f84d70e4cfcae895f03eb4ca8f94a4b2",
                },
            },
        ],
    },
]
