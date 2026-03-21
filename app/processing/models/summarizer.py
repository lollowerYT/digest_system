# models/summarizer.py
import aiohttp
import asyncio
from typing import List

# Семафор для ограничения одновременных запросов к Ollama (например, не больше 2)
ollama_semaphore = asyncio.Semaphore(2)

class SaigaSummarizer:
    def __init__(self, model_name: str, host: str = "http://localhost:11434"):
        self.model_name = model_name
        self.host = host

    def _create_prompt(self, system: str, user: str) -> str:
        return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
{user}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>"""

    async def _call_ollama(self, prompt: str, temperature: float = 0.3, max_tokens: int = 500, retries: int = 2) -> str:
        """Асинхронный вызов Ollama с ограничением параллелизма и повторными попытками."""
        async with ollama_semaphore:  # ограничиваем число одновременных вызовов
            for attempt in range(retries + 1):
                try:
                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "model": self.model_name,
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": temperature, "max_tokens": max_tokens}
                        }
                        async with session.post(f"{self.host}/api/generate", json=payload, timeout=60) as resp:
                            if resp.status != 200:
                                text = await resp.text()
                                raise Exception(f"Ollama error {resp.status}: {text}")
                            data = await resp.json()
                            return data["response"]
                except asyncio.TimeoutError:
                    if attempt < retries:
                        wait = 2 ** attempt  # exponential backoff
                        print(f"⚠️ Таймаут, повтор через {wait} сек...")
                        await asyncio.sleep(wait)
                    else:
                        return "[Таймаут при генерации после нескольких попыток]"
                except Exception as e:
                    if attempt < retries:
                        print(f"⚠️ Ошибка: {e}, повтор...")
                        await asyncio.sleep(2)
                    else:
                        return f"[Ошибка: {e}]"
            return "[Неизвестная ошибка]"

    async def summarize_cluster(self, news_list: List[str], max_sentences: int = 3) -> str:
        combined_text = "\n\n".join([f"Новость {i+1}: {text}" for i, text in enumerate(news_list)])
        system_msg = """Ты — Сайга, русскоязычный ассистент для анализа новостей. 
Твоя задача — проанализировать группу новостей на одну тему и создать краткое содержание,
объединяющее все новости в связный пересказ."""
        user_msg = f"""Проанализируй эти новости и создай краткое содержание (не более {max_sentences} предложений), 
объединяющее все новости в связный пересказ. Сохрани хронологию событий:

{combined_text}"""
        prompt = self._create_prompt(system_msg, user_msg)
        return await self._call_ollama(prompt, temperature=0.3, max_tokens=500)

    async def generate_title(self, cluster_news: List[str]) -> str:
        if not cluster_news:
            return "Без темы"
        text = cluster_news[0]
        system_msg = "Ты — Сайга. Придумай короткий, информативный заголовок для группы новостей."
        user_msg = f"Придумай короткий заголовок (3-6 слов) для этой группы новостей:\n\n{text}"
        prompt = self._create_prompt(system_msg, user_msg)
        return await self._call_ollama(prompt, temperature=0.4, max_tokens=50)