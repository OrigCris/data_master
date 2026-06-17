"""Configuração de path para a suíte de testes.

Permite importar tanto o código da Function App quanto as bibliotecas Spark
(funções puras) sem instalar nada como pacote.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel in ("function_app", "Databricks/lib", "cli"):
    p = str(ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)
