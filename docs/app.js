async function main() {
  const metaEl = document.getElementById("meta");
  const stocksEl = document.getElementById("stocks");
  const zgbEl = document.getElementById("zgb");
  const zgkEl = document.getElementById("zgk");

  let data;
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    data = await res.json();
  } catch (e) {
    metaEl.textContent = "讀取 data.json 失敗。先去 GitHub Actions 跑一次 Update data。";
    metaEl.classList.add("bad");
    return;
  }

  metaEl.textContent = `更新時間：${data.generated_at}｜最新交易日：${data.latest_trading_day}｜前一交易日：${data.prev_trading_day}`;

  // Stocks
  stocksEl.innerHTML = "";
  for (const s of data.stocks) {
    const card = document.createElement("div");
    card.className = "card";
    const price = s.price || {};
    const f = s.foreign_net_shares || {};
    card.innerHTML = `
      <div class="row">
        <div>
          <div class="kv">
            <span class="pill">${s.ticker}</span>
            <strong>${s.name}</strong>
          </div>
          <div style="margin-top:6px">
            <small>收盤</small> <strong>${price.close ?? "-"}</strong>
            <span style="margin-left:10px"><small>漲跌</small> <strong>${price.change ?? "-"}</strong> <small>(${price.change_pct ?? "-"})</small></span>
          </div>
          <div style="margin-top:6px">
            <small>外資買賣超(張)</small>
            <div class="kv" style="margin-top:4px">
              <span class="pill">${data.latest_trading_day}: ${f.D0 ?? "-"}</span>
              <span class="pill">${data.prev_trading_day}: ${f.D1 ?? "-"}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="tabs" id="tabs-${s.ticker}"></div>
      <div id="list-${s.ticker}"></div>
    `;

    const tabs = card.querySelector(`#tabs-${s.ticker}`);
    const list = card.querySelector(`#list-${s.ticker}`);
    const cats = ["法說", "營收", "重大訊息", "產能", "美國出口管制"];
    let active = cats[0];

    function renderList(cat) {
      active = cat;
      tabs.querySelectorAll("button").forEach(btn => btn.classList.toggle("active", btn.dataset.cat === active));
      const items = (s.news && s.news[cat]) ? s.news[cat] : [];
      if (!items.length) {
        list.innerHTML = `<p class="muted">這類今天沒有抓到新聞（或資料源暫時無回應）。</p>`;
        return;
      }
      const html = items.map(it => `<li><a href="${it.link}" target="_blank" rel="noreferrer">${it.title}</a><br><small>${it.date}</small></li>`).join("");
      list.innerHTML = `<ul>${html}</ul>`;
    }

    for (const c of cats) {
      const btn = document.createElement("button");
      btn.className = "tab" + (c === active ? " active" : "");
      btn.textContent = c;
      btn.dataset.cat = c;
      btn.addEventListener("click", () => renderList(c));
      tabs.appendChild(btn);
    }
    renderList(active);

    stocksEl.appendChild(card);
  }

  // ZGB
  const zgb = data.fubon_zgb || {};
  const zgbBrokers = zgb.brokers || [];
  zgbEl.innerHTML = `
    <div class="row">
      <div>
        <span class="pill">資料日期 ${zgb.date ?? "-"}</span>
        <span class="pill">單位 ${zgb.unit ?? "-"}</span>
      </div>
    </div>
    <table>
      <thead><tr><th>券商名稱</th><th>買進金額</th><th>賣出金額</th><th>差額</th></tr></thead>
      <tbody>
        ${zgbBrokers.map(b => `<tr><td>${b.name}</td><td>${b.buy}</td><td>${b.sell}</td><td>${b.diff}</td></tr>`).join("")}
      </tbody>
    </table>
    ${zgb.error ? `<p class="bad">ZGB 抓取錯誤：${zgb.error}</p>` : ""}
  `;

  // ZGK_D
  const zgk = data.fubon_zgk_d || {};
  const buy = zgk.buy || [];
  const sell = zgk.sell || [];
  zgkEl.innerHTML = `
    <div class="row">
      <div>
        <span class="pill">資料日期 ${zgk.date ?? "-"}</span>
      </div>
    </div>
    <div class="grid">
      <div class="card" style="padding:0;border:none;background:transparent">
        <h3 style="margin:0 0 6px;font-size:16px">買超</h3>
        <table>
          <thead><tr><th>#</th><th>股票</th><th>超張數</th><th>收盤</th><th>漲跌</th></tr></thead>
          <tbody>
            ${buy.map(r => `<tr><td>${r.rank}</td><td>${r.stock}</td><td>${r.net}</td><td>${r.close}</td><td>${r.change}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
      <div class="card" style="padding:0;border:none;background:transparent">
        <h3 style="margin:0 0 6px;font-size:16px">賣超</h3>
        <table>
          <thead><tr><th>#</th><th>股票</th><th>超張數</th><th>收盤</th><th>漲跌</th></tr></thead>
          <tbody>
            ${sell.map(r => `<tr><td>${r.rank}</td><td>${r.stock}</td><td>${r.net}</td><td>${r.close}</td><td>${r.change}</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>
    ${zgk.error ? `<p class="bad">ZGK_D 抓取錯誤：${zgk.error}</p>` : ""}
  `;
}

main();
