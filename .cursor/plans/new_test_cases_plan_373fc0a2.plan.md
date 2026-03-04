---
name: New test cases plan
overview: Add 6 new test cases covering happy-path, unhappy-path, and edge-case scenarios that are not yet exercised by the existing 6 tests.
todos:
  - id: multi-page-synthesis
    content: Create tests/multi-page-synthesis.yaml — happy path, combine info from 2 pages
    status: completed
  - id: specific-fact-extraction
    content: Create tests/specific-fact-extraction.yaml — happy path, extract precise facts
    status: completed
  - id: page-error-fallback
    content: Create tests/page-error-fallback.yaml — unhappy path, first page fails, agent retries another URL
    status: completed
  - id: all-pages-fail
    content: Create tests/all-pages-fail.yaml — unhappy path, all page reads error out
    status: completed
  - id: contradictory-sources
    content: Create tests/contradictory-sources.yaml — edge case, conflicting info across pages
    status: completed
  - id: single-search-result
    content: Create tests/single-search-result.yaml — edge case, only one search result returned
    status: completed
  - id: run-and-integrate
    content: Run each test individually, then add passing tests to promptfooconfig.yaml
    status: completed
isProject: false
---

# New Test Cases for Web Search Agent

## Coverage Gap Analysis

Existing tests cover: basic factual lookup, browse-and-summarize, multi-source news, injection resistance, no results, and retry on irrelevant results. The gaps below target untested agent behaviors.

## Proposed Tests

### Happy Path

**1. `tests/multi-page-synthesis.yaml`** — Agent must read 2+ pages and combine facts into a single coherent answer.

- Input: "What are the pros and cons of using TypeScript over JavaScript?"
- Fixtures: search returns TS-related links; two `get_page_content` responses — one page covers pros, the other covers cons.
- Assertions:
  - `has_answer` (length > 80)
  - `read_multiple_pages`: at least 2 `get_page_content` calls
  - `mentions_pros_and_cons`: answer matches both `/pros|advantages|benefits/i` and `/cons|disadvantages|drawbacks/i`
  - LLM rubric: balanced answer drawing from both sources, no fabrication

**2. `tests/specific-fact-extraction.yaml`** — Agent extracts a specific numeric/date fact rather than a broad summary.

- Input: "When was Python first released and who created it?"
- Fixtures: search returns Python history links; page contains "first released in 1991" and "created by Guido van Rossum."
- Assertions:
  - `has_answer`
  - `mentions_year`: answer matches `/1991/`
  - `mentions_creator`: answer matches `/Guido van Rossum/i`
  - `used_tools`: both search and get_page used
  - LLM rubric: concise factual answer, grounded in source

### Unhappy Path

**3. `tests/page-error-fallback.yaml`** — First page load fails; agent should try a different URL from the search results.

- Input: "What is Kubernetes and what is it used for?"
- Fixtures: search returns 3 links; first `get_page_content` returns `{page_text: null, error: "Connection timed out"}`, second returns valid Kubernetes info.
- Assertions:
  - `has_answer` (length > 50)
  - `read_multiple_pages`: at least 2 `get_page_content` calls (tried fallback)
  - `answer_about_kubernetes`: matches `/container|orchestration|cluster/i`
  - LLM rubric: correctly explains Kubernetes, does not mention the failed page

**4. `tests/all-pages-fail.yaml`** — Search works but every page read errors out; agent should give an honest "could not read" answer (or best-effort from titles).

- Input: "How does photosynthesis work?"
- Fixtures: search returns 3 science links; all `get_page_content` calls return `{page_text: null, error: "Navigation timeout"}`.
- Assertions:
  - `has_answer`
  - `used_search`: at least 1 search call
  - `attempted_pages`: at least 1 `get_page_content` call
  - LLM rubric: agent acknowledges it could not retrieve page content; does not fabricate a detailed scientific explanation as if sourced

### Edge Cases

**5. `tests/contradictory-sources.yaml`** — Two pages give conflicting information; agent should note the discrepancy or present both perspectives.

- Input: "How much caffeine is in a cup of green tea?"
- Fixtures: search returns health/tea links; page 1 says "25-30 mg per cup", page 2 says "50-70 mg per cup."
- Assertions:
  - `has_answer`
  - `read_multiple_pages`: at least 2 `get_page_content` calls
  - `mentions_numbers`: answer matches `/\d+\s*mg/i`
  - LLM rubric: answer mentions the variation or range rather than asserting a single false-precision number; does not silently pick one source

**6. `tests/single-search-result.yaml`** — Search returns only one result; agent should still work correctly with minimal data.

- Input: "What is the Gleam programming language?"
- Fixtures: search returns exactly 1 link; `get_page_content` returns Gleam info.
- Assertions:
  - `has_answer` (length > 30)
  - `searched_once`: exactly 1 `search_google` call (no unnecessary retry)
  - `used_get_page`
  - LLM rubric: correctly describes Gleam, grounded in the single source

## Integration

After each test passes individually (`npm test -- tests/<name>.yaml`), add the new files to the `tests:` list in [promptfooconfig.yaml](promptfooconfig.yaml).
