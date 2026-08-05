/* latest.json + history.jsonl 을 읽어 카드로 그린다. 의존성 없음. */

const won = n => n.toLocaleString('ko-KR');
const $ = (t, cls, txt) => {
  const e = document.createElement(t);
  if (cls) e.className = cls;
  if (txt != null) e.textContent = txt;
  return e;
};

// 캐시 때문에 옛날 값이 보이는 걸 막는다 (Pages 는 정적 파일을 오래 캐싱한다).
const bust = url => `${url}?v=${Math.floor(Date.now() / 60000)}`;

init();

async function init() {
  let data, history;
  try {
    [data, history] = await Promise.all([
      fetch(bust('data/latest.json')).then(r => r.json()),
      fetch(bust('data/history.jsonl')).then(r => r.ok ? r.text() : '').catch(() => ''),
    ]);
  } catch (e) {
    document.getElementById('app').innerHTML =
      '<div class="loading">요금 데이터를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.</div>';
    return;
  }

  const series = parseHistory(history);
  document.getElementById('updated').textContent =
    `${fmtTime(data.collected_at)} 기준 · ${ago(data.collected_at)}`;
  document.getElementById('pax').textContent = `성인 ${data.adults}명 · ${data.rooms}객실`;
  document.getElementById('footer-note').textContent =
    `적용 환율 100엔 = 약 ${Math.round(data.fx_jpy_krw * 100).toLocaleString('ko-KR')}원 ` +
    `(네이버가 제공하는 원화·엔화 요금에서 역산한 값입니다.)`;

  const app = document.getElementById('app');
  app.innerHTML = '';
  data.stays.forEach(stay => app.appendChild(renderStay(stay, series)));
}

function renderStay(stay, series) {
  const sec = $('section', 'stay');
  const head = $('div', 'stay-head');
  head.appendChild($('h2', null, stay.label));
  head.appendChild($('span', 'dates',
    `${fmtDate(stay.check_in)} – ${fmtDate(stay.check_out)} · ${stay.nights}박`));
  sec.appendChild(head);

  // 가장 싼 곳이 위로 오게. 일행이 순위를 바로 보게 하려는 의도.
  const hotels = [...stay.hotels].sort((a, b) =>
    (a.best?.krw ?? Infinity) - (b.best?.krw ?? Infinity));

  hotels.forEach((h, i) => sec.appendChild(renderHotel(h, stay, i, series)));
  return sec;
}

function renderHotel(h, stay, idx, series) {
  const card = $('div', 'card' + (idx === 0 && h.best ? ' cheapest' : ''));
  const top = $('div', 'card-top');

  const left = $('div');
  const title = $('div');
  title.style.cssText = 'display:flex;gap:8px;align-items:center';
  title.appendChild($('span', 'rank', String(idx + 1)));
  title.appendChild($('h3', 'hotel-name', h.name_ko));
  left.appendChild(title);
  left.appendChild($('p', 'hotel-sub', h.name_ja));
  top.appendChild(left);

  const right = $('div', 'price-col');
  if (h.best) {
    const p = $('div', 'price');
    p.append(won(h.best.krw), Object.assign($('small'), { textContent: '원' }));
    right.appendChild(p);

    const sub = $('div', 'price-sub');
    sub.textContent = `¥${won(h.best.jpy)} · 1인 ${won(Math.round(h.best.krw / 3))}원`;
    right.appendChild(sub);

    const key = `${stay.id}/${h.key}`;
    const d = delta(series[key]);
    if (d) {
      const el = $('div', 'price-sub');
      const tag = $('span', 'delta ' + (d < 0 ? 'down' : 'up'),
        `${d < 0 ? '▼' : '▲'} ${won(Math.abs(d))}원`);
      el.append(tag, ' 직전 대비');
      right.appendChild(el);
    }
  } else {
    right.appendChild($('div', 'price-sub', '조회 실패'));
  }
  top.appendChild(right);
  card.appendChild(top);

  if (h.best) {
    const b = $('div', 'badges');
    if (h.record_low) b.appendChild($('span', 'badge record', '★ 역대 최저'));
    // 지금이 최저가 아니면, 얼마까지 내려간 적 있는지 같이 보여준다.
    else if (h.prior_low_krw && h.prior_low_krw < h.best.krw) {
      b.appendChild($('span', 'badge record',
        `역대 최저 ${won(h.prior_low_krw)}원 (지금 +${won(h.best.krw - h.prior_low_krw)})`));
    }
    b.appendChild($('span', 'badge seller', h.best.seller));
    if (h.best.dinner && h.best.breakfast) b.appendChild($('span', 'badge meal', '1박2식'));
    else if (h.best.breakfast) b.appendChild($('span', 'badge meal', '조식 포함'));
    if (h.best.capacity) b.appendChild($('span', 'badge', `정원 ${h.best.capacity}`));
    if (h.best.free_cancel) b.appendChild($('span', 'badge cancel', '무료 취소'));
    if (h.best.official) b.appendChild($('span', 'badge', '공식 사이트'));
    if (h.best.krw_estimated) b.appendChild($('span', 'badge', '원화 환산값'));
    card.appendChild(b);

    card.appendChild($('div', 'room', h.best.room));
    card.appendChild(spark(series[`${stay.id}/${h.key}`]));
  }

  const links = $('div', 'links');
  links.appendChild(link(h.naver_url, '네이버에서 예약', 'primary'));
  links.appendChild(link(h.rakuten_url, '라쿠텐에서 예약'));
  links.appendChild(link(h.official, '공식 사이트'));
  card.appendChild(links);

  if (h.offers?.length > 1) card.appendChild(offerTable(h));

  const errs = Object.entries(h.errors || {});
  if (errs.length) {
    card.appendChild($('div', 'err',
      '일부 판매처 조회 실패: ' + errs.map(([k, v]) => `${k} (${v})`).join(', ')));
  }
  return card;
}

function offerTable(h) {
  const d = $('details');
  d.appendChild($('summary', null, `판매처별 요금 ${h.offers.length}건 비교 (전체 ${h.offer_count}건 중)`));
  const t = $('table');
  t.innerHTML = '<thead><tr><th>판매처</th><th>객실 / 플랜</th><th style="text-align:right">총액</th></tr></thead>';
  const tb = $('tbody');
  h.offers.forEach(o => {
    const tr = $('tr');
    tr.appendChild($('td', null, o.seller));
    const room = $('td');
    room.textContent = o.room;
    const tags = [];
    if (o.dinner && o.breakfast) tags.push('1박2식');
    else if (o.breakfast) tags.push('조식');
    else if (o.breakfast === false && o.dinner === false) tags.push('식사 없음');
    if (o.capacity) tags.push(`정원 ${o.capacity}`);
    if (o.free_cancel) tags.push('무료취소');
    if (tags.length) {
      const s = $('span');
      s.style.cssText = 'color:var(--muted);font-size:.92em';
      s.textContent = ` · ${tags.join(' · ')}`;
      room.appendChild(s);
    }
    tr.appendChild(room);
    const price = $('td', 'num');
    price.append(`${won(o.krw)}원`, $('br'), Object.assign($('span'), {
      textContent: `¥${won(o.jpy)}`,
      style: 'color:var(--muted);font-weight:400',
    }));
    tr.appendChild(price);
    tb.appendChild(tr);
  });
  t.appendChild(tb);
  d.appendChild(t);
  return d;
}

function link(href, label, cls) {
  const a = $('a', cls, label);
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener';
  return a;
}

/* ── 가격 추이 ───────────────────────────── */

function parseHistory(text) {
  const out = {};
  text.split('\n').forEach(line => {
    if (!line.trim()) return;
    let r;
    try { r = JSON.parse(line); } catch { return; }
    if (!r.krw) return;
    (out[`${r.stay}/${r.hotel}`] ||= []).push({ t: new Date(r.t), krw: r.krw });
  });
  Object.values(out).forEach(a => a.sort((x, y) => x.t - y.t));
  return out;
}

function delta(pts) {
  if (!pts || pts.length < 2) return 0;
  return pts.at(-1).krw - pts.at(-2).krw;
}

function spark(pts) {
  const box = $('div', 'spark');
  if (!pts || pts.length < 2) {
    box.appendChild($('div', 'spark-empty',
      '가격 추이는 데이터가 2회 이상 쌓이면 표시됩니다.'));
    return box;
  }

  const W = 300, H = 46, pad = 4;
  const ys = pts.map(p => p.krw);
  const min = Math.min(...ys), max = Math.max(...ys);
  const flat = max === min; // 값이 안 변했으면 바닥에 붙이지 말고 가운데 직선으로 그린다
  const x = i => pad + (i * (W - pad * 2)) / (pts.length - 1);
  const y = v => flat ? H / 2 : H - pad - ((v - min) / (max - min)) * (H - pad * 2);
  const line = pts.map((p, i) => `${x(i)},${y(p.krw)}`).join(' ');
  const lowIdx = ys.indexOf(min);

  box.innerHTML = `
<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img"
     aria-label="최근 가격 추이. 최저 ${won(min)}원, 최고 ${won(max)}원.">
  <polygon points="${line} ${x(pts.length - 1)},${H} ${x(0)},${H}"
           fill="var(--accent)" opacity=".08"/>
  <polyline points="${line}" fill="none" stroke="var(--accent)"
            stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"
            vector-effect="non-scaling-stroke"/>
  <circle cx="${x(lowIdx)}" cy="${y(min)}" r="3" fill="var(--gold)"/>
  <circle cx="${x(pts.length - 1)}" cy="${y(pts.at(-1).krw)}" r="3" fill="var(--accent)"/>
</svg>`;

  const cap = $('div', 'spark-empty');
  cap.style.marginTop = '3px';
  cap.textContent = flat
    ? `최근 ${pts.length}회 확인 · 변동 없음 (${won(min)}원)`
    : `최근 ${pts.length}회 · 최저 ${won(min)}원 / 최고 ${won(max)}원`;
  box.appendChild(cap);
  return box;
}

/* ── 시간 표기 ───────────────────────────── */

function fmtDate(s) {
  const [, m, d] = s.split('-');
  return `${+m}월 ${+d}일`;
}

function fmtTime(iso) {
  return new Date(iso).toLocaleString('ko-KR', {
    month: 'numeric', day: 'numeric', hour: 'numeric', minute: '2-digit',
    timeZone: 'Asia/Seoul',
  });
}

function ago(iso) {
  const mins = Math.round((Date.now() - new Date(iso)) / 60000);
  if (mins < 1) return '방금 확인';
  if (mins < 60) return `${mins}분 전 확인`;
  const h = Math.round(mins / 60);
  return h < 24 ? `${h}시간 전 확인` : `${Math.round(h / 24)}일 전 확인`;
}
