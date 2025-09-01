import boto3
import os
import tempfile
from botocore.exceptions import ClientError, NoCredentialsError
from utils.logger import setup_logger

# Configurar o logger específico para este módulo
logger = setup_logger(
    "aws_handler",
    log_file="logs/aws_handler.log"
)

class S3Handler:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None, region_name='us-east-1'):
        """
        Inicializa o handler do S3.
        
        Args:
            aws_access_key_id: Chave de acesso AWS (opcional, pode vir de variáveis de ambiente)
            aws_secret_access_key: Chave secreta AWS (opcional, pode vir de variáveis de ambiente)
            region_name: Região AWS (padrão: us-east-1)
        """
        self.region_name = region_name
        
        # Usar credenciais fornecidas ou variáveis de ambiente
        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
        else:
            # Tentar usar credenciais de variáveis de ambiente ou IAM role
            self.s3_client = boto3.client('s3', region_name=region_name)
        
        logger.info(f"Handler S3 inicializado para região: {region_name}")
    
    def download_certificate(self, bucket_name, s3_key, temp_dir=None):
        """
        Faz download do certificado .p12 do S3 para um diretório temporário.
        
        Args:
            bucket_name: Nome do bucket S3
            s3_key: Chave do objeto no S3 (caminho completo)
            temp_dir: Diretório temporário (opcional, usa sistema padrão se não especificado)
        
        Returns:
            str: Caminho completo do arquivo baixado
            
        Raises:
            Exception: Se houver erro no download
        """
        try:
            # Criar diretório temporário se não especificado
            if temp_dir is None:
                temp_dir = tempfile.gettempdir()
            
            # Nome do arquivo a partir da chave S3
            filename = os.path.basename(s3_key)
            local_path = os.path.join(temp_dir, filename)
            
            logger.info(f"Iniciando download do certificado: {s3_key} do bucket {bucket_name}")
            logger.info(f"Salvando em: {local_path}")
            
            # Fazer download do arquivo
            self.s3_client.download_file(bucket_name, s3_key, local_path)
            
            # Verificar se o arquivo foi baixado
            if os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                logger.info(f"Certificado baixado com sucesso. Tamanho: {file_size} bytes")
                return local_path
            else:
                raise Exception(f"Arquivo não foi criado localmente: {local_path}")
                
        except NoCredentialsError:
            error_msg = "Credenciais AWS não encontradas"
            logger.error(error_msg)
            raise Exception(error_msg)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            error_msg = f"Erro do S3: {error_code} - {error_message}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Erro inesperado ao baixar certificado: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    def cleanup_certificate(self, local_path):
        """
        Remove o arquivo de certificado baixado localmente.
        
        Args:
            local_path: Caminho do arquivo local a ser removido
        """
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Certificado removido: {local_path}")
            else:
                logger.warning(f"Arquivo não encontrado para remoção: {local_path}")
        except Exception as e:
            logger.error(f"Erro ao remover certificado: {str(e)}")
