<script lang="ts">
  type Job = {
    co: string
    title: string
    loc: string
    url: string
    lo: number
    hi: number
    remote: boolean
    us: boolean
    lane: string[]
  }

  const LANES = [
    "swe",
    "frontend",
    "backend",
    "fullstack",
    "platform",
    "devex",
    "infra",
    "ai",
    "data",
    "mobile",
    "qa",
    "security",
    "design",
    "pm",
    "em",
  ]

  let jobs = $state<Job[]>([])
  let generated = $state("")
  let error = $state("")

  let q = $state("")
  let lanes = $state<string[]>([])
  let minComp = $state(0)
  let remoteOnly = $state(true)
  let usOnly = $state(true)
  let sort = $state<"comp" | "co" | "title">("comp")
  // Painting five thousand rows on load is the only real perf cost here. Render a
  // window and let the button grow it. No virtualization until this stops working.
  let limit = $state(200)

  $effect(() => {
    fetch("/data/jobs.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => {
        jobs = d.jobs
        generated = d.generated
      })
      .catch((e) => (error = e.message))
  })

  const filtered = $derived.by(() => {
    const needle = q.trim().toLowerCase()
    const out = jobs.filter((j) => {
      if (remoteOnly && !j.remote) return false
      if (usOnly && !j.us) return false
      // A posting with no published range shows at every comp floor. Most boards
      // do not post ranges, and hiding them would hide half the market.
      if (minComp && j.hi && j.hi < minComp * 1000) return false
      if (lanes.length && !lanes.some((l) => j.lane.includes(l))) return false
      if (needle && !`${j.title} ${j.co}`.toLowerCase().includes(needle)) return false
      return true
    })
    if (sort === "comp") out.sort((a, b) => b.hi - a.hi || a.co.localeCompare(b.co))
    else out.sort((a, b) => a[sort].localeCompare(b[sort]))
    return out
  })

  const companies = $derived(new Set(filtered.map((j) => j.co)).size)

  const toggleLane = (l: string) =>
    (lanes = lanes.includes(l) ? lanes.filter((x) => x !== l) : [...lanes, l])

  const money = (j: Job) =>
    j.hi ? `$${Math.round(j.lo / 1000)}k - $${Math.round(j.hi / 1000)}k` : "not posted"
</script>

<svelte:head>
  <title>job board</title>
  <meta
    name="description"
    content="A filterable board of remote engineering, design, and product roles, rescanned daily."
  />
</svelte:head>

<header>
  <h1>job board</h1>
  {#if error}
    <p class="err">Could not load postings: {error}</p>
  {:else if !jobs.length}
    <p>Loading postings...</p>
  {:else}
    <p>
      {filtered.length.toLocaleString()} roles across {companies} companies. Scanned
      {generated.slice(0, 10)}.
    </p>
  {/if}
</header>

<section class="filters">
  <input type="search" bind:value={q} placeholder="Search title or company" />

  <div class="chips">
    {#each LANES as l (l)}
      <button class="chip" class:on={lanes.includes(l)} onclick={() => toggleLane(l)}>{l}</button>
    {/each}
    {#if lanes.length}
      <button class="chip clear" onclick={() => (lanes = [])}>clear</button>
    {/if}
  </div>

  <div class="row">
    <label>
      Min comp
      <input type="number" bind:value={minComp} min="0" max="500" step="10" />k
    </label>
    <label><input type="checkbox" bind:checked={remoteOnly} /> Remote only</label>
    <label><input type="checkbox" bind:checked={usOnly} /> US-eligible</label>
    <label>
      Sort
      <select bind:value={sort}>
        <option value="comp">comp</option>
        <option value="co">company</option>
        <option value="title">title</option>
      </select>
    </label>
  </div>
</section>

<table>
  <thead>
    <tr><th>Company</th><th>Role</th><th>Location</th><th>Comp</th></tr>
  </thead>
  <tbody>
    {#each filtered.slice(0, limit) as j (j.url + j.title)}
      <tr>
        <td class="co">{j.co}</td>
        <td><a href={j.url} target="_blank" rel="noopener">{j.title}</a></td>
        <td class="loc">{j.loc}</td>
        <td class="comp" class:none={!j.hi}>{money(j)}</td>
      </tr>
    {/each}
  </tbody>
</table>

{#if filtered.length > limit}
  <button class="more" onclick={() => (limit += 200)}>
    Show more ({(filtered.length - limit).toLocaleString()} left)
  </button>
{:else if jobs.length && !filtered.length}
  <p class="empty">Nothing matches. Loosen a filter.</p>
{/if}

<footer>
  <p>
    Public postings from Greenhouse, Ashby, and Lever, rescanned daily. Dead links drop off
    on the next scan. Comp is parsed from the posting and is sometimes wrong, so open the
    posting before you act on it.
  </p>
  <p><a href="https://github.com/marcuslyons/job-board">Source</a></p>
</footer>

<style>
  :global(body) {
    margin: 0;
    padding: 1.5rem;
    font:
      15px/1.5 ui-sans-serif,
      system-ui,
      sans-serif;
    color: #16181d;
    background: #fff;
  }
  @media (prefers-color-scheme: dark) {
    :global(body) {
      color: #e6e8ec;
      background: #14161a;
    }
  }
  h1 {
    margin: 0 0 0.25rem;
    font-size: 1.4rem;
  }
  header p {
    margin: 0 0 1rem;
    opacity: 0.7;
  }
  .err {
    color: #c0392b;
  }
  .filters {
    display: grid;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }
  input[type="search"] {
    padding: 0.5rem 0.7rem;
    font: inherit;
    width: min(100%, 28rem);
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .chip {
    padding: 0.25rem 0.6rem;
    font: inherit;
    font-size: 0.85rem;
    border: 1px solid currentColor;
    border-radius: 999px;
    background: none;
    color: inherit;
    cursor: pointer;
    opacity: 0.55;
  }
  .chip.on {
    opacity: 1;
    color: #fff;
    background: #2b6cb0;
    border-color: #2b6cb0;
  }
  .row {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
  }
  label {
    display: inline-flex;
    gap: 0.35rem;
    align-items: center;
  }
  input[type="number"] {
    width: 5rem;
    padding: 0.3rem;
    font: inherit;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th {
    text-align: left;
    border-bottom: 1px solid currentColor;
    padding: 0.4rem 0.5rem;
  }
  td {
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid rgba(127, 127, 127, 0.25);
    vertical-align: top;
  }
  .co {
    white-space: nowrap;
    opacity: 0.8;
  }
  .loc {
    opacity: 0.7;
    max-width: 18rem;
  }
  .comp {
    white-space: nowrap;
  }
  .comp.none {
    opacity: 0.45;
  }
  a {
    color: inherit;
  }
  .more {
    margin: 1rem 0;
    padding: 0.5rem 1rem;
    font: inherit;
    cursor: pointer;
  }
  .empty,
  footer {
    opacity: 0.7;
    font-size: 0.85rem;
  }
  footer {
    margin-top: 2rem;
    max-width: 42rem;
  }
</style>
