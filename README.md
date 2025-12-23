# miniflux-ai

[![GitHub issues](https://img.shields.io/github/issues/serpicroon/miniflux-ai)](https://github.com/serpicroon/miniflux-ai/issues)
[![GitHub license](https://img.shields.io/github/license/serpicroon/miniflux-ai)](https://github.com/serpicroon/miniflux-ai/blob/main/LICENSE)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Fserpicroon%2Fminiflux--ai-blue)](https://github.com/serpicroon/miniflux-ai/pkgs/container/miniflux-ai)

> **Transform your RSS feed into an intelligent information hub**

An advanced, self-deployed AI companion for [Miniflux](https://miniflux.app/). While others just summarize, this project provides a robust pipeline to translate, analyze, and curate your information diet.

---

## 🚀 Why This Fork?

Built from the ground up for stability and data integrity.

### 1. 🛡️ Non-Destructive Processing
Unlike tools that overwrite content or clutter articles with raw text, this project uses **Semantic HTML Markers**.
- **Data Safety**: Original article content is **never modified**, only appended to.
- **Idempotency**: Agents can be re-run safely without duplicating content.
- **Clean UI**: AI outputs are injected as clean, styled HTML components.

### 2. 🔗 Source-Traceable Daily Digest
More than just a summary. The digest engine generates a structured briefing where every insight is verifiable:
- **Topic Clustering**: Intelligently groups related news (e.g., "AI Breakthroughs", "Global Markets").
- **Citation Backlinks**: Every point includes clickable references linking directly to the source article.
- **Deduplication**: Automatically filters out duplicate stories across different feeds.

### 3. 🎯 Powerful Rule-Based Filtering
Process exactly what matters with Miniflux-compatible filtering rules.
- **Flexible Targeting**: Match by title, URL, content, author, feed, tags—you name it.
- **Smart Filters**: Combine regex patterns with numeric operators (content length, token counts).
- **Token-Aware**: No more wasting API credits on trivial posts or empty updates.

### 4. ⚡ Enterprise-Level Concurrency
Designed to handle thousands of unread entries efficiently.
- **Global Thread Pool**: A singleton executor manages system resources to prevent overloads.
- **Pagination**: Fetches entries in batches to manage memory usage.
- **Retry Logic**: Built-in handling for network jitters and API rate limits.

---

## ✨ Endless Possibilities with Agents

You are not limited to "Summary" and "Translation". Define **custom agents** in your config to extract exactly what you need.

**Example: The "Market Analyst" Agent**
*Want to find trading signals in tech news?*
```yaml
agents:
  analyst:
    prompt: "Analyze this article for potential stock market impacts. Bullish or Bearish?"
    template: '<div class="insight-box">📈 <strong>Market Impact:</strong> {content}</div>'
    deny_rules:
      - EntryTitle=(?i)(advertisement|sponsored)  # Block ads
      - EntryContentLength=lt:100  # Only process substantial articles
    allow_rules:
      - FeedSiteURL=.*bloomberg\.com.*
      - FeedSiteURL=.*techcrunch\.com.*
```

**Example: The "TL;DR" Agent**
*Just want 3 bullet points for long-form content?*
```yaml
agents:
  tldr:
    prompt: "Give me 3 bullet points."
    template: '<div class="tldr">📝 {content}</div>'
    allow_rules:
      - EntryContentLength=between:200,2000  # Focus on medium-length articles
```

*Configure as many agents as you want. They run in sequence and stack beautifully.*

---

## 🚀 Quick Start

### Using Docker Compose (Recommended)

The easiest way to get started. We provide a complete `docker-compose.yml` that sets up Miniflux, the database, and the AI service together.

```bash
# 1. Clone the repository
git clone https://github.com/serpicroon/miniflux-ai.git
cd miniflux-ai

# 2. Configure your environment
cp config.sample.English.yml config.yml
# Edit config.yml with your API keys and preferences

# 3. Start the services
docker-compose up -d
```

### Standalone Docker

```bash
docker run -d \
  --name miniflux-ai \
  -v $(pwd)/config.yml:/app/config.yml \
  ghcr.io/serpicroon/miniflux-ai:latest
```

---

## ⚙️ Configuration

Instead of reading a long wiki, please refer to the extensively commented sample files:

- **[config.sample.English.yml](config.sample.English.yml)** - Recommended starting point.
- **[config.sample.Chinese.yml](config.sample.Chinese.yml)** - Chinese version with localized prompts.

**Key capabilities you can tweak:**
- **Rule-Based Filtering**: Control exactly which entries each agent processes with:
  - **deny_rules**: Block unwanted content (ads, spam, specific topics)
  - **allow_rules**: Whitelist only relevant entries
  - **Numeric operators**: `gt:`, `ge:`, `lt:`, `le:`, `eq:`, `between:` for content length filtering
  - **Regex patterns**: Powerful pattern matching across entry and feed fields
- **Digest Schedule**: Morning coffee or evening review? You decide.
- **HTML Templates**: Customize exactly how the AI output looks in your reader.

---

## 🔌 Setup Guide

### 1. Enable Real-time Processing
Go to Miniflux **Settings → Integrations → Webhook** and set:
- **Url**: `http://miniflux-ai/api/miniflux-ai` (use container name)
- **Secret**: Match the `webhook_secret` in your `config.yml`

### 2. Subscribe to Daily Digest
Once running, the system will **automatically create** a new feed in your Miniflux named **"Minifluxᴬᴵ Digest for you"**.
*Just wait for your first scheduled digest to arrive!*

---

## 🔧 Troubleshooting

<details>
<summary><strong>Rule-based filters not working?</strong></summary>

The filtering system uses **Regex patterns**.

**Rule Format**: `FieldName=RegexPattern`

**Supported Fields**:
- **Text fields** (regex matching):
  - Entry: `EntryTitle`, `EntryURL`, `EntryContent`, `EntryAuthor`, `EntryTag`
  - Feed: `FeedSiteURL`, `FeedTitle`, `FeedCategoryTitle`
- **Numeric fields** (operator matching):
  - `EntryContentLength` - Token count with `gt:`, `ge:`, `lt:`, `le:`, `eq:`, `between:` operators
- **Special**:
  - `NeverMatch` - Placeholder that never matches (useful for disabling rules)

**Examples**:
*   ✅ `FeedSiteURL=.*github\.com.*` (Match any github.com URL)
*   ✅ `EntryTitle=(?i)python` (Case-insensitive title match)
*   ✅ `EntryContentLength=gt:100` (More than 100 tokens)
*   ✅ `EntryContentLength=ge:50` (50 or more tokens)
*   ✅ `EntryContentLength=between:50,200` (50-200 tokens)
*   ❌ `*github.com*` (Old glob pattern - no longer supported)

**Rule Processing Order**:
1. **deny_rules** checked first → if matched, block immediately
2. **allow_rules** checked second → if defined, entry must match
3. **Default** → if no allow_rules defined, keep entry

**Tips**:
- Use `(?i)` prefix for case-insensitive regex matching
- Escape special regex characters (e.g., `\.` for literal dot)
- **deny_rules** always override **allow_rules** (security first)
- Omit `allow_rules` for blacklist mode (block specific, keep rest)
- Test regex at [regex101.com](https://regex101.com) (Python flavor)

See [config.sample.English.yml](config.sample.English.yml) for more examples.
</details>

<details>
<summary><strong>Webhook not triggering?</strong></summary>

*   Ensure the Miniflux container can reach the `miniflux-ai` container (they should be in the same Docker network).
*   Verify the webhook secret matches in both places.
</details>

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
