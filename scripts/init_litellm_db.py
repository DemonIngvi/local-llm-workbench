#!/usr/bin/env python3
"""
Инициализация базы данных LiteLLM с виртуальными ключами и квотами.

Этот скрипт создаёт:
1. Виртуальные ключи для OpenCode и DeepSeek
2. Настраивает квоты (лимиты токенов и бюджета)
3. Ограничивает доступ к моделям

Требования:
- PostgreSQL должен быть запущен и доступен
- Переменные окружения должны быть установлены в .env
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import secrets
import hashlib

def get_db_connection():
    """Получить подключение к PostgreSQL."""
    return psycopg2.connect(
        host=os.environ.get('POSTGRES_HOST', 'localhost'),
        port=int(os.environ.get('POSTGRES_PORT', '5432')),
        database=os.environ.get('POSTGRES_DB', 'litellm'),
        user=os.environ.get('POSTGRES_USER', 'litellm'),
        password=os.environ.get('LITELLM_DB_PASSWORD', 'litellm_password')
    )

def hash_token(token):
    """Хешировать токен для хранения."""
    return hashlib.sha256(token.encode()).hexdigest()

def create_virtual_key(cursor, key_name, token, allowed_models, tpm_limit, rpm_limit, max_budget):
    """Создать виртуальный ключ с квотами."""
    token_hash = hash_token(token)
    
    # Вставка в таблицу LiteLLM_UserAPIKeyToken
    cursor.execute("""
        INSERT INTO "LiteLLM_UserAPIKeyToken" (
            token, key_name, key_alias, 
            user_id, team_id, 
            max_budget, spend, 
            models, tpm_limit, rpm_limit,
            expires, 
            created_at, updated_at
        ) VALUES (
            %s, %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s,
            %s,
            NOW(), NOW()
        )
        ON CONFLICT (token) DO UPDATE SET
            key_name = EXCLUDED.key_name,
            models = EXCLUDED.models,
            tpm_limit = EXCLUDED.tpm_limit,
            rpm_limit = EXCLUDED.rpm_limit,
            max_budget = EXCLUDED.max_budget,
            updated_at = NOW()
    """, (
        token, key_name, key_name,
        'default_user_id', None,
        max_budget, 0.0,
        allowed_models, tpm_limit, rpm_limit,
        None  # expires = None (не истекает)
    ))
    
    print(f"[OK] Создан ключ '{key_name}'")
    print(f"  Токен: {token[:10]}...{token[-10:]}")
    print(f"  Модели: {allowed_models}")
    print(f"  TPM лимит: {tpm_limit}")
    print(f"  RPM лимит: {rpm_limit}")
    print(f"  Макс. бюджет: ${max_budget}")

def main():
    """Основная функция инициализации."""
    print("=" * 60)
    print("Инициализация базы данных LiteLLM")
    print("=" * 60)
    
    # Получаем токены из .env или генерируем новые
    opencode_key = os.environ.get('LITELLM_OPENCODE_KEY')
    if not opencode_key:
        opencode_key = f"sk-opencode-{secrets.token_hex(24)}"
        print(f"\n[WARN] LITELLM_OPENCODE_KEY не установлен в .env")
        print(f"  Сгенерирован новый ключ: {opencode_key}")
        print(f"  Добавьте в .env: LITELLM_OPENCODE_KEY={opencode_key}")
    
    deepseek_key = os.environ.get('LITELLM_DEEPSEEK_KEY')
    if not deepseek_key:
        deepseek_key = f"sk-deepseek-{secrets.token_hex(24)}"
        print(f"\n[WARN] LITELLM_DEEPSEEK_KEY не установлен в .env")
        print(f"  Сгенерирован новый ключ: {deepseek_key}")
        print(f"  Добавьте в .env: LITELLM_DEEPSEEK_KEY={deepseek_key}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("\n[OK] Подключение к PostgreSQL установлено")
        
        # Создаём ключ для OpenCode
        create_virtual_key(
            cursor,
            key_name="opencode_key",
            token=opencode_key,
            allowed_models=[],
            tpm_limit=1000000,
            rpm_limit=100,
            max_budget=10.0
        )
        
        # Создаём ключ для DeepSeek
        create_virtual_key(
            cursor,
            key_name="deepseek_key",
            token=deepseek_key,
            allowed_models=[],
            tpm_limit=500000,
            rpm_limit=50,
            max_budget=5.0
        )
        
        conn.commit()
        
        print("\n" + "=" * 60)
        print("[OK] Инициализация завершена успешно!")
        print("=" * 60)
        print("\nВиртуальные ключи созданы:")
        print(f"  - OpenCode: {opencode_key[:20]}...")
        print(f"  - DeepSeek: {deepseek_key[:20]}...")
        print("\nУбедитесь, что ключи добавлены в .env файл:")
        print(f"  LITELLM_OPENCODE_KEY={opencode_key}")
        print(f"  LITELLM_DEEPSEEK_KEY={deepseek_key}")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"\n[ERROR] Ошибка подключения к PostgreSQL: {e}")
        print("\nУбедитесь, что:")
        print("  1. PostgreSQL запущен: docker compose up postgres")
        print("  2. Переменные окружения установлены в .env")
        print("  3. База данных создана")
        sys.exit(1)

if __name__ == "__main__":
    main()
