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
        "hotels": [
            {
                "key": "basics",
                "name_ko": "더 베이직스 후쿠오카",
                "name_ja": "THE BASICS FUKUOKA",
                "naver_id": "N5041269",
                "rakuten_no": "177662",
                "official": "https://www.thebasics.jp/fukuoka/",
            },
            {
                "key": "blossom",
                "name_ko": "더 블러썸 하카타 프리미어",
                "name_ja": "THE BLOSSOM HAKATA Premier",
                "naver_id": "N4849822",
                "rakuten_no": "172876",
                "official": "https://www.jrk-hotels.co.jp/Hakata_premier/",
            },
            {
                "key": "mitsui",
                "name_ko": "미쓰이 가든 호텔 후쿠오카 나카스",
                "name_ja": "三井ガーデンホテル福岡中洲",
                "naver_id": "N5007190",
                "rakuten_no": "178294",
                "official": "https://www.gardenhotels.co.jp/fukuoka-nakasu/",
            },
            {
                "key": "crosslife",
                "name_ko": "크로스 라이프 하카타 텐진",
                "name_ja": "クロスライフ博多天神",
                "naver_id": "N5303716",
                "rakuten_no": "184507",
                "official": "https://crosslife-hakatatenjin.orixhotelsandresorts.com/",
            },
        ],
    },
    {
        "id": "yufuin",
        "label": "유후인",
        "check_in": "2026-08-22",
        "check_out": "2026-08-24",
        "nights": 2,
        "hotels": [
            {
                "key": "musouen",
                "name_ko": "야마노호텔 무소우엔",
                "name_ja": "由布院温泉 山のホテル 夢想園",
                "naver_id": "KYK1070636135",
                "rakuten_no": "44815",
                "official": "https://www.musouen.co.jp/",
            },
            {
                "key": "baien",
                "name_ko": "바이엔",
                "name_ja": "由布院 梅園 GARDEN RESORT",
                "naver_id": "N1736235",
                "rakuten_no": "39494",
                "official": "https://www.yufuin-baien.com/",
            },
        ],
    },
]
