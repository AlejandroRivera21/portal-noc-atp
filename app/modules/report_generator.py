"""
modules/report_generator.py
Genera el reporte HTML ejecutivo gerencial.
"""
import base64
import io
import os
import math
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from modules.data_processor import (
    COL_TRANS, COL_CODE, COL_TIME,
    FALLAS_TECNICAS, COLORES_PROCESO, PROCESOS_IMPORTANTES
)


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=130,
                facecolor=fig.get_facecolor())
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def _logo_b64() -> str:
    for ruta in ["logo_ATP.png", "atp-portal/logo_ATP.png",
                 os.path.join(os.path.dirname(__file__), "..", "logo_ATP.png")]:
        if os.path.exists(ruta):
            with open(ruta, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""


def _gauge_sla(sla_valor: float, titulo: str = "Tasa de Éxito") -> str:
    """
    Gauge semicircular correcto.
    El arco va de izquierda (15,85) a derecha (155,85) pasando por arriba.
    pct=100  → termina en (155, 85) → arco completo
    pct=50   → termina en (85, 15)  → arco a la mitad (arriba)
    pct=0    → termina en (15, 85)  → arco vacío
    """
    color = "#1D9E75" if sla_valor >= 99 else ("#F39C12" if sla_valor >= 95 else "#E74C3C")
    pct   = min(max(sla_valor, 0), 100)
    r     = 70
    cx, cy = 85, 85
    # angle_rad: 0% → π (izquierda), 100% → 0 (derecha)
    angle_rad = math.radians(180.0 - (pct / 100.0) * 180.0)
    end_x = cx + r * math.cos(angle_rad)
    end_y = cy - r * math.sin(angle_rad)
    large = 1 if pct > 50 else 0
    return f"""
    <svg width="170" height="110" viewBox="0 0 170 110">
      <path d="M {cx-r},{cy} A {r},{r} 0 0 1 {cx+r},{cy}"
            fill="none" stroke="#EAEAEA" stroke-width="14" stroke-linecap="round"/>
      <path d="M {cx-r},{cy} A {r},{r} 0 {large} 1 {end_x:.1f},{end_y:.1f}"
            fill="none" stroke="{color}" stroke-width="14" stroke-linecap="round"/>
      <text x="{cx}" y="{cy+5}" text-anchor="middle"
            font-size="22" font-weight="bold" fill="{color}">{pct:.1f}%</text>
      <text x="{cx}" y="{cy+22}" text-anchor="middle"
            font-size="10" fill="#666">{titulo}</text>
    </svg>"""


def _grafica_barras_procesos(resumen_df: pd.DataFrame) -> str:
    if resumen_df.empty:
        return ""
    df = resumen_df.sort_values('SLA_pct', ascending=True).head(12)
    fig, ax = plt.subplots(figsize=(10, max(3, len(df) * 0.55)))
    fig.patch.set_facecolor('#FAFBFD')
    ax.set_facecolor('#FAFBFD')
    colores = ['#E74C3C' if v < 95 else ('#F39C12' if v < 99 else '#1D9E75')
               for v in df['SLA_pct']]
    bars = ax.barh(df[COL_TRANS], df['SLA_pct'], color=colores, height=0.6, edgecolor='none')
    ax.axvline(99.9, color='#3C3489', linewidth=1.8, linestyle='--', alpha=0.9, label='ANS 99.9%')
    ax.axvline(95.0, color='#E74C3C', linewidth=1.2, linestyle=':', alpha=0.7, label='Umbral crítico 95%')
    for bar, val in zip(bars, df['SLA_pct']):
        ax.text(min(val + 0.3, 103), bar.get_y() + bar.get_height() / 2,
                f'{val:.1f}%', va='center', ha='left', fontsize=9, fontweight='bold',
                color='#1D9E75' if val >= 99 else ('#F39C12' if val >= 95 else '#E74C3C'))
    ax.set_xlim(0, 106)
    ax.set_xlabel('Tasa de Éxito (%)', fontsize=10, color='#555')
    ax.tick_params(axis='y', labelsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.xaxis.grid(True, alpha=0.25)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, loc='lower right')
    plt.title('Tasa de Éxito por Proceso vs ANS Contractual', fontsize=11, fontweight='bold', color='#2C3E50', pad=8)
    plt.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


def _grafica_donut(total_ok, total_fallas, total_timeouts) -> str:
    otros = max(0, total_fallas - total_timeouts)
    datos, labels, colores_d = [], [], []
    if total_ok > 0:        datos.append(total_ok);        labels.append('OK');           colores_d.append('#1D9E75')
    if total_timeouts > 0:  datos.append(total_timeouts);  labels.append('Timeout');      colores_d.append('#E74C3C')
    if otros > 0:           datos.append(otros);           labels.append('Error');        colores_d.append('#F39C12')
    if not datos:
        return ""
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    fig.patch.set_facecolor('#FAFBFD')
    wedges, _, autotexts = ax.pie(
        datos, labels=None, colors=colores_d,
        autopct=lambda p: f'{p:.1f}%' if p > 3 else '',
        pctdistance=0.78, startangle=90,
        wedgeprops=dict(width=0.52, edgecolor='white', linewidth=2)
    )
    for at in autotexts:
        at.set_fontsize(9); at.set_fontweight('bold')
    total = sum(datos)
    ax.text(0, 0, f'{total:,}', ha='center', va='center', fontsize=16, fontweight='bold', color='#2C3E50')
    ax.text(0, -0.25, 'TX Total', ha='center', va='center', fontsize=9, color='#666')
    items = [mpatches.Patch(color=c, label=l) for c, l in zip(colores_d, labels)]
    ax.legend(handles=items, loc='lower center', bbox_to_anchor=(0.5, -0.12), ncol=3, fontsize=8, frameon=False)
    ax.set_title('Composición de Transacciones', fontsize=10, fontweight='bold', color='#2C3E50', pad=6)
    plt.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


def _grafica_timeline(df: pd.DataFrame) -> str:
    df_imp = df[df[COL_TRANS].isin(PROCESOS_IMPORTANTES)].copy()
    if df_imp.empty:
        return ""
    dias      = (df_imp[COL_TIME].max() - df_imp[COL_TIME].min()).days
    intervalo = '5min' if dias <= 1 else ('30min' if dias <= 7 else '1h')
    fmt_fecha  = '%H:%M' if dias <= 1 else ('%d/%m %H:%M' if dias <= 7 else '%d/%m')
    df_imp['Intervalo'] = df_imp[COL_TIME].dt.floor(intervalo)
    df_t = df_imp.groupby(['Intervalo', COL_TRANS]).size().reset_index(name='Count')
    fig, ax = plt.subplots(figsize=(13, 4.5))
    fig.patch.set_facecolor('#FAFBFD')
    ax.set_facecolor('#FAFBFD')
    for proc in PROCESOS_IMPORTANTES:
        d = df_t[df_t[COL_TRANS] == proc]
        if not d.empty:
            ax.plot(d['Intervalo'], d['Count'], label=proc, linewidth=1.8,
                    color=COLORES_PROCESO.get(proc, '#95A5A6'), alpha=0.85, marker='o', markersize=2)
    ax.set_xlabel(f'Tiempo (intervalo: {intervalo})', fontsize=9, color='#666')
    ax.set_ylabel('Transacciones', fontsize=9, color='#666')
    ax.grid(True, alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=8)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt_fecha))
    plt.xticks(rotation=30, ha='right', fontsize=8)
    ax.legend(loc='upper right', fontsize=8, ncol=2)
    plt.title('Evolución Temporal — Procesos Críticos', fontsize=11, fontweight='bold', color='#2C3E50', pad=8)
    plt.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


def _grafica_top_errores(top_err: pd.DataFrame) -> str:
    if top_err.empty:
        return ""
    fig, ax = plt.subplots(figsize=(10, max(2.5, len(top_err) * 0.6)))
    fig.patch.set_facecolor('#FAFBFD')
    ax.set_facecolor('#FAFBFD')
    bars = ax.barh(top_err['Error'], top_err['Cantidad'], color='#E74C3C', alpha=0.85, height=0.5)
    for bar, (_, row) in zip(bars, top_err.iterrows()):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{int(row['Cantidad']):,} ({row['Pct']}%)", va='center', ha='left', fontsize=9)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.xaxis.grid(True, alpha=0.2)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', labelsize=8)
    plt.title('Top Fallas Técnicas', fontsize=11, fontweight='bold', color='#2C3E50', pad=8)
    plt.tight_layout()
    b64 = _fig_to_b64(fig)
    plt.close(fig)
    return b64


def generar_html_ejecutivo(df: pd.DataFrame, kpis: dict,
                            operador: str, periodo_str: str,
                            alertas: list) -> str:
    logo_b64 = _logo_b64()
    logo_src = f"data:image/png;base64,{logo_b64}" if logo_b64 else ""

    resumen   = kpis.get("resumen_proceso", pd.DataFrame())
    top_err   = kpis.get("top_errores", pd.DataFrame())
    total_tx  = kpis.get("total_tx", 0)
    sla       = kpis.get("sla_global", 0.0)
    pct_err   = kpis.get("pct_error", 0.0)
    pct_to    = kpis.get("pct_timeout", 0.0)
    total_ok  = total_tx - kpis.get("total_fallas", 0)
    total_fal = kpis.get("total_fallas", 0)
    total_to  = kpis.get("total_timeouts", 0)

    if sla >= 99.9:
        estado_color = "#1D9E75"; estado_label = "✅ OPERACIÓN NORMAL"; estado_bg = "#F0FDF4"
    elif sla >= 95:
        estado_color = "#F39C12"; estado_label = "⚠️ ATENCIÓN REQUERIDA"; estado_bg = "#FFFBEB"
    else:
        estado_color = "#E74C3C"; estado_label = "🔴 ALERTA CRÍTICA"; estado_bg = "#FEF2F2"

    ts_gen      = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    gauge_sla   = _gauge_sla(sla, "Tasa de Éxito")
    b64_barras  = _grafica_barras_procesos(resumen)
    b64_donut   = _grafica_donut(total_ok, total_fal, total_to)
    b64_tiempo  = _grafica_timeline(df) if not df.empty else ""
    b64_errores = _grafica_top_errores(top_err)

    filas_tabla = ""
    if not resumen.empty:
        for _, r in resumen.iterrows():
            sla_r = r.get('SLA_pct', 0)
            sla_color = "#1D9E75" if sla_r >= 99 else ("#F39C12" if sla_r >= 95 else "#E74C3C")
            semaforo  = "🟢" if sla_r >= 99 else ("🟡" if sla_r >= 95 else "🔴")
            filas_tabla += f"""
            <tr>
                <td style="font-weight:600;color:#2C3E50;">{semaforo} {r[COL_TRANS]}</td>
                <td style="text-align:right;">{int(r['Total']):,}</td>
                <td style="text-align:right;color:#1D9E75;">{int(r['OK']):,}</td>
                <td style="text-align:right;color:#E74C3C;">{int(r['Fallas']):,}</td>
                <td style="text-align:right;font-weight:700;color:{sla_color};">{sla_r:.1f}%</td>
                <td style="text-align:right;">{r.get('Error_pct',0):.1f}%</td>
            </tr>"""

    bloque_alertas = ""
    if alertas:
        items_alerta = ""
        for a in alertas:
            c_map = {"CRÍTICO": "#FEE2E2", "SERIO": "#FEF3C7", "MEDIO": "#FFF9C4", "BAJO": "#ECFDF5"}
            b_map = {"CRÍTICO": "#E74C3C", "SERIO": "#F39C12", "MEDIO": "#FFD700", "BAJO": "#1D9E75"}
            bg  = c_map.get(a['nivel'], "#FFF3CD")
            brd = b_map.get(a['nivel'], "#F39C12")
            items_alerta += f"""
            <div style="background:{bg};border-left:4px solid {brd};
                        padding:10px 14px;border-radius:4px;margin-bottom:8px;">
                <strong style="color:{brd};">[{a['nivel']}]</strong>
                {a['titulo']} — <span style="color:#555;">{a['descripcion']}</span>
            </div>"""
        bloque_alertas = f"""
        <div class="section">
          <div class="section-title">⚠️ Alertas Activas en este Período</div>
          {items_alerta}
        </div>"""

    cumple_ans  = sla >= 99.9
    sla_card_cl = 'verde' if sla >= 99.9 else ('naranja' if sla >= 95 else 'rojo')
    sla_color_v = '#1D9E75' if sla >= 99.9 else ('#F39C12' if sla >= 95 else '#E74C3C')
    err_card_cl = 'verde' if pct_err < 5 else 'rojo'
    err_color_v = '#1D9E75' if pct_err < 5 else '#E74C3C'
    to_card_cl  = 'verde' if pct_to < 5 else 'rojo'
    to_color_v  = '#1D9E75' if pct_to < 5 else '#E74C3C'

    logo_html = (f"<img src='{logo_src}' style='height:44px;'>"
                 if logo_src else "<div style='font-size:22px;font-weight:800;color:#3C3489;'>ATP</div>")

    gauge_label = ('🟢 Tasa de éxito por encima del ANS contractual (99.9%)' if sla >= 99.9
                   else ('🟡 Tasa de éxito por debajo del ANS — revisar operación' if sla >= 95
                         else '🔴 CRÍTICO — activar protocolo de escalamiento'))

    img = lambda b64: (f"<img src='data:image/png;base64,{b64}' style='width:100%;'>" if b64
                       else "<p style='color:#aaa;text-align:center;padding:40px 0;'>Sin datos</p>")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Reporte Ejecutivo — Portal ATP NOC</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0;}}
  body{{font-family:'Inter',sans-serif;background:#EEF2F7;color:#2C3E50;}}
  .page{{max-width:1100px;margin:0 auto;padding:24px;}}
  .header{{background:white;border-radius:12px;padding:20px 28px;
           display:flex;justify-content:space-between;align-items:center;
           box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:16px;
           border-top:4px solid #3C3489;}}
  .header-title{{font-size:20px;font-weight:700;color:#2C3E50;}}
  .header-sub{{font-size:12px;color:#888;margin-top:4px;}}
  .operador-badge{{background:#3C3489;color:white;padding:6px 16px;
                   border-radius:20px;font-size:14px;font-weight:600;}}
  .estado-banner{{background:{estado_bg};border:1.5px solid {estado_color};
                  border-radius:10px;padding:14px 24px;margin-bottom:16px;
                  display:flex;align-items:center;gap:16px;}}
  .estado-label{{font-size:18px;font-weight:700;color:{estado_color};}}
  .estado-info{{font-size:12px;color:#666;}}
  .kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px;}}
  .kpi-card{{background:white;border-radius:10px;padding:18px;
             box-shadow:0 2px 6px rgba(0,0,0,.07);text-align:center;border-top:3px solid #E0E0E0;}}
  .kpi-card.verde{{border-top-color:#1D9E75;}}
  .kpi-card.rojo{{border-top-color:#E74C3C;}}
  .kpi-card.naranja{{border-top-color:#F39C12;}}
  .kpi-card.morado{{border-top-color:#3C3489;}}
  .kpi-val{{font-size:30px;font-weight:700;line-height:1;margin:6px 0;}}
  .kpi-label{{font-size:11px;color:#888;font-weight:500;text-transform:uppercase;letter-spacing:.5px;}}
  .kpi-sub{{font-size:10px;color:#aaa;margin-top:4px;}}
  .ans-badge{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;}}
  .ans-ok{{background:#DCFCE7;color:#166534;}}
  .ans-ko{{background:#FEE2E2;color:#991B1B;}}
  .section{{background:white;border-radius:10px;padding:20px 24px;
            box-shadow:0 2px 6px rgba(0,0,0,.07);margin-bottom:16px;}}
  .section-title{{font-size:14px;font-weight:700;color:#2C3E50;
                  border-left:4px solid #3C3489;padding-left:10px;
                  margin-bottom:16px;text-transform:uppercase;letter-spacing:.3px;}}
  .grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}}
  table{{width:100%;border-collapse:collapse;}}
  th{{background:#F8FAFC;font-size:11px;font-weight:600;text-transform:uppercase;
     letter-spacing:.3px;padding:10px 12px;text-align:left;
     border-bottom:2px solid #E8ECF0;color:#666;}}
  td{{padding:9px 12px;border-bottom:1px solid #F0F4F8;font-size:12px;}}
  tr:last-child td{{border-bottom:none;}}
  .footer{{text-align:center;font-size:10px;color:#aaa;margin-top:20px;padding:12px;}}
  .gauge-container{{display:flex;justify-content:center;padding:10px 0;}}
  @media print{{body{{background:white;}} .page{{padding:0;}}}}
</style>
</head>
<body>
<div class="page">

  <div class="header">
    <div style="display:flex;align-items:center;gap:18px;">
      {logo_html}
      <div>
        <div class="header-title">PORTAL NOC — REPORTE EJECUTIVO DE OPERACIÓN</div>
        <div class="header-sub">Orquestador de Telecomunicaciones — Red Neutra ATP Fiber Colombia</div>
      </div>
    </div>
    <div style="text-align:right;">
      <div class="operador-badge">{operador}</div>
      <div style="font-size:11px;color:#888;margin-top:6px;">{periodo_str}</div>
      <div style="font-size:10px;color:#aaa;">Generado: {ts_gen}</div>
    </div>
  </div>

  <div class="estado-banner">
    <div>
      <div class="estado-label">{estado_label}</div>
      <div class="estado-info">ANS Contractual: Disponibilidad mensual ≥ 99.9% |
        CRÍTICO: respuesta 15 min, restablecimiento 3 h</div>
    </div>
    <div style="margin-left:auto;">
      <span class="ans-badge {'ans-ok' if cumple_ans else 'ans-ko'}">
        {'✅ CUMPLE ANS' if cumple_ans else '⚠️ INCUMPLE ANS'}
      </span>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card morado">
      <div class="kpi-label">Total Transacciones</div>
      <div class="kpi-val" style="color:#3C3489;">{total_tx:,}</div>
      <div class="kpi-sub">Período analizado</div>
    </div>
    <div class="kpi-card {sla_card_cl}">
      <div class="kpi-label">Tasa de Éxito</div>
      <div class="kpi-val" style="color:{sla_color_v};">{sla:.2f}%</div>
      <div class="kpi-sub">ANS mínimo: 99.9%</div>
    </div>
    <div class="kpi-card {err_card_cl}">
      <div class="kpi-label">% Error</div>
      <div class="kpi-val" style="color:{err_color_v};">{pct_err:.2f}%</div>
      <div class="kpi-sub">{total_fal:,} fallas en período</div>
    </div>
    <div class="kpi-card {to_card_cl}">
      <div class="kpi-label">% Timeouts</div>
      <div class="kpi-val" style="color:{to_color_v};">{pct_to:.2f}%</div>
      <div class="kpi-sub">Umbral alerta: 5%</div>
    </div>
  </div>

  <div class="grid-2">
    <div class="section">
      <div class="section-title">Indicador Tasa de Éxito</div>
      <div class="gauge-container">{gauge_sla}</div>
      <div style="text-align:center;margin-top:8px;">
        <div style="font-size:11px;color:#888;">{gauge_label}</div>
      </div>
    </div>
    <div class="section">
      <div class="section-title">Composición de Transacciones</div>
      {img(b64_donut)}
    </div>
  </div>

  {"<div class='section'><div class='section-title'>Tasa de Éxito por Proceso vs ANS Contractual</div>" + img(b64_barras) + "</div>" if b64_barras else ""}
  {"<div class='section'><div class='section-title'>Evolución Temporal — Procesos Críticos</div>" + img(b64_tiempo) + "</div>" if b64_tiempo else ""}

  <div class="section">
    <div class="section-title">Consolidado por Proceso</div>
    <table>
      <thead>
        <tr>
          <th>Proceso</th><th style="text-align:right;">Total TX</th>
          <th style="text-align:right;">Exitosas</th><th style="text-align:right;">Fallas</th>
          <th style="text-align:right;">Tasa de Éxito</th><th style="text-align:right;">% Error</th>
        </tr>
      </thead>
      <tbody>
        {filas_tabla}
        <tr style="background:#F8FAFC;font-weight:700;border-top:2px solid #E0E0E0;">
          <td>TOTALES</td>
          <td style="text-align:right;">{total_tx:,}</td>
          <td style="text-align:right;color:#1D9E75;">{total_ok:,}</td>
          <td style="text-align:right;color:#E74C3C;">{total_fal:,}</td>
          <td style="text-align:right;color:{sla_color_v};">{sla:.2f}%</td>
          <td style="text-align:right;">{pct_err:.2f}%</td>
        </tr>
      </tbody>
    </table>
  </div>

  {"<div class='section'><div class='section-title'>Top Fallas Técnicas</div>" + img(b64_errores) + "</div>" if b64_errores else ""}

  {bloque_alertas}

  <div class="section">
    <div class="section-title">Niveles de ANS Contractual (Tecnotree)</div>
    <table>
      <thead>
        <tr><th>Criticidad</th><th>T. Respuesta</th><th>T. Restablecimiento</th>
            <th>Solución Definitiva</th><th>Umbral Plan Mejora</th></tr>
      </thead>
      <tbody>
        <tr><td><span style="color:#E74C3C;font-weight:700;">🔴 CRÍTICO</span></td>
            <td>15 minutos</td><td>3 horas</td><td>2 días calendario</td><td>≥ 2 fallas/mes</td></tr>
        <tr><td><span style="color:#F39C12;font-weight:700;">🟠 SERIO</span></td>
            <td>15 minutos</td><td>8 horas</td><td>7 días calendario</td><td>≥ 4 fallas/mes</td></tr>
        <tr><td><span style="color:#FFD700;font-weight:700;">🟡 MEDIO</span></td>
            <td>8 horas</td><td>5 días</td><td>30 días calendario</td><td>≥ 4 fallas/mes</td></tr>
        <tr><td><span style="color:#1D9E75;font-weight:700;">🟢 BAJO</span></td>
            <td>24 horas</td><td>30 días</td><td>90 días calendario</td><td>N/A</td></tr>
      </tbody>
    </table>
  </div>

  <div class="footer">
    Reporte generado automáticamente por Portal NOC ATP — Gerencia Fibra / Dirección Ingeniería<br>
    {ts_gen} | {periodo_str} | Operador: {operador}
  </div>

</div>
</body>
</html>"""

    return html