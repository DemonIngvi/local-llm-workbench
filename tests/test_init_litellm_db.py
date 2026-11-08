"""
Тесты для инициализации базы данных LiteLLM.
"""

import unittest
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Мок psycopg2 для тестов
sys.modules['psycopg2'] = MagicMock()
sys.modules['psycopg2.extras'] = MagicMock()

import init_litellm_db


class InitLiteLLMDatabaseTests(unittest.TestCase):
    """Тесты для инициализации базы данных LiteLLM."""
    
    def test_create_virtual_key(self):
        """Тест создания виртуального ключа."""
        # Создаём мок курсора
        mock_cursor = MagicMock()
        
        # Вызываем функцию
        init_litellm_db.create_virtual_key(
            mock_cursor,
            key_name="test_key",
            token="sk-test-123",
            allowed_models=["model1", "model2"],
            tpm_limit=1000,
            rpm_limit=10,
            max_budget=5.0
        )
        
        # Проверяем, что INSERT был вызван
        self.assertTrue(mock_cursor.execute.called)
        
        # Проверяем параметры
        call_args = mock_cursor.execute.call_args
        self.assertIn("LiteLLM_UserAPIKeyToken", call_args[0][0])
    
    def test_hash_token(self):
        """Тест хеширования токена."""
        token = "sk-test-token"
        hashed = init_litellm_db.hash_token(token)
        
        # Проверяем, что результат - строка
        self.assertIsInstance(hashed, str)
        
        # Проверяем длину (SHA-256 = 64 символа)
        self.assertEqual(len(hashed), 64)
        
        # Проверяем детерминированность
        self.assertEqual(hashed, init_litellm_db.hash_token(token))
        
        # Проверяем, что разные токены дают разные хеши
        self.assertNotEqual(
            init_litellm_db.hash_token("token1"),
            init_litellm_db.hash_token("token2")
        )
    
    @patch('init_litellm_db.psycopg2.connect')
    def test_main_with_mock_connection(self, mock_connect):
        """Тест основной функции с моком подключения."""
        # Настраиваем моки
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Устанавливаем переменные окружения
        os.environ['LITELLM_OPENCODE_KEY'] = 'sk-opencode-test'
        os.environ['LITELLM_DEEPSEEK_KEY'] = 'sk-deepseek-test'
        
        try:
            # Вызываем main
            init_litellm_db.main()
            
            # Проверяем, что подключение было установлено
            self.assertTrue(mock_connect.called)
            
            # Проверяем, что курсор был создан
            self.assertTrue(mock_conn.cursor.called)
            
            # Проверяем, что INSERT вызывался дважды (для двух ключей)
            self.assertEqual(mock_cursor.execute.call_count, 2)
            
            # Проверяем, что транзакция была закоммичена
            self.assertTrue(mock_conn.commit.called)
            
        finally:
            # Очищаем переменные окружения
            os.environ.pop('LITELLM_OPENCODE_KEY', None)
            os.environ.pop('LITELLM_DEEPSEEK_KEY', None)


if __name__ == '__main__':
    unittest.main()

