import numpy as np
import re
import torch
import torch.nn.functional as F
from typing import List, Optional
from transformers import AutoTokenizer, AutoModel

class QwenEmbedder:
    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Embedding-4B",
        device: Optional[str] = None,
        embedding_dim: int = 4096
    ):
        self.model_name = model_name
        self.embedding_dim = embedding_dim

        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        print(f"🚀 Загрузка модели {model_name} на {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side='left')

        # Загружаем модель целиком на GPU в половинной точности
        self.model = AutoModel.from_pretrained(
            model_name,
            torch_dtype=torch.float16,      # float16 для скорости и экономии памяти
        ).to(self.device)                    # явно перемещаем на устройство

        self.model.eval()
        print(f"✅ Модель загружена")

    def clean_text(self, text: str) -> str:
        if not isinstance(text, str):
            text = str(text)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'[^\w\s.,!?;:()\-«»"\'—]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        max_len = 4096
        if len(text) > max_len:
            text = text[:max_len]
        return text

    def last_token_pool(self, last_hidden_states, attention_mask):
        left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
        if left_padding:
            return last_hidden_states[:, -1]
        else:
            sequence_lengths = attention_mask.sum(dim=1) - 1
            batch_size = last_hidden_states.shape[0]
            return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]

    def get_batch_embeddings(
        self,
        texts: List[str],
        batch_size: int = 80       # подберите максимальное значение, которое влезает в память
    ) -> np.ndarray:
        cleaned_texts = [self.clean_text(t) for t in texts]
        all_embeddings = []

        for i in range(0, len(cleaned_texts), batch_size):
            batch_texts = cleaned_texts[i:i+batch_size]

            inputs = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=8192,
                return_tensors="pt"
            )
            # Перемещаем вход на то же устройство, где находится модель
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.inference_mode():    # быстрее, чем no_grad
                outputs = self.model(**inputs)
                embeddings = self.last_token_pool(outputs.last_hidden_state, inputs['attention_mask'])
                embeddings = F.normalize(embeddings, p=2, dim=1)

            all_embeddings.append(embeddings.cpu().numpy())

        return np.concatenate(all_embeddings, axis=0).astype(np.float32)

    def compute_similarity(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        emb1_norm = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
        emb2_norm = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)
        return np.dot(emb1_norm, emb2_norm.T)