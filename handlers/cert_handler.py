from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import os
from utils.logger import setup_logger

logger = setup_logger(
    "cert_handler",
    log_file="logs/cert_handler.log"
)

def load_certificates(pfx_path, pfx_password):
    """
    Carrega certificado PFX e extrai chave privada e certificado em formato PEM.
    Usa /tmp na Lambda (writable) ou diretório atual localmente.
    """
    # Determinar diretório para arquivos temporários
    # Lambda tem /tmp como único diretório writable
    temp_dir = "/tmp" if os.path.exists("/tmp") and os.access("/tmp", os.W_OK) else "."
    private_key_path = os.path.join(temp_dir, "private_key.pem")
    cert_path = os.path.join(temp_dir, "cert.pem")
    
    logger.info(f"Carregando certificado PFX: {pfx_path}")
    logger.debug(f"Diretório temporário: {temp_dir}")
    logger.debug(f"Tamanho da senha: {len(pfx_password)} bytes")
    
    # Verificar se o arquivo existe
    if not os.path.exists(pfx_path):
        raise FileNotFoundError(f"Arquivo PFX não encontrado: {pfx_path}")
    
    # Verificar tamanho do arquivo
    file_size = os.path.getsize(pfx_path)
    logger.debug(f"Tamanho do arquivo PFX: {file_size} bytes")
    
    if file_size == 0:
        raise ValueError("Arquivo PFX está vazio ou corrompido")
    
    try:
        # Ler arquivo PFX
        with open(pfx_path, 'rb') as pfx_file:
            pfx_data = pfx_file.read()
        
        logger.debug(f"Dados PFX lidos: {len(pfx_data)} bytes")
        
        # Carregar certificado
        private_key, cert, _ = pkcs12.load_key_and_certificates(
            pfx_data, 
            pfx_password, 
            default_backend()
        )
        
        logger.info("Certificado PFX carregado com sucesso")
        
        # Escrever chave privada e certificado em arquivos PEM
        with open(private_key_path, "wb") as key_file, open(cert_path, "wb") as cert_file:
            key_file.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
            cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
        
        logger.info(f"Arquivos PEM criados: {private_key_path}, {cert_path}")
        
        return private_key_path, cert_path
        
    except ValueError as e:
        error_msg = str(e)
        logger.error(f"Erro ao processar certificado PFX: {error_msg}")
        
        if "Invalid password" in error_msg or "PKCS12" in error_msg:
            logger.error("DIAGNÓSTICO: Senha incorreta ou arquivo PFX corrompido")
            logger.error(f"  - Verifique a senha no Parameter Store")
            logger.error(f"  - Verifique se o arquivo no S3 está íntegro")
            logger.error(f"  - Tamanho do arquivo: {file_size} bytes")
            logger.error(f"  - Tamanho da senha: {len(pfx_password)} bytes")
            raise ValueError(f"Senha do certificado PFX incorreta ou arquivo corrompido. Erro: {error_msg}")
        raise
        
    except Exception as e:
        logger.error(f"Erro inesperado ao processar certificado: {type(e).__name__}: {str(e)}")
        raise

def clean_temp_files():
    """Remove arquivos temporários PEM criados."""
    temp_dir = "/tmp" if os.path.exists("/tmp") and os.access("/tmp", os.W_OK) else "."
    private_key_path = os.path.join(temp_dir, "private_key.pem")
    cert_path = os.path.join(temp_dir, "cert.pem")
    
    try:
        if os.path.exists(private_key_path):
            os.remove(private_key_path)
            logger.debug(f"Arquivo removido: {private_key_path}")
        if os.path.exists(cert_path):
            os.remove(cert_path)
            logger.debug(f"Arquivo removido: {cert_path}")
    except Exception as e:
        logger.warning(f"Erro ao remover arquivos temporários: {e}")
