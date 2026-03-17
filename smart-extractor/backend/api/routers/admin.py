from fastapi import APIRouter, Request, Query
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from services.database import get_user_credits, clear_extracoes, get_extraction_repo, get_usage_stats, set_plan
from services.request_context import current_tenant_id, current_user_id
import logging


router = APIRouter(tags=["Administração e Usuários"])
_logger = logging.getLogger("smart_extractor")


@router.get("/api/status")
def api_status():
    """Status da API (abrir o sistema em / para o frontend)."""
    return {"status": "online", "version": "3.2", "docs": "/docs"}


@router.get("/credits/{user_id}")
def get_credits_endpoint(user_id: str):
    return {"user_id": user_id, "credits": get_user_credits(user_id)}


@router.get("/historico/{user_id}")
def get_historico(user_id: str, limit: int = 20):
    if limit > 100:
        limit = 100
    extraction_repo = get_extraction_repo(tenant_id=user_id)
    return {
        "user_id": user_id,
        "extractions": extraction_repo.get_user_history(user_id, limit=limit),
    }


@router.get("/api/knowledge-base")
async def get_knowledge_base(user_id: str = "default"):
    """
    Retorna o conteúdo completo do knowledge_base.json para o painel de gestão
    (card Inteligência Pericial + modal Biblioteca de Regras).
    Rota obrigatória para o frontend; nunca retorna 404.
    """
    from services.knowledge_base import KnowledgeBase

    try:
        # Sprint 1: tenant_id vem preferencialmente do contexto; query param é legado.
        tenant_id = current_tenant_id() or user_id
        kb = KnowledgeBase(tenant_id=tenant_id)
        data = kb.get_all()
        if not isinstance(data.get("rules"), list):
            data = {"rules": [], "_meta": data.get("_meta", {"version": "1.0"})}
        rules = data.get("rules") or []
        # Regra de segurança SaaS: se vazio, envia regra de teste para validar conexão
        if not rules:
            data["rules"] = [
                {
                    "rule_id": "SISTEMA_OK",
                    "descricao": "Conexão estabelecida. Aguardando novos aprendizados...",
                    "condicao": {"tipo": "verba_ausente"},
                    "status": "active",
                    "confidence_score": 100,
                }
            ]
        return data
    except Exception as e:
        _logger.error(
            "knowledge_base_read_failed",
            extra={"error": str(e)},
        )
        return {
            "rules": [
                {
                    "rule_id": "SISTEMA_OK",
                    "descricao": "Conexão estabelecida. Aguardando novos aprendizados...",
                    "condicao": {"tipo": "verba_ausente"},
                    "status": "active",
                    "confidence_score": 100,
                }
            ],
            "_meta": {"version": "1.0", "error": str(e)},
        }


@router.get("/api/stats")
def api_stats(user_id: str = "default"):
    """
    Dashboard de estatísticas para o frontend (view 'Estatísticas').

    Retorna:
      - processos_analisados: total de registros na tabela extracoes.
      - regras_oficiais_ativas: regras dinâmicas com status 'active' (confidence_score >= 3).
      - regras_em_teste_shadow: regras dinâmicas com status 'shadow'.
      - omissoes_detectadas: soma dos campos 'punicoes' das regras dinâmicas (proxy de omissões).
      - ultimas_regras: últimas 5 regras dinâmicas (ordenadas por updated_at/created_at).
      - top_verbas_divergencias: top verbas presentes nas condições de tipo 'verba_*'.
    """
    from services.knowledge_base import KnowledgeBase

    # Sprint 1/2: tenant_id vem preferencialmente do contexto; query param é legado.
    tenant_id = current_tenant_id() or user_id
    kb = KnowledgeBase(tenant_id=tenant_id)
    stats_kb = kb.stats()
    rules_all = kb._data.get("rules", []) if hasattr(kb, "_data") else []

    # KPIs de regras dinâmicas
    regras_ativas = stats_kb.get("active", 0)
    regras_shadow = stats_kb.get("shadow", 0)

    # Omissões detectadas: soma das punições (regras que "erraram" predições)
    omissoes = 0
    total_acertos = 0
    total_punicoes = 0
    for r in rules_all:
        try:
            total_acertos += int(r.get("acertos", 0) or 0)
            total_punicoes += int(r.get("punicoes", 0) or 0)
            omissoes += int(r.get("punicoes", 0) or 0)
        except Exception:
            continue

    # Eficiência do motor: acertos / (acertos + punições), em percentual
    total_avaliados = total_acertos + total_punicoes
    eficiencia_motor = round((total_acertos / total_avaliados) * 100, 1) if total_avaliados > 0 else None

    # Últimas regras aprendidas (5 mais recentes)
    ultimas = sorted(
        rules_all,
        key=lambda r: (r.get("updated_at") or r.get("created_at") or ""),
        reverse=True,
    )[:5]

    ultimas_slim = [
        {
            "rule_id": r.get("rule_id"),
            "descricao": r.get("descricao"),
            "status": r.get("status"),
            "confidence_score": r.get("confidence_score", 0),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }
        for r in ultimas
    ]

    # Top verbas com divergências: condicao.tipo verba_ausente / verba_presente
    contagens: dict[str, int] = {}
    for r in rules_all:
        cond = r.get("condicao") or {}
        tipo = (cond.get("tipo") or "").lower()
        if tipo not in ("verba_ausente", "verba_presente"):
            continue
        verba = (cond.get("verba") or "").strip()
        if not verba:
            continue
        key = verba
        contagens[key] = contagens.get(key, 0) + 1

    total_refs = sum(contagens.values()) or 1
    top_verbas = sorted(
        [{"verba": k, "contagem": v, "percentual": (v / total_refs) * 100.0} for k, v in contagens.items()],
        key=lambda x: x["contagem"],
        reverse=True,
    )[:5]

    # Se não houver dados suficientes, retorna um mock seguro
    if not rules_all and not contagens:
        top_verbas = [
            {"verba": "Horas Extras", "contagem": 0, "percentual": 0.0},
            {"verba": "DSR", "contagem": 0, "percentual": 0.0},
            {"verba": "Aviso Prévio", "contagem": 0, "percentual": 0.0},
        ]

    extraction_repo = get_extraction_repo(tenant_id=tenant_id)

    return {
        "processos_analisados": extraction_repo.get_total_extractions(),
        "regras_oficiais_ativas": regras_ativas,
        "regras_em_teste_shadow": regras_shadow,
        "omissoes_detectadas": omissoes,
        "eficiencia_motor": eficiencia_motor,   # float 0-100 ou null se sem dados
        "ultimas_regras": ultimas_slim,
        "top_verbas_divergencias": top_verbas,
    }


@router.delete("/api/admin/reset-contagem")
def reset_contagem():
    """
    Zera o histórico de extrações (tabela extracoes).

    Operação administrativa global — sem filtro de tenant (intencional).
    Documentado em refatoracao_necessaria.mdc § Sprint 2.

    Isso faz com que 'Processos Analisados' volte a 0 no Dashboard.
    Não apaga: créditos, cache de PDFs, jobs, Knowledge Base, learning_log.
    Use apenas para reiniciar os testes sem contaminar estatísticas.
    """
    deleted = clear_extracoes()
    return {
        "ok": True,
        "registros_removidos": deleted,
        "mensagem": f"{deleted} extração(ões) removida(s). Contador zerado.",
    }


@router.get("/api/billing/usage")
async def get_billing_usage(
    request: Request,
    user_id: str = Query(..., description="ID do tenant/usuário"),
):
    """
    Retorna métricas de uso e plano do tenant.
    Usado pelo Dashboard e por ferramentas administrativas.
    """
    from services.request_context import get_request_context

    ctx = get_request_context()
    effective_user_id = ctx.tenant_id or user_id or "anonimo"

    try:
        stats = get_usage_stats(effective_user_id)
        return {
            "user_id": effective_user_id,
            **stats,
        }
    except Exception as e:
        _logger.error(
            "billing_usage_error",
            extra={"user_id": effective_user_id, "error": str(e)},
        )
        return {
            "user_id": effective_user_id,
            "creditos_restantes": 0,
            "plano": "free",
            "limite_pdfs": 10,
            "limite_lab": 3,
            "pdfs_usados": 0,
            "lab_analises_usadas": 0,
            "erro": str(e),
        }


class PlanUpdateRequest(BaseModel):
    user_id: str
    plan: str  # "free" | "pro" | "enterprise"


@router.post("/api/admin/billing/plan")
async def set_billing_plan(body: PlanUpdateRequest):
    """
    Atualiza o plano de um tenant. Operação administrativa.
    Valores válidos: free, pro, enterprise.
    """
    planos_validos = {"free", "pro", "enterprise"}
    if body.plan not in planos_validos:
        return JSONResponse(
            status_code=400,
            content={"error": f"Plano inválido. Válidos: {planos_validos}"},
        )
    try:
        set_plan(body.user_id, body.plan)
        _logger.info(
            "billing_plan_updated",
            extra={"user_id": body.user_id, "plano": body.plan},
        )
        return {"ok": True, "user_id": body.user_id, "plano": body.plan}
    except Exception as e:
        _logger.error(
            "billing_plan_update_error",
            extra={"user_id": body.user_id, "error": str(e)},
        )
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )

