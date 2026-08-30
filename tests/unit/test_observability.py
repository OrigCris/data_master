"""Testes da lógica pura de observabilidade (sem Spark).

A decisão de anomalia de volume, o corte de freshness e a média móvel são funções
puras — a coleta das métricas depende do Spark e não é exercitada aqui.
"""
from quality.observability import (
    ObservabilityReport,
    ObservationResult,
    freshness_exceeded,
    rolling_average,
    volume_anomaly,
)


def test_rolling_average_vazio_eh_zero():
    assert rolling_average([]) == 0.0


def test_rolling_average_ignora_none():
    assert rolling_average([10, None, 20]) == 15.0


def test_volume_dentro_da_faixa_nao_eh_anomalia():
    is_anom, _ = volume_anomaly(1000, 1000, lo=0.7, hi=1.3)
    assert not is_anom


def test_volume_muito_baixo_eh_anomalia():
    # ontem ~10M, hoje 40k → claramente anômalo
    is_anom, detail = volume_anomaly(40_000, 10_000_000)
    assert is_anom
    assert "40000" in detail.replace("_", "")


def test_volume_muito_alto_eh_anomalia():
    is_anom, _ = volume_anomaly(2000, 1000, lo=0.7, hi=1.3)
    assert is_anom


def test_volume_sem_historico_nao_eh_anomalia():
    is_anom, detail = volume_anomaly(123, 0)
    assert not is_anom
    assert "sem histórico" in detail


def test_freshness_dentro_do_limite():
    assert not freshness_exceeded(30, 60)


def test_freshness_excedido():
    assert freshness_exceeded(120, 60)


def test_freshness_sem_dado_conta_como_stale():
    assert freshness_exceeded(None, 60)


def test_freshness_sem_limite_nunca_falha():
    assert not freshness_exceeded(None, None)


def test_report_gate_por_severidade():
    rep = ObservabilityReport(
        dataset="ds",
        observed_date=__import__("datetime").date(2026, 1, 1),
        results=[
            ObservationResult("row_count", 40.0, "warn", False, "anômalo"),
            ObservationResult("freshness_minutes", 10.0, "critical", True, "ok"),
        ],
    )
    assert not rep.passed
    # a única falha é warn → não interrompe
    assert rep.critical_failures == []
    rep.raise_if_critical_failed()
