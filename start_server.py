#!/usr/bin/env python3
"""
Простой скрипт для запуска MCP сервера OpenSearch через uv
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Запускает MCP сервер через uv с конфигурацией fort-elkdev"""
    
    print("🚀 Запуск MCP сервера для OpenSearch (fort-elkdev.gearwap.ru)")
    
    # Проверяем наличие конфигурационного файла
    config_file = "fort_config.yml"
    if not os.path.exists(config_file):
        print(f"❌ Файл конфигурации {config_file} не найден!")
        print("💡 Убедитесь, что вы находитесь в корневой папке проекта")
        return 1
    
    print(f"📁 Используем конфигурацию: {config_file}")
    
    # Команда для запуска через uv
    cmd = ["uv", "run", "mcp-server-opensearch", "--config", config_file]
    
    print(f"🔧 Выполняем команду: {' '.join(cmd)}")
    print("📝 Для остановки нажмите Ctrl+C")
    print("💡 Запуск через uv в stdio режиме")
    print("-" * 50)
    
    try:
        # Запускаем сервер через uv
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n⏹️ Сервер остановлен пользователем")
        return 0
    except FileNotFoundError:
        print("\n❌ uv не найден в системе")
        print("💡 Установите uv: https://docs.astral.sh/uv/getting-started/installation/")
        print("💡 Альтернативно: pip install -e . && python -m mcp_server_opensearch --config fort_config.yml")
        return 1
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка запуска сервера: {e}")
        print("\n🔧 Попробуйте:")
        print("   1. Убедиться, что uv установлен: uv --version")
        print("   2. Инициализировать проект: uv sync")
        print("   3. Проверить конфигурацию в fort_config.yml")
        print("   4. Проверить доступность сервера: https://fort-elkdev.gearwap.ru")
        return 1
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 