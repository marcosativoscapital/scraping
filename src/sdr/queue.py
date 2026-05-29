"""Gestão de fila de prospecção para o SDR."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..db.store import Store


class SDRQueue:
    """Operações de SDR sobre os leads + playbooks."""

    def __init__(self, store: Store | None = None):
        self.store = store or Store()

    # ====== Atribuição ======
    def assign_lead(self, lead_id: int, sdr_email: str) -> None:
        """Atribui um lead a um SDR específico."""
        now = datetime.now().isoformat()
        with self.store.conn() as c:
            c.execute(
                """UPDATE leads
                   SET sdr_assigned = ?, sdr_assigned_at = ?
                   WHERE id = ?""",
                (sdr_email, now, lead_id),
            )

    def auto_assign_hot_leads(self, sdr_email: str, min_score: int = 60, max_n: int = 20) -> int:
        """Auto-atribui leads quentes não atribuídos."""
        with self.store.conn() as c:
            rows = c.execute(
                """SELECT id FROM leads
                   WHERE COALESCE(score_icp, 0) >= ?
                   AND sdr_assigned IS NULL
                   ORDER BY score_icp DESC LIMIT ?""",
                (min_score, max_n),
            ).fetchall()
            ids = [r["id"] for r in rows]
        for lead_id in ids:
            self.assign_lead(lead_id, sdr_email)
        return len(ids)

    def queue_for(self, sdr_email: str | None = None, status: str | None = None) -> list[dict]:
        """Retorna fila do SDR (todos seus leads agrupados por status do toque)."""
        with self.store.conn() as c:
            sql = """SELECT l.*, COUNT(a.id) as toques_totais,
                     MAX(a.criado_em) as ultimo_toque
                     FROM leads l
                     LEFT JOIN sdr_activities a ON a.lead_id = l.id
                     WHERE l.sdr_assigned IS NOT NULL"""
            params = []
            if sdr_email:
                sql += " AND l.sdr_assigned = ?"
                params.append(sdr_email)
            if status:
                sql += " AND l.sdr_status = ?"
                params.append(status)
            sql += " GROUP BY l.id ORDER BY l.score_icp DESC, l.criado_em DESC"
            rows = c.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    # ====== Atividades ======
    def log_activity(
        self,
        lead_id: int,
        sdr_email: str,
        tipo: str,
        canal: str | None = None,
        playbook_id: str | None = None,
        outcome: str | None = None,
        notas: str | None = None,
    ) -> int:
        """Registra atividade do SDR sobre um lead.

        tipo: toque_enviado | resposta_recebida | reuniao_agendada | qualificado | descartado
        canal: linkedin | email | sms | whatsapp | voz
        outcome: positivo | neutro | negativo | objecao | sem_resposta
        """
        now = datetime.now().isoformat()
        with self.store.conn() as c:
            cur = c.execute(
                """INSERT INTO sdr_activities
                   (lead_id, sdr_email, tipo, canal, playbook_id, outcome, notas, criado_em)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (lead_id, sdr_email, tipo, canal, playbook_id, outcome, notas, now),
            )
            # Atualiza status na tabela leads
            self._update_lead_status(c, lead_id, tipo, outcome, now)
            return cur.lastrowid

    def _update_lead_status(self, conn, lead_id: int, tipo: str, outcome: str | None, now: str):
        """Atualiza sdr_status do lead conforme tipo da atividade."""
        status_map = {
            "toque_enviado": "contatado",
            "resposta_recebida": "respondeu",
            "reuniao_agendada": "reuniao_agendada",
            "qualificado": "qualificado",
            "descartado": "descartado",
        }
        new_status = status_map.get(tipo)
        if new_status:
            conn.execute(
                "UPDATE leads SET sdr_status = ?, sdr_status_at = ? WHERE id = ?",
                (new_status, now, lead_id),
            )

    def activities_for_lead(self, lead_id: int) -> list[dict]:
        with self.store.conn() as c:
            rows = c.execute(
                "SELECT * FROM sdr_activities WHERE lead_id = ? ORDER BY criado_em DESC",
                (lead_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ====== Playbooks atribuídos ======
    def assign_playbooks(self, lead_id: int, playbooks: list[dict]) -> None:
        """Salva playbooks selecionados pelo agente para um lead."""
        now = datetime.now().isoformat()
        with self.store.conn() as c:
            c.execute("DELETE FROM lead_playbooks WHERE lead_id = ?", (lead_id,))
            for pb in playbooks:
                c.execute(
                    """INSERT INTO lead_playbooks
                       (lead_id, playbook_id, playbook_nome, categoria, ordem, justificativa,
                        sinal_detectado, status, criado_em)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'sugerido', ?)""",
                    (
                        lead_id,
                        pb.get("playbook_id"),
                        pb.get("playbook_nome"),
                        pb.get("categoria"),
                        pb.get("ordem", 99),
                        pb.get("justificativa"),
                        pb.get("sinal_detectado"),
                        now,
                    ),
                )

    def playbooks_for_lead(self, lead_id: int) -> list[dict]:
        with self.store.conn() as c:
            rows = c.execute(
                "SELECT * FROM lead_playbooks WHERE lead_id = ? ORDER BY ordem",
                (lead_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_playbook_status(self, lead_id: int, playbook_id: str, status: str) -> None:
        """status: sugerido | em_execucao | concluido | abandonado"""
        with self.store.conn() as c:
            c.execute(
                """UPDATE lead_playbooks SET status = ?, atualizado_em = ?
                   WHERE lead_id = ? AND playbook_id = ?""",
                (status, datetime.now().isoformat(), lead_id, playbook_id),
            )

    # ====== Métricas ======
    def metrics(self, sdr_email: str | None = None) -> dict[str, Any]:
        with self.store.conn() as c:
            sql_base = "FROM leads WHERE sdr_assigned IS NOT NULL"
            params = []
            if sdr_email:
                sql_base += " AND sdr_assigned = ?"
                params.append(sdr_email)

            total = c.execute(f"SELECT COUNT(*) n {sql_base}", params).fetchone()["n"]
            por_status = {
                r["sdr_status"] or "a_contatar": r["n"]
                for r in c.execute(
                    f"SELECT sdr_status, COUNT(*) n {sql_base} GROUP BY sdr_status",
                    params,
                ).fetchall()
            }

            # Atividades do dia
            hoje = datetime.now().strftime("%Y-%m-%d")
            sql_act = "SELECT tipo, COUNT(*) n FROM sdr_activities WHERE criado_em LIKE ?"
            act_params = [f"{hoje}%"]
            if sdr_email:
                sql_act += " AND sdr_email = ?"
                act_params.append(sdr_email)
            sql_act += " GROUP BY tipo"
            atividades_hoje = {
                r["tipo"]: r["n"]
                for r in c.execute(sql_act, act_params).fetchall()
            }

            return {
                "total_atribuidos": total,
                "por_status": por_status,
                "atividades_hoje": atividades_hoje,
            }
