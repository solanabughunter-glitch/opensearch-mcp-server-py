# 🚀 Быстрый старт OpenSearch MCP Server

## Установка и запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/VladMain/opensearch-mcp-server-py.git
cd opensearch-mcp-server-py
```

### 2. Установка зависимостей

**Вариант A: С помощью uv (рекомендуется)**
```bash
# Установите uv, если не установлен
# https://docs.astral.sh/uv/getting-started/installation/

uv sync
```

**Вариант B: С помощью pip**
```bash
pip install -e .
```

### 3. Настройка конфигурации

Скопируйте и отредактируйте конфигурационный файл:
```bash
cp fort_config.yml your_config.yml
```

Пример конфигурации:
```yaml
clusters:
  your-cluster:
    opensearch_url: "https://your-opensearch.example.com"
    opensearch_username: "your_username"
    opensearch_password: "your_password"
    use_dashboards_api: true  # Для подключения через Dashboards API
```

### 4. Запуск сервера

**Вариант A: С помощью uv**
```bash
uv run mcp-server-opensearch --config your_config.yml
```

**Вариант B: С помощью Python**
```bash
python -m mcp_server_opensearch --config your_config.yml
```

**Вариант C: Удобный скрипт**
```bash
python start_server.py
```

## Интеграция с Claude Desktop

1. Скопируйте содержимое `claude_desktop_config.json` в конфигурацию Claude Desktop
2. Укажите правильный путь к вашему проекту
3. Перезапустите Claude Desktop

## Поддержка OpenSearch Dashboards

Этот MCP сервер поддерживает подключение через OpenSearch Dashboards API, когда прямой доступ к OpenSearch недоступен.

Установите в конфигурации:
```yaml
use_dashboards_api: true
```

Подробная инструкция: `FORT_OPENSEARCH_SETUP.md`

## Доступные инструменты

- **ListIndexTool** - список индексов
- **SearchIndexTool** - поиск по индексам
- **IndexMappingTool** - получение маппингов
- **ClusterHealthTool** - статус кластера
- **CountTool** - подсчет документов
- **GetShardsTool** - информация о шардах
- **MsearchTool** - множественный поиск
- **ExplainTool** - объяснение запросов

## Примеры использования

Через Claude Desktop можете задавать вопросы типа:

- "Покажи список индексов в OpenSearch"
- "Найди топ 5 событий по полю domain за последние 24 часа в индексе client.*"
- "Проверь здоровье кластера"
- "Сколько документов в индексе logs-2024.12.01?" 