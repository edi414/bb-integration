#!/bin/bash

# Script to remove cronjob for BB Integration System

echo "🗑️  Removendo Cronjob do Sistema de Integração BB..."

# Check if cronjob exists
if crontab -l 2>/dev/null | grep -q "main.py"; then
    echo "⚠️  Cronjob encontrado. Removendo..."
    crontab -l 2>/dev/null | grep -v "main.py" | crontab -
    echo "✅ Cronjob removido com sucesso!"
else
    echo "ℹ️  Nenhum cronjob encontrado para remover."
fi

echo ""
echo "📝 Para verificar se foi removido:"
echo "   crontab -l"
