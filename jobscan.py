#!/usr/bin/env python3
"""
jobscan.py — fan out across Greenhouse + Ashby boards, filter for a profile.

Usage:
    python3 ~/.pi/agent/jobscan.py                 # scan, print matches
    python3 ~/.pi/agent/jobscan.py --all           # don't filter on comp
    python3 ~/.pi/agent/jobscan.py --slugs a,b,c   # scan specific boards only
    python3 ~/.pi/agent/jobscan.py --check FILE    # re-check saved URLs for 404s

Neither board has a global search API, so this iterates company slugs.
Add slugs to SEED as you find them.
"""
import html as _html
import json, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

SEED = """
1password abnormalsecurity affirm airbnb airtable algolia alloy anduril angellist
anthropic apollographql arcadia ashbyhq assembled atlassian attentive auth0
benchling betterup bitgo blend bolt braze bubble calendly carta cedar census
chainguard checkr chime circleci clari clearbit clickup close cloudflare coalition
cockroachlabs coda codecademy cohere coinbase color confluent coreweave cresta
crunchyroll databricks datadog dbtlabs deel descript discord dbt doordash doximity
dropbox duolingo earnin elastic envoy equipmentshare evenup every expel faire
fanatics fastly featurebase fictiv figma fireworksai firstbase fivetran flexport
fluidstack flock front gem gitbook github gitlab glean gong grafana grammarly
greenhouse gusto handshake harness hashicorp headway hightouch hinge hopper
houseparty hudl huggingface humaninterest instacart intercom jasper jerry
jobandtalent kandji klaviyo knowbe4 kong komodohealth lacework lattice launchdarkly
leaplegal linear liveperson loom lucid lyft mapbox marqeta mavenclinic mercury
metronome miro modernhealth modal mongodb monte-carlo motive mozilla narvar netlify
newfront notion nuna nylas oak oklo olo ondeck onetrust opendoor openai
opensea optimizely outschool overjet oyster pachyderm pagerduty panther parsec
patreon pave paxos pendo persona pilot pinterest pipe planetscale plaid pockethealth
postman postscript prefect pricefx primer productboard pulley puppet quora rampnetwork
recurly reddit redpanda remote replit retool rippling roblox robinhood rokt roon
samsara scaleai scribd sentry shieldai shipbob shopmonkey sierra signifyd slack
smartsheet snorkelai snyk socure sonarsource sourcegraph spotify spring stackblitz
starburst stedi strava stripe stytch substack superhuman supabase tailscale talkdesk
teleport temporal tessian thoughtspot tigergraph together toast tome tremendous
tubi twilio uber unity upstart valon vanta vercel verkada via viam vimeo voleon
wandb warp watershed wealthfront webflow whatnot whoop wiz workrise writer
zapier zed zenefits zipline zocdoc zoox
hims-and-hers check-technologies mavenclinic filevine
reddit databricks pinterest toast elastic komodohealth smartsheet upstart
cresta calendly earnin gusto verkada fivetran launchdarkly coinbase anthropic
headway webflow valon tremendous mongodb
figma samsara tailscale affirm
""".split()
SEED = sorted(set(SEED))   # the list is hand-maintained; de-dupe on load

TITLE_HIT = re.compile(r"""
 (developer\s+(experience|productivity|platform|tools)|devex|devprod
 |platform\s+engineer|infrastructure\s+engineer|build\s+(systems?|engineer)
 |continuous\s+integration|ci/?cd|release\s+engineer
 |(ai|agent|llm)\s+(enablement|engineer|platform|infrastructure|tooling)
 |internal\s+tools|engineering\s+productivity|forward\s+deployed)
""", re.I | re.X)

LEVEL_HIT = re.compile(r'\b(staff|principal|senior|sr\.?|lead)\b', re.I)
BAD = re.compile(r'\b(intern|manager|director|head\s+of|vp\b|sales|recruit|designer'
                 r'|marketing|counsel|analyst|support|success|accountant)\b', re.I)
REMOTE = re.compile(r'\bremote\b|\banywhere\b', re.I)
ONSITE = re.compile(r'(hybrid|in[- ]office)', re.I)
# "San Mateo, CA, United States" is not remote; "Remote, US" is.
def is_remote(loc):
    if ONSITE.search(loc or ''):
        return False
    if REMOTE.search(loc or ''):
        return True
    return bool(re.fullmatch(r'\s*united states\s*', loc or '', re.I))
# Match an explicit range: "$150,000 - $200,000" / "$150K — $200K"
RANGE = re.compile(r'\$\s?([\d,]{5,9})(?:\s?K)?\s*(?:-|–|—|to)\s*\$?\s?([\d,]{5,9})(?:\s?K)?', re.I)


def get(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def comp_range(text):
    """Lowest posted range and its ceiling. Multi-geo postings list several;
    take the one with the LOWEST floor, which is the non-metro band."""
    # Amounts arrive wrapped in markup: <span>$286,762</span>—<span>$347,488</span>.
    # Strip tags, then unescape entities, then collapse whitespace, so the two
    # numbers end up adjacent with only a separator between them.
    # Content arrives double-encoded: entities first, then markup. Unescape
    # twice so &lt;span&gt; becomes a real tag, strip tags, then collapse space,
    # so the two amounts end up adjacent with only a separator between them.
    text = _html.unescape(_html.unescape(text or ''))
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text))
    out = []
    for lo, hi in RANGE.findall(text):
        try:
            lo_i, hi_i = int(lo.replace(',', '')), int(hi.replace(',', ''))
        except ValueError:
            continue
        if 50_000 <= lo_i < hi_i <= 900_000:
            out.append((lo_i, hi_i))
    if not out:
        return (0, 0)
    return min(out, key=lambda p: p[0])


def greenhouse(slug):
    try:
        d = get(f'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true')
    except Exception:
        return []
    out = []
    for j in d.get('jobs', []):
        loc = (j.get('location') or {}).get('name', '')
        out.append(dict(co=slug, title=j['title'].strip(), loc=loc,
                        url=j.get('absolute_url', ''), gh_id=j.get('id'),
                        comp=comp_range(j.get('content', ''))))
    return out


def ashby(slug):
    try:
        d = get(f'https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true')
    except Exception:
        return []
    out = []
    for j in d.get('jobs', []):
        c = (j.get('compensation') or {}).get('compensationTierSummary') or ''
        out.append(dict(co=slug, title=j['title'].strip(), loc=j.get('location') or '',
                        url=j.get('jobUrl', ''), gh_id=None,
                        comp=comp_range(c or j.get('descriptionHtml', ''))))
    return out


def lever(slug):
    try:
        d = get(f'https://api.lever.co/v0/postings/{slug}?mode=json')
    except Exception:
        return []
    out = []
    for j in d:
        cat = j.get('categories') or {}
        sal = j.get('salaryRange') or {}
        lo, hi = sal.get('min') or 0, sal.get('max') or 0
        if not hi:
            lo, hi = comp_range(j.get('description', '') + j.get('additional', ''))
        out.append(dict(co=slug, title=j.get('text', '').strip(),
                        loc=cat.get('location') or '', url=j.get('hostedUrl', ''),
                        gh_id=None, comp=(lo, hi)))
    return out


def scan(slugs):
    rows = []
    with ThreadPoolExecutor(max_workers=24) as ex:
        for res in ex.map(lambda s: greenhouse(s) + ashby(s) + lever(s), slugs):
            rows.extend(res)
    return rows


LANES = {
    'devex': r'developer\s+(experience|productivity|tools?)|devex|devprod|build\s+system|continuous\s+integration|ci/?cd|release\s+eng',
    'platform': r'platform',
    'infra': r'infrastructure|\bsre\b|site\s+reliability|cloud\s+engineer',
    'ai': r'\b(ai|ml|llm|agent|machine\s+learning|genai)\b|forward\s+deployed',
    'data': r'\bdata\b|analytics|warehouse',
    'frontend': r'front[- ]?end|\bui\b|\bweb\b|react|typescript|javascript|client\s+engineer|design\s+engineer',
    'backend': r'back[- ]?end|\bapi\b|services?\s+engineer',
    'fullstack': r'full[- ]?stack',
    'mobile': r'\b(ios|android|mobile|react\s+native)\b',
    'qa': r'\b(qa|sdet|test)\b|quality',
    'security': r'security|appsec|\bgrc\b',
    'design': r'designer|\bux\b|\bui/ux\b',
    'pm': r'product\s+manager|\btpm\b|program\s+manager',
    'em': r'engineering\s+manager|\bem\b,|director.*engineer|head\s+of\s+eng',
}
LANE_RX = {k: re.compile(v, re.I) for k, v in LANES.items()}

# Engineering titles that carry no topic keyword: "Senior Software Engineer",
# "Staff Software Engineer, IAM Control Plane". Without a fallback lane these fall
# out of the board entirely. An 8-company sample hid 158 of them, several of them
# roles worth applying to.
GENERIC = re.compile(r'software (engineer|development engineer|engineering)|\bswe\b'
                     r'|web developer|application developer|systems? engineer', re.I)
# Titles the fallback would otherwise sweep in. Narrower than BAD on purpose: the
# board keeps manager and designer roles, because the people sharing it include an
# engineering manager and two designers.
NOT_ENG = re.compile(r'\b(intern|internship|apprentice|co-?op)\b|new ?grad|early career'
                     r'|university|high school|solutions?\s+(architect|engineer|consultant)'
                     r'|sales\s+engineer|support\s+engineer|technical\s+account'
                     r'|account\s+(executive|manager)|customer\s+success|recruit'
                     r'|partner\s+engineer|field\s+engineer|integration\s+engineer'
                     r'|\bit\s+support\b', re.I)

# "Bengaluru" and "Remote, United Kingdom" are both remote and both unreachable from
# Boise. The UI needs to filter on reach, which is a different question from remote.
US_OK = re.compile(r'united states|\bu\.?s\.?a?\b|anywhere|north america|remote', re.I)
US_NO = re.compile(r'united kingdom|\buk\b|ireland|germany|spain|sweden|france|poland'
                   r'|netherlands|portugal|romania|czech|india|bangalore|bengaluru|japan'
                   r'|singapore|australia|canada|toronto|vancouver|brazil|argentina|mexico'
                   r'|israel|china|korea|taiwan|emea|apac|london|dublin|berlin|barcelona'
                   r'|amsterdam|bucharest|tokyo|sydney', re.I)
# "Seattle, WA" splits to a bare state code, which no keyword above catches.
US_STATE = re.compile(r'^[A-Z]{2}$')
US_HARD = re.compile(r'united states|\bu\.?s\.?a?\b', re.I)


def us_reachable(loc):
    """One listed location is enough. Same shape as the watcher's usEligible: a bare
    "Remote" counts, but once any part names a foreign country the posting has to say
    United States somewhere, so "Remote, United Kingdom" does not sneak through on the
    word remote alone."""
    parts = [p.strip() for p in re.split(r'[,|;•\n]|\sor\s', loc or '') if p.strip()]
    if not parts:
        return True
    ok = lambda p: (US_OK.search(p) or US_STATE.match(p)) and not US_NO.search(p)
    if not any(ok(p) for p in parts):
        return False
    if not any(US_NO.search(p) for p in parts):
        return True
    return any(US_HARD.search(p) or US_STATE.match(p) for p in parts)


def lanes_for(title):
    if NOT_ENG.search(title):
        return []
    hits = [k for k, rx in LANE_RX.items() if rx.search(title)]
    if not hits and GENERIC.search(title):
        return ['swe']
    return hits


def emit_json(rows):
    import datetime
    seen, out = set(), []
    for r in rows:
        k = (r['co'], r['title'])
        if k in seen or not r['title']:
            continue
        seen.add(k)
        lanes = lanes_for(r['title'])
        if not lanes:                      # non-technical roles: skip
            continue
        out.append({'co': r['co'], 'title': r['title'], 'loc': r['loc'],
                    'url': r['url'], 'lo': r['comp'][0], 'hi': r['comp'][1],
                    'remote': is_remote(r['loc']), 'us': us_reachable(r['loc']),
                    'lane': lanes})
    print(json.dumps({'generated': datetime.datetime.now(datetime.UTC)
                      .isoformat(timespec='seconds').replace('+00:00', 'Z'),
                      'jobs': sorted(out, key=lambda j: (-j['hi'], j['co']))},
                     separators=(',', ':')))


def main():
    args = sys.argv[1:]
    if '--json' in args:
        emit_json(scan(SEED))
        return
    slugs = SEED
    if '--slugs' in args:
        slugs = args[args.index('--slugs') + 1].split(',')
    floor = 0 if '--all' in args else 200_000

    rows = scan(slugs)
    hits = [r for r in rows
            if TITLE_HIT.search(r['title']) and LEVEL_HIT.search(r['title'])
            and not BAD.search(r['title'])
            and is_remote(r['loc'])
            and (r['comp'][1] == 0 or r['comp'][1] >= floor)]

    # The Greenhouse list endpoint truncates content, so the salary block is
    # missing. Fetch detail only for postings that already passed the filters.
    def fill(r):
        if r['comp'][1] or not r.get('gh_id'):
            return r
        try:
            d = get(f"https://boards-api.greenhouse.io/v1/boards/{r['co']}/jobs/{r['gh_id']}")
            r['comp'] = comp_range(d.get('content', ''))
        except Exception:
            pass
        return r

    with ThreadPoolExecutor(max_workers=16) as ex:
        hits = list(ex.map(fill, hits))
    hits = [r for r in hits if r['comp'][1] == 0 or r['comp'][1] >= floor]

    seen, uniq = set(), []
    for r in sorted(hits, key=lambda r: (-r['comp'][1], r['co'])):
        k = (r['co'], r['title'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    print(f"scanned {len(slugs)} slugs, {len(rows)} postings, {len(uniq)} matches\n")
    for r in uniq:
        lo, hi = r['comp']
        c = f"${lo//1000}-{hi//1000}k" if hi else "not posted"
        print(f"{c:>13}  {r['co']:<16} {r['title'][:52]:<54} {r['loc'][:26]}")
        print(f"{'':>13}  {r['url']}")


if __name__ == '__main__':
    main()
