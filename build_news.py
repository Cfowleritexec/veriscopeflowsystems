"""Refresh AI news and risk links while retaining one curated free learning resource."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
import html
import sys
import re

ROOT = Path(__file__).resolve().parent
FEED = 'https://blog.google/innovation-and-ai/technology/ai/rss/'
RISK_FEED = 'https://blogs.microsoft.com/on-the-issues/feed/'
# Verified official announcement. Retained when no newer relevant feed item exists.
RISK_REFERENCE = (
    datetime(2026, 9, 14, tzinfo=timezone.utc),
    'Humanist AI in practice: A public consultation on our Code of Conduct for MAI Models',
    'https://microsoft.ai/news/mai-code-of-conduct/',
)

def select_risk(xml, now):
    candidates = [RISK_REFERENCE] if RISK_REFERENCE[0] <= now else []
    for item in ET.fromstring(xml).findall('./channel/item'):
        title = (item.findtext('title') or '').strip()
        url = (item.findtext('link') or '').strip()
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '')
        except (ValueError, TypeError):
            continue
        is_ai = re.search(r'\bAI\b|artificial intelligence', title, re.I)
        is_risk = re.search(r'\brisk\w*\b|\bsafety\b|\bsecurity\b|\bprivacy\b|\bgovernance\b|\bresponsibl\w*\b|code of conduct|human control|\bsafeguards\b', title, re.I)
        if (is_ai and is_risk and date.tzinfo is not None and date <= now
                and urlparse(url).scheme == 'https' and urlparse(url).hostname == 'blogs.microsoft.com'):
            candidates.append((date, title, url))
    if not candidates:
        raise ValueError('No verified AI risk article available.')
    return max(candidates, key=lambda item: item[0])

def build(xml, risk_xml):
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
    if not items:
        raise ValueError('Insufficient valid headlines; existing preview preserved.')
    cards = []
    selected = [(items[0], 'Google', 'AI Developments')]
    selected.append((select_risk(risk_xml, now), 'Microsoft', 'AI Risks & Governance'))
    for (date, title, url), publisher, category in selected:
        cards.append(f'''<article class="ai-news-card"><p class="ai-news-topic">{html.escape(category)}</p><p class="ai-news-meta">{publisher} · <time datetime="{date.date()}">{date.strftime('%b %d, %Y')}</time></p><h3><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(title)}</a></h3><a class="ai-news-read" href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer" aria-label="Read {html.escape(title, quote=True)} on {publisher} (opens in a new tab)">Read at {publisher} <span aria-hidden="true">↗</span></a></article>''')
    # Curated resource: provider page verified September 16, 2026 (UTC).
    # This is a learning resource, not a dated news announcement.
    cards.insert(1, '''<article class="ai-news-card"><p class="ai-news-topic">AI Learning &amp; Readiness</p><p class="ai-news-meta">IBM SkillsBuild · Free · About 90 minutes</p><h3><a href="https://skillsbuild.org/adult-learners/try-it-before-you-register" target="_blank" rel="noopener noreferrer">Exploring Artificial Intelligence</a></h3><p class="ai-news-meta">Build your understanding of AI at your own pace. Try the course as a guest, with no registration required.</p><a class="ai-news-read" href="https://skillsbuild.org/adult-learners/try-it-before-you-register" target="_blank" rel="noopener noreferrer" aria-label="Find Exploring Artificial Intelligence on IBM SkillsBuild (opens in a new tab)">Explore the free course <span aria-hidden="true">↗</span></a></article>''')
    section = '''<!-- AI NEWS START -->
<section id="ai-news" aria-labelledby="ai-news-title"><div class="section-inner">
<div class="ai-news-heading"><div><div class="section-label"><div class="section-label-line"></div><span class="section-label-text">AI News &amp; Learning</span></div><h2 id="ai-news-title" class="section-title">AI moves quickly.<br><em>Stay informed.</em></h2></div><span class="ai-news-badge">From the source ↗</span></div>
<p class="ai-news-intro">Stay informed about AI developments, build your understanding, and explore the risks and governance that guide responsible decisions.</p>
<div class="ai-news-grid">''' + ''.join(cards) + f'''</div>
<div class="ai-news-foot"><p>News: Google &amp; Microsoft · News checked <time datetime="{now.isoformat()}">{now.strftime('%b %d, %Y')} (UTC)</time></p><div><a href="{FEED}" target="_blank" rel="noopener noreferrer">Google feed ↗</a> · <a href="{RISK_FEED}" target="_blank" rel="noopener noreferrer">Microsoft feed ↗</a></div></div>
<p class="ai-news-disclosure">Learning resource: IBM SkillsBuild · Selected Sep 16, 2026. Third-party news and education, provided for information. Inclusion does not imply endorsement by Veriscope.</p>
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
    print('Updated AI developments and risk news; retained the curated learning resource.')

if __name__ == '__main__':
    if '--cached' in sys.argv:
        xml = (ROOT / 'google-feed.xml').read_bytes()
        risk_xml = (ROOT / 'risk-feed.xml').read_bytes()
    else:
        with urlopen(Request(FEED, headers={'User-Agent': 'VeriscopeNewsPreview/1.0'}), timeout=25) as response:
            xml = response.read(2_000_000)
        with urlopen(Request(RISK_FEED, headers={'User-Agent': 'VeriscopeNewsPreview/1.0'}), timeout=25) as response:
            risk_xml = response.read(2_000_000)
    build(xml, risk_xml)
