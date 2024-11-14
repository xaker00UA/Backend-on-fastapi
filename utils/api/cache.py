import threading
import time


class Cache:
    def __init__(self, max_size=100, ttl=60, check_interval=1):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl
        self.time = time
        self.check_interval = check_interval
        self.lock = threading.Lock()
        self._start_cleanup_task()

    def _is_expired(self, timestamp):
        """Проверяем, истёк ли срок жизни записи."""
        return time.time() - timestamp > self.ttl

    def _cleanup(self):
        """Удаляем устаревшие записи."""
        with self.lock:
            current_time = time.time()
            keys_to_remove = [
                key
                for key, (_, timestamp) in self.cache.items()
                if self._is_expired(timestamp)
            ]
            for key in keys_to_remove:
                del self.cache[key]

    def _start_cleanup_task(self):
        """Запускаем фоновую задачу для регулярной очистки кэша."""

        def cleanup_loop():
            while True:
                time.sleep(self.check_interval)  # Ждем интервал между проверками
                self._cleanup()  # Очищаем устаревшие записи

        # Запускаем фоновый поток для регулярной очистки
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()

    def get(self, key):
        """Возвращаем данные из кэша, если они не истекли."""
        with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if not self._is_expired(timestamp):
                    return value
                else:
                    del self.cache[key]  # Удаляем устаревшую запись
        return None

    def set(self, key, value):
        """Сохраняем данные в кэше."""
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Если кэш переполнен, удаляем первый элемент (FIFO)
                self.cache.pop(next(iter(self.cache)))
            self.cache[key] = (value, time.time())
