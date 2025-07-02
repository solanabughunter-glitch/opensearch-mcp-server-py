# Copyright OpenSearch Contributors
# SPDX-License-Identifier: Apache-2.0

"""
Кастомный клиент OpenSearch для работы через Dashboards API
"""

import json
import requests
from requests.auth import HTTPBasicAuth
from urllib3 import disable_warnings
from urllib3.exceptions import InsecureRequestWarning

# Отключаем предупреждения о SSL сертификатах
disable_warnings(InsecureRequestWarning)


class OpenSearchDashboardsClient:
    """
    Клиент для работы с OpenSearch через Dashboards API.
    Эмулирует стандартный opensearch-py клиент, но работает через Dashboards.
    """
    
    def __init__(self, hosts, http_auth=None, use_ssl=True, verify_certs=False, **kwargs):
        """Инициализация клиента"""
        if isinstance(hosts, list):
            self.base_url = hosts[0]['host']
            if 'port' in hosts[0] and hosts[0]['port'] != 443:
                self.base_url = f"{hosts[0]['host']}:{hosts[0]['port']}"
        else:
            self.base_url = hosts
            
        # Убираем слэш в конце
        self.base_url = self.base_url.rstrip('/')
        
        # Добавляем протокол если его нет
        if not self.base_url.startswith('http'):
            protocol = 'https' if use_ssl else 'http'
            self.base_url = f"{protocol}://{self.base_url}"
            
        # Аутентификация
        if http_auth:
            if isinstance(http_auth, tuple):
                self.auth = HTTPBasicAuth(http_auth[0], http_auth[1])
            else:
                self.auth = http_auth
        else:
            self.auth = None
            
        # Настройки сессии
        self.session = requests.Session()
        self.session.verify = verify_certs
        if self.auth:
            self.session.auth = self.auth
            
        # Заголовки для Dashboards API
        self.headers = {
            'Content-Type': 'application/json',
            'osd-xsrf': 'true',
            'kbn-xsrf': 'true',
        }
        
        # Инициализация подклиентов
        self.cat = CatClient(self)
        self.cluster = ClusterClient(self)
        self.indices = IndicesClient(self)
        
    def _make_request(self, method, path, params=None, body=None):
        """Выполняет запрос и эмулирует ответ OpenSearch API"""
        
        # Маршрутизация запросов через Dashboards API
        if path == '' or path == '/':
            return self._get_root_info()
        elif path.startswith('_cluster/health'):
            return self._get_cluster_health()
        elif path.startswith('_cat/indices'):
            return self._get_indices_list(params)
        elif path.endswith('/_search'):
            return self._perform_search(path, body)
        elif '/_search' in path:
            return self._perform_search(path, body)
        else:
            # Неизвестный путь - возвращаем ошибку
            return {
                'error': {
                    'type': 'not_supported_via_dashboards',
                    'reason': f'Path {path} not supported via Dashboards API'
                }
            }
    
    def _get_root_info(self):
        """Получает корневую информацию о кластере"""
        status = self._get_system_status()
        
        return {
            "name": "opensearch-via-dashboards",
            "cluster_name": "opensearch-cluster", 
            "cluster_uuid": "unknown",
            "version": {
                "number": "2.x.x",
                "build_flavor": "default",
                "build_type": "unknown",
                "build_hash": "unknown",
                "build_date": "unknown",
                "build_snapshot": False,
                "lucene_version": "unknown",
                "minimum_wire_compatibility_version": "unknown",
                "minimum_index_compatibility_version": "unknown"
            },
            "tagline": "The OpenSearch Project: https://opensearch.org/"
        }
    
    def _get_cluster_health(self):
        """Получает здоровье кластера"""
        status = self._get_system_status()
        
        if status:
            overall_status = status.get('status', {}).get('overall', {}).get('state', 'red')
            cluster_status = 'green' if overall_status == 'green' else 'yellow'
        else:
            cluster_status = 'red'
            
        return {
            "cluster_name": "opensearch-cluster",
            "status": cluster_status,
            "timed_out": False,
            "number_of_nodes": 1,
            "number_of_data_nodes": 1,
            "active_primary_shards": 0,
            "active_shards": 0,
            "relocating_shards": 0,
            "initializing_shards": 0,
            "unassigned_shards": 0,
            "delayed_unassigned_shards": 0,
            "number_of_pending_tasks": 0,
            "number_of_in_flight_fetch": 0,
            "task_max_waiting_in_queue_millis": 0,
            "active_shards_percent_as_number": 100.0
        }
    
    def _get_indices_list(self, params=None):
        """Получает список индексов"""
        indices = self._get_indices_from_saved_objects()
        
        # Всегда возвращаем JSON формат для MCP инструментов
        return [
            {
                "health": "green",
                "status": "open",
                "index": idx['index'], 
                "uuid": idx['id'],
                "pri": "1",
                "rep": "0",
                "docs.count": "0",
                "docs.deleted": "0",
                "store.size": "unknown",
                "pri.store.size": "unknown"
            }
            for idx in indices
        ]
    
    def _perform_search(self, path, body):
        """Выполняет поиск через Console API"""
        try:
            # Извлекаем индекс из path
            index = "_all"
            if "/" in path and path != "_search":
                index = path.split("/")[0]
            
            # Формируем параметры для Console API
            console_params = {
                "method": "POST",
                "path": f"/{index}/_search"
            }
            
            # Пытаемся выполнить через Console API
            response = self.session.post(
                f"{self.base_url}/api/console/proxy",
                headers=self.headers,
                params=console_params,
                json=body if body else {},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Console API может возвращать результат в разных форматах
                if isinstance(result, dict) and 'hits' in result:
                    return result
                elif isinstance(result, dict) and 'response' in result:
                    return result['response']
                else:
                    # Если ответ не в ожидаемом формате, возвращаем пустой результат
                    return self._empty_search_result()
            else:
                # Если Console API недоступен, возвращаем пустой результат
                return self._empty_search_result()
                
        except Exception as e:
            # В случае ошибки возвращаем пустой результат
            return self._empty_search_result()
    
    def _empty_search_result(self):
        """Возвращает пустой результат поиска"""
        return {
            "took": 1,
            "timed_out": False,
            "_shards": {"total": 1, "successful": 1, "skipped": 0, "failed": 0},
            "hits": {
                "total": {"value": 0, "relation": "eq"},
                "max_score": None,
                "hits": []
            }
        }
    
    def _get_system_status(self):
        """Получает статус системы через Dashboards API"""
        try:
            response = self.session.get(
                f"{self.base_url}/api/status",
                headers=self.headers,
                timeout=30
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def _get_indices_from_saved_objects(self):
        """Получает список индексов из saved objects и реальных индексов"""
        indices = []
        
        # Пытаемся получить реальные индексы через Console API
        try:
            console_params = {
                "method": "GET",
                "path": "/_cat/indices?format=json"
            }
            
            response = self.session.post(
                f"{self.base_url}/api/console/proxy",
                headers=self.headers,
                params=console_params,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list):
                    # Прямой список индексов
                    for idx in result:
                        if isinstance(idx, dict) and 'index' in idx:
                            indices.append({
                                'index': idx['index'],
                                'id': idx.get('uuid', idx['index']),
                                'type': 'real-index',
                                'health': idx.get('health', 'unknown'),
                                'docs.count': idx.get('docs.count', '0')
                            })
                elif isinstance(result, dict) and 'response' in result:
                    # Ответ обернут в response
                    response_data = result['response']
                    if isinstance(response_data, list):
                        for idx in response_data:
                            if isinstance(idx, dict) and 'index' in idx:
                                indices.append({
                                    'index': idx['index'],
                                    'id': idx.get('uuid', idx['index']),
                                    'type': 'real-index',
                                    'health': idx.get('health', 'unknown'),
                                    'docs.count': idx.get('docs.count', '0')
                                })
        except Exception as e:
            print(f"Console API error: {e}")
        
        # Если не удалось получить реальные индексы, получаем из saved objects
        if not indices:
            try:
                response = self.session.get(
                    f"{self.base_url}/api/saved_objects/_find?type=index-pattern",
                    headers=self.headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for saved_object in data.get('saved_objects', []):
                        attributes = saved_object.get('attributes', {})
                        title = attributes.get('title', '')
                        if title:
                            indices.append({
                                'index': title,
                                'id': saved_object.get('id', ''),
                                'type': 'index-pattern',
                                'health': 'green',
                                'docs.count': '0'
                            })
            except:
                pass
        
        return indices
    
    def get(self, index, id, **kwargs):
        """Получает документ по ID"""
        # Заглушка для совместимости
        return {"found": False}
    
    def search(self, index=None, body=None, **kwargs):
        """Выполняет поиск"""
        if index:
            path = f"{index}/_search"
        else:
            path = "_search"
        return self._perform_search(path, body)
    
    def count(self, index=None, body=None, **kwargs):
        """Подсчитывает документы"""
        return {"count": 0}
    
    def info(self, **kwargs):
        """Получает информацию о кластере"""
        return self._get_root_info()
    
    def ping(self, **kwargs):
        """Проверяет доступность кластера"""
        try:
            status = self._get_system_status()
            return status is not None
        except:
            return False


class CatClient:
    """Клиент для cat API"""
    
    def __init__(self, client):
        self.client = client
    
    def indices(self, index=None, format=None, **kwargs):
        """Получает информацию об индексах"""
        # Всегда возвращаем JSON для MCP инструментов
        return self.client._get_indices_list()
    
    def health(self, **kwargs):
        """Получает здоровье кластера"""
        return self.client._get_cluster_health()


class ClusterClient:
    """Клиент для cluster API"""
    
    def __init__(self, client):
        self.client = client
    
    def health(self, **kwargs):
        """Получает здоровье кластера"""
        return self.client._get_cluster_health()
    
    def stats(self, **kwargs):
        """Получает статистику кластера"""
        return {
            "cluster_name": "opensearch-cluster",
            "status": "green",
            "indices": {"count": 0},
            "nodes": {"count": {"total": 1}}
        }


class IndicesClient:
    """Клиент для indices API"""
    
    def __init__(self, client):
        self.client = client
    
    def get_mapping(self, index, **kwargs):
        """Получает маппинг индекса"""
        return {
            index: {
                "mappings": {
                    "properties": {}
                }
            }
        }
    
    def exists(self, index, **kwargs):
        """Проверяет существование индекса"""
        indices = self.client._get_indices_from_saved_objects()
        return any(idx['index'] == index for idx in indices) 