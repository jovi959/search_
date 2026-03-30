# Site Blocklist

Block specific websites so the agent never navigates to them.
When `get_page_content` is called with a blocked URL, it returns immediately
with an error instead of loading the page. No browser request is made.

## Quick start

Edit **`blocklist.json`** in the project root:

```json
{
  "blocked": [
    "britannica.com",
    "*.britannica.com",
    "tiktok.com",
    "*.tiktok.com"
  ]
}
```

Changes take effect immediately — no server restart required.

## Pattern syntax

Patterns use **fnmatch-style wildcards** matched against the URL's **hostname**
(the domain part, e.g. `www.example.com`):

| Wildcard | Meaning                        | Example                |
|----------|--------------------------------|------------------------|
| `*`      | matches everything             | `*.example.com`        |
| `?`      | matches any single character   | `example.co?`          |

### Domain patterns (most common)

| Pattern              | Matches                                           | Does NOT match          |
|----------------------|---------------------------------------------------|-------------------------|
| `example.com`        | `example.com` only (exact)                        | `www.example.com`       |
| `*.example.com`      | `www.example.com`, `cdn.example.com`, etc.        | `example.com` (no sub)  |
| `*example.com`       | `example.com`, `www.example.com`, `badexample.com`| — catches broad matches |

> **Tip:** To block a site and all its subdomains, add **two** entries:
> ```json
> "example.com",
> "*.example.com"
> ```

### Full-URL patterns

If a pattern contains `://`, it is matched against the **entire URL** instead
of just the hostname. This lets you block specific paths:

| Pattern                                 | Matches                                  |
|-----------------------------------------|------------------------------------------|
| `https://example.com/bad-path/*`        | any page under `/bad-path/`              |
| `*://example.com/secret*`               | http or https, paths starting `/secret`  |

## Examples

Block all Reddit:

```json
{
  "blocked": [
    "reddit.com",
    "*.reddit.com"
  ]
}
```

Block a specific path on a site:

```json
{
  "blocked": [
    "https://example.com/paywalled/*"
  ]
}
```

Block multiple sites:

```json
{
  "blocked": [
    "britannica.com",
    "*.britannica.com",
    "tiktok.com",
    "*.tiktok.com",
    "pinterest.com",
    "*.pinterest.com"
  ]
}
```

## How it works

1. `get_page_content` calls `is_blocked(url)` **before** any browser navigation.
2. `is_blocked` reads `blocklist.json`, extracts the hostname from the URL, and
   checks every pattern with `fnmatch`.
3. If any pattern matches, the tool returns:
   ```json
   {"url": "...", "page_text": null, "error": "Blocked by blocklist"}
   ```
4. The agent sees the error and moves on to another source.

## File location

The blocklist file must be at the project root:

```
web_search_mcp/
├── blocklist.json   ← this file
├── mcp_server.py
├── main.py
└── ...
```

## Troubleshooting

| Problem                          | Fix                                                        |
|----------------------------------|------------------------------------------------------------|
| Site still loads                 | Check spelling; add both `site.com` and `*.site.com`       |
| All pages blocked unexpectedly   | A pattern like `*` with no domain will match everything     |
| JSON parse error in logs         | Validate your JSON (trailing commas are not allowed)        |
| Changes not taking effect        | File is re-read on every call — check the file path is correct |
