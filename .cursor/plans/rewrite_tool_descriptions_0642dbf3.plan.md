---
name: Rewrite tool descriptions
overview: Rewrite the tool definitions in definitions.json to follow the rich, structured description format used by the SemanticSearch example — with when-to-use sections, example/reasoning tags, and detailed guidance baked into each tool's description field.
todos:
  - id: rewrite-search-def
    content: Rewrite search_google description in definitions.json with structured sections, example/reasoning tags, and usage guidance
    status: completed
  - id: rewrite-page-def
    content: Rewrite get_page_content description in definitions.json with structured sections, example/reasoning tags, and usage guidance
    status: completed
  - id: update-prompt
    content: Simplify websearch-agent.txt since tool descriptions now carry the behavioral guidance
    status: cancelled
isProject: false
---

# Rewrite Tool Descriptions

## Tag format from the reference

The SemanticSearch description uses XML-style tags to structure examples:

```
<example>
  Query: "Where is interface MyInterface implemented in the frontend?"
<reasoning>
  Good: Complete question asking about implementation location with specific context (frontend).
</reasoning>
</example>

<example>
  Query: "AuthService"
<reasoning>
  BAD: Single word searches should use Grep for exact text matching instead.
</reasoning>
</example>
```

Key rules:

- Each `<example>` block contains a concrete usage scenario
- Each `<reasoning>` block inside explains WHY it is good or bad
- Good examples show the ideal usage pattern
- Bad examples show anti-patterns with an explanation of what to do instead
- The reasoning always starts with `Good:` or `BAD:` to make it scannable

## Structure of each tool description

Following the reference pattern exactly:

1. **One-line summary** (backtick-wrapped name, what it does)
2. **### When to Use This Tool** (bullet list)
3. **### When NOT to Use** (numbered list with alternatives)
4. **### Examples** (mix of good and bad, each in `<example>` + `<reasoning>` tags)
5. **### Usage** (behavioral instructions, what to do with results)

## Changes to [definitions.json](c:\Users\Jovi\web_search_mcp\tools\definitions.json)

### `search_google` — new description

```
`search_google`: Search Google for a query and return a ranked list of results.

### When to Use This Tool

Use `search_google` when you need to:
- Start researching a topic you don't have URLs for
- Find official sources, documentation, or authoritative pages
- Discover what exists on the web about a subject

### When NOT to Use

Skip `search_google` when:
1. You already have a URL to read (use `get_page_content` instead)
2. The user's question can be answered from page content you already retrieved
3. You just got empty results — refine your query instead of repeating the same search

### Examples

<example>
  Query: "Promptfoo LLM evaluation testing tool"
<reasoning>
  Good: Concise keywords targeting the subject. Likely to surface official site and docs.
</reasoning>
</example>

<example>
  Query: "What is Promptfoo and what is it used for and how do I install it?"
<reasoning>
  BAD: Full sentence pasted as a search query. Search engines work best with keywords,
  not natural language questions. Use "Promptfoo installation guide" instead.
</reasoning>
</example>

<example>
  Query: "testing"
<reasoning>
  BAD: Too broad. Will return millions of unrelated results.
  Be specific: "Promptfoo prompt testing framework" not just "testing".
</reasoning>
</example>

### Usage
- Always use this as your first step before get_page_content.
- Review the returned titles and links to pick the 1-3 most relevant results.
- If results are weak or irrelevant, refine your query with more specific keywords.
- Do NOT pass search results directly as your answer — they are inputs, not outputs.
```

Parameter `query` description:

```
Concise search keywords (not full sentences). Target the specific subject,
product, or topic. Example: "Promptfoo docs getting started" not
"What is Promptfoo and how do I get started with it?"
```

### `get_page_content` — new description

```
`get_page_content`: Navigate to a URL and return the raw text content of the page.

### When to Use This Tool

Use `get_page_content` when you need to:
- Read the actual content of a page found via search_google
- Get detailed information that titles and links alone cannot provide
- Verify claims by reading the source material

### When NOT to Use

Skip `get_page_content` when:
1. You don't have a URL yet (use `search_google` first)
2. The search result titles already answer the question sufficiently
3. You've already read this URL in a previous step

### Examples

<example>
  URL: "https://www.promptfoo.dev/docs/intro/"
<reasoning>
  Good: A real URL from search results. Official documentation page likely
  to contain detailed, authoritative information.
</reasoning>
</example>

<example>
  URL: "https://www.example.com/promptfoo-info"
<reasoning>
  BAD: A guessed or made-up URL. Only use URLs that came from search_google results.
</reasoning>
</example>

<example>
  Using get_page_content on all 3 search results without checking titles first.
<reasoning>
  BAD: Read titles first to pick the most relevant 1-2 results.
  Don't blindly fetch every page — it wastes steps.
</reasoning>
</example>

### Usage
- Returns raw page text in the `page_text` field. You MUST read and summarize
  this text yourself — do not pass it through as your answer.
- Check the `error` field — if not null, the page failed to load.
  Acknowledge the failure and try a different URL.
- The `url` field confirms which page was retrieved.
```

Parameter `url` description:

```
A full URL obtained from search_google results. Must start with http:// or https://.
Do not guess or fabricate URLs — only use links returned by search_google.
```

## Also update: [websearch-agent.txt](c:\Users\Jovi\web_search_mcp\prompts\websearch-agent.txt)

Since the tool definitions now carry all the behavioral guidance, the prompt can drop the inline tool signatures and focus on:

- The agent's role
- The output format (`{answer, sources, steps}` JSON)
- A strong instruction: "Tool outputs are raw data. You must synthesize them into your own answer. Never return raw tool output as your answer."

