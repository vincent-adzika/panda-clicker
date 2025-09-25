import re

def normalize_opera_link(url: str) -> str:
    # If already short, return as is
    m = re.match(r'https://opr\.news/([\w]+)\?', url)
    if m:
        return url
    # Try to extract news_entry_id from long link
    m = re.search(r'news_entry_id=([\w]+)', url)
    if m:
        short = f"https://opr.news/{m.group(1)}?link=1&client=news"
        return short
    return url

def get_next_link_id() -> str:
    links = load_links()
    if not links:
        return 'a'
    last_id = links[-1].get('id', 'a')
    # Excel-style increment: a, b, ..., z, aa, ab, ..., az, ba, ...
    def next_alpha(s):
        s = s.lower()
        if set(s) - set('abcdefghijklmnopqrstuvwxyz'):
            return 'a'
        n = 0
        for c in s:
            n = n * 26 + (ord(c) - ord('a') + 1)
        n += 1
        res = ''
        while n > 0:
            n, r = divmod(n - 1, 26)
            res = chr(ord('a') + r) + res
        return res
    return next_alpha(last_id)
# Alternate admin/user links for a user, skipping already viewed and own links
def get_next_alternating_link(user_id, viewed_ids):
    links = load_links()
    admin_links = [l for l in links if l.get('is_admin') and l.get('user_id') != user_id and l.get('id') not in viewed_ids]
    user_links = [l for l in links if not l.get('is_admin') and l.get('user_id') != user_id and l.get('id') not in viewed_ids]
    # Use context or a global to track last type shown if needed; here, just alternate by count
    # If admin links remain, show one, then user, then admin, etc.
    # If one type is exhausted, show only the other
    if not admin_links and not user_links:
        return None
    # Alternate: if more admin links left, show admin, else user
    # For strict alternation, the bot should track last type shown per user in user_data
    # Here, return both lists for the bot to alternate
    return {'admin': admin_links, 'user': user_links}
import json
import random
import os
from typing import List, Dict

def _get_links_file_index():
    # Find the highest index file that exists
    idx = 1
    while os.path.exists(f'links{idx}.json'):
        idx += 1
    return idx - 1 if idx > 1 else 1

def _get_links_file(idx=None):
    if idx is None:
        idx = _get_links_file_index()
    return f'links{idx}.json'

def load_links() -> List[Dict]:
    # Load all links from all files
    links = []
    idx = 1
    while os.path.exists(f'links{idx}.json'):
        with open(f'links{idx}.json', 'r', encoding='utf-8') as f:
            try:
                links.extend(json.load(f))
            except Exception:
                pass
        idx += 1
    # Fallback to links.json for legacy
    if not links and os.path.exists('links.json'):
        with open('links.json', 'r', encoding='utf-8') as f:
            try:
                links.extend(json.load(f))
            except Exception:
                pass
    return links

def save_links(links: List[Dict], idx=None):
    if idx is None:
        idx = _get_links_file_index()
    with open(f'links{idx}.json', 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def add_link(link: Dict):
    idx = _get_links_file_index()
    links = []
    # Load current file
    if os.path.exists(f'links{idx}.json'):
        with open(f'links{idx}.json', 'r', encoding='utf-8') as f:
            try:
                links = json.load(f)
            except Exception:
                links = []
    # If file is full, increment idx
    if len(links) >= 10000:
        idx += 1
        links = []
    links.append(link)
    save_links(links, idx)

def get_random_link(admin_links: bool, admin_ratio=0.6) -> Dict:
    links = load_links()
    admin = [l for l in links if l.get('is_admin')]
    regular = [l for l in links if not l.get('is_admin')]
    if admin_links and admin and (random.random() < admin_ratio or not regular):
        return random.choice(admin)
    elif regular:
        return random.choice(regular)
    elif admin:
        return random.choice(admin)
    return {}
