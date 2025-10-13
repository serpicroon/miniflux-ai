# miniflux-ai

[![GitHub issues](https://img.shields.io/github/issues/serpicroon/miniflux-ai)](https://github.com/serpicroon/miniflux-ai/issues)
[![GitHub license](https://img.shields.io/github/license/serpicroon/miniflux-ai)](https://github.com/serpicroon/miniflux-ai/blob/main/LICENSE)
[![Docker Image](https://img.shields.io/badge/docker-ghcr.io%2Fserpicroon%2Fminiflux--ai-blue)](https://github.com/serpicroon/miniflux-ai/pkgs/container/miniflux-ai)

> **Supercharge your RSS reading experience with AI-powered content processing**

An intelligent RSS feed processor that integrates seamlessly with Miniflux, leveraging Large Language Models (LLMs) to generate summaries, translations, and AI-driven news insights. Transform your information consumption with automated content enhancement and daily digest generation.

## ✨ Features

### 🔗 **Seamless Miniflux Integration**
- **Real-time Processing**: Webhook support for instant content processing
- **API Integration**: Fetch and process unread entries via Miniflux API

### 🤖 **Advanced LLM Processing**
- **Multi-Agent System**: Configurable AI agents for different content processing tasks
- **Smart Summaries**: Generate concise, professional summaries of articles
- **Translation**: High-quality translations preserving journalistic tone
- **Custom Prompts**: Fully customizable prompts for each processing agent

### 📰 **AI-Powered Daily Digest**
- **Scheduled Generation**: Automated daily digest creation at configurable times
- **Smart Categorization**: Intelligent content grouping and prioritization
- **RSS Feed Output**: Dedicated RSS feed for AI-generated digests

### ⚙️ **Flexible Configuration**
- **YAML Configuration**: Easy-to-manage configuration
- **URL Filtering**: Allow/deny lists for targeted content processing
- **Output Templates**: Customizable HTML templates for processed content
- **Rate Limiting**: Built-in request rate limiting and timeout management

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Miniflux instance** with API access
- **LLM API access** (OpenAI, Ollama, or compatible)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/serpicroon/miniflux-ai.git
   cd miniflux-ai
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the application**
   ```bash
   cp config.sample.English.yml config.yml
   # cp config.sample.Chinese.yml config.yml
   # Edit config.yml with your settings
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

The project includes a complete `docker-compose.yml` with Miniflux and PostgreSQL:

```yaml
services:
  miniflux:
    image: miniflux/miniflux:latest
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "80:8080"
    environment:
      - DATABASE_URL=postgres://miniflux:secret@postgres/miniflux?sslmode=disable
      - RUN_MIGRATIONS=1
      - CREATE_ADMIN=1
      - ADMIN_USERNAME=admin
      - ADMIN_PASSWORD=test123

  postgres:
    image: postgres:17-alpine
    environment:
      - POSTGRES_USER=miniflux
      - POSTGRES_PASSWORD=secret
      - POSTGRES_DB=miniflux
    volumes:
      - miniflux-db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "miniflux"]
      interval: 10s
      start_period: 30s

  miniflux-ai:
    container_name: miniflux-ai
    image: ghcr.io/serpicroon/miniflux-ai:latest
    restart: unless-stopped
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./config.yml:/app/config.yml
      # Optional: Persistent storage for digest data
      # - ./data:/app/data

volumes:
  miniflux-db:
```

**Deploy the stack:**
```bash
docker-compose up -d
```

### Standalone Docker

```bash
docker run -d \
  --name miniflux-ai \
  -v $(pwd)/config.yml:/app/config.yml \
  -e TZ=Asia/Shanghai \
  ghcr.io/serpicroon/miniflux-ai:latest
```

## ⚙️ Configuration

Create your configuration file from the provided templates:

```bash
# For English configuration
cp config.sample.English.yml config.yml

# For Chinese configuration  
cp config.sample.Chinese.yml config.yml
```

Edit `config.yml` to configure:
- **Miniflux**: API endpoint and credentials
- **LLM**: Model settings and API configuration
- **Digest**: Schedule and RSS feed settings
- **Agents**: AI processing agents and prompts

Refer to the sample configuration files for detailed examples and documentation.

### Webhook Setup

1. **Configure webhook in Miniflux:**
   - Go to Settings → Integrations → Webhook
   - Set URL: `http://your-miniflux-ai-server/api/miniflux-ai`
   - Set secret in `config.yml` under `miniflux.webhook_secret`

2. **For Docker Compose setup:**
   - Use container name: `http://miniflux-ai/api/miniflux-ai`

### Adding New Agents

1. **Define agent in `config.yml`:**
   ```yaml
   agents:
     your_agent:
       prompt: "Your custom prompt here..."
       template: "<div>${content}</div>"
       allow_list: []
       deny_list: []
   ```

2. **The system automatically processes unread entries with all configured agents**

### Custom LLM Integration

The project uses OpenAI-compatible APIs. Supported providers:
- **OpenAI GPT models**
- **Ollama (local LLMs)**
- **Anthropic Claude**
- **Google Gemini**
- **Any OpenAI-compatible API**

## 🔧 Troubleshooting

### Common Issues

<details>
<summary><strong>Content formatting issues in Miniflux</strong></summary>

Add this CSS to Miniflux Settings → Custom CSS:
```css
pre code {
    white-space: pre-wrap;
    word-wrap: break-word;
}
```
</details>

<details>
<summary><strong>Webhook not receiving events</strong></summary>

1. Verify webhook URL is accessible from Miniflux
2. Check webhook secret configuration
3. Review application logs for authentication errors
4. Ensure firewall allows incoming connections
</details>

<details>
<summary><strong>LLM timeout errors</strong></summary>

1. Increase `timeout` value in `config.yml`
2. Reduce `max_workers` for lower concurrency
3. Check LLM service availability
4. Verify API key and endpoint configuration
</details>

<details>
<summary><strong>Allow/deny lists not working as expected</strong></summary>

The filtering system uses **fnmatch patterns** (not regex) to match against the `site_url` field from RSS feeds.

1. **Wrong pattern syntax**: Use `*` for wildcards, not regex `.*`
   ```yaml
   # ✅ Correct (fnmatch)
   - https://example.com/*
   - *github.com/trending*
   
   # ❌ Wrong (regex syntax)
   - https://example\.com/.*
   - .*github\.com/trending.*
   ```

2. **Incomplete URL matching**: Match the full `site_url`, not just the domain
   ```yaml
   # ✅ Correct - matches full site_url
   - https://github.com/trending/?since=daily*
   - *spoken_language_code=zh*
   
   # ❌ Wrong - only domain
   - github.com
   - trending
   ```

3. **Case sensitivity**: Patterns are case-sensitive
   ```yaml
   # ✅ Match both cases if needed
   - *GitHub.com*
   - *github.com*
   ```

**Testing your patterns:**
```python
import fnmatch
site_url = "https://github.com/trending/?since=daily&spoken_language_code=zh"
pattern = "*github.com/trending*"
print(fnmatch.fnmatch(site_url, pattern))  # Should return True
```

**Debug tip**: Check your Miniflux feed detail to see the actual `site_url` values being processed.
</details>

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow Python PEP 8 style guidelines
- Add type hints for new functions
- Include docstrings for public methods
- Write tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Qetesh](https://github.com/Qetesh)** - Original author and creator of this project
- **[Miniflux](https://miniflux.app/)** - Minimalist RSS reader
- **[OpenAI](https://openai.com/)** - GPT models and API
- **Contributors** - Thank you to all contributors who help improve this project
