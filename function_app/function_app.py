from __future__ import annotations
import azure.functions as func
from utils.logging_utils import get_logger
from generators.ura import gerar_eventos_ura
from generators.calls import gerar_fato_chamada_humana
from generators.surveys import gerar_fato_pesquisa_satisfacao
from services.eventhub_client import send_events
from auth.credentials import get_spn_credential
from config.settings import settings

app = func.FunctionApp()
logger = get_logger(__name__)

@app.schedule(
    schedule="0 */2 * * * *", # a cada 2 minutos
    arg_name="myTimer",
    run_on_startup=True,
    use_monitor=False,
)
def ura_calls_surveys(myTimer: func.TimerRequest) -> None:
    """Dispara a geração e envio de eventos (URA, Calls, Surveys) usando SPN do KV."""
    logger.info("Iniciando execução do TimerTrigger (*/2 min).")

    # Credencial do SPN (lida do Key Vault via Managed Identity)
    spn_cred = get_spn_credential()

    # Geração dos eventos
    eventos_ura = gerar_eventos_ura()
    eventos_calls = gerar_fato_chamada_humana(eventos_ura)
    eventos_survey = gerar_fato_pesquisa_satisfacao(eventos_ura)

    # Envio
    sent_ura = send_events(settings.eh_name_ura, spn_cred, eventos_ura)
    sent_calls = send_events(settings.eh_name_calls, spn_cred, eventos_calls)
    sent_surveys = send_events(settings.eh_name_surveys, spn_cred, eventos_survey)

    logger.info(
        "Envio concluído",
        extra={"counts": {"ura": sent_ura, "calls": sent_calls, "surveys": sent_surveys}},
    )