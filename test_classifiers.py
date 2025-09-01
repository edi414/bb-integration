import sys
sys.path.append(r'D:\OneDrive\Documentos\VS Code\Mercado\bb_integration')

import pandas as pd
from handlers.database import get_db_connection
from services.bank_statement_analyser import BankStatementAnalyzer
from services.embedding_classifier import EmbeddingClassifier
from utils.logger import setup_logger
import time

# Configurar o logger
logger = setup_logger(
    "test_classifiers",
    log_file="logs/test_classifiers.log"
)

import dotenv
dotenv.load_dotenv()
import os
openai_api_key = os.getenv('OPENAI_API_KEY')
print(openai_api_key)

def update_categories_in_database(batch_size=100):
    try:
        logger.info("Iniciando atualização de categorias no banco de dados")
        
        # Inicializa o classificador
        classifier = EmbeddingClassifier(k_neighbors=3)
        
        # Obtém conexão com o banco
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM extrato_juridica 
            WHERE finance_category IS NULL 
            AND indicadorsinallancamento = 'D'
        """)
        total_transactions = cursor.fetchone()[0]
        logger.info(f"Total de transações a processar: {total_transactions}")
        
        processed = 0
        updated = 0
        
        while processed < total_transactions:
            cursor.execute("""
                SELECT 
                    id,
                    textodescricaohistorico,
                    textoinformacaocomplementar
                FROM extrato_juridica
                WHERE finance_category IS NULL 
                AND indicadorsinallancamento = 'D'
                ORDER BY datalancamento DESC
                LIMIT %s
                OFFSET %s
            """, (batch_size, processed))
            
            batch = cursor.fetchall()
            if not batch:
                break
                
            for transaction in batch:
                try:
                    transaction_id = transaction[0]
                    description = transaction[1]
                    additional_info = transaction[2]
                    
                    # Classifica a transação
                    classification = classifier.classify_transaction(
                        description,
                        additional_info
                    )
                    
                    # Atualiza a categoria independente do score
                    cursor.execute("""
                        UPDATE extrato_juridica 
                        SET finance_category = %s
                        WHERE id = %s
                    """, (classification["category"], transaction_id))
                    updated += 1
                    
                    # Log detalhado da classificação
                    logger.info(f"\nTransação {transaction_id}:")
                    logger.info(f"Descrição: {description}")
                    logger.info(f"Info: {additional_info}")
                    logger.info(f"Categoria: {classification['category']} (score: {classification['score']:.3f})")
                    logger.info("K vizinhos mais próximos:")
                    for sim, cat in classification['neighbors']:
                        logger.info(f"  {cat}: {sim:.3f}")
                    logger.info("Scores por categoria:")
                    for cat, score in sorted(classification['all_scores'].items(), key=lambda x: x[1], reverse=True):
                        logger.info(f"  {cat}: {score:.3f}")
                    logger.info("-" * 50)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar transação {transaction_id}: {e}")
                    continue
            
            # Commit a cada lote
            conn.commit()
            processed += len(batch)
            
            logger.info(f"Progresso: {processed}/{total_transactions} transações processadas")
            logger.info(f"Atualizadas: {updated}")
            
        # Fecha conexão
        cursor.close()
        conn.close()
        
        logger.info("\nResumo da atualização:")
        logger.info(f"Total processado: {processed}")
        logger.info(f"Atualizadas: {updated}")
        
    except Exception as e:
        logger.error(f"Erro durante a atualização: {e}", exc_info=True)
        if 'conn' in locals():
            conn.close()

update_categories_in_database()

def test_embedding_classifier():
    try:
        logger.info("Iniciando teste do classificador de embeddings")
        
        # Inicializa o classificador com K=3 vizinhos
        classifier = EmbeddingClassifier(k_neighbors=3)
        
        # Obtém amostra de transações reais
        df = get_sample_transactions(limit=20)  # Aumentei para 20 transações para ter uma amostra melhor
        
        if df.empty:
            logger.error("Nenhuma transação encontrada para teste")
            return
        
        # Processa cada transação
        results = []
        for idx, row in df.iterrows():
            try:
                # Pula se já tiver categoria
                if pd.notna(row['finance_category']):
                    continue
                
                start_time = time.time()
                classification = classifier.classify_transaction(
                    row['textodescricaohistorico'],
                    row['textoinformacaocomplementar']
                )
                processing_time = time.time() - start_time
                
                results.append({
                    "case": idx + 1,
                    "description": row['textodescricaohistorico'],
                    "additional_info": row['textoinformacaocomplementar'],
                    "category": classification["category"],
                    "score": classification["score"],
                    "all_scores": classification["all_scores"],
                    "neighbors": classification["neighbors"],
                    "time": processing_time
                })
                
                logger.info(f"\nTransação {idx + 1}:")
                logger.info(f"Descrição: {row['textodescricaohistorico']}")
                logger.info(f"Info: {row['textoinformacaocomplementar']}")
                logger.info(f"Categoria: {classification['category']} (score: {classification['score']:.3f})")
                logger.info("K vizinhos mais próximos:")
                for sim, cat in classification['neighbors']:
                    logger.info(f"  {cat}: {sim:.3f}")
                logger.info("Scores por categoria:")
                for cat, score in sorted(classification['all_scores'].items(), key=lambda x: x[1], reverse=True):
                    logger.info(f"  {cat}: {score:.3f}")
                logger.info(f"Tempo: {processing_time:.2f}s")
                logger.info("-" * 50)
                
            except Exception as e:
                logger.error(f"Erro ao processar transação {idx}: {e}")
                continue
        
        # Cria DataFrame com resultados
        results_df = pd.DataFrame(results)
        
        # Salva resultados em CSV
        results_df.to_csv('embedding_classifier_test.csv', index=False, encoding='utf-8')
        
        # Calcula estatísticas
        total_cases = len(results_df)
        avg_time = results_df['time'].mean()
        avg_score = results_df['score'].mean()
        
        # Mostra estatísticas
        logger.info("\nEstatísticas do Teste:")
        logger.info(f"Total de transações processadas: {total_cases}")
        logger.info(f"Tempo médio: {avg_time:.2f}s")
        logger.info(f"Score médio: {avg_score:.3f}")
        
        # Mostra distribuição de categorias
        logger.info("\nDistribuição de categorias:")
        category_counts = results_df['category'].value_counts()
        logger.info(category_counts)
        
        # Mostra exemplos de cada categoria
        logger.info("\nExemplos por categoria:")
        for category in category_counts.index:
            examples = results_df[results_df['category'] == category].head(3)
            logger.info(f"\nCategoria: {category}")
            for _, example in examples.iterrows():
                logger.info(f"Descrição: {example['description']}")
                logger.info(f"Info: {example['additional_info']}")
                logger.info(f"Score: {example['score']:.3f}")
                logger.info("Vizinhos mais próximos:")
                for sim, cat in example['neighbors']:
                    logger.info(f"  {cat}: {sim:.3f}")
                logger.info("-" * 30)
        
    except Exception as e:
        logger.error(f"Erro durante o teste: {e}", exc_info=True)

def get_sample_transactions(limit=10):
    try:
        conn = get_db_connection()
        query = """
            SELECT 
                textodescricaohistorico,
                textoinformacaocomplementar,
                indicadorsinallancamento,
                finance_category
            FROM extrato_juridica
            WHERE indicadorsinallancamento = 'D'
            ORDER BY datalancamento DESC
            LIMIT %s
        """
        
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        
        logger.info(f"Obtidas {len(df)} transações para teste")
        return df
    
    except Exception as e:
        logger.error(f"Erro ao obter transações: {e}", exc_info=True)
        return pd.DataFrame()

test_embedding_classifier()
