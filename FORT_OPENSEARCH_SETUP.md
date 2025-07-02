# Настройка MCP сервера для OpenSearch (fort-elkdev.gearwap.ru)

## Обзор

Этот документ описывает настройку MCP (Model Context Protocol) сервера для доступа к вашему развернутому OpenSearch сервису через OpenSearch Dashboards API.

## Что было сделано

### 1. Создан кастомный клиент для Dashboards API

- **Файл**: `src/opensearch/dashboards_client.py`
- **Назначение**: Эмулирует стандартный opensearch-py клиент, но работает через OpenSearch Dashboards API
- **Функции**:
  - Получение информации о кластере
  - Список индексов
  - Статус кластера
  - Базовый поиск (заглушка)

### 2. Обновлен основной клиент

- **Файл**: `src/opensearch/client.py`
- **Изменения**: Добавлена поддержка режима `use_dashboards_api`
- **Логика**: Если в конфигурации установлен флаг `use_dashboards_api: true`, используется кастомный Dashboards клиент

### 3. Расширена модель конфигурации

- **Файл**: `src/mcp_server_opensearch/clusters_information.py`
- **Добавлено**: Поле `use_dashboards_api` в модель `ClusterInfo`
- **Функция**: Отключена проверка подключения при загрузке для Dashboards кластеров

### 4. Исправлена система фильтрации инструментов

- **Файл**: `src/tools/tool_filter.py`
- **Проблема**: Функция получения версии OpenSearch вызывалась без имени кластера
- **Решение**: Добавлена логика использования первого доступного кластера для проверки версии

## Конфигурация

### Основной файл конфигурации: `fort_config.yml`

```yaml
version: "1.0"
description: "OpenSearch cluster configuration for fort-elkdev.gearwap.ru"

clusters:
  # Ваш рабочий кластер OpenSearch через Dashboards
  fort-elkdev:
    opensearch_url: "https://fort-elkdev.gearwap.ru"
    opensearch_username: "pophadze"
    opensearch_password: "mynameistoizy95"
    # Используем Dashboards API вместо прямого OpenSearch API
    use_dashboards_api: true
```

## Использование

### Запуск MCP сервера

```bash
# Запуск в фоновом режиме
python -m mcp_server_opensearch --config fort_config.yml

# Или с использованием uv
uv run mcp-server-opensearch --config fort_config.yml
```

### Тестирование

Создан скрипт тестирования `test_mcp_server.py`:

```bash
python test_mcp_server.py
```

Результаты тестирования:
- ✅ Ping/Info - работает
- ✅ Cluster Health - работает  
- ✅ List Indices - работает (найдено 20 индексов)

## Доступные возможности

### Через Dashboards API доступны:

1. **Информация о кластере**
   - Общая информация о системе
   - Статус кластера (green/yellow/red)

2. **Управление индексами**
   - Список всех индексов
   - Получение информации об индексах
   - Проверка существования индексов

3. **Системная информация**
   - Статус OpenSearch Dashboards
   - Доступные saved objects (индексные паттерны)

### Ограничения

- **Поиск**: Базовая заглушка (возвращает пустые результаты)
- **Сложные операции**: Не все OpenSearch API доступны через Dashboards
- **Производительность**: Дополнительный слой абстракции

## Интеграция с Claude Desktop

Для использования с Claude Desktop добавьте в конфигурацию MCP:

```json
{
  "mcpServers": {
    "opensearch-fort": {
      "command": "python",
      "args": ["-m", "mcp_server_opensearch", "--config", "fort_config.yml"],
      "cwd": "/path/to/opensearch-mcp-server-py"
    }
  }
}
```

## Архитектура решения

```
Claude Desktop
    ↓ (MCP Protocol)
MCP Server (opensearch-mcp-server-py)
    ↓ (HTTP Requests)
OpenSearch Dashboards API
    ↓ (Internal calls)
OpenSearch Cluster (fort-elkdev.gearwap.ru)
```

## Файлы для работы

### Основные файлы
- `fort_config.yml` - конфигурация кластера
- `src/opensearch/dashboards_client.py` - клиент Dashboards API
- `src/opensearch/client.py` - основной клиент (модифицированный)

### Тестовые файлы  
- `test_mcp_server.py` - основной тест
- `test_dashboards_api.py` - тест Dashboards API
- `create_dashboards_adapter.py` - прототип адаптера

### Утилиты
- `test_connection.py` - тест подключения
- `test_with_credentials.py` - тест с учетными данными
- `find_opensearch_api.py` - поиск API endpoints

## Безопасность

⚠️ **Внимание**: Учетные данные хранятся в открытом виде в конфигурационном файле. 

**Рекомендации**:
1. Не коммитьте `fort_config.yml` в git
2. Используйте переменные окружения для продакшена
3. Ограничьте доступ к файлу конфигурации

## Следующие шаги

1. **Расширение поиска**: Реализовать поиск через Console API
2. **Оптимизация**: Кэширование запросов к Dashboards
3. **Мониторинг**: Добавить логирование и метрики
4. **Безопасность**: Зашифровать учетные данные

## Поддержка

В случае проблем:
1. Проверьте доступность `https://fort-elkdev.gearwap.ru`
2. Убедитесь в корректности учетных данных
3. Проверьте логи MCP сервера
4. Запустите тест: `python test_mcp_server.py` 