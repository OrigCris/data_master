from __future__ import annotations

import azure.functions as func
from auth.credentials import get_credential
from config.settings import settings
from generators.calls import gerar_fato_chamada_humana
from generators.surveys import gerar_fato_pesquisa_satisfacao
from generators.ura import gerar_eventos_ura
from services.eventhub_client import send_events
from utils.logging_utils import get_logger

app = func.FunctionApp()
logger = get_logger(__name__)

@app.schedule(
    schedule="0 */2 * * * *", # a cada 2 minutos
    arg_name="myTimer",
    # Produção: sem execução em deploy/restart/scale (evita disparos inesperados);
    # o agendamento é persistido pelo monitor do runtime.
    run_on_startup=False,
    use_monitor=True,
)
def ura_calls_surveys(myTimer: func.TimerRequest) -> None:
    """Dispara a geração e envio de eventos (URA, Calls, Surveys) via Managed Identity."""
    logger.info("Iniciando execução do TimerTrigger (*/2 min).")

    # Autenticação passwordless pela Managed Identity da Function App.
    cred = get_credential()

    eventos_ura = gerar_eventos_ura()
    eventos_calls = gerar_fato_chamada_humana(eventos_ura)
    eventos_survey = gerar_fato_pesquisa_satisfacao(eventos_ura)

    sent_ura = send_events(settings.eh_name_ura, cred, eventos_ura)
    sent_calls = send_events(settings.eh_name_calls, cred, eventos_calls)
    sent_surveys = send_events(settings.eh_name_surveys, cred, eventos_survey)

    logger.info(
        "Envio concluído",
        extra={"counts": {"ura": sent_ura, "calls": sent_calls, "surveys": sent_surveys}},
    )
