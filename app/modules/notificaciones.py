"""
modules/notificaciones.py
Email Outlook + JIRA API — notificaciones automáticas de alertas ATP
"""
import os
import base64
import smtplib
import requests
import urllib3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COLOR_NIVEL = {"CRÍTICO": "#FF0000", "SERIO": "#FF8C00", "MEDIO": "#FFD700", "BAJO": "#1D9E75"}
ICONO_NIVEL = {"CRÍTICO": "🔴",      "SERIO": "🟠",       "MEDIO": "🟡",      "BAJO": "🟢"}

DESTINATARIOS = ["derly.mazenett@atpsites.com", "martin.rivera@atpsites.com", "eduardo.castillo@atpsites.com"]


def enviar_alerta_teams(alerta: dict, operador: str, kpis: dict) -> dict:
    """Envía alerta por correo Outlook al equipo NOC ATP."""
    email_from     = os.getenv("EMAIL_FROM", "")
    email_password = os.getenv("EMAIL_PASSWORD", "")
    smtp_server    = os.getenv("EMAIL_SMTP", "smtp.office365.com")
    smtp_port      = int(os.getenv("EMAIL_SMTP_PORT", 587))

    if not email_from or "PLACEHOLDER" in email_password:
        return {"ok": False, "msg": "EMAIL no configurado en .env"}

    nivel  = alerta.get("nivel", "SERIO")
    icono  = ICONO_NIVEL.get(nivel, "⚠️")
    color  = COLOR_NIVEL.get(nivel, "#FF8C00")
    ts     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    asunto = f"{icono} [{nivel}] {alerta.get('titulo', '')} — Portal NOC ATP"

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
    <div style="max-width:600px;margin:auto;background:white;border-radius:8px;
                border-left:6px solid {color};padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <h2 style="color:{color};margin-top:0;">{icono} ALERTA {nivel} — Portal ATP NOC</h2>
        <h3 style="color:#333;">{alerta.get('titulo', '')}</h3>
        <p style="color:#555;">{alerta.get('descripcion', '')}</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;">
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">Operador</td>
                <td style="padding:8px;border:1px solid #eee;">{operador}</td>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">SLA Actual</td>
                <td style="padding:8px;border:1px solid #eee;">{kpis.get('sla_global', 0):.2f}%</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">% Timeouts</td>
                <td style="padding:8px;border:1px solid #eee;">{kpis.get('pct_timeout', 0):.2f}%</td>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">% Error Técnico</td>
                <td style="padding:8px;border:1px solid #eee;">{kpis.get('pct_error', 0):.2f}%</td>
            </tr>
            <tr style="background:#f9f9f9;">
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">Total TX</td>
                <td style="padding:8px;border:1px solid #eee;">{kpis.get('total_tx', 0):,}</td>
            </tr>
            <tr>
                <td style="padding:8px;border:1px solid #eee;font-weight:bold;">Detectado</td>
                <td style="padding:8px;border:1px solid #eee;">{ts}</td>
            </tr>
        </table>
        <div style="margin-top:20px;padding:12px;background:#fff3cd;border-radius:6px;
                    border-left:4px solid #ffc107;">
            <strong>⏱ ANS Contractual:</strong><br>
            Tiempo respuesta CRÍTICO = 15 min | Restablecimiento = 3 horas
        </div>
        <p style="margin-top:20px;font-size:12px;color:#999;">
            Portal NOC ATP — Andean Telecom Partners<br>
            Este correo fue generado automáticamente.
        </p>
    </div>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = email_from
        msg["To"]      = ", ".join(DESTINATARIOS)
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.sendmail(email_from, DESTINATARIOS, msg.as_string())
        return {"ok": True, "msg": f"Alerta enviada por correo ✅ ({ts})"}
    except Exception as e:
        return {"ok": False, "msg": f"Error enviando correo: {e}"}


def enviar_alerta_timeouts(
    operador: str,
    total_timeouts: int,
    ventana_min: int,
    detalle_timeouts: list,
) -> dict:
    """
    Envía correo específico cuando se detectan 3+ timeouts en la ventana de tiempo.
    detalle_timeouts: lista de dicts con {timestamp, proceso, time_taken_ms}
    """
    email_from     = os.getenv("EMAIL_FROM", "")
    email_password = os.getenv("EMAIL_PASSWORD", "")
    smtp_server    = os.getenv("EMAIL_SMTP", "smtp.office365.com")
    smtp_port      = int(os.getenv("EMAIL_SMTP_PORT", 587))

    if not email_from or not email_password or "PLACEHOLDER" in email_password:
        return {"ok": False, "msg": "EMAIL no configurado en .env"}

    ts     = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    asunto = f"🔴 ALERTA TIMEOUT — {total_timeouts} timeouts en {ventana_min} min — {operador} — Portal NOC ATP"

    # Construir tabla de detalle
    filas_detalle = ""
    for i, t in enumerate(detalle_timeouts[:10]):  # máximo 10 filas
        bg = "#fff" if i % 2 == 0 else "#f9f9f9"
        filas_detalle += f"""
        <tr style="background:{bg};">
            <td style="padding:8px;border:1px solid #eee;">{t.get('timestamp','—')}</td>
            <td style="padding:8px;border:1px solid #eee;">{t.get('proceso','—')}</td>
            <td style="padding:8px;border:1px solid #eee;font-weight:bold;color:#C0392B;">
                {int(t.get('time_taken_ms', 0)):,} ms
            </td>
        </tr>
        """

    cuerpo_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
    <div style="max-width:650px;margin:auto;background:white;border-radius:8px;
                border-left:6px solid #FF0000;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

        <h2 style="color:#FF0000;margin-top:0;">
            🔴 ALERTA DE TIMEOUTS — Portal NOC ATP
        </h2>

        <div style="background:#FEE2E2;border-radius:8px;padding:16px;margin-bottom:20px;text-align:center;">
            <div style="font-size:48px;font-weight:800;color:#991B1B;">{total_timeouts}</div>
            <div style="font-size:16px;color:#991B1B;font-weight:600;">
                timeouts detectados en los últimos {ventana_min} minutos
            </div>
            <div style="font-size:13px;color:#C0392B;margin-top:4px;">
                Umbral: 3 timeouts / {ventana_min} min — Operador: <strong>{operador}</strong>
            </div>
        </div>

        <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr>
                <td style="padding:10px;border:1px solid #eee;font-weight:bold;background:#f9f9f9;">
                    Operador
                </td>
                <td style="padding:10px;border:1px solid #eee;">{operador}</td>
            </tr>
            <tr>
                <td style="padding:10px;border:1px solid #eee;font-weight:bold;background:#f9f9f9;">
                    Detectado
                </td>
                <td style="padding:10px;border:1px solid #eee;">{ts}</td>
            </tr>
            <tr>
                <td style="padding:10px;border:1px solid #eee;font-weight:bold;background:#f9f9f9;">
                    Ventana analizada
                </td>
                <td style="padding:10px;border:1px solid #eee;">Últimos {ventana_min} minutos</td>
            </tr>
            <tr>
                <td style="padding:10px;border:1px solid #eee;font-weight:bold;background:#f9f9f9;">
                    Total timeouts
                </td>
                <td style="padding:10px;border:1px solid #eee;color:#991B1B;font-weight:bold;">
                    {total_timeouts} (umbral: 3)
                </td>
            </tr>
        </table>

        <h3 style="color:#333;border-bottom:2px solid #FEE2E2;padding-bottom:8px;">
            📋 Detalle de timeouts detectados
        </h3>
        <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#991B1B;color:white;">
                <th style="padding:10px;text-align:left;">Fecha/Hora</th>
                <th style="padding:10px;text-align:left;">Proceso</th>
                <th style="padding:10px;text-align:left;">Tiempo (ms)</th>
            </tr>
            {filas_detalle}
        </table>
        {"<p style='font-size:11px;color:#888;margin-top:4px;'>* Mostrando máximo 10 registros</p>" if len(detalle_timeouts) > 10 else ""}

        <div style="margin-top:20px;padding:14px;background:#FEF3C7;border-radius:6px;
                    border-left:4px solid #F59E0B;">
            <strong>⚡ Acción requerida:</strong><br>
            Revisar el sistema Tecnotree — posible degradación del servicio.<br>
            ANS: Tiempo de respuesta CRÍTICO = <strong>15 minutos</strong>
        </div>

        <p style="margin-top:20px;font-size:12px;color:#999;border-top:1px solid #eee;padding-top:12px;">
            Portal NOC ATP — Andean Telecom Partners<br>
            Monitor automático de timeouts 24/7 — Este correo fue generado automáticamente.<br>
            Próxima revisión en {ventana_min} minutos.
        </p>
    </div>
    </body></html>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = email_from
        msg["To"]      = ", ".join(DESTINATARIOS)
        msg.attach(MIMEText(cuerpo_html, "html"))
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.sendmail(email_from, DESTINATARIOS, msg.as_string())
        return {"ok": True, "msg": f"Alerta de timeouts enviada ✅ ({ts})"}
    except Exception as e:
        return {"ok": False, "msg": f"Error enviando correo de timeouts: {e}"}


# ─────────────────────────────────────────────────────────────
# JIRA
# ─────────────────────────────────────────────────────────────

def _jira_headers() -> dict:
    user  = os.getenv("JIRA_USER", "")
    token = os.getenv("JIRA_API_TOKEN", "")
    cred  = base64.b64encode(f"{user}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {cred}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def _jira_base() -> str:
    return os.getenv("JIRA_URL", "").rstrip("/")


def buscar_ticket_abierto(alerta: dict, operador: str) -> str | None:
    base    = _jira_base()
    project = os.getenv("JIRA_PROJECT_KEY", "ATP")
    if not base or "PLACEHOLDER" in os.getenv("JIRA_API_TOKEN", "PLACEHOLDER"):
        return None
    metrica = alerta.get("metrica", "")
    jql = (f'project = "{project}" AND status != Done '
           f'AND labels = "atp-alerta-auto" '
           f'AND labels = "{metrica.lower()}" '
           f'AND labels = "{operador.lower()}" '
           f'ORDER BY created DESC')
    try:
        r = requests.get(f"{base}/rest/api/3/search",
                         headers=_jira_headers(),
                         params={"jql": jql, "maxResults": 1},
                         timeout=10, verify=False)
        if r.status_code == 200:
            issues = r.json().get("issues", [])
            if issues:
                return issues[0]["key"]
    except Exception:
        pass
    return None


def crear_ticket_jira(alerta: dict, operador: str, kpis: dict) -> dict:
    base    = _jira_base()
    project = os.getenv("JIRA_PROJECT_KEY", "ATP")
    if not base or "PLACEHOLDER" in os.getenv("JIRA_API_TOKEN", "PLACEHOLDER"):
        return {"ok": False, "key": None, "url": None,
                "msg": "JIRA no configurado — completar JIRA_URL y JIRA_API_TOKEN en .env"}

    ticket_existente = buscar_ticket_abierto(alerta, operador)
    if ticket_existente:
        return {"ok": True, "key": ticket_existente,
                "url": f"{base}/browse/{ticket_existente}",
                "msg": f"Ticket ya existe: {ticket_existente} (no se creó duplicado)"}

    nivel     = alerta.get("nivel", "SERIO")
    ts        = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    metrica   = alerta.get("metrica", "ALERTA")
    prioridad_map = {"CRÍTICO": "Highest", "SERIO": "High", "MEDIO": "Medium", "BAJO": "Low"}
    prioridad = prioridad_map.get(nivel, "High")

    descripcion = (
        f"*Alerta automática generada por Portal ATP NOC*\n\n"
        f"*Operador:* {operador}\n*Nivel:* {nivel}\n*Detectado:* {ts}\n\n"
        f"h3. Detalle\n{alerta.get('descripcion', '')}\n\n"
        f"h3. KPIs al momento del disparo\n"
        f"||Métrica||Valor||\n"
        f"|Total TX|{kpis.get('total_tx', 0):,}|\n"
        f"|SLA Global|{kpis.get('sla_global', 0):.2f}%|\n"
        f"|% Error Técnico|{kpis.get('pct_error', 0):.2f}%|\n"
        f"|% Timeout|{kpis.get('pct_timeout', 0):.2f}%|\n\n"
        f"_Ticket generado automáticamente por Portal NOC ATP_"
    )

    payload = {
        "fields": {
            "project":     {"key": project},
            "summary":     f"[{nivel}] {alerta.get('titulo', '')} — {operador} {ts}",
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph",
                              "content": [{"type": "text", "text": descripcion}]}],
            },
            "issuetype": {"name": "Bug"},
            "priority":  {"name": prioridad},
            "labels":    ["atp-alerta-auto", metrica.lower(), operador.lower(), "noc-portal"],
        }
    }

    try:
        r = requests.post(f"{base}/rest/api/3/issue",
                          headers=_jira_headers(), json=payload,
                          timeout=15, verify=False)
        if r.status_code == 201:
            key = r.json().get("key", "")
            url = f"{base}/browse/{key}"
            return {"ok": True, "key": key, "url": url, "msg": f"Ticket creado: {key} ✅"}
        return {"ok": False, "key": None, "url": None,
                "msg": f"JIRA respondió {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"ok": False, "key": None, "url": None, "msg": f"Error creando ticket: {e}"}