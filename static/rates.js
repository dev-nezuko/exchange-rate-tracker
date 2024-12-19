(function () {
  const board = document.getElementById('board');
  const dateline = document.getElementById('dateline');
  const statusBox = document.getElementById('status');
  const table = document.getElementById('rates');
  const tbody = document.getElementById('rows');
  const filter = document.getElementById('filter');
  const count = document.getElementById('count');

  const currencyNames = typeof Intl.DisplayNames === 'function'
    ? new Intl.DisplayNames(['en'], { type: 'currency' })
    : null;
  const longDate = new Intl.DateTimeFormat('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
  });

  let rows = [];

  function nameFor(code) {
    try {
      return currencyNames ? currencyNames.of(code) : code;
    } catch (err) {
      return code;
    }
  }

  function formatRate(rate) {
    const digits = rate >= 100 ? 2 : 4;
    return rate.toLocaleString('en-GB', { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  function changeCell(change) {
    const td = document.createElement('td');
    td.className = 'change num';
    if (change === null || change === undefined) {
      td.classList.add('flat');
      td.textContent = 'first sample';
      return td;
    }
    const direction = change > 0 ? 'up' : change < 0 ? 'down' : 'flat';
    const marker = { up: '▲', down: '▼', flat: '–' }[direction];
    const label = { up: 'up', down: 'down', flat: 'unchanged' }[direction];
    td.classList.add(direction);
    const sign = change > 0 ? '+' : '';
    td.innerHTML = '<span aria-hidden="true"></span> <span class="visually-hidden"></span>';
    td.children[0].textContent = marker + ' ' + sign + change.toFixed(4);
    td.children[1].textContent = label + ' ' + Math.abs(change).toFixed(4);
    return td;
  }

  function render() {
    const query = filter.value.trim().toLowerCase();
    const visible = rows.filter((row) =>
      !query || row.currency.toLowerCase().includes(query) || row.name.toLowerCase().includes(query));

    tbody.replaceChildren(...visible.map((row) => {
      const tr = document.createElement('tr');
      const code = document.createElement('td');
      code.className = 'code';
      code.textContent = row.currency;
      const name = document.createElement('td');
      name.className = 'name';
      name.textContent = row.name;
      const rate = document.createElement('td');
      rate.className = 'rate num';
      rate.textContent = formatRate(row.rate);
      tr.append(code, name, rate, changeCell(row.change));
      return tr;
    }));

    count.textContent = query
      ? `${visible.length} of ${rows.length} currencies`
      : `${rows.length} currencies`;
    if (rows.length && !visible.length) {
      showStatus(`No currency matches “${filter.value.trim()}”.`);
      table.hidden = true;
    } else if (rows.length) {
      statusBox.hidden = true;
      table.hidden = false;
    }
  }

  function showStatus(message, isError) {
    statusBox.hidden = false;
    statusBox.className = isError ? 'status error' : 'status';
    statusBox.setAttribute('role', isError ? 'alert' : 'status');
    statusBox.textContent = message;
  }

  async function load() {
    board.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch('/exchange-rates/latest', { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error(`The API answered ${response.status}.`);
      const body = await response.json();

      if (!body.published_on || !body.rates.length) {
        dateline.textContent = 'No ECB publication has been imported yet.';
        showStatus('The table fills after the first import: run "python seeders.py" or enable the scheduler.');
        return;
      }

      dateline.innerHTML = 'Published by the ECB on <strong></strong>';
      dateline.querySelector('strong').textContent = longDate.format(new Date(body.published_on + 'T00:00:00Z'));
      rows = body.rates.map((row) => ({ ...row, name: nameFor(row.currency) }));
      filter.disabled = false;
      render();
    } catch (err) {
      dateline.textContent = 'Rates are unavailable right now.';
      showStatus(`Could not load rates. ${err.message}`, true);
      const retry = document.createElement('button');
      retry.type = 'button';
      retry.textContent = 'Try again';
      retry.addEventListener('click', () => {
        showStatus('Retrying…');
        load();
      });
      statusBox.append(retry);
    } finally {
      board.setAttribute('aria-busy', 'false');
    }
  }

  filter.addEventListener('input', render);
  load();
})();
