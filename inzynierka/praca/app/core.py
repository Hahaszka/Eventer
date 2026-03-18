import os
import json
import logging
import asyncio
import re
from sentence_transformers import SentenceTransformer
from ollama import AsyncClient

logger = logging.getLogger(__name__)

# Ustawienia modeli (zamrożonych w Dockerze)
VECTOR_MODEL = 'sentence-transformers/all-MiniLM-L6-v2'
OLLAMA_MODEL = 'gemma3:4b'
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")

# Globalny bufor dla wektoryzatora (ładuje się tylko raz przy starcie)
encoder = None

def get_encoder():
    global encoder
    if encoder is None:
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        encoder = SentenceTransformer(VECTOR_MODEL)
    return encoder

class AsyncHybridSearchEngine:
    def __init__(self, db_session):
        self.session = db_session
        self.encoder = get_encoder()

    async def _generate_embedding(self, text_input: str) -> list:
        # Wrzucamy obliczenia AI do osobnego wątku, by nie blokować innych użytkowników
        vec = await asyncio.to_thread(self.encoder.encode, str(text_input))
        return vec.tolist()

    async def search(self, text_input: str, top_k: int = 1) -> list:
        from app.models import WarehouseProduct
        from sqlalchemy import select

        query_embedding = await self._generate_embedding(text_input)
        
        # Wyszukiwanie wektorowe pgvector
        stmt = select(WarehouseProduct).order_by(
            WarehouseProduct.embedding.l2_distance(query_embedding)
        ).limit(top_k)
        
        result = await self.session.execute(stmt)
        products = result.scalars().all()
        
        return [
            {
                "id": p.id,
                "sku_code": p.sku_code,
                "product_name": p.product_name,
                "category": p.category,
                "final_score": 0.9  # Orientacyjny score dla l2_distance
            } for p in products
        ]

class AsyncLocalLLMVerifier:
    def __init__(self):
        # Inicjalizacja asynchronicznego klienta Ollamy
        self.client = AsyncClient(host=OLLAMA_HOST)

    async def verify_match(self, invoice_item: str, candidate: dict) -> dict:
        prompt = f"""
        Sprawdź, czy produkt z faktury to ten sam, co w bazie. Zignoruj literówki.
        Faktura: "{invoice_item}"
        Magazyn: "{candidate['product_name']}" (SKU: {candidate['sku_code']})

        Zwróć odpowiedź WYŁĄCZNIE jako JSON:
        {{
            "is_match": true/false,
            "confidence_score": 0.0-1.0,
            "reasoning": "krotkie uzasadnienie po polsku, max 20 wyrazów."
        }}
        """
        try:
            # Komunikacja z modelem Gemma 3
            response = await self.client.chat(
                model=OLLAMA_MODEL, 
                messages=[{'role': 'user', 'content': prompt}], 
                format='json', 
                options={'temperature': 0.0}
            )
            content = response['message']['content']
            
            # Pancerne zabezpieczenie przed usterkami modelu (np. dodanie tagów Markdown do JSON-a)
            content = re.sub(r'^```(json)?\s*', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\s*```$', '', content)
            
            data = json.loads(content)
            
            if isinstance(data, dict):
                # Na wypadek zagnieżdżonego słownika
                for k, v in data.items():
                    if isinstance(v, list): return v[0] if v else {}
                return data
                
            return data[0] if isinstance(data, list) and data else {}
            
        except Exception as e:
            logger.error(f"Błąd ekstrakcji LLM: {e}")
            return {
                "is_match": False, 
                "confidence_score": 0.0, 
                "reasoning": f"Błąd weryfikacji AI: {str(e)}"
            }