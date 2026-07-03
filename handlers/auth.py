import requests
import logging

def get_token(basic_auth, token_url, scope):
    headers = {
        'Authorization': basic_auth,
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'grant_type': 'client_credentials',
        'scope': scope
    }
    response = requests.post(token_url, headers=headers, data=data)
    if response.status_code == 200:
        token = response.json().get('access_token')
        logging.info("Token obtido com sucesso.")
        return token
    else:
        logging.error(f"Erro ao obter o token: {response.status_code} - {response.text}")
        raise Exception(f"Erro ao obter o token: {response.status_code} - {response.text}")
