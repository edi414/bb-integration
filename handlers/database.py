import psycopg2
from psycopg2 import sql, errors
from tqdm import tqdm
from datetime import datetime
from datetime import timedelta
import os
from dotenv import load_dotenv
from utils.logger import setup_logger

# Configurar o logger específico para este módulo
logger = setup_logger(
    "database",
    log_file="logs/database.log"
)

load_dotenv()

def get_db_connection():
    """
    Cria e retorna uma conexão com o banco de dados usando as variáveis de ambiente.
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT')
        )
        logger.debug("Conexão com o banco de dados estabelecida com sucesso")
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco de dados: {e}", exc_info=True)
        raise

def inserir_no_banco(df):
    if df.empty:
        logger.warning("DataFrame vazio - nenhum registro para inserir")
        return

    logger.info(f"Iniciando inserção de {len(df)} registros no banco de dados")
    conn = get_db_connection()
    cursor = conn.cursor()

    insert_query = sql.SQL("""
        INSERT INTO extrato_juridica (
            indicadortipolancamento, datalancamento, datamovimento, 
            codigoagenciaorigem, numerolote, numerodocumento, 
            codigohistorico, valorlancamento, codigobancocontrapartida, 
            codigoagenciacontrapartida, textoinformacaocomplementar, 
            numerocpfcnpjcontrapartida, indicadortipopessoacontrapartida, 
            numerocontacontrapartida, textodescricaohistorico, 
            textodvcontacontrapartida, indicadorsinallancamento,
            finance_category
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """)

    registros_inseridos = 0
    registros_duplicados = 0
    registros_com_erro = 0

    with tqdm(total=len(df), desc="Inserindo registros", unit="registro") as pbar:
        for index, row in df.iterrows():
            try:
                cursor.execute(insert_query, (
                    int(row["indicadorTipoLancamento"]),
                    row["dataLancamento"],
                    row["dataMovimento"],
                    int(row["codigoAgenciaOrigem"]),
                    int(row["numeroLote"]),
                    int(row["numeroDocumento"]),
                    int(row["codigoHistorico"]),
                    row["valorLancamento"],
                    int(row["codigoBancoContrapartida"]),
                    int(row["codigoAgenciaContrapartida"]),
                    row["textoInformacaoComplementar"],
                    str(row["numeroCpfCnpjContrapartida"]),
                    row["indicadorTipoPessoaContrapartida"],
                    row["numeroContaContrapartida"],
                    row["textoDescricaoHistorico"],
                    row["textoDvContaContrapartida"],
                    row["indicadorSinalLancamento"],
                    row["finance_category"]
                ))
                conn.commit()
                registros_inseridos += 1
            except errors.UniqueViolation:
                logger.debug(f"Registro duplicado encontrado no índice {index}")
                conn.rollback()
                registros_duplicados += 1
            except Exception as e:
                logger.error(f"Erro ao processar registro {index}: {e}", exc_info=True)
                conn.rollback()
                registros_com_erro += 1

            pbar.update(1)

    cursor.close()
    conn.close()
    
    logger.info(f"Inserção concluída:")
    logger.info(f"- Registros inseridos com sucesso: {registros_inseridos}")
    logger.info(f"- Registros duplicados: {registros_duplicados}")
    logger.info(f"- Registros com erro: {registros_com_erro}")
    logger.info(f"- Total processado: {len(df)}")

def registrar_status(process_name, status, data=None):
    """
    Registra o status do processo no banco de dados.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if data:
            created_at = datetime.strptime(data, '%d%m%Y')
        else:
            created_at = datetime.now()

        cursor.execute("""
            INSERT INTO process_status (created_at, process_name, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (process_name, created_at) 
            DO UPDATE SET status = EXCLUDED.status
        """, (created_at, process_name, status))

        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Status '{status}' registrado para o processo '{process_name}' na data {created_at}")
    except Exception as e:
        logger.error(f"Erro ao registrar status: {e}", exc_info=True)

def obter_datas_falhadas(process_name):
    """
    Retorna as datas com status 'Erro' do processo.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TO_CHAR(created_at, 'DDMMYYYY')
            FROM process_status
            WHERE process_name = %s AND status = 'Erro'
        """, (process_name,))
        resultados = cursor.fetchall()
        conn.close()
        datas_falhadas = [row[0] for row in resultados]
        logger.info(f"Encontradas {len(datas_falhadas)} datas falhadas para o processo '{process_name}'")
        return datas_falhadas
    except Exception as e:
        logger.error(f"Erro ao consultar datas falhadas: {e}", exc_info=True)
        return []

def obter_datas_nao_registradas():
    """
    Verifica o intervalo de datas do mês atual e retorna todas as datas
    (incluindo finais de semana) que não possuem registros na tabela extrato_juridica.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.now()
        primeiro_dia = datetime(hoje.year, hoje.month, 1)
        ontem = hoje - timedelta(days=1)

        # Garantir que não processamos datas futuras
        if ontem > hoje:
            ontem = hoje

        todas_as_datas = []
        data_atual = primeiro_dia
        while data_atual <= ontem:
            todas_as_datas.append(data_atual.strftime('%Y-%m-%d'))
            data_atual += timedelta(days=1)

        logger.debug(f"Verificando {len(todas_as_datas)} datas no período")

        cursor.execute("""
            SELECT DISTINCT TO_CHAR(datalancamento, 'YYYY-MM-DD') AS data
            FROM extrato_juridica
            WHERE datalancamento IS NOT NULL
        """)
        datas_registradas = {row[0] for row in cursor.fetchall()}

        conn.close()

        datas_nao_registradas = [
            datetime.strptime(data, '%Y-%m-%d').strftime('%d%m%Y')
            for data in todas_as_datas if data not in datas_registradas
        ]

        logger.info(f"Encontradas {len(datas_nao_registradas)} datas não registradas")
        return datas_nao_registradas

    except Exception as e:
        logger.error(f"Erro ao consultar datas não registradas: {e}", exc_info=True)
        return []

