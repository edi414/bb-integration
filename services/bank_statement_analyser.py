import sys
sys.path.append(r'D:\OneDrive\Documentos\VS Code\Mercado\bb_integration')

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal
from handlers.logger import setup_logger
import json
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o logger específico para este módulo
logger = setup_logger(
    "bank_statement_analyzer",
    log_file="logs/bank_statement_analyzer.log"
)

class TransactionCategory(BaseModel):
    category: Literal[
        "Pagamento para Fornecedor",
        "Pagamento de Contas Internas",
        "Impostos",
        "Transferências Internas e Aplicações",
        "Estornos",
        "Outros"
    ] = Field(description="The category of the financial transaction")

class BankStatementAnalyzer:
    def __init__(self):
        try:
            # Configure OpenAI with GPT-4
            self.llm = ChatOpenAI(
                model="gpt-4.1-nano",
                temperature=0.1,  # Lower temperature for more consistent results
                api_key=os.getenv('OPENAI_API_KEY')
            )
            self.parser = PydanticOutputParser(pydantic_object=TransactionCategory)
            
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", """Você é um classificador de transações financeiras especializado em supermercados. Sua tarefa é classificar transações bancárias de uma conta jurídica de supermercado em categorias específicas.

                Categorias e seus contextos:
                
                1. Pagamento para Fornecedor:
                   - Pagamentos a fornecedores de produtos (distribuidores, atacadistas)
                   - Pagamentos a fornecedores de serviços (limpeza, segurança, manutenção)
                   - Pagamentos a fornecedores de equipamentos e materiais
                   - Pagamentos a fornecedores de embalagens e materiais de expedição
                   - Pagamentos a fornecedores de produtos perecíveis e não perecíveis
                   Exemplos: "Pagto Fornecedor", "Pagto Distribuidor", "Pagto Atacado"

                2. Pagamento de Contas Internas:
                   - Pagamentos de contas de água, luz, gás, telefone
                   - Pagamentos de serviços de internet e sistemas
                   - Pagamentos de serviços de limpeza e manutenção
                   - Pagamentos de serviços de segurança
                   - Pagamentos de serviços de TI e suporte
                   Exemplos: "Pagto Energia", "Pagto Água", "Pagto Internet"

                3. Impostos:
                   - Pagamentos de ICMS, PIS, COFINS
                   - Pagamentos de ISS
                   - Pagamentos de IPTU
                   - Pagamentos de taxas municipais
                   - Pagamentos de taxas de licenciamento
                   Exemplos: "Pagto ICMS", "Pagto ISS", "Pagto IPTU"

                4. Transferências Internas e Aplicações:
                   - Transferências entre contas da empresa
                   - Aplicações financeiras
                   - Resgates de aplicações
                   - Transferências para contas de investimento
                   - Movimentações entre contas da mesma empresa
                   Exemplos: "Transferência", "Aplicação", "Resgate"

                5. Estornos:
                   - Estornos de cartão de crédito
                   - Estornos de pagamentos
                   - Devoluções de valores
                   - Cancelamentos de operações
                   - Reembolsos
                   Exemplos: "Estorno", "Devolução", "Reembolso"

                6. Outros:
                   - Qualquer transação que não se encaixe nas categorias acima
                   - Transações não identificadas
                   - Transações atípicas
                   - Transações que precisam de análise manual
                   Exemplos: "Transferência não identificada", "Pagamento não categorizado"

                Você deve responder APENAS com um objeto JSON neste formato exato:
                {{
                    "category": "uma das categorias listadas acima"
                }}

                Não inclua nenhum outro texto ou explicação."""),
                ("human", """Classifique esta transação:
                Descrição: {description}
                Informação Adicional: {additional_info}
                
                {format_instructions}""")
            ])
            logger.info("BankStatementAnalyzer initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing BankStatementAnalyzer: {e}", exc_info=True)
            raise

    def categorize_transaction(self, description: str, additional_info: str) -> str:
        try:
            logger.debug(f"Classifying transaction - Description: {description}, Additional Info: {additional_info}")
            
            # Format the prompt with the transaction details
            formatted_prompt = self.prompt.format_messages(
                description=description,
                additional_info=additional_info,
                format_instructions=self.parser.get_format_instructions()
            )
            
            # Get response from LLM
            response = self.llm.invoke(formatted_prompt)
            logger.debug(f"LLM Response: {response.content}")
            
            # Try to extract JSON from the response
            try:
                # First try to parse the response directly
                result = self.parser.parse(response.content)
            except Exception as e:
                logger.debug(f"Direct parsing failed, attempting to extract JSON from response: {e}")
                # If that fails, try to find JSON in the response
                try:
                    # Look for JSON-like structure in the response
                    json_str = response.content
                    if "{" in json_str and "}" in json_str:
                        start = json_str.find("{")
                        end = json_str.rfind("}") + 1
                        json_str = json_str[start:end]
                        # Parse the extracted JSON
                        result = self.parser.parse(json_str)
                    else:
                        raise ValueError("No JSON structure found in response")
                except Exception as e2:
                    logger.error(f"Failed to extract JSON from response: {e2}")
                    return "Outros"
            
            logger.info(f"Transaction categorized as: {result.category}")
            return result.category
            
        except Exception as e:
            logger.error(f"Error categorizing transaction: {e}", exc_info=True)
            return "Outros"