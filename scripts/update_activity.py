"""Render Rahul's rolling contribution calendar for the profile README."""

from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


INK = ("#dfd9ce", "#a4b2ed", "#7186dc", "#445bc3", "#192a98")
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "activity.svg"


class CalendarPage(HTMLParser):
    """The date and color are on the cell. Its linked tooltip contains the count."""

    def __init__(self):
        super().__init__()
        self.cells = {}
        self.labels = {}
        self.tooltip = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and "data-date" in attrs:
            self.cells[attrs["id"]] = (date.fromisoformat(attrs["data-date"]), int(attrs["data-level"]))
        elif tag == "tool-tip":
            self.tooltip = attrs.get("for")

    def handle_data(self, data):
        if self.tooltip:
            self.labels[self.tooltip] = self.labels.get(self.tooltip, "") + data

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.tooltip = None

    def records(self):
        for cell_id, (day, level) in self.cells.items():
            number = self.labels[cell_id].strip().split()[0].replace(",", "")
            yield day, (0 if number == "No" else int(number), level)


def fetch_days(start, end):
    days = {}
    for year in range(start.year, end.year + 1):
        url = f"https://github.com/users/RahulGPi/contributions?from={year}-01-01&to={year}-12-31"
        request = Request(url, headers={"Accept-Language": "en", "User-Agent": "RahulGPi-profile-calendar"})
        page = CalendarPage()
        with urlopen(request, timeout=25) as response:
            page.feed(response.read().decode("utf-8"))
        page.close()
        days.update((day, values) for day, values in page.records() if start <= day <= end)
    if len(days) != (end - start).days + 1:
        raise ValueError("GitHub returned an incomplete calendar")
    return days


def render_calendar(days):
    start, end = min(days), max(days)
    first_sunday = start - timedelta(days=(start.weekday() + 1) % 7)
    total = sum(count for count, _ in days.values())
    active = sum(count > 0 for count, _ in days.values())
    period = f"{start:%d %b %Y} – {end:%d %b %Y}"
    marks = []
    for day, (_, level) in sorted(days.items()):
        week, weekday = divmod((day - first_sunday).days, 7)
        x, y = 27 + 17 * week, 101 + 13 * weekday
        color = INK[level]
        marks.append(f'  <circle cx="{x}" cy="{y}" r="4.8" fill="{color}"/>')
        if day.day == 1 and week < 52:
            marks.append(f'  <text x="{x - 4}" y="84" class="month">{day:%b}</text>')

    dots = "\n".join(marks)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="940" height="205"
     viewBox="0 0 940 205" role="img" aria-labelledby="title desc">
  <title id="title">{total:,} contributions on {active} days</title>
  <desc id="desc">{period}. Each dot is one day. Darker blue indicates more contributions.</desc>
  <style>.month {{ font: 13px monospace; fill: #544e46 }}</style>
  <rect width="940" height="205" fill="#fff5e5"/>
  <text x="23" y="47" font-family="Georgia, serif" font-size="35" fill="#201d1b">{total:,} contributions</text>
  <text x="914" y="30" text-anchor="end" font-family="monospace" font-size="16" fill="#192a98">{active} active days</text>
  <text x="914" y="51" text-anchor="end" font-family="sans-serif" font-size="15" fill="#544e46">{period}</text>
{dots}
</svg>
'''


if __name__ == "__main__":
    yesterday = datetime.now(timezone.utc).date() - timedelta(days=1)
    calendar = fetch_days(yesterday - timedelta(days=364), yesterday)
    OUTPUT.write_text(render_calendar(calendar), encoding="utf-8")
