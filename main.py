import logging
import os
import tempfile
from dotenv import load_dotenv
from handlers.auth import get_token
from services.etl_process import executar_etl, get_extrato_data
from handlers.database import inserir_no_banco, registrar_status, obter_datas_falhadas, obter_datas_nao_registradas
from datetime import datetime, timedelta
import calendar
from utils.logger import setup_logger
from handlers.aws_handler import S3Handler

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logger específico para este módulo
logger = setup_logger(
    "extrato_bb",
    log_file="logs/extrato_bb.log"
)

# Configurações gerais
token_url = os.getenv('TOKEN_URL')
scope = os.getenv('SCOPE')
pfx_password = os.getenv('PFX_PASSWORD').encode('utf-8')
extrato_url = os.getenv('EXTRATO_URL')
process_name = os.getenv('PROCESS_NAME')
basic = os.getenv('BASIC_AUTH')

# Configurações AWS
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION', 'us-east-1')
s3_bucket = os.getenv('S3_BUCKET')
s3_certificate_key = os.getenv('S3_CERTIFICATE_KEY')

# Inicializar handler AWS
s3_handler = S3Handler(aws_access_key, aws_secret_key, aws_region)

def obter_datas_pendentes():
    # Data de ontem
    data_ontem = (datetime.now() - timedelta(days=1)).strftime('%d%m%Y')

    # Obter datas falhadas do banco
    datas_falhadas = obter_datas_falhadas(process_name)

    # Obter datas sem registros em `datalancamento`
    datas_nao_registradas = obter_datas_nao_registradas()

    # Combinar todas as datas
    datas_pendentes = set(datas_falhadas + datas_nao_registradas)
    
    # Garantir que a data de ontem esteja na lista
    if data_ontem not in datas_pendentes:
        datas_pendentes.add(data_ontem)

    # Filtrar datas futuras
    datas_pendentes = [
        data for data in datas_pendentes 
        if datetime.strptime(data, '%d%m%Y').date() <= datetime.now().date()
    ]

    logger.info(f"Datas pendentes após filtro de datas futuras: {sorted(datas_pendentes)}")
    return sorted(datas_pendentes)

datas_pendentes = obter_datas_pendentes()
logger.info(f"Quantidade de datas pendentes: {len(datas_pendentes)}")
logger.info(f"Datas pendentes para processamento: {datas_pendentes}")

for data in datas_pendentes:
    # Variável para armazenar o caminho do certificado baixado
    local_cert_path = None
    
    try:
        # Remover zero inicial das datas, se necessário
        if data.startswith("0"):
            data = data[1:]

        # Registrar início do processo para a data
        logger.info(f"Iniciando processamento para a data {data}")
        registrar_status(process_name, 'Iniciado', data)

        # Download do certificado do S3
        logger.info("Fazendo download do certificado do S3")
        local_cert_path = s3_handler.download_certificate(
            s3_bucket, 
            s3_certificate_key
        )
        logger.info(f"Certificado baixado com sucesso: {local_cert_path}")

        # Obter token e preparar cabeçalhos
        logger.debug("Obtendo token de autenticação")
        token = get_token(basic, token_url, scope)
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Executar ETL para a data específica
        logger.info(f"Executando ETL para a data {data}")
        date_inicio = data
        date_fim = data
        df_resultante = executar_etl(extrato_url, headers, local_cert_path, pfx_password, date_inicio, date_fim)

        # Inserir no banco de dados
        logger.info(f"Inserindo dados no banco para a data {data}")
        inserir_no_banco(df_resultante)

        # Registrar sucesso para a data
        registrar_status(process_name, 'Processada', data)
        logger.info(f"Processo concluído com sucesso para a data {data}")

    except Exception as e:
        registrar_status(process_name, 'Erro', data)
        logger.error(f"Erro ao processar a data {data}: {str(e)}", exc_info=True)
        logger.error(f"Detalhes do erro: {type(e).__name__}")
        print(f"Erro ao processar a data {data}. Verifique os logs.")
    
    finally:
        # Limpar certificado baixado localmente
        if local_cert_path and os.path.exists(local_cert_path):
            try:
                s3_handler.cleanup_certificate(local_cert_path)
                logger.info("Certificado temporário removido com sucesso")
            except Exception as cleanup_error:
                logger.warning(f"Erro ao remover certificado temporário: {cleanup_error}")
