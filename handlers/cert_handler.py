from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import os

def load_certificates(pfx_path, pfx_password):
    with open(pfx_path, 'rb') as pfx_file:
        pfx_data = pfx_file.read()

    private_key, cert, _ = pkcs12.load_key_and_certificates(pfx_data, pfx_password, default_backend())

    with open("private_key.pem", "wb") as key_file, open("cert.pem", "wb") as cert_file:
        key_file.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
        cert_file.write(cert.public_bytes(serialization.Encoding.PEM))

def clean_temp_files():
    os.remove("private_key.pem")
    os.remove("cert.pem")
