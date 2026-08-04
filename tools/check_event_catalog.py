"""Reconcile the document 03 event catalog against document 04 declarations.

Guards review findings C3, C4, C5, C37, C38: a consumer declared in the catalog
but absent from a sub-application, or vice versa, is an unbuildable
consumer-driven conformance test and a silently undeclared dependency.

Run from the repository root.  Exits non-zero on any discrepancy.
"""
import os, re, sys, collections

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'architecture')
D3 = open(os.path.join(DOCS, '03-integration-contracts.md')).read()
D4 = open(os.path.join(DOCS, '04-subapplication-architectures.md')).read()

SLUGS = {'registry','telemetry','pdm','fleet-status','maintenance','supply','pma',
         'failure-intel','design-advisory','gateway','audit','notification',
         'knowledge-retrieval','reference-data','sync','tool-server','auth'}

# --- parse doc 03 catalog: rows are | `event` | payload | consumers |
cat = {}                       # event -> set(consumer slugs)
sec = D3[D3.index('## 6. Event catalog'):D3.index('## 7. Shared payload')]
for line in sec.splitlines():
    m = re.match(r'\|\s*`([a-z_]+\.[a-z_]+)`\s*\|(.*?)\|(.*?)\|\s*$', line)
    if not m: continue
    ev, _, cons = m.groups()
    found = {s for s in SLUGS if re.search(r'`'+re.escape(s)+r'`', cons)}
    cat[ev] = found

# --- parse doc 04 published/consumed per section
pub = collections.defaultdict(set); con = collections.defaultdict(set)
cur = None
NAME2SLUG = {
 'Asset & Configuration Registry':'registry','Condition & Telemetry':'telemetry',
 'Predictive Maintenance':'pdm','Fleet Status & Readiness':'fleet-status',
 'Maintenance Execution & Scheduling':'maintenance','Supply Chain & Inventory':'supply',
 'Post-Mission Analysis':'pma','Failure Intelligence':'failure-intel',
 'System Test & Design Advisory':'design-advisory'}
for line in D4.splitlines():
    h = re.match(r'## \d+\. (.+)', line)
    if h: cur = NAME2SLUG.get(h.group(1).strip()); continue
    if not cur: continue
    for label, tgt in (('Events published:',pub), ('Events consumed:',con)):
        if line.startswith('**'+label):
            tgt[cur] |= set(re.findall(r'`([a-z_]+\.[a-z_]+)`', line))

print(f"doc03 catalog events: {len(cat)}")
print(f"doc04 published: {sum(len(v) for v in pub.values())}  consumed: {sum(len(v) for v in con.values())}\n")

errs = 0
# 1. every catalog event is published by exactly the sub-app that owns its topic
published_all = {e for s in pub.values() for e in s}
for ev in sorted(cat):
    if ev not in published_all:
        print(f"[MISSING PUBLISHER] {ev} in catalog, published by nobody in doc04"); errs+=1
for slug, evs in pub.items():
    for ev in sorted(evs):
        if ev not in cat:
            print(f"[NOT IN CATALOG] {slug} publishes {ev}, absent from doc03 catalog"); errs+=1

# 2. declared consumers in 03 must consume in 04
for ev, consumers in sorted(cat.items()):
    for c in sorted(consumers):
        if c in NAME2SLUG.values() and ev not in con[c]:
            print(f"[DECLARED NOT CONSUMED] doc03 says {c} consumes {ev}; doc04 does not"); errs+=1

# 3. consumers in 04 must be declared in 03
for slug, evs in sorted(con.items()):
    for ev in sorted(evs):
        if ev not in cat:
            print(f"[UNKNOWN EVENT] {slug} consumes {ev}, not in catalog"); errs+=1
        elif slug not in cat[ev]:
            print(f"[UNDECLARED DEPENDENCY] {slug} consumes {ev}; doc03 does not list it"); errs+=1

print(f"\n{'PASS' if errs==0 else str(errs)+' discrepancies'}")
sys.exit(1 if errs else 0)
