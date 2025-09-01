import sys
sys.path.append(r'D:\OneDrive\Documentos\VS Code\Mercado\bb_integration')

import numpy as np
from openai import OpenAI
from utils.logger import setup_logger
from typing import List, Dict, Tuple
import json
import os
from dotenv import load_dotenv
from collections import Counter

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logger
logger = setup_logger(
    "embedding_classifier",
    log_file="logs/embedding_classifier.log"
)

class EmbeddingClassifier:
    def __init__(self, k_neighbors=3):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.k = k_neighbors
        self.categories = json.load(open('data/categories_definition.json'))
        self.category_embeddings = self._load_or_create_embeddings()
        self.training_data = self._prepare_training_data()
        
    def _get_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Erro ao obter embedding: {e}", exc_info=True)
            return None

    def _load_or_create_embeddings(self) -> Dict[str, List[float]]:
        embeddings_file = "data/category_embeddings.json"
        
        if os.path.exists(embeddings_file):
            try:
                with open(embeddings_file, 'r', encoding='utf-8') as f:
                    embeddings = json.load(f)
                logger.info("Embeddings carregados do arquivo")
                return embeddings
            except Exception as e:
                logger.error(f"Erro ao carregar embeddings: {e}")
        
        logger.info("Criando novos embeddings para as categorias")
        category_embeddings = {}
        os.makedirs(os.path.dirname(embeddings_file), exist_ok=True)
        
        for category, info in self.categories.items():
            context = f"{info['description']} Exemplos: {', '.join(info['examples'])}"
            embedding = self._get_embedding(context)
            if embedding:
                category_embeddings[category] = embedding
                logger.info(f"Embedding criado para categoria: {category}")
        
        try:
            with open(embeddings_file, 'w', encoding='utf-8') as f:
                json.dump(category_embeddings, f)
            logger.info("Embeddings salvos no arquivo")
        except Exception as e:
            logger.error(f"Erro ao salvar embeddings: {e}")
        
        return category_embeddings

    def _prepare_training_data(self) -> List[Tuple[List[float], str]]:
        training_data = []
        
        for category, info in self.categories.items():
            desc_embedding = self._get_embedding(info['description'])
            if desc_embedding:
                training_data.append((desc_embedding, category))
            
            for example in info['examples']:
                example_embedding = self._get_embedding(example)
                if example_embedding:
                    training_data.append((example_embedding, category))
        
        logger.info(f"Preparados {len(training_data)} exemplos de treinamento")
        return training_data

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

    def _knn_classify(self, query_embedding: List[float]) -> Dict[str, any]:
        similarities = []
        for train_embedding, category in self.training_data:
            similarity = self._cosine_similarity(query_embedding, train_embedding)
            similarities.append((similarity, category))
        
        similarities.sort(reverse=True)
        
        k_neighbors = similarities[:self.k]
        
        # Calcula a média ponderada dos scores para cada categoria
        category_scores = {}
        for sim, category in k_neighbors:
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(sim)
        
        # Calcula a média dos scores para cada categoria
        avg_scores = {
            category: sum(scores) / len(scores)
            for category, scores in category_scores.items()
        }
        
        # Escolhe a categoria com maior score médio
        best_category = max(avg_scores.items(), key=lambda x: x[1])
        
        # Calcula o score médio geral
        avg_similarity = sum(sim for sim, _ in k_neighbors) / self.k
        
        # Prepara os scores para todas as categorias
        all_scores = {}
        for category in self.categories.keys():
            all_scores[category] = avg_scores.get(category, 0.0)
        
        return {
            "category": best_category[0],
            "score": best_category[1],
            "all_scores": all_scores,
            "neighbors": [(sim, cat) for sim, cat in k_neighbors]
        }

    def classify_transaction(self, description: str, additional_info: str) -> Dict[str, any]:
        try:
            # Combina descrição e informação adicional
            transaction_text = f"{description} {additional_info}"
            
            # Obtém o embedding da transação
            transaction_embedding = self._get_embedding(transaction_text)
            if not transaction_embedding:
                logger.error("Não foi possível obter embedding da transação")
                return {"category": "Outros", "score": 0.0, "all_scores": {}, "neighbors": []}
            
            # Classifica usando KNN
            result = self._knn_classify(transaction_embedding)
            
            # Adiciona informações de debug
            logger.debug(f"K vizinhos mais próximos para: {transaction_text}")
            for sim, cat in result["neighbors"]:
                logger.debug(f"  {cat}: {sim:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao classificar transação: {e}", exc_info=True)
            return {"category": "Outros", "score": 0.0, "all_scores": {}, "neighbors": []}