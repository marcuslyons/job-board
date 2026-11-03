#!/usr/bin/env python3
"""Run: python3 test_jobscan.py

The classifier decides what the whole board shows, and it fails silently: a title
that matches no lane disappears without a trace. Every case below is a real title
pulled from a live scan.
"""
from jobscan import lanes_for, us_reachable, comp_range

KEEP = {
    # the generic-title hole: these matched no lane before the swe fallback
    "Senior Software Engineer": "swe",
    "Staff Software Engineer, IAM Control Plane": "swe",
    "Software Engineer, High Availability and Disaster Recovery": "swe",
    "Software Engineer - C++": "swe",
    # topic lanes still win over the fallback
    "Staff Software Engineer, DevEx": "devex",
    "Senior Infrastructure Engineer/SRE": "infra",
    "Lead Platform Engineer, Identity & Access": "platform",
    "Senior Staff Machine Learning Engineer, GenAI Platform": "ai",
    "Senior Data Platform Engineer": "data",
    "Senior Frontend Engineer": "frontend",
    "Senior Software Engineer, React": "frontend",
    "Senior Backend Engineer, AI Engineering: Chat": "backend",
    "Senior Full-Stack Engineer": "fullstack",
    "Senior iOS Engineer": "mobile",
    "Senior Security Engineer, AppSec": "security",
    "Senior Product Designer": "design",
    "Senior Product Manager, Payments": "pm",
    "Engineering Manager, Platform": "em",
    "Staff Software Engineer (Continuous Integration)": "devex",
}

DROP = [
    "Integration Engineer, Professional Services",
    "Partner Solutions Architect - Billing",
    "Manager, Technical Account Management",
    "High School Internship, Software Engineering (Summer 2027)",
    "Software Engineer, New Grad",
    "Software Engineer, Early Career",
    "IT Support Engineer",
    "Senior Recruiter, Engineering",
    "Account Executive, Enterprise",
    "Staff Accountant",
]

for title, lane in KEEP.items():
    got = lanes_for(title)
    assert lane in got, f"{title!r} -> {got}, expected {lane}"

for title in DROP:
    assert not lanes_for(title), f"{title!r} -> {lanes_for(title)}, expected no lane"

US = [
    "Remote - US",
    "Remote, United States",
    "United States",
    "Seattle, WA",
    "Remote",
    "San Francisco, CA; Remote, Canada",
    "Remote, Canada; Remote, United States",
    "",
]
NOT_US = [
    "Remote, United Kingdom",
    "Bengaluru, India",
    "London",
    " -REMOTE, UK-",
    "Dublin, Ireland",
    "Toronto",
]

for loc in US:
    assert us_reachable(loc), f"{loc!r} should be US-reachable"
for loc in NOT_US:
    assert not us_reachable(loc), f"{loc!r} should not be US-reachable"

# Comp parsing took four passes to get right; these are the shapes that broke it.
assert comp_range("$150,000 - $200,000") == (150000, 200000)
assert comp_range("&lt;span&gt;$286,762&lt;/span&gt;—&lt;span&gt;$347,488&lt;/span&gt;") == (286762, 347488)
# multi-geo: take the band with the lowest floor, which is the non-metro one
assert comp_range("$180,000 - $240,000 ... $151,000 - $242,000") == (151000, 242000)
assert comp_range("no numbers here") == (0, 0)
assert comp_range("401(k) and $5,000 stipend") == (0, 0)

print("ok")
