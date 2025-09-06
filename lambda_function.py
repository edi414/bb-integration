import json
import os
from datetime import datetime
from utils.logger import setup_logger

from main import obter_datas_pendentes, processar_data

logger = setup_logger(
    "extrato_bb_lambda",
    log_file="logs/extrato_bb_lambda.log"
)

def lambda_handler(event, context):
    try:
        logger.info(f"Event: {json.dumps(event)}")
        logger.info(f"Context: {context}")
        
        # Obter datas pendentes (reutiliza função do main.py)
        datas_pendentes = obter_datas_pendentes()
        logger.info(f"Quantidade de datas pendentes: {len(datas_pendentes)}")
        logger.info(f"Datas pendentes para processamento: {datas_pendentes}")

        resultados = []
        
        # Processar cada data (reutiliza lógica do main.py)
        for data in datas_pendentes:
            resultado_data = {
                'data': data,
                'status': 'erro',
                'mensagem': '',
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                # Reutilizar a lógica de processamento do main.py
                processar_data(data)
                
                resultado_data['status'] = 'sucesso'
                resultado_data['mensagem'] = f'Processamento concluído para {data}'
                logger.info(f"✅ Data {data} processada com sucesso")

            except Exception as e:
                logger.error(f"❌ Erro ao processar a data {data}: {str(e)}", exc_info=True)
                resultado_data['status'] = 'erro'
                resultado_data['mensagem'] = str(e)
            
            resultados.append(resultado_data)

        # Resumo final
        sucessos = len([r for r in resultados if r['status'] == 'sucesso'])
        erros = len([r for r in resultados if r['status'] == 'erro'])
        
        logger.info(f"Sucessos: {sucessos}")
        logger.info(f"Erros: {erros}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Processamento concluído',
                'sucessos': sucessos,
                'erros': erros,
                'resultados': resultados,
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2)
        }

    except Exception as e:
        logger.error(f"Erro geral no Lambda: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }, ensure_ascii=False)
        }
