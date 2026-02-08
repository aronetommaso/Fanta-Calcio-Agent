import asyncio
import logging
from typing import List, Union, Any

import fastembed
from fastembed import TextEmbedding, SparseTextEmbedding # IMPORTANTE: Importiamo entrambi

from datapizza.core.embedder import BaseEmbedder
from datapizza.type import SparseEmbedding

log = logging.getLogger(__name__)

class FastEmbedder(BaseEmbedder):
    def __init__(
        self,
        model_name: str,
        embedding_name: str | None = None,
        cache_dir: str | None = None,
        sparse: bool = False, # <--- NUOVO PARAMETRO: Default False (Denso)
        **kwargs,
    ):
        self.model_name = model_name
        self.sparse = sparse # Salviamo la preferenza
        
        if embedding_name:
            self.embedding_name = embedding_name
        else:
            self.embedding_name = model_name

        self.cache_dir = cache_dir
        
        # LOGICA DI SELEZIONE: Denso o Sparso?
        if self.sparse:
            log.info(f"Loading SPARSE model: {model_name}")
            self.embedder = fastembed.SparseTextEmbedding(
                model_name=model_name, cache_dir=cache_dir, **kwargs
            )
        else:
            log.info(f"Loading DENSE model: {model_name}")
            self.embedder = fastembed.TextEmbedding(
                model_name=model_name, cache_dir=cache_dir, **kwargs
            )

    def embed(
        self, text: str | list[str], model_name: str | None = None
    ) -> Union[List[float], List[List[float]], SparseEmbedding, List[SparseEmbedding]]:
        
        # fastembed accetta sia stringhe che liste
        embeddings_gen = self.embedder.embed(text)

        if self.sparse:
            # --- LOGICA VECCHIA (SPARSE) ---
            results = [
                SparseEmbedding(
                    name=self.embedding_name,
                    values=embedding.values.tolist(),
                    indices=embedding.indices.tolist(),
                )
                for embedding in embeddings_gen
            ]
        else:
            # --- LOGICA NUOVA (DENSE) ---
            # Convertiamo il generatore in liste di float
            results = [e.tolist() for e in embeddings_gen]

        # Gestione input singolo vs batch
        if isinstance(text, str):
            # Se l'input era una stringa singola, restituiamo il primo elemento
            return results[0] if results else []
        
        # Se era una lista, restituiamo la lista completa
        return results

    async def a_embed(
        self, text: str | list[str], model_name: str | None = None
    ):
        return await asyncio.to_thread(self.embed, text)
        
    # FIX AGGIUNTIVO: Per renderlo compatibile con la Pipeline di DataPizza
    # implementiamo _run che chiama embed
    def _run(self, text=None, **kwargs):
        content = text or kwargs.get('input') or kwargs.get('text')
        if not content:
            return []
        return self.embed(content)