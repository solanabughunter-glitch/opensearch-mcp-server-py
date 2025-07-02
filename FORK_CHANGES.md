# 🔀 Изменения в форке

Этот репозиторий является форком от [opensearch-project/opensearch-mcp-server-py](https://github.com/opensearch-project/opensearch-mcp-server-py) с дополнительной функциональностью.

## 🆕 Новая функциональность

### OpenSearch Dashboards API Support
- **Новый клиент**: `src/opensearch/dashboards_client.py`
- **Поддержка подключения** через OpenSearch Dashboards API когда прямой доступ к OpenSearch недоступен
- **Полная эмуляция** opensearch-py клиента через Dashboards
- **Автоматическое обнаружение** Console API

### Конфигурация
Добавлен новый параметр в конфигурацию кластера:
```yaml
clusters:
  your-cluster:
    opensearch_url: "https://your-dashboards.example.com"
    opensearch_username: "username"
    opensearch_password: "password"
    use_dashboards_api: true  # 🆕 НОВЫЙ ПАРАМЕТР
```

### Поддерживаемые операции через Dashboards
- ✅ `ping()` - проверка подключения
- ✅ `info()` - информация о кластере
- ✅ `cluster.health()` - здоровье кластера
- ✅ `cat.indices()` - список индексов
- ✅ Console API для продвинутых запросов

## 📁 Измененные файлы

### Основной код
- `src/opensearch/client.py` - добавлена поддержка `use_dashboards_api`
- `src/opensearch/dashboards_client.py` - **НОВЫЙ** кастомный клиент
- `src/mcp_server_opensearch/clusters_information.py` - обновлена модель кластера
- `src/tools/tool_filter.py` - исправлена логика определения версии

### Конфигурация и документация
- `README.md` - обновлен с информацией о форке
- `QUICK_START.md` - **НОВЫЙ** краткий гайд
- `FORT_OPENSEARCH_SETUP.md` - **НОВЫЙ** детальная инструкция
- `pyproject.toml` - обновлены ссылки и версия
- `start_server.py` - обновлен для uv
- `claude_desktop_config.json` - готовая конфигурация

## 🎯 Совместимость

✅ **Полная обратная совместимость** с оригинальным MCP сервером  
✅ **Все существующие функции** работают без изменений  
✅ **Дополнительная возможность** подключения через Dashboards  
✅ **Стандартные MCP инструменты** остаются неизменными  

## 🚀 Применение

Идеально подходит для случаев, когда:
- Прямой доступ к OpenSearch API заблокирован
- Доступен только OpenSearch Dashboards
- Нужна работа через корпоративный proxy
- Требуется дополнительная аутентификация

## 🔄 Синхронизация с upstream

Форк основан на версии `0.3.0` оригинального репозитория.
Периодически синхронизируется с upstream для получения новых функций.

## 📞 Обратная связь

Если у вас есть вопросы по новой функциональности или предложения по улучшению, создавайте issues в этом репозитории. 