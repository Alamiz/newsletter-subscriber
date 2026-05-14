# Newsletter Automation Tool

CLI-based newsletter subscription automation tool using:
- Python
- Playwright
- Camoufox
- Rich CLI

Primary goal:
1. Stealth / human realism
2. Reliability
3. Scalable handler architecture

Speed is NOT the priority.

---

# Core Architecture

The system is EMAIL-CENTRIC.

Each email gets:
- one persistent browser profile
- one assigned proxy
- one browser context/session

The same profile is reused across ALL newsletters for that email.

Profiles are deleted only after all newsletters finish.

NEVER reuse profiles across different emails.

---

# Input Files

## emails.txt

```txt
email@example.com
```

## proxies.txt

```txt
user:password@ip:port
```

## newsletters.txt

```txt
morningbrew
thehustle
```

Each entry maps directly to:

```txt
handlers/<newsletter>.py
```

Handlers are dynamically imported.

---

# Project Structure

```txt
/core
/handlers
/utils
/output
/profiles

emails.txt
proxies.txt
newsletters.txt

subscribe.py
start.bat
```

---

# Handler Rules

Handlers contain ONLY newsletter-specific logic.

Handlers SHOULD:
- navigate
- click
- fill fields
- validate success conditions

Handlers SHOULD NOT:
- manage retries
- manage threading
- manage proxies
- manage filesystem writes
- manage output folders
- manage screenshots
- manage orchestration

Use function-based handlers:

```python
async def run(page, email, logger):
```

The user provides:
- selectors
- flow steps
- success conditions

Follow them exactly.

---

# Concurrency Model

Default:
- 10 concurrent emails

Execution flow:
1. load email
2. assign proxy
3. create persistent profile
4. process all newsletters sequentially
5. destroy profile
6. load next email

Concurrency is managed centrally via ThreadPoolExecutor.

Handlers must remain concurrency-agnostic.

---

# Retry Rules

Retries are mandatory.

Rules:
- retry full handler execution
- max 3 retries
- restart browser/context on retry

If proxy fails:
- rotate to next proxy

If CAPTCHA appears:
- take screenshot
- mark as CAPTCHA
- continue queue

---

# Statuses

- SUCCESS
- FAILED
- ERROR
- CAPTCHA

---

# Screenshots

Take screenshots ONLY on:
- FAILED
- ERROR
- CAPTCHA

---

# Logging

Logging must be extremely verbose.

Each email run should include:
- run.log
- screenshots folder
- metadata.json

Log:
- steps
- selectors
- retries
- URLs
- timings
- failure reasons
- proxy info

---

# Output Structure

```txt
/output
    /<newsletter>
        /SUCCESS
        /FAILED
        /ERROR
        /CAPTCHA
```

Each email gets its own folder.

---

# Browser Rules

Do NOT:
- disable Camoufox protections
- remove humanization
- optimize aggressively for speed
- process same email concurrently

Contexts may:
- open tabs
- use evaluate()
- use multiple pages

---

# CLI Requirements

Use Rich for a colorful CLI.

Display:
- progress bars
- active emails
- recent statuses
- ETA
- elapsed time
- status counts
- current newsletter

---

# Coding Style

- prefer async Playwright APIs
- keep handlers thin
- centralize orchestration logic
- use enums for statuses
- use structured result objects
- avoid overengineering

---

# AI Agent Rules

When adding a new handler:
1. create file in `/handlers`
2. implement only newsletter logic
3. follow existing patterns
4. reuse shared utilities
5. avoid duplicating orchestration logic

NEVER:
- reuse profiles across emails
- disable retries
- disable logging
- disable failure screenshots
- move orchestration into handlers
- optimize for speed over stealth

---

# start.bat

Responsibilities:
1. git pull
2. install/update dependencies if needed
3. run subscribe.py