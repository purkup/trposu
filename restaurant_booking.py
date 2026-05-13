import json
import math
import re
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
    url_for,
)


DATA_FILE = Path(__file__).with_name("bookings.txt")
CONFIG_FILE = Path(__file__).with_name("config.txt")

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"
SECRET_KEY = "local-only-secret-change-if-you-want"

BOOKING_HORIZON_DAYS = 30

DEFAULT_CONFIG = {
    "two_seat_tables": 1,
    "four_seat_tables": 1,
    "intervals": ["17:00 - 19:00", "19:00 - 21:00", "21:00 - 23:00"],
}

INTERVAL_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d - ([01]\d|2[0-3]):[0-5]\d$")


class BookingSystem:
    def __init__(self):
        self.config = self.load_config()
        self.bookings = self.load_bookings()

    # ---------- config ----------
    def load_config(self):
        if not CONFIG_FILE.exists():
            cfg = {
                "two_seat_tables": DEFAULT_CONFIG["two_seat_tables"],
                "four_seat_tables": DEFAULT_CONFIG["four_seat_tables"],
                "intervals": list(DEFAULT_CONFIG["intervals"]),
            }
            self._write_config(cfg)
            return cfg
        try:
            with CONFIG_FILE.open("r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError):
            raw = {}
        cfg = {
            "two_seat_tables": DEFAULT_CONFIG["two_seat_tables"],
            "four_seat_tables": DEFAULT_CONFIG["four_seat_tables"],
            "intervals": list(DEFAULT_CONFIG["intervals"]),
        }
        if isinstance(raw, dict):
            if isinstance(raw.get("two_seat_tables"), int) and raw["two_seat_tables"] >= 0:
                cfg["two_seat_tables"] = raw["two_seat_tables"]
            if isinstance(raw.get("four_seat_tables"), int) and raw["four_seat_tables"] >= 0:
                cfg["four_seat_tables"] = raw["four_seat_tables"]
            if isinstance(raw.get("intervals"), list):
                cfg["intervals"] = [s for s in raw["intervals"] if isinstance(s, str)]
        return cfg

    def _write_config(self, cfg):
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def save_config(self):
        self._write_config(self.config)

    @property
    def two_seat_tables(self):
        return [f"T2-{n}" for n in range(1, self.config["two_seat_tables"] + 1)]

    @property
    def four_seat_tables(self):
        return [f"T4-{n}" for n in range(1, self.config["four_seat_tables"] + 1)]

    @property
    def intervals(self):
        return self.config["intervals"]

    # ---------- bookings ----------
    def load_bookings(self):
        if not DATA_FILE.exists():
            return []
        try:
            with DATA_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        if not isinstance(data, list):
            return []
        # Старый формат без даты — стираем (см. дизайн).
        if any(not isinstance(b, dict) or "date" not in b for b in data):
            DATA_FILE.write_text("[]", encoding="utf-8")
            return []
        return data

    def save_bookings(self):
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.bookings, f, ensure_ascii=False, indent=2)

    def get_next_id(self):
        if not self.bookings:
            return 1
        return max(b["id"] for b in self.bookings) + 1

    # ---------- table selection ----------
    def get_table_state(self, table_id, date_str, interval):
        is_full_busy = False
        busy_halves = set()
        for booking in self.bookings:
            if booking["date"] != date_str or booking["interval"] != interval:
                continue
            for table in booking["tables"]:
                if table["id"] != table_id:
                    continue
                if table["half"] == 0:
                    is_full_busy = True
                else:
                    busy_halves.add(table["half"])
        return is_full_busy, busy_halves

    def choose_tables(self, table_ids, count, date_str, interval, quick_dinner):
        if quick_dinner:
            return self.choose_quick_tables(table_ids, count, date_str, interval)
        free_tables = []
        for tid in table_ids:
            full, halves = self.get_table_state(tid, date_str, interval)
            if not full and not halves:
                free_tables.append({"id": tid, "half": 0})
        if len(free_tables) < count:
            return None
        return free_tables[:count]

    def choose_quick_tables(self, table_ids, count, date_str, interval):
        best = None
        best_busy = -1
        for half in (1, 2):
            cands = []
            for tid in table_ids:
                full, halves = self.get_table_state(tid, date_str, interval)
                if full or half in halves:
                    continue
                has_other = bool(halves)
                cands.append((not has_other, tid))
            if len(cands) < count:
                continue
            cands.sort()
            sel = [{"id": tid, "half": half} for _, tid in cands[:count]]
            busy = sum(1 for has_no, _ in cands[:count] if not has_no)
            if busy > best_busy:
                best = sel
                best_busy = busy
        return best

    # ---------- create / cancel ----------
    def create_booking(self, name, visitors, date_str, interval, quick_dinner):
        name = name.strip()
        if not name:
            raise ValueError("Введите имя клиента.")
        if visitors < 1:
            raise ValueError("Количество посетителей должно быть больше нуля.")
        try:
            d = date.fromisoformat(date_str)
        except (ValueError, TypeError):
            raise ValueError("Выберите корректную дату.")
        today = date.today()
        if d < today:
            raise ValueError("Нельзя бронировать на прошедшую дату.")
        if d > today + timedelta(days=BOOKING_HORIZON_DAYS):
            raise ValueError(f"Можно бронировать максимум на {BOOKING_HORIZON_DAYS} дней вперёд.")
        if interval not in self.intervals:
            raise ValueError("Выберите корректный интервал времени.")
        date_str = d.isoformat()

        if visitors <= 2:
            tables = self.choose_tables(self.two_seat_tables, 1, date_str, interval, quick_dinner)
            if tables is None:
                tables = self.choose_tables(self.four_seat_tables, 1, date_str, interval, quick_dinner)
        else:
            needed = math.ceil(visitors / 4)
            tables = self.choose_tables(self.four_seat_tables, needed, date_str, interval, quick_dinner)

        if tables is None:
            raise ValueError("На выбранное время нет подходящих свободных столов.")

        booking = {
            "id": self.get_next_id(),
            "name": name,
            "visitors": visitors,
            "date": date_str,
            "interval": interval,
            "quick_dinner": quick_dinner,
            "tables": tables,
        }
        self.bookings.append(booking)
        self.save_bookings()
        return booking

    def cancel_booking(self, name, booking_id):
        name = name.strip()
        for b in self.bookings:
            if b["id"] == booking_id and b["name"].lower() == name.lower():
                self.bookings.remove(b)
                self.save_bookings()
                return True
        return False

    # ---------- info ----------
    def get_interval_info(self, date_str, interval):
        result = {
            "date": date_str,
            "interval": interval,
            "totals": {
                "two_seat_total": self.config["two_seat_tables"],
                "four_seat_total": self.config["four_seat_tables"],
            },
            "summary": None,
            "bookings": [],
        }
        interval_bookings = [
            b for b in self.bookings
            if b["date"] == date_str and b["interval"] == interval
        ]
        two_ids, four_ids = set(), set()
        quick2 = quick4 = full2 = full4 = 0
        for b in interval_bookings:
            for t in b["tables"]:
                if t["id"].startswith("T2"):
                    two_ids.add(t["id"])
                    if t["half"] == 0:
                        full2 += 1
                    else:
                        quick2 += 1
                else:
                    four_ids.add(t["id"])
                    if t["half"] == 0:
                        full4 += 1
                    else:
                        quick4 += 1
        result["summary"] = {
            "two_used": len(two_ids),
            "four_used": len(four_ids),
            "full2": full2, "quick2": quick2,
            "full4": full4, "quick4": quick4,
        }
        for b in interval_bookings:
            tables_str = []
            for t in b["tables"]:
                if t["half"] == 0:
                    tables_str.append(t["id"])
                else:
                    tables_str.append(f"{t['id']} половина {t['half']}")
            result["bookings"].append({
                "id": b["id"],
                "name": b["name"],
                "visitors": b["visitors"],
                "quick_dinner": b["quick_dinner"],
                "tables_str": ", ".join(tables_str),
            })
        return result

    # ---------- admin config ops ----------
    def future_bookings(self):
        today_str = date.today().isoformat()
        return [b for b in self.bookings if b["date"] >= today_str]

    def update_tables(self, new_two, new_four):
        if new_two < 0 or new_four < 0:
            raise ValueError("Количество столов не может быть отрицательным.")
        conflicts = []
        for b in self.future_bookings():
            for t in b["tables"]:
                if not t["id"].startswith(("T2-", "T4-")):
                    continue
                idx = int(t["id"].split("-")[1])
                limit = new_two if t["id"].startswith("T2-") else new_four
                if idx > limit:
                    conflicts.append({
                        "id": b["id"], "name": b["name"], "date": b["date"],
                        "interval": b["interval"], "table": t["id"],
                    })
                    break
        if conflicts:
            return False, conflicts
        self.config["two_seat_tables"] = new_two
        self.config["four_seat_tables"] = new_four
        self.save_config()
        return True, []

    def add_interval(self, value):
        value = value.strip()
        if not INTERVAL_RE.match(value):
            raise ValueError("Интервал должен быть в формате HH:MM - HH:MM (например, 17:00 - 19:00).")
        if value in self.config["intervals"]:
            raise ValueError("Такой интервал уже существует.")
        self.config["intervals"].append(value)
        self.save_config()

    def remove_interval(self, value):
        if value not in self.config["intervals"]:
            raise ValueError("Такого интервала нет.")
        conflicts = [
            {"id": b["id"], "name": b["name"], "date": b["date"], "interval": b["interval"]}
            for b in self.future_bookings() if b["interval"] == value
        ]
        if conflicts:
            return False, conflicts
        self.config["intervals"].remove(value)
        self.save_config()
        return True, []

    def rename_interval(self, old, new):
        new = new.strip()
        if old not in self.config["intervals"]:
            raise ValueError("Исходного интервала нет.")
        if not INTERVAL_RE.match(new):
            raise ValueError("Интервал должен быть в формате HH:MM - HH:MM.")
        if new == old:
            return True, []
        if new in self.config["intervals"]:
            raise ValueError("Такой интервал уже существует.")
        conflicts = [
            {"id": b["id"], "name": b["name"], "date": b["date"], "interval": b["interval"]}
            for b in self.future_bookings() if b["interval"] == old
        ]
        if conflicts:
            return False, conflicts
        idx = self.config["intervals"].index(old)
        self.config["intervals"][idx] = new
        self.save_config()
        return True, []


app = Flask(__name__)
app.secret_key = SECRET_KEY
system = BookingSystem()


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            if request.path.startswith("/admin/api/"):
                return jsonify({"ok": False, "error": "Требуется вход администратора."}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper


BASE_CSS = """
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 760px; margin: 24px auto; padding: 0 16px; background: #fafafa; color: #222; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  h3 { margin-top: 0; font-size: 16px; }
  .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 8px; }
  .topbar a { color: #2563eb; text-decoration: none; font-size: 14px; }
  .topbar a:hover { text-decoration: underline; }
  .card { background: white; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 16px; }
  label { display: block; margin-bottom: 4px; font-weight: 500; font-size: 14px; }
  input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; background: white; }
  .row { display: flex; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .row > div { flex: 1; min-width: 150px; }
  button { background: #2563eb; color: white; border: none; padding: 10px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; }
  button:hover { background: #1d4ed8; }
  button:disabled { background: #9ca3af; cursor: not-allowed; }
  button.danger { background: #dc2626; }
  button.danger:hover { background: #b91c1c; }
  .checkbox { display: flex; align-items: center; gap: 8px; margin: 8px 0 12px; }
  .checkbox input { width: auto; }
  .info { background: #f3f4f6; padding: 12px; border-radius: 4px; font-size: 13px; line-height: 1.6; white-space: pre-wrap; font-family: ui-monospace, "SF Mono", Menlo, monospace; min-height: 24px; }
  .msg { padding: 10px; border-radius: 4px; margin-bottom: 12px; font-size: 14px; }
  .msg.ok { background: #d1fae5; color: #065f46; }
  .msg.err { background: #fee2e2; color: #991b1b; }
  .conflicts { background: #fef3c7; color: #78350f; padding: 10px; border-radius: 4px; margin-top: 8px; font-size: 13px; }
  .conflicts ul { margin: 6px 0 0; padding-left: 20px; }
  .interval-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
  .interval-row input { flex: 1; }
  .interval-row button { padding: 8px 12px; font-size: 13px; }
  .muted { color: #6b7280; font-size: 13px; }
"""


INDEX_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Бронирование столов</title>
<style>__BASE_CSS__</style>
</head>
<body>
  <div class="topbar">
    <h1>Бронирование столов в ресторане</h1>
    <a href="/admin">ADMIN →</a>
  </div>

  {% if not intervals %}
  <div class="card">
    <div class="msg err">Администратор пока не настроил временные интервалы. Бронирование недоступно.</div>
  </div>
  {% endif %}

  <div class="card">
    <div class="row">
      <div>
        <label>Дата</label>
        <input type="date" id="view-date" min="{{ today }}" max="{{ max_date }}" value="{{ today }}" onchange="loadInfo()">
      </div>
      <div>
        <label>Интервал</label>
        <select id="view-interval" onchange="loadInfo()">
          {% for iv in intervals %}<option>{{ iv }}</option>{% endfor %}
        </select>
      </div>
    </div>
  </div>

  <div class="card">
    <h3>Новая бронь</h3>
    <div id="book-msg"></div>
    <div class="row">
      <div><label>Имя клиента</label><input id="b-name"></div>
      <div><label>Количество посетителей</label><input id="b-visitors" type="number" min="1"></div>
    </div>
    <div class="row">
      <div>
        <label>Дата</label>
        <input type="date" id="b-date" min="{{ today }}" max="{{ max_date }}" value="{{ today }}">
      </div>
      <div>
        <label>Интервал</label>
        <select id="b-interval">
          {% for iv in intervals %}<option>{{ iv }}</option>{% endfor %}
        </select>
      </div>
    </div>
    <div class="checkbox">
      <input type="checkbox" id="b-quick">
      <label for="b-quick" style="margin:0;font-weight:normal">Быстрый ужин</label>
    </div>
    <button onclick="book()" {% if not intervals %}disabled{% endif %}>Забронировать</button>
  </div>

  <div class="card">
    <h3>Отменить бронь</h3>
    <div id="cancel-msg"></div>
    <div class="row">
      <div><label>Имя клиента</label><input id="c-name"></div>
      <div><label>Номер брони</label><input id="c-id" type="number"></div>
    </div>
    <button class="danger" onclick="cancelBooking()">Отменить бронь</button>
  </div>

  <div class="card">
    <h3>Информация по выбранному времени</h3>
    <div id="info" class="info"></div>
  </div>

<script>
async function loadInfo() {
  const d = document.getElementById('view-date').value;
  const iv = document.getElementById('view-interval').value;
  if (!iv) {
    document.getElementById('info').textContent = 'Нет доступных интервалов.';
    return;
  }
  const r = await fetch('/api/places?date=' + encodeURIComponent(d) + '&interval=' + encodeURIComponent(iv));
  const data = await r.json();
  const twoFree = data.totals.two_seat_total - data.summary.two_used;
  const fourFree = data.totals.four_seat_total - data.summary.four_used;
  const lines = [
    `Дата: ${data.date}`,
    `Интервал: ${data.interval}`,
    '',
    `Свободно столов на 2 места: ${twoFree} из ${data.totals.two_seat_total}`,
    `Свободно столов на 4 места: ${fourFree} из ${data.totals.four_seat_total}`,
    ''
  ];
  if (data.bookings.length === 0) {
    lines.push('На это время броней нет.');
  } else {
    lines.push('Список броней:');
    for (const b of data.bookings) {
      const t = b.quick_dinner ? 'быстрый ужин' : 'обычная бронь';
      lines.push(`#${b.id} ${b.name} — ${t}`);
    }
  }
  document.getElementById('info').textContent = lines.join('\\n');
}

function showMsg(elId, text, ok) {
  const el = document.getElementById(elId);
  el.innerHTML = `<div class="msg ${ok ? 'ok' : 'err'}">${text}</div>`;
  setTimeout(() => { el.innerHTML = ''; }, 5000);
}

async function book() {
  const body = {
    name: document.getElementById('b-name').value,
    visitors: parseInt(document.getElementById('b-visitors').value || '0', 10),
    date: document.getElementById('b-date').value,
    interval: document.getElementById('b-interval').value,
    quick_dinner: document.getElementById('b-quick').checked,
  };
  const r = await fetch('/api/book', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (data.ok) {
    showMsg('book-msg', `${data.booking.name}, ваша бронь создана. Номер брони: ${data.booking.id}`, true);
    document.getElementById('b-name').value = '';
    document.getElementById('b-visitors').value = '';
    document.getElementById('b-quick').checked = false;
    document.getElementById('view-date').value = body.date;
    document.getElementById('view-interval').value = body.interval;
    loadInfo();
  } else {
    showMsg('book-msg', data.error, false);
  }
}

async function cancelBooking() {
  const body = {
    name: document.getElementById('c-name').value,
    id: parseInt(document.getElementById('c-id').value || '0', 10),
  };
  const r = await fetch('/api/cancel', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (data.ok) {
    showMsg('cancel-msg', 'Бронь отменена.', true);
    document.getElementById('c-name').value = '';
    document.getElementById('c-id').value = '';
    loadInfo();
  } else {
    showMsg('cancel-msg', data.error, false);
  }
}

if (document.getElementById('view-interval').value) {
  loadInfo();
} else {
  document.getElementById('info').textContent = 'Нет доступных интервалов.';
}
</script>
</body>
</html>""".replace("__BASE_CSS__", BASE_CSS)


LOGIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Вход администратора</title>
<style>__BASE_CSS__</style>
</head>
<body>
  <div class="topbar">
    <h1>Вход администратора</h1>
    <a href="/">← На главную</a>
  </div>
  <div class="card">
    {% if error %}<div class="msg err">{{ error }}</div>{% endif %}
    <form method="post">
      <div class="row">
        <div><label>Логин</label><input name="login" autofocus></div>
      </div>
      <div class="row">
        <div><label>Пароль</label><input name="password" type="password"></div>
      </div>
      <button type="submit">Войти</button>
    </form>
  </div>
</body>
</html>""".replace("__BASE_CSS__", BASE_CSS)


ADMIN_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ADMIN</title>
<style>__BASE_CSS__</style>
</head>
<body>
  <div class="topbar">
    <h1>ADMIN</h1>
    <div>
      <a href="/">← На главную</a>
      &nbsp;·&nbsp;
      <a href="/admin/logout">Выйти</a>
    </div>
  </div>

  <div class="card">
    <h3>Количество столов</h3>
    <div id="tables-msg"></div>
    <div class="row">
      <div><label>Столов на 2 места</label><input id="t-two" type="number" min="0" value="{{ two }}"></div>
      <div><label>Столов на 4 места</label><input id="t-four" type="number" min="0" value="{{ four }}"></div>
    </div>
    <button onclick="saveTables()">Сохранить</button>
    <div class="muted" style="margin-top:8px">Уменьшение блокируется, если есть будущие брони на столики, которые исчезли бы.</div>
  </div>

  <div class="card">
    <h3>Временные интервалы</h3>
    <div id="intervals-msg"></div>
    <div id="intervals-list">
      {% for iv in intervals %}
      <div class="interval-row" data-original="{{ iv }}">
        <input type="text" value="{{ iv }}">
        <button onclick="saveInterval(this)">Сохранить</button>
        <button class="danger" onclick="removeInterval(this)">Удалить</button>
      </div>
      {% endfor %}
    </div>
    <div class="interval-row" style="margin-top:12px">
      <input type="text" id="new-interval" placeholder="например, 13:00 - 15:00">
      <button onclick="addInterval()">Добавить</button>
    </div>
    <div class="muted" style="margin-top:8px">Формат HH:MM - HH:MM. Удалить или переименовать можно только если на этот интервал нет будущих броней.</div>
  </div>

<script>
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function showMsg(elId, text, ok, conflicts) {
  const el = document.getElementById(elId);
  let html = `<div class="msg ${ok ? 'ok' : 'err'}">${escapeHtml(text)}</div>`;
  if (conflicts && conflicts.length) {
    html += '<div class="conflicts"><b>Мешающие брони:</b><ul>';
    for (const c of conflicts) {
      const tbl = c.table ? `, ${escapeHtml(c.table)}` : '';
      html += `<li>#${c.id} ${escapeHtml(c.name)}, ${escapeHtml(c.date)}, ${escapeHtml(c.interval)}${tbl}</li>`;
    }
    html += '</ul></div>';
  }
  el.innerHTML = html;
  if (ok) setTimeout(() => { el.innerHTML = ''; }, 4000);
}

async function saveTables() {
  const body = {
    two: parseInt(document.getElementById('t-two').value || '0', 10),
    four: parseInt(document.getElementById('t-four').value || '0', 10),
  };
  const r = await fetch('/admin/api/tables', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (data.ok) {
    showMsg('tables-msg', 'Сохранено.', true);
  } else {
    showMsg('tables-msg', data.error, false, data.conflicts);
  }
}

function renderIntervals(list) {
  const wrap = document.getElementById('intervals-list');
  wrap.innerHTML = '';
  for (const iv of list) {
    const row = document.createElement('div');
    row.className = 'interval-row';
    row.dataset.original = iv;
    row.innerHTML = `
      <input type="text" value="${escapeHtml(iv)}">
      <button onclick="saveInterval(this)">Сохранить</button>
      <button class="danger" onclick="removeInterval(this)">Удалить</button>
    `;
    wrap.appendChild(row);
  }
}

async function addInterval() {
  const value = document.getElementById('new-interval').value;
  const r = await fetch('/admin/api/intervals/add', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  const data = await r.json();
  if (data.ok) {
    document.getElementById('new-interval').value = '';
    renderIntervals(data.intervals);
    showMsg('intervals-msg', 'Интервал добавлен.', true);
  } else {
    showMsg('intervals-msg', data.error, false);
  }
}

async function removeInterval(btn) {
  const row = btn.closest('.interval-row');
  const value = row.dataset.original;
  if (!confirm(`Удалить интервал "${value}"?`)) return;
  const r = await fetch('/admin/api/intervals/remove', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  const data = await r.json();
  if (data.ok) {
    renderIntervals(data.intervals);
    showMsg('intervals-msg', 'Интервал удалён.', true);
  } else {
    showMsg('intervals-msg', data.error, false, data.conflicts);
  }
}

async function saveInterval(btn) {
  const row = btn.closest('.interval-row');
  const oldValue = row.dataset.original;
  const newValue = row.querySelector('input').value;
  if (oldValue === newValue) {
    showMsg('intervals-msg', 'Значение не изменилось.', true);
    return;
  }
  const r = await fetch('/admin/api/intervals/rename', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old: oldValue, new: newValue }),
  });
  const data = await r.json();
  if (data.ok) {
    renderIntervals(data.intervals);
    showMsg('intervals-msg', 'Интервал обновлён.', true);
  } else {
    showMsg('intervals-msg', data.error, false, data.conflicts);
  }
}
</script>
</body>
</html>""".replace("__BASE_CSS__", BASE_CSS)


@app.route('/')
def index():
    today_str = date.today().isoformat()
    max_date = (date.today() + timedelta(days=BOOKING_HORIZON_DAYS)).isoformat()
    return render_template_string(
        INDEX_HTML,
        intervals=system.intervals,
        today=today_str,
        max_date=max_date,
    )


@app.route('/api/places')
def api_places():
    date_str = request.args.get('date', date.today().isoformat())
    interval = request.args.get('interval', '')
    if interval not in system.intervals:
        if system.intervals:
            interval = system.intervals[0]
        else:
            return jsonify({
                "date": date_str,
                "interval": "",
                "totals": {
                    "two_seat_total": system.config["two_seat_tables"],
                    "four_seat_total": system.config["four_seat_tables"],
                },
                "summary": {"two_used": 0, "four_used": 0, "full2": 0, "quick2": 0, "full4": 0, "quick4": 0},
                "bookings": [],
            })
    return jsonify(system.get_interval_info(date_str, interval))


@app.route('/api/book', methods=['POST'])
def api_book():
    data = request.get_json(silent=True) or {}
    try:
        visitors = int(data.get('visitors', 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Количество посетителей должно быть целым числом."}), 400
    try:
        booking = system.create_booking(
            str(data.get('name', '')),
            visitors,
            str(data.get('date', '')),
            str(data.get('interval', '')),
            bool(data.get('quick_dinner', False)),
        )
        return jsonify({"ok": True, "booking": booking})
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route('/api/cancel', methods=['POST'])
def api_cancel():
    data = request.get_json(silent=True) or {}
    try:
        bid = int(data.get('id', 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Номер брони должен быть числом."}), 400
    name = str(data.get('name', ''))
    if not name.strip() or bid <= 0:
        return jsonify({"ok": False, "error": "Заполните имя и номер брони."}), 400
    if system.cancel_booking(name, bid):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Бронь с такими данными не найдена."}), 404


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if request.form.get('login', '').strip() == ADMIN_LOGIN and request.form.get('password', '') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        error = "Неверный логин или пароль."
    return render_template_string(LOGIN_HTML, error=error)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template_string(
        ADMIN_HTML,
        two=system.config["two_seat_tables"],
        four=system.config["four_seat_tables"],
        intervals=system.intervals,
    )


@app.route('/admin/api/tables', methods=['POST'])
@admin_required
def admin_api_tables():
    data = request.get_json(silent=True) or {}
    try:
        new_two = int(data.get('two', 0))
        new_four = int(data.get('four', 0))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Введите целые числа."}), 400
    try:
        ok, conflicts = system.update_tables(new_two, new_four)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    if not ok:
        return jsonify({
            "ok": False,
            "error": "Уменьшение заблокировано: есть будущие брони на исчезающие столики.",
            "conflicts": conflicts,
        }), 409
    return jsonify({"ok": True})


@app.route('/admin/api/intervals/add', methods=['POST'])
@admin_required
def admin_api_intervals_add():
    data = request.get_json(silent=True) or {}
    try:
        system.add_interval(str(data.get('value', '')))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    return jsonify({"ok": True, "intervals": system.intervals})


@app.route('/admin/api/intervals/remove', methods=['POST'])
@admin_required
def admin_api_intervals_remove():
    data = request.get_json(silent=True) or {}
    try:
        ok, conflicts = system.remove_interval(str(data.get('value', '')))
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    if not ok:
        return jsonify({
            "ok": False,
            "error": "Удаление заблокировано: есть будущие брони на этот интервал.",
            "conflicts": conflicts,
        }), 409
    return jsonify({"ok": True, "intervals": system.intervals})


@app.route('/admin/api/intervals/rename', methods=['POST'])
@admin_required
def admin_api_intervals_rename():
    data = request.get_json(silent=True) or {}
    try:
        ok, conflicts = system.rename_interval(
            str(data.get('old', '')),
            str(data.get('new', '')),
        )
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    if not ok:
        return jsonify({
            "ok": False,
            "error": "Переименование заблокировано: есть будущие брони на этот интервал.",
            "conflicts": conflicts,
        }), 409
    return jsonify({"ok": True, "intervals": system.intervals})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
