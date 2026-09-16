"""Refresh headline-only preview from Google's public AI RSS feed (no API key)."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import html
import sys

ROOT = Path(__file__).resolve().parent
FEED = 'https://blog.google/innovation-and-ai/technology/ai/rss/'

def build(xml):
    now = datetime.now(timezone.utc)
    items = []
    seen = set()
    for item in ET.fromstring(xml).findall('./channel/item'):
        title = (item.findtext('title') or '').strip()
        url = (item.findtext('link') or '').strip()
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '')
            if date.tzinfo is None:
                continue
        except (ValueError, TypeError):
            continue
        if not title or urlparse(url).scheme != 'https' or urlparse(url).hostname != 'blog.google' or date > now or url in seen:
            continue
        seen.add(url)
        items.append((date, title, url))
    items.sort(key=lambda item: item[0], reverse=True)
    if len(items) < 3:
        raise ValueError('Insufficient valid headlines; existing preview preserved.')
    cards = []
    for date, title, url in items[:3]:
        cards.append(f'''<article class="ai-news-card"><p class="ai-news-meta">Google · <time datetime="{date.date()}">{date.strftime('%b %d, %Y')}</time></p><h3><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(title)}</a></h3><a class="ai-news-read" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="Read {html.escape(title, quote=True)} on Google (opens in a new tab)">Read at Google <span aria-hidden="true">↗</span></a></article>''')
    section = '''<!-- AI NEWS START -->
<section id="ai-news" aria-labelledby="ai-news-title"><div class="section-inner">
<div class="ai-news-heading"><div><div class="section-label"><div class="section-label-line"></div><span class="section-label-text">AI News &amp; Developments</span></div><h2 id="ai-news-title" class="section-title">AI moves quickly.<br><em>Stay informed.</em></h2></div><span class="ai-news-badge">From the source ↗</span></div>
<p class="ai-news-intro">Explore recent AI announcements as you consider what comes next for your organization.</p>
<div class="ai-news-grid">''' + ''.join(cards) + f'''</div>
<div class="ai-news-foot"><p>Source: Google’s official AI blog · Checked <time datetime="{now.isoformat()}">{now.strftime('%b %d, %Y')} (UTC)</time></p><a href="{FEED}" target="_blank" rel="noopener noreferrer">View source feed ↗</a></div>
<p class="ai-news-disclosure">Publisher announcements, provided for information. Inclusion does not imply endorsement by Veriscope.</p>
</div></section>
<!-- AI NEWS END -->'''
    path = ROOT / 'index.html'
    page = path.read_text(encoding='utf-8')
    if '<!-- AI NEWS START -->' in page:
        start = page.index('<!-- AI NEWS START -->')
        end = page.index('<!-- AI NEWS END -->') + len('<!-- AI NEWS END -->')
        page = page[:start] + section + page[end:]
    else:
        page = page.replace('<section class="about" id="about">', section + '\n<section class="about" id="about">')
    path.write_text(page, encoding='utf-8')
    print('Updated three verified, dated headlines.')

if __name__ == '__main__':
    if '--cached' in sys.argv:
        xml = (ROOT / 'google-feed.xml').read_bytes()
    else:
        with urlopen(Request(FEED, headers={'User-Agent': 'VeriscopeNewsPreview/1.0'}), timeout=25) as response:
            xml = response.read(2_000_000)
    build(xml)
