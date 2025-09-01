#!/bin/bash

# Script to configure cronjob for BB Integration System
# Executes daily at 10:00 BR time (13:00 UTC)

echo "🔧 Configurando Cronjob para Sistema de Integração BB..."

# Get current directory
CURRENT_DIR=$(pwd)
PYTHON_PATH=$(which python3)

# Check if Python was found
if [ -z "$PYTHON_PATH" ]; then
    echo "❌ Python3 não encontrado. Instale o Python3 primeiro."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$CURRENT_DIR/logs"

# Create cronjob command (10:00 BR time = 13:00 UTC)
CRON_COMMAND="0 13 * * * cd $CURRENT_DIR && $PYTHON_PATH main.py >> $CURRENT_DIR/logs/cron.log 2>&1"

# Check if cronjob already exists
if crontab -l 2>/dev/null | grep -q "main.py"; then
    echo "⚠️  Cronjob já existe. Removendo versão anterior..."
    crontab -l 2>/dev/null | grep -v "main.py" | crontab -
fi

# Add new cronjob
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

echo "✅ Cronjob configurado com sucesso!"
echo ""
echo "📋 Detalhes do Cronjob:"
echo "   Comando: $CRON_COMMAND"
echo "   Execução: Diariamente às 10:00 BR time (13:00 UTC)"
echo "   Log: $CURRENT_DIR/logs/cron.log"
echo ""
echo "📝 Para verificar o cronjob:"
echo "   crontab -l"
echo ""
echo "📝 Para remover o cronjob:"
echo "   crontab -r"
echo ""
echo "📝 Para testar manualmente:"
echo "   python3 main.py"
echo ""
echo "📝 Para verificar os logs do cronjob:"
echo "   tail -f $CURRENT_DIR/logs/cron.log"
