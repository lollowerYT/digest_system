# utils/filtering.py
"""Общие функции для семантической фильтрации новостей."""

import numpy as np
from typing import Optional

# Эталонные рекламные фразы (можно расширять)
AD_EXAMPLES = [
    "Купите сейчас со скидкой 50%",
    "Заработок в интернете без вложений",
    "Инвестиции с гарантией доходности",
    "Уникальное предложение, только сегодня",
    "Спешите купить, количество ограничено",
    "Промокод на скидку при первом заказе",
    "Лучший курс по криптовалюте",
    "Зарабатывай от 1000$ в день",
    "Регистрируйся и получай бонус",
    "Начни зарабатывать прямо сейчас",
]

_ad_embedding = None
_embedder_instance = None

def set_embedder(embedder):
    """Устанавливает экземпляр эмбеддера для использования в фильтрации."""
    global _embedder_instance
    _embedder_instance = embedder

def get_ad_embedding(embedder=None) -> np.ndarray:
    """
    Возвращает усреднённый нормализованный эмбеддинг рекламных примеров.
    Результат кэшируется после первого вызова.
    """
    global _ad_embedding, _embedder_instance
    if _ad_embedding is not None:
        return _ad_embedding

    emb = embedder or _embedder_instance
    if emb is None:
        raise ValueError("Эмбеддер не задан. Вызовите set_embedder() или передайте embedder.")

    # Получаем эмбеддинги для всех примеров (предполагается, что они уже нормализованы)
    embeddings = emb.get_batch_embeddings(AD_EXAMPLES)
    _ad_embedding = np.mean(embeddings, axis=0)
    # Дополнительная нормализация на всякий случай
    _ad_embedding = _ad_embedding / np.linalg.norm(_ad_embedding)
    return _ad_embedding

def filter_ad_by_embeddings(embeddings: np.ndarray, threshold: float = 0.6) -> np.ndarray:
    """
    Принимает матрицу нормализованных эмбеддингов (n, dim).
    Возвращает булев массив: True для рекламных новостей.
    """
    ad_emb = get_ad_embedding()
    # Косинусное сходство = скалярное произведение (векторы нормализованы)
    similarities = np.dot(embeddings, ad_emb)
    return similarities >= threshold