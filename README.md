# job-board

A filterable board of open engineering, design, and product roles, rescanned every
morning. No account, no tracking, no backend. Built for people job hunting after a
layoff, including the ones I worked with.

## How it works

```
jobscan.py --json  →  static/data/jobs.json  →  SvelteKit (adapter-static)  →  Netlify
                             ↑
                    GitHub Actions, daily cron
```

`jobscan.py` fans out across ~250 company slugs on Greenhouse, Ashby, and Lever. Every
posting it can normalize goes into the JSON. All filtering happens in the browser, so
the board is useful to a frontend engineer and a platform engineer at the same time.

A dead posting disappears on the next scan, which is how you find out a company pulled
a req.

## Caveats worth knowing

**Comp is parsed, not published.** Roughly half the postings publish a range at all.
Multi-geo postings list several bands and the scanner takes the one with the lowest
floor, which is the non-metro band. Open the posting before you act on the number.

**Postings with no published range are never hidden.** They show as "not posted" at
every comp floor. Hiding them would hide half the board.

**Lanes are keyword matches on the title.** A title with no topic keyword, such as
"Senior Software Engineer", lands in `swe`. Titles that match nothing are dropped, which
is how non-engineering roles stay off the board.

**US-eligible is a guess.** It reads the location string. "Remote, United Kingdom" is
out, "Remote, Canada; Remote, United States" is in, a bare "Remote" is assumed in.

## Running it

```bash
python3 test_jobscan.py                        # classifier and comp-parser checks
python3 jobscan.py --json > static/data/jobs.json
pnpm install && pnpm dev
```

Scanning all slugs takes about 25 seconds.

Other modes, for scanning by hand:

```bash
python3 jobscan.py                      # my own filter: platform, senior+, remote, $200k+
python3 jobscan.py --all                # same, no comp floor
python3 jobscan.py --slugs stripe,figma # a few boards only
```

## Adding a company

One slug in the `SEED` list in `jobscan.py`. The same slug is tried against all three
board vendors, so you do not need to know which one a company uses. A slug that matches
nothing costs one failed request.

## License

MIT
