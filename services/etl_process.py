import requests
import pandas as pd
import datetime as dt
import os
from dotenv import load_dotenv
from handlers.cert_handler import load_certificates, clean_temp_files
from utils.logger import setup_logger
from services.embedding_classifier import EmbeddingClassifier

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logger específico para este módulo
logger = setup_logger(
    "etl_process",
    log_file="logs/etl_process.log"
)

classifier = EmbeddingClassifier(k_neighbors=3)

def get_extrato_data(extrato_url, headers, date_inicio, date_fim, pfx_password, pfx_path):
    logger.info(f"Iniciando extração de dados para o período {date_inicio} - {date_fim}")
    load_certificates(pfx_password=pfx_password, pfx_path=pfx_path)

    numero_pagina = 1
    lista_lancamentos = []

    try:
        while True:
            params = {
                'gw-dev-app-key': os.getenv('DEVELOPER_APPLICATION_KEY'),
                'dataInicioSolicitacao': date_inicio,
                'dataFimSolicitacao': date_fim,
                'numeroPaginaSolicitacao': numero_pagina
            }
            
            logger.debug(f"Obtendo página {numero_pagina} do extrato")
            response = requests.get(
                extrato_url,
                headers=headers,
                params=params,
                cert=("cert.pem", "private_key.pem")
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Página {numero_pagina} obtida com sucesso")
                lista_lancamentos.extend(data['listaLancamento'])

                if numero_pagina >= data['quantidadeTotalPagina']:
                    logger.info(f"Todas as {data['quantidadeTotalPagina']} páginas foram obtidas")
                    break

                numero_pagina += 1

            else:
                logger.error(f"Erro ao obter dados da página {numero_pagina}: {response.status_code} - {response.text}")
                raise Exception(f"Erro ao obter dados da página {numero_pagina}: {response.status_code} - {response.text}")
            
    finally:
        clean_temp_files()
        logger.debug(f"Total de {len(lista_lancamentos)} lançamentos obtidos")

    return lista_lancamentos

def processar_lancamento(lancamento):
    try:
        # Verificar se o indicadorTipoLancamento é 'S' ou 'R'
        if lancamento['indicadorTipoLancamento'] in ['S', 'R', 'D']:
            logger.debug(f"Registro filtrado - indicadorTipoLancamento = {lancamento['indicadorTipoLancamento']}")
            return None

        data_movimento = None
        if lancamento['dataMovimento']:
            data_movimento_str = str(lancamento['dataMovimento'])
            if len(data_movimento_str) < 8:
                data_movimento_str = data_movimento_str.zfill(8)
            try:
                data_movimento = dt.datetime.strptime(data_movimento_str, '%d%m%Y').date()
            except ValueError as e:
                logger.error(f"Erro ao converter dataMovimento: {data_movimento_str} - Erro: {e}")
        
        data_lancamento = None
        data_lancamento_str = str(lancamento['dataLancamento'])
        if len(data_lancamento_str) < 8:
            data_lancamento_str = data_lancamento_str.zfill(8)
        try:
            data_lancamento = dt.datetime.strptime(data_lancamento_str, '%d%m%Y').date()
        except ValueError as e:
            logger.error(f"Erro ao converter dataLancamento: {data_lancamento_str} - Erro: {e}")

        # Process finance category for debit transactions
        finance_category = None
        if lancamento['indicadorSinalLancamento'] == 'D':
            classification = classifier.classify_transaction(
                lancamento['textoDescricaoHistorico'],
                lancamento['textoInformacaoComplementar']
            )
            finance_category = classification["category"]
            
            # Log classification details
            logger.info(f"\nClassificação para transação:")
            logger.info(f"Descrição: {lancamento['textoDescricaoHistorico']}")
            logger.info(f"Info: {lancamento['textoInformacaoComplementar']}")
            logger.info(f"Categoria: {finance_category} (score: {classification['score']:.3f})")
            logger.info("K vizinhos mais próximos:")
            for sim, cat in classification['neighbors']:
                logger.info(f"  {cat}: {sim:.3f}")
            logger.info("Scores por categoria:")
            for cat, score in sorted(classification['all_scores'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {cat}: {score:.3f}")
            logger.info("-" * 50)

        processed = {
            "indicadorTipoLancamento": int(lancamento['indicadorTipoLancamento']),
            "dataLancamento": data_lancamento,
            "dataMovimento": data_movimento,
            "codigoAgenciaOrigem": int(lancamento['codigoAgenciaOrigem']),
            "numeroLote": int(lancamento['numeroLote']),
            "numeroDocumento": int(lancamento['numeroDocumento']),
            "codigoHistorico": int(lancamento['codigoHistorico']),
            "valorLancamento": lancamento['valorLancamento'],
            "codigoBancoContrapartida": int(lancamento['codigoBancoContrapartida']),
            "codigoAgenciaContrapartida": int(lancamento['codigoAgenciaContrapartida']),
            "textoInformacaoComplementar": lancamento['textoInformacaoComplementar'],
            "numeroCpfCnpjContrapartida": str(lancamento['numeroCpfCnpjContrapartida']),
            "indicadorTipoPessoaContrapartida": lancamento['indicadorTipoPessoaContrapartida'],
            "numeroContaContrapartida": lancamento['numeroContaContrapartida'],
            "textoDescricaoHistorico": lancamento['textoDescricaoHistorico'],
            "textoDvContaContrapartida": lancamento['textoDvContaContrapartida'],
            "indicadorSinalLancamento": lancamento['indicadorSinalLancamento'],
            "finance_category": finance_category
        }
        return processed
    except Exception as e:
        logger.error(f"Erro ao processar lançamento: {lancamento} - Erro: {str(e)}", exc_info=True)
        raise

def executar_etl(extrato_url, headers, pfx_path, pfx_password, date_inicio, date_fim):
    logger.info(f"Iniciando processo ETL para o período {date_inicio} - {date_fim}")
    
    lista_lancamento = get_extrato_data(extrato_url, headers, date_inicio, date_fim, pfx_password, pfx_path)
    logger.info(f"Processando {len(lista_lancamento)} lançamentos")
    
    dados_processados = [processar_lancamento(lancamento) for lancamento in lista_lancamento]
    # Filtrar registros None (onde indicadorTipoLancamento = 'S' ou 'R' ou 'D')
    dados_processados = [d for d in dados_processados if d is not None]
    logger.info(f"Após filtrar registros com indicadorTipoLancamento S/R/D: {len(dados_processados)} registros")
    
    df = pd.DataFrame(dados_processados)
    
    # Remover registros de saldo
    df = df[~df['textoDescricaoHistorico'].isin(['SALDO ANTERIOR', 'S A L D O'])]
    logger.info(f"Após remover registros de saldo: {len(df)} registros")
    
    if len(df) == 0:
        logger.warning(f"Nenhum registro válido encontrado para o período {date_inicio} - {date_fim}")
    else:
        logger.info(f"Exemplo de registros a serem inseridos:")
        logger.info(f"Colunas: {df.columns.tolist()}")
        logger.info(f"Primeiros registros:\n{df.head().to_string()}")
    
    return df


