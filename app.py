import json
import os
import re

import gradio as gr
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent as create_react_agent
from tavily import TavilyClient

from prompts import CHAT_SYSTEM_TEMPLATE, TOS_ANALYSIS_PROMPT
from tools import extract_pdf_text, fetch_url_content

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.2,
)

# ── Agent tool ────────────────────────────────────────────────────────────────
@tool
def search_web(query: str) -> str:
    """Search the web for information about a company's privacy record, data breaches, fines, or legal issues."""
    try:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(query, max_results=5, search_depth="basic")
        results = response.get("results", [])
        if not results:
            return "No results found."
        return "\n\n".join(
            f"**{r['title']}**\n{r['content']}\nURL: {r['url']}"
            for r in results
        )
    except Exception as e:
        return f"Search failed: {e}"


TOOLS = [search_web]

# ── Analysis engine ───────────────────────────────────────────────────────────
def analyze_tos(tos_text: str, service_name: str) -> dict:
    prompt = TOS_ANALYSIS_PROMPT.format(
        service_name=service_name or "Servicio Desconocido",
        tos_text=tos_text[:35_000],
    )
    try:
        response = llm.invoke(prompt)
    except Exception as e:
        return {"error": f"AI model error: {e}"}
    raw = response.content

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"error": "No se pudo procesar el análisis", "raw": raw[:500]}


# ── HTML formatter ────────────────────────────────────────────────────────────
GRADE_COLORS = {
    "A": ("#059669", "#ecfdf5"),
    "B": ("#65a30d", "#f7fee7"),
    "C": ("#d97706", "#fffbeb"),
    "D": ("#ea580c", "#fff7ed"),
    "F": ("#dc2626", "#fef2f2"),
}


def _severity_badge(sev: str) -> str:
    colors = {"high": "#ff4444", "medium": "#ffbb00", "low": "#00cc88"}
    c = colors.get(sev.lower(), "#888")
    return f'<span style="background:{c}15;color:{c};border:1px solid {c}40;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:600;text-transform:uppercase">{sev}</span>'


def _item_row(icon: str, title: str, detail: str, quote: str = "", badge: str = "") -> str:
    q = f'<blockquote style="margin:6px 0 0 0;padding:6px 10px;border-left:3px solid #3b82f620;color:#64748b;font-size:12px;font-style:italic">{quote}</blockquote>' if quote else ""
    return f"""
    <div style="padding:12px 0;border-bottom:1px solid #e2e8f0">
      <div style="display:flex;align-items:flex-start;gap:10px">
        <span style="font-size:18px;margin-top:1px">{icon}</span>
        <div style="flex:1">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
            <span style="font-weight:600;color:#1e293b">{title}</span>
            {badge}
          </div>
          <p style="margin:4px 0 0 0;color:#475569;font-size:13px;line-height:1.5">{detail}</p>
          {q}
        </div>
      </div>
    </div>"""


def _section_card(title: str, icon: str, accent: str, body: str) -> str:
    return f"""
    <div style="background:#ffffff;border:1px solid #e2e8f0;border-top:3px solid {accent};border-radius:12px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06)">
      <h3 style="margin:0 0 12px 0;color:{accent};font-size:15px;display:flex;align-items:center;gap:8px">
        {icon} {title}
      </h3>
      {body}
    </div>"""


def format_analysis_html(data: dict) -> str:
    if "error" in data:
        return f'<div style="background:#fef2f2;border:1px solid #fca5a5;border-radius:12px;padding:20px;color:#991b1b">❌ {data["error"]}</div>'

    grade = data.get("overall_score", "?")
    fg, bg = GRADE_COLORS.get(grade, ("#888", "#1a1a2e"))

    # ── Header ────────────────────────────────────────────────────────────────
    header = f"""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;flex-wrap:wrap;gap:16px">
      <div>
        <h2 style="margin:0;font-size:24px;color:#0f172a">{data.get('service_name','')}</h2>
        <p style="margin:6px 0 0 0;color:#64748b;font-size:14px">{data.get('tldr','')}</p>
      </div>
      <div style="text-align:center;background:{bg};border:2px solid {fg};border-radius:16px;padding:12px 24px;min-width:90px">
        <div style="font-size:48px;font-weight:900;color:{fg};line-height:1">{grade}</div>
        <div style="font-size:11px;color:{fg};text-transform:uppercase;letter-spacing:1px;margin-top:4px">Puntuación de Privacidad</div>
      </div>
    </div>
    <div style="background:#f8fafc;border-left:4px solid {fg};border-radius:8px;padding:14px 18px;margin-bottom:20px;color:#334155;font-size:14px;line-height:1.6">
      {data.get('overall_summary','')}
      <br><br><em style="color:#94a3b8;font-size:12px">{data.get('score_reasoning','')}</em>
    </div>"""

    # ── Red Flags ─────────────────────────────────────────────────────────────
    red_flags_html = ""
    for rf in data.get("red_flags", []):
        red_flags_html += _item_row("🚩", rf.get("title",""), rf.get("detail",""), rf.get("quote",""), _severity_badge(rf.get("severity","medium")))
    red_section = _section_card("Alertas Rojas", "🔴", "#ff4444", red_flags_html or "<p style='color:#666'>Ninguna identificada.</p>")

    # ── Data Collected ────────────────────────────────────────────────────────
    data_html = ""
    for dc in data.get("data_collected", []):
        shared = f'<span style="color:#b45309;font-size:12px">Compartido con: {dc.get("shared_with","?")}</span>'
        data_html += _item_row("📊", dc.get("category",""), dc.get("detail",""), badge=shared)
    data_section = _section_card("Datos Recopilados", "📊", "#4466ff", data_html or "<p style='color:#666'>No especificado.</p>")

    # ── Rights Given Up ───────────────────────────────────────────────────────
    rights_html = ""
    for r in data.get("rights_you_give_up", []):
        rights_html += _item_row("⚖️", r.get("right",""), r.get("detail",""), r.get("quote",""))
    rights_section = _section_card("Derechos que Cedes", "⚖️", "#ff8800", rights_html or "<p style='color:#666'>Ninguno identificado.</p>")

    # ── Financial Traps ───────────────────────────────────────────────────────
    fin_html = ""
    for ft in data.get("financial_traps", []):
        fin_html += _item_row("💰", ft.get("title",""), ft.get("detail",""), ft.get("quote",""))
    fin_section = _section_card("Trampas Financieras", "💰", "#ffbb00", fin_html or "<p style='color:#666'>Ninguna identificada.</p>")

    # ── Data Retention + Jurisdiction ────────────────────────────────────────
    dr = data.get("data_retention", {})
    jur = data.get("jurisdiction", {})
    arb = "✅ Sí" if jur.get("arbitration") else "❌ No"
    caw = "✅ Sí" if jur.get("class_action_waiver") else "❌ No"
    meta_body = f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div>
        <p style="color:#64748b;font-size:11px;margin:0 0 4px 0;text-transform:uppercase;letter-spacing:1px">Retención de Datos</p>
        <p style="color:#0f172a;margin:0 0 4px 0;font-weight:600">{dr.get('duration','No especificado')}</p>
        <p style="color:#475569;font-size:13px;margin:0">{dr.get('detail','')}</p>
      </div>
      <div>
        <p style="color:#64748b;font-size:11px;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:1px">Jurisdicción</p>
        <p style="color:#0f172a;margin:0 0 4px 0;font-weight:600">{jur.get('governing_law','No especificado')}</p>
        <p style="color:#475569;font-size:12px;margin:0">Arbitraje obligatorio: {arb} &nbsp;|&nbsp; Sin demandas colectivas: {caw}</p>
      </div>
    </div>"""
    meta_section = _section_card("Retención & Jurisdicción", "📅", "#00cc88", meta_body)

    # ── Positives ─────────────────────────────────────────────────────────────
    pos_items = "".join(f'<li style="color:#475569;font-size:13px;margin-bottom:6px">{p}</li>' for p in data.get("positives", []))
    pos_section = _section_card("Aspectos Positivos", "✅", "#059669", f'<ul style="margin:0;padding-left:20px">{pos_items}</ul>' if pos_items else "<p style='color:#94a3b8'>Ninguno identificado.</p>")

    return f'<div style="font-family:Inter,sans-serif;max-width:100%;color:#1e293b">{header}{red_section}{data_section}{rights_section}{fin_section}{meta_section}{pos_section}</div>'


# ── Chat agent ────────────────────────────────────────────────────────────────
def build_agent(system_prompt: str):
    """Create a LangGraph react agent with the given system prompt."""
    return create_react_agent(llm, TOOLS, system_prompt=system_prompt)


def chat_respond(message, history, tos_text, analysis_data):
    if not tos_text:
        history.append({"role": "assistant", "content": "⚠️ Primero analiza un documento de Términos de Servicio usando el panel de arriba."})
        return "", history

    analysis_summary = json.dumps(analysis_data, ensure_ascii=False, indent=2)[:4000] if analysis_data else "{}"
    service_name = analysis_data.get("service_name", "Desconocido") if analysis_data else "Desconocido"

    system_prompt = CHAT_SYSTEM_TEMPLATE.format(
        service_name=service_name,
        tos_context=tos_text[:20_000],
        analysis_summary=analysis_summary,
    )

    # Build message list: system + history + new user message
    messages = [SystemMessage(content=system_prompt)]
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=message))

    agent = build_agent(system_prompt)
    try:
        result = agent.invoke({"messages": messages})
        last = result["messages"][-1]
        reply = last.content if hasattr(last, "content") else str(last)
    except Exception as e:
        reply = f"Error al procesar: {e}"

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": reply})
    return "", history


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

*, body, .gradio-container { font-family: 'Inter', sans-serif !important; color: #0f172a !important; }
.gradio-container { background: #f8fafc !important; }

.rtdt-header {
    text-align: center;
    padding: 40px 20px 24px;
    background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
    border-bottom: 1px solid #e2e8f0;
    margin-bottom: 8px;
}
.rtdt-logo {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 4px;
    color: #dc2626;
    text-transform: uppercase;
    margin-bottom: 12px;
}
.rtdt-title {
    font-size: 42px;
    font-weight: 900;
    color: #0f172a;
    margin: 0 0 8px 0;
    letter-spacing: -1px;
}
.rtdt-title span { color: #dc2626; }
.rtdt-subtitle {
    color: #64748b;
    font-size: 15px;
    margin: 0;
}

.input-panel {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 8px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
}

.analyze-btn {
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    border: none !important;
    border-radius: 12px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    padding: 14px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 14px rgba(220,38,38,0.25) !important;
}
.analyze-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(220,38,38,0.35) !important;
}

.section-label {
    color: #475569;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    padding: 16px 0 8px 0;
}

/* Chatbot */
.chatbot-wrap { border: 1px solid #e2e8f0 !important; border-radius: 16px !important; background: #ffffff !important; }

/* Tabs */
.tab-nav button { color: #64748b !important; border-bottom: 2px solid transparent !important; }
.tab-nav button.selected { color: #dc2626 !important; border-bottom: 2px solid #dc2626 !important; }

/* Inputs */
input[type=text], textarea {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    color: #0f172a !important;
    border-radius: 8px !important;
}
input[type=text]:focus, textarea:focus { border-color: #3b82f6 !important; }
"""


# ── UI ────────────────────────────────────────────────────────────────────────
def run_url(url, svc):
    if not url.strip():
        yield gr.update(), gr.update(visible=False), gr.update(visible=False), "", {}
        return
        
    loading_html = '<div style="padding:40px;text-align:center;color:#64748b;font-family:Inter,sans-serif"><h3 style="margin:0;color:#0f172a">⏳ Analizando...</h3><p style="margin:8px 0 0 0">Leyendo y procesando el documento, esto puede tomar unos segundos.</p></div>'
    yield gr.update(value=loading_html, visible=True), gr.update(visible=False), gr.update(visible=False), "", {}

    text, err = fetch_url_content(url)
    if err:
        html = f'<div style="background:#2e0d0d;border:1px solid #ff4444;border-radius:12px;padding:20px;color:#ff8888;font-family:Inter,sans-serif">❌ {err}</div>'
        yield gr.update(value=html, visible=True), gr.update(visible=False), gr.update(visible=False), "", {}
        return
        
    data = analyze_tos(text, svc or url)
    yield gr.update(value=format_analysis_html(data), visible=True), gr.update(visible=True), gr.update(visible=True), text, data


def run_text(raw, svc):
    if not raw.strip():
        yield gr.update(), gr.update(visible=False), gr.update(visible=False), "", {}
        return
        
    loading_html = '<div style="padding:40px;text-align:center;color:#64748b;font-family:Inter,sans-serif"><h3 style="margin:0;color:#0f172a">⏳ Analizando...</h3><p style="margin:8px 0 0 0">Leyendo y procesando el documento, esto puede tomar unos segundos.</p></div>'
    yield gr.update(value=loading_html, visible=True), gr.update(visible=False), gr.update(visible=False), "", {}

    data = analyze_tos(raw, svc or "Documento Pegado")
    yield gr.update(value=format_analysis_html(data), visible=True), gr.update(visible=True), gr.update(visible=True), raw, data


def run_pdf(pdf_file, svc):
    if pdf_file is None:
        yield gr.update(), gr.update(visible=False), gr.update(visible=False), "", {}
        return
        
    loading_html = '<div style="padding:40px;text-align:center;color:#64748b;font-family:Inter,sans-serif"><h3 style="margin:0;color:#0f172a">⏳ Analizando...</h3><p style="margin:8px 0 0 0">Leyendo y procesando el documento, esto puede tomar unos segundos.</p></div>'
    yield gr.update(value=loading_html, visible=True), gr.update(visible=False), gr.update(visible=False), "", {}

    with open(pdf_file, "rb") as f:
        raw_bytes = f.read()
    text, err = extract_pdf_text(raw_bytes)
    if err:
        html = f'<div style="background:#2e0d0d;border:1px solid #ff4444;border-radius:12px;padding:20px;color:#ff8888;font-family:Inter,sans-serif">❌ {err}</div>'
        yield gr.update(value=html, visible=True), gr.update(visible=False), gr.update(visible=False), "", {}
        return
        
    data = analyze_tos(text, svc or "PDF Subido")
    yield gr.update(value=format_analysis_html(data), visible=True), gr.update(visible=True), gr.update(visible=True), text, data


with gr.Blocks(title="RTDT — ReadTheDamnTerms") as demo:
    tos_state = gr.State("")
    analysis_state = gr.State({})

    # ── Header ────────────────────────────────────────────────────────────────
    gr.HTML("""
    <div class="rtdt-header">
        <div class="rtdt-logo">RTDT</div>
        <h1 class="rtdt-title">Read<span>The</span>DamnTerms</h1>
        <p class="rtdt-subtitle">Deja de aceptar a ciegas. Conoce exactamente a qué estás accediendo.</p>
    </div>
    """)


    # ── Input ─────────────────────────────────────────────────────────────────
    with gr.Group(elem_classes="input-panel"):
        with gr.Tabs():
            with gr.TabItem("🌐 URL"):
                url_input = gr.Textbox(label="URL de Términos de Servicio", placeholder="https://ejemplo.com/terminos", show_label=True)
                svc_url = gr.Textbox(label="Nombre del servicio (opcional)", placeholder="ej. Spotify")
                btn_url = gr.Button("🔍 Analizar Términos", elem_classes="analyze-btn")

            with gr.TabItem("📋 Pegar Texto"):
                text_input = gr.Textbox(label="Pega el texto de los Términos de Servicio", lines=10, placeholder="Pega el texto completo de los ToS / Política de Privacidad aquí...")
                svc_text = gr.Textbox(label="Nombre del servicio (opcional)", placeholder="ej. Netflix")
                btn_text = gr.Button("🔍 Analizar Términos", elem_classes="analyze-btn")

            with gr.TabItem("📄 Subir PDF"):
                pdf_input = gr.File(label="Subir PDF", file_types=[".pdf"])
                svc_pdf = gr.Textbox(label="Nombre del servicio (opcional)", placeholder="ej. OpenAI")
                btn_pdf = gr.Button("🔍 Analizar Términos", elem_classes="analyze-btn")

    # ── Report ────────────────────────────────────────────────────────────────
    gr.HTML('<div class="section-label">📋 Reporte de Análisis</div>')
    report_html = gr.HTML(visible=False)

    # ── Chat ──────────────────────────────────────────────────────────────────
    gr.HTML('<div class="section-label">💬 Haz preguntas de seguimiento</div>')
    with gr.Group(visible=False) as chat_group:
        chatbot = gr.Chatbot(
            label="Chatea con RTDT",
            height=400,
            elem_classes="chatbot-wrap",
        )
        with gr.Row():
            chat_input = gr.Textbox(label="", placeholder="Pregunta sobre cláusulas específicas, tus derechos, uso de datos...", scale=5, show_label=False)
            send_btn = gr.Button("Enviar →", scale=1, variant="primary")

    chat_vis = gr.Column(visible=False)  # dummy to track visibility

    # ── Events ────────────────────────────────────────────────────────────────
    common_outputs = [report_html, chat_group, chat_vis, tos_state, analysis_state]

    btn_url.click(run_url, inputs=[url_input, svc_url], outputs=common_outputs)
    btn_text.click(run_text, inputs=[text_input, svc_text], outputs=common_outputs)
    btn_pdf.click(run_pdf, inputs=[pdf_input, svc_pdf], outputs=common_outputs)

    send_btn.click(chat_respond, inputs=[chat_input, chatbot, tos_state, analysis_state], outputs=[chat_input, chatbot])
    chat_input.submit(chat_respond, inputs=[chat_input, chatbot, tos_state, analysis_state], outputs=[chat_input, chatbot])


if __name__ == "__main__":
    custom_theme = gr.themes.Default().set(
        block_background_fill="white",
        block_background_fill_dark="white",
        panel_background_fill="white",
        panel_background_fill_dark="white"
    )
    demo.launch(css=CSS, theme=custom_theme)
