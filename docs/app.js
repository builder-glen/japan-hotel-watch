/* latest.json + history.jsonl 을 읽어 카드로 그린다. 의존성 없음. */

const won = n => n.toLocaleString('ko-KR');
let PAX = 3; // latest.json 의 adults 로 덮어씀
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
  PAX = data.adults || 3;
  document.getElementById('updated').textContent =
    `${fmtTime(data.collected_at)} 기준 · ${ago(data.collected_at)}`;
  document.getElementById('pax').textContent = `성인 ${data.adults}명 · ${data.rooms}객실`;
  document.getElementById('footer-note').textContent =
    `적용 환율 100엔 = 약 ${Math.round(data.fx_jpy_krw * 100).toLocaleString('ko-KR')}원 ` +
    `(네이버가 제공하는 원화·엔화 요금에서 역산한 값입니다.)`;

  const app = document.getElementById('app');
  app.innerHTML = '';
  const health = sourceHealth(data);
  if (health) app.appendChild(health);
  data.stays.forEach(stay => app.appendChild(renderStay(stay, series)));
}

function renderStay(stay, series) {
  const sec = $('section', 'stay');
  const head = $('div', 'stay-head');
  head.appendChild($('h2', null, stay.label));
  head.appendChild($('span', 'dates',
    `${fmtDate(stay.check_in)} – ${fmtDate(stay.check_out)} · ${stay.nights}박`));
  sec.appendChild(head);

  const basis = $('div', 'basis');
  basis.appendChild($('strong', null,
    `아래 금액은 모두 ${stay.nights}박 전체 총액 · 성인 ${PAX}명 1객실 합계입니다.`));
  basis.appendChild($('span', null, ' 1박 요금도, 1인 요금도 아닙니다. 소비세는 포함돼 있습니다.'));
  if (stay.local_tax) basis.appendChild($('div', 'basis-tax', `추가 부담: ${stay.local_tax}`));
  sec.appendChild(basis);

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
    sub.textContent = `¥${won(h.best.jpy)} · 1인 ${won(Math.round(h.best.krw / PAX))}원`;
    right.appendChild(sub);

    // 총액인지 1박 요금인지 헷갈리면 비교가 통째로 어긋난다. 매번 명시한다.
    right.appendChild($('div', 'price-basis', `${stay.nights}박 총액 · ${PAX}명 합계`));

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
    // 료칸은 식사 포함 여부가 금액의 대부분을 좌우한다. 대표 가격에 반드시 같이 보여준다.
    if (h.best.dinner && h.best.breakfast) b.appendChild($('span', 'badge meal', '1박2식'));
    else if (h.best.breakfast) b.appendChild($('span', 'badge meal', '조식 포함'));
    else if (h.best.breakfast === false && h.best.dinner === false)
      b.appendChild($('span', 'badge', '식사 없음'));
    if (h.best.age_min) b.appendChild($('span', 'badge stale', `${agoMin(h.best.age_min)} 확인값`));
    if (h.best.capacity) b.appendChild($('span', 'badge', `정원 ${h.best.capacity}`));
    if (h.best.free_cancel) b.appendChild($('span', 'badge cancel', '무료 취소'));
    if (h.best.official) b.appendChild($('span', 'badge', '공식 사이트'));
    if (h.best.krw_estimated) b.appendChild($('span', 'badge', '원화 환산값'));
    card.appendChild(b);

    card.appendChild($('div', 'room', h.best.room));
    const xc = crossCheck(h.by_source);
    if (xc) card.appendChild(xc);
    card.appendChild(spark(series[`${stay.id}/${h.key}`]));
  }

  const links = $('div', 'links');
  // 첫 버튼은 지금 최저가를 실제로 파는 곳으로 바로 보낸다.
  if (h.best?.url) links.appendChild(link(h.best.url, `최저가 보기 · ${h.best.seller}`, 'primary'));
  links.appendChild(link(h.naver_url, '네이버 비교'));
  links.appendChild(link(h.rakuten_url, '라쿠텐'));
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

/** 조회 경로 중 실패한 게 있으면 알린다.
 *  한 경로가 통째로 빠진 채 계산된 "최저가"를 그냥 믿게 두면 안 된다. */
function sourceHealth(data) {
  const hotels = data.stays.flatMap(s => s.hotels);
  const failed = {};
  hotels.forEach(h => Object.keys(h.errors || {}).forEach(src => {
    failed[src] = (failed[src] || 0) + 1;
  }));
  const names = Object.keys(failed);
  if (!names.length) return null;

  // 실패한 경로가 직전 값으로 살아있는지 확인 — 살아있으면 공백이 아니라 지연일 뿐이다.
  const carried = names.filter(s =>
    hotels.some(h => h.by_source?.[s] && h.by_source[s].age_min > 0));

  const box = $('div', 'health');
  box.appendChild($('strong', null, '이번 조회에서 응답이 없던 경로가 있습니다. '));
  box.appendChild(document.createTextNode(
    names.map(s => `${SOURCE_LABEL[s] || s} ${failed[s]}곳`).join(', ') + '. ' +
    (carried.length
      ? '해당 경로는 마지막으로 받은 값을 그대로 쓰고 있습니다. 각 금액 옆의 확인 시각을 봐주세요.'
      : '아래 금액은 나머지 경로만으로 계산된 값이라, 평소보다 비싸 보일 수 있습니다.')));
  return box;
}

/** 값이 몇 분 전 것인지 짧게. 0이면 방금 값이라 표기하지 않는다. */
function agoMin(m) {
  if (!m) return '';
  if (m < 60) return `${m}분 전`;
  const h = Math.round(m / 60);
  return h < 24 ? `${h}시간 전` : `${Math.round(h / 24)}일 전`;
}

const SOURCE_LABEL = {
  naver: '네이버 (해외 OTA 10곳)',
  agoda: '아고다 직접',
  official: '공식 홈페이지',
  rakuten: '라쿠텐 (일본 내수)',
};

/** 서로 독립적인 네 경로의 최저가를 나란히 보여준다.
 *  한 숫자를 믿게 하는 것보다, 값이 갈리는 걸 보이게 하는 쪽이 정직하다. */
function crossCheck(bySource) {
  const rows = Object.entries(bySource || {}).sort((a, b) => a[1].krw - b[1].krw);
  if (rows.length < 2) return null;

  const box = $('div', 'xcheck');
  box.appendChild($('div', 'xcheck-title', `조회 경로 ${rows.length}곳 비교`));

  const lo = rows[0][1].krw, hi = rows.at(-1)[1].krw;
  rows.forEach(([src, v], i) => {
    const r = $('div', 'xcheck-row' + (i === 0 ? ' win' : ''));
    r.appendChild($('span', null, SOURCE_LABEL[src] || src));
    const gapTxt = i === 0 ? '' : ` (+${won(v.krw - lo)})`;
    const val = $('span', 'xcheck-val', `${won(v.krw)}원${gapTxt}`);
    if (v.age_min) {
      // 이번 조회에서 못 받아 직전 값을 쓰는 경로는 언제 값인지 밝힌다.
      const old = $('span', 'xcheck-age', ` ${agoMin(v.age_min)}`);
      val.appendChild(old);
    }
    r.appendChild(val);
    box.appendChild(r);
  });

  box.appendChild($('div', 'xcheck-note',
    `가장 싼 경로와 가장 비싼 경로가 ${won(hi - lo)}원 차이납니다.` +
    ' 경로마다 파는 객실·플랜이 달라서 생기는 차이이니, 아래 비교표에서 객실명을 확인하세요.'));
  return box;
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

  const wrap = $('div', 'chart');
  const tip = $('div', 'chart-tip');
  tip.hidden = true;
  const canvas = $('div', 'chart-canvas');
  wrap.append(canvas, tip);
  box.appendChild(wrap);
  box.appendChild(caption(pts));

  // viewBox 폭을 실제 렌더 폭에 맞춰야 1 유저단위 = 1 CSS픽셀이 된다.
  // 고정 폭(300)으로 두면 SVG 가 좌우에 여백을 두고 가운데 정렬돼서
  // 마우스 좌표와 그래프 좌표가 어긋난다. 폭이 바뀌면 다시 그린다.
  new ResizeObserver(() => drawChart(canvas, tip, pts)).observe(canvas);
  return box;
}

function caption(pts) {
  const ys = pts.map(p => p.krw);
  const min = Math.min(...ys), max = Math.max(...ys);
  const span = `${fmtShort(pts[0].t)} ~ ${fmtShort(pts.at(-1).t)}`;
  return $('div', 'spark-empty', max === min
    ? `${span} · ${pts.length}회 확인 · 변동 없음`
    : `${span} · ${pts.length}회 확인 · 최저 ${won(min)}원 / 최고 ${won(max)}원`);
}

function drawChart(canvas, tip, pts) {
  const W = Math.round(canvas.clientWidth);
  if (W < 40) return; // 아직 레이아웃이 안 잡힘

  const H = 64, padX = 6, padTop = 16, padBot = 14;
  const ys = pts.map(p => p.krw);
  const min = Math.min(...ys), max = Math.max(...ys);
  const flat = max === min; // 값이 안 변했으면 바닥에 붙이지 말고 가운데 직선으로
  const x = i => padX + (i * (W - padX * 2)) / (pts.length - 1);
  const y = v => flat
    ? (padTop + H - padBot) / 2
    : H - padBot - ((v - min) / (max - min)) * (H - padTop - padBot);

  const line = pts.map((p, i) => `${x(i)},${y(p.krw)}`).join(' ');
  const lowIdx = ys.indexOf(min);
  const lastIdx = pts.length - 1;

  // 점이 많아지면 전부 찍으면 지저분해서 일정 간격으로 솎아낸다.
  // 단 최저점과 마지막 점은 무조건 남긴다 — 이 둘이 판단 근거다.
  const step = Math.max(1, Math.ceil(pts.length / 30));
  const dots = pts.map((_, i) => i)
    .filter(i => i % step === 0 || i === lowIdx || i === lastIdx);

  canvas.innerHTML = `
<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img"
     aria-label="가격 추이 ${pts.length}회. 최저 ${won(min)}원, 최고 ${won(max)}원, 현재 ${won(pts.at(-1).krw)}원.">
  <polygon points="${line} ${x(lastIdx)},${H - padBot} ${x(0)},${H - padBot}"
           fill="var(--accent)" opacity=".08"/>
  <polyline points="${line}" fill="none" stroke="var(--accent)"
            stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
  ${dots.map(i => `<circle cx="${x(i)}" cy="${y(pts[i].krw)}" r="2"
     fill="${i === lowIdx ? 'var(--gold)' : 'var(--accent)'}"/>`).join('')}
  <circle cx="${x(lastIdx)}" cy="${y(pts[lastIdx].krw)}" r="3.4" fill="var(--accent)"/>
  ${flat || lowIdx === lastIdx ? '' : `<text x="${labelX(x(lowIdx))}" y="${y(min) + 11}" class="pt-label low"
     text-anchor="${anchor(x(lowIdx))}">${won(min)}</text>`}
  <text x="${labelX(x(lastIdx))}" y="${y(pts[lastIdx].krw) - 6}" class="pt-label now"
        text-anchor="${anchor(x(lastIdx))}">${won(pts[lastIdx].krw)}</text>
  <g class="hover-layer"></g>
</svg>`;

  const svg = canvas.querySelector('svg');
  const layer = svg.querySelector('.hover-layer');

  const show = i => {
    const p = pts[i];
    layer.innerHTML =
      `<line x1="${x(i)}" y1="0" x2="${x(i)}" y2="${H}" class="hover-line"/>` +
      `<circle cx="${x(i)}" cy="${y(p.krw)}" r="4" class="hover-dot"/>`;
    tip.hidden = false;
    tip.textContent = `${fmtShort(p.t)} · ${won(p.krw)}원`;
    // 1 유저단위 = 1 픽셀이므로 그대로 쓴다. 좌우로 잘리지 않게만 가둔다.
    const half = tip.offsetWidth / 2 || 40;
    tip.style.left = `${Math.min(Math.max(x(i), half), W - half)}px`;
  };
  const hide = () => { layer.innerHTML = ''; tip.hidden = true; };

  const nearest = ev => {
    const r = svg.getBoundingClientRect();
    const vx = ev.clientX - r.left;
    let best = 0, bd = Infinity;
    pts.forEach((_, i) => {
      const d = Math.abs(x(i) - vx);
      if (d < bd) { bd = d; best = i; }
    });
    return best;
  };

  svg.addEventListener('pointermove', ev => show(nearest(ev)));
  svg.addEventListener('pointerdown', ev => show(nearest(ev)));
  svg.addEventListener('pointerleave', hide);
  svg.addEventListener('pointercancel', hide);

  // 라벨이 좌우 끝에서 잘리지 않게 앵커를 바꾼다.
  function anchor(px) { return px < 40 ? 'start' : px > W - 40 ? 'end' : 'middle'; }
  function labelX(px) { return px < 40 ? padX : px > W - 40 ? W - padX : px; }
}

function fmtShort(d) {
  const parts = new Intl.DateTimeFormat('ko-KR', {
    month: 'numeric', day: 'numeric', hour: '2-digit',
    hour12: false, timeZone: 'Asia/Seoul',
  }).formatToParts(d);
  const get = t => parts.find(p => p.type === t)?.value ?? '';
  return `${get('month')}/${get('day')} ${get('hour')}시`;
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
