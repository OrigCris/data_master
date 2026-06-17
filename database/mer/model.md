# Modelo de Entidade-Relacionamento (MER)

Modelo lógico do domínio **call center**, organizado pela arquitetura Medallion.
Diagramas em Mermaid (renderizam no GitHub). O DDL físico está em [`../ddl`](../ddl).

## Visão de negócio

Uma **chamada** chega à **URA** (autoatendimento). Se o cliente é **derivado**,
gera um ou mais **atendimentos humanos** (por um **assistente**) e, eventualmente,
responde a uma **pesquisa de satisfação**. Clientes e assistentes são dimensões.

## Bronze (núcleo cru)

```mermaid
erDiagram
    DIM_CLIENTES   ||--o{ URA_ONCE     : "id_cliente"
    DIM_ASSISTENTES ||--o{ CALLS_ONCE  : "id_assistente"
    URA_ONCE       ||--o{ CALLS_ONCE   : "id_chamada (derivada)"
    URA_ONCE       ||--o| SURVEYS_ONCE : "id_chamada"

    DIM_CLIENTES {
        int id_cliente PK
        string nome "PII"
        string cpf "PII"
        string email "PII"
        date data_nascimento "PII"
        string segmento
    }
    DIM_ASSISTENTES {
        int identificadorAssistente PK
        string nomeAssistente "PII"
        string area
        string nomeSupervisor
        string nomeGerente
    }
    URA_ONCE { string body "json cru" }
    CALLS_ONCE { string body "json cru" }
    SURVEYS_ONCE { string body "json cru" }
```

## Silver (normalizada)

```mermaid
erDiagram
    TABE_URA_ANLT ||--o{ TABE_CALLS    : "ID_CHAM"
    TABE_URA_ANLT ||--o| TABE_PESQ_URA : "ID_CHAM"

    TABE_URA_ANLT {
        string ID_CHAM PK
        string ID_CLIE
        string ID_FILA
        boolean IN_AUTN
        boolean IN_DERV_ATEN
        int CD_PERI
        date DT_INIC
    }
    TABE_CALLS {
        string ID_CHAM PK
        string ID_ATEN PK
        int ID_ASST
        int IN_TRAF
        int IN_TRAF_INDV
    }
    TABE_PESQ_URA {
        string ID_PESQ PK
        string ID_CHAM
        int VL_NOTA
        date DT_ENVI
    }
```

## Gold (visões analíticas)

| Tabela | Grão | Origem |
|---|---|---|
| `visao_ura_calls` | dia × fila | `tabe_ura_anlt` + `tabe_calls` |
| `visao_assistentes` | dia × assistente | `tabe_calls` + `tabe_pesq_ura` + `dim_assistentes` |

> A coluna `CD_PERI` (yyyyMM) e a data de referência (`DT_INIC`/`DT_REFE`) são as
> chaves de particionamento lógico (liquid clustering) em todas as camadas.
