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

### 3. 💰 Cost-Efficient Filtering
Don't waste API credits on empty updates or image-only posts.
- **Smart Skip**: Ignores entries that are too short or lack meaningful text content.
- **Token-Based Thresholds**: Define minimum length using `tiktoken` counts. This ensures fair filtering for both concise languages (like Chinese) and verbose ones (like English), avoiding processing of low-value entries.

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
    allow_rules:
      - FeedSiteUrl=.*bloomberg\.com.*
      - FeedSiteUrl=.*techcrunch\.com.*
```

**Example: The "TL;DR" Agent**
*Just want 3 bullet points?*
```yaml
agents:
  tldr:
    prompt: "Give me 3 bullet points."
    template: '<div class="tldr">📝 {content}</div>'
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
- **Rule-Based Filtering**: Control exactly which entries each agent processes using powerful regex rules.
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

The filtering system uses **Regex patterns** with Miniflux-style rules.

**Rule Format**: `FieldName=RegexPattern`

**Supported Fields**:
- Entry fields: `EntryTitle`, `EntryURL`, `EntryContent`, `EntryAuthor`, `EntryTag`
- Feed fields: `FeedSiteUrl`, `FeedTitle`, `FeedCategoryTitle`
- Special: `EntryContentMinLength` (numeric), `NeverMatch` (placeholder)

**Examples**:
*   ✅ `FeedSiteUrl=.*github\.com.*` (Match any github.com URL)
*   ✅ `EntryTitle=(?i)python` (Case-insensitive title match)
*   ✅ `EntryContentMinLength=100` (Minimum 100 tokens)
*   ❌ `*github.com*` (Old glob pattern - no longer supported)

**Tips**:
- Use `(?i)` prefix for case-insensitive matching
- Remember to escape special regex characters (e.g., `\.` for literal dot)
- Rules are evaluated in order; first match wins

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
