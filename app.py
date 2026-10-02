"""
Pirajá · Entero
Plataforma de análise epidemiológica de exames parasitológicos —
módulo de parasitos intestinais (exames de fezes e lâmina/fita adesiva).

Rodar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analysis_engine import (
    METHOD_CATALOG,
    PARASITE_MAP,
    PATOGENICOS,
    COMENSAIS,
    build_per_child,
    compute_metrics,
    get_active_methods,
    normalize_columns,
    validate_columns,
)
from report_pdf import build_pdf_report

APP_DIR = Path(__file__).parent

# ----------------------------------------------------------------
# Identidade visual Pirajá — paleta "Mata, barro e papel"
# ----------------------------------------------------------------
BRAND_DIR = APP_DIR / "brand"
LOGO_PDF_PATH = BRAND_DIR / "piraja-entero-cor.png"        # cabeçalho do PDF
FAVICON_PATH = BRAND_DIR / "piraja-favicon.png"             # ícone da aba do navegador
LOGO_SIDEBAR_SVG = BRAND_DIR / "piraja-entero-negativo.svg" # sidebar (fundo verde-mata)

MATA = "#11483D"          # verde-mata — principal
FOLHA = "#328567"         # verde-folha — secundária
COBRE = "#9C4A2F"         # cobre — acento do módulo Entero
COBRE_CLARO = "#D08A6A"   # cobre claro — acento sobre fundo escuro
PAPEL = "#F4F1EA"         # papel — fundos
TINTA = "#1B2421"         # tinta — texto corrido

BG = PAPEL
SURFACE = "#FBF9F4"
INK = TINTA
INK_SOFT = "#4E5B55"
INK_FAINT = "#7A857F"
TEAL = FOLHA
TEAL_DARK = MATA
TEAL_TINT = "#E3EEE8"
BRICK = COBRE
BRICK_TINT = "#F3E4DB"
SAGE = "#A9C3B8"          # neutro esverdeado (categorias sem classificação)
LINE = "#DCD6C8"
MATA_DOT = "#1F6150"      # pontos do padrão "Campo" sobre verde-mata


def _svg_data_uri(path):
    import base64
    try:
        return "data:image/svg+xml;base64," + base64.b64encode(Path(path).read_bytes()).decode()
    except OSError:
        return ""


LOGO_SIDEBAR_URI = _svg_data_uri(LOGO_SIDEBAR_SVG)

st.set_page_config(
    page_title="Pirajá · Painel de análise epidemiológica",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------
# CSS de marca
# ----------------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Instrument+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"]  {{
        font-family: 'Instrument Sans', sans-serif;
        color: {INK};
    }}
    .stApp {{
        background-color: {BG};
    }}
    h1, h2, h3 {{
        font-family: 'Fraunces', serif !important;
        color: {TEAL_DARK} !important;
    }}
    /* ----- reforço de contraste: TODO texto renderizado pelo Streamlit -----
       O Streamlit pode aplicar automaticamente um tema escuro conforme a
       preferência do sistema operacional/navegador do usuário. Nesse caso a
       cor de texto herdada da regra genérica acima (html, body, [class*="css"])
       pode ser sobrescrita por um texto claro, enquanto os fundos abaixo
       continuam claros (fixados manualmente) — resultando em texto invisível.

       IMPORTANTE: st.markdown('<div class="pj-step-wrap">', ...) e o
       st.write(...) / st.markdown('</div>', ...) que vêm depois são chamadas
       SEPARADAS — cada uma gera seu próprio bloco no DOM, como elementos
       IRMÃOS, não um dentro do outro. A div de marca não chega a "abraçar" de
       fato o texto entre a abertura e o fechamento, então seletores do tipo
       ".pj-step-wrap p" NÃO alcançam esse texto. Por isso as regras
       abaixo miram diretamente os contêineres que o Streamlit usa para
       QUALQUER texto (st.write, st.markdown, st.caption), não os nossos
       contêineres de marca — funciona não importa como o HTML foi quebrado. */
    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] small,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] em,
    [data-testid="stMarkdownContainer"] u,
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p,
    [data-testid="stCaptionContainer"] small,
    [data-testid="stText"] {{
        color: {INK_SOFT} !important;
    }}
    [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], [data-testid="stText"],
    [data-testid="stWidgetLabel"], [data-testid="stFileUploader"], [data-testid="stDataFrame"],
    [data-testid="stAlert"], [data-testid="stExpander"] summary {{
        font-family: 'Instrument Sans', sans-serif;
    }}
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4 {{
        color: {TEAL_DARK} !important;
    }}
    /* elementos de marca com cor própria (sobrescrevem a regra genérica acima
       por especificidade/ordem — mantidos explicitamente) */
    .pj-card p, .pj-note {{
        color: {INK_SOFT} !important;
    }}
    .pj-topbar .name, .pj-section-title, .pj-section-subtitle,
    .pj-step .step-title {{
        color: {TEAL_DARK} !important;
    }}
    .pj-section-caption, .pj-topbar .sub, .pj-card .kicker {{
        color: {INK_FAINT} !important;
    }}
    /* ----- eyebrow / section labels ----- */
    .pj-eyebrow {{
        font-family: 'Instrument Sans', sans-serif;
        font-weight: 600;
        font-size: 12px;
        letter-spacing: .14em;
        text-transform: uppercase;
        color: {BRICK} !important;
    }}

    /* ----- top brand bar ----- */
    .pj-topbar {{
        display:flex; align-items:baseline; justify-content:space-between; gap:14px;
        padding: 4px 0 16px 0;
        border-bottom: 1px solid {LINE};
        margin-bottom: 22px;
    }}
    .pj-topbar .name {{
        font-family:'Fraunces', serif; font-weight:600; font-size: 22px; color:{TEAL_DARK};
        line-height:1.15;
    }}
    .pj-topbar .sub {{
        font-family:'Instrument Sans', sans-serif; font-weight:600; font-size:11.5px;
        letter-spacing:.14em; color:{INK_FAINT}; text-transform:uppercase;
    }}

    /* ----- hero (verde-mata + padrão "Campo") ----- */
    .pj-hero {{
        position: relative; overflow: hidden;
        background: {MATA};
        border-radius: 14px;
        padding: 36px 40px;
        margin-bottom: 22px;
    }}
    .pj-hero::before {{
        content: ""; position: absolute; inset: 0; pointer-events: none;
        background-image: radial-gradient(circle, {MATA_DOT} 3.2px, transparent 3.8px);
        background-size: 26px 26px;
        background-position: 13px 13px;
        -webkit-mask-image: linear-gradient(to left, #000 15%, transparent 70%);
                mask-image: linear-gradient(to left, #000 15%, transparent 70%);
    }}
    .pj-hero .pj-hero-cluster {{
        position: absolute; right: 34px; top: 26px; width: 120px; height: 90px; pointer-events: none;
    }}
    .pj-hero > *:not(.pj-hero-cluster) {{ position: relative; }}
    [data-testid="stMarkdownContainer"] .pj-hero .pj-eyebrow {{ color: {COBRE_CLARO} !important; }}
    [data-testid="stMarkdownContainer"] .pj-hero h2 * {{ color: {PAPEL} !important; }}
    [data-testid="stMarkdownContainer"] .pj-hero h2 {{
        color: {PAPEL} !important;
        margin: 6px 0 12px 0 !important;
        font-size: 32px !important; font-weight: 500 !important; line-height: 1.15 !important;
        max-width: 760px;
    }}
    [data-testid="stMarkdownContainer"] .pj-hero p {{
        color: rgba(244, 241, 234, .82) !important;
        font-size: 15.5px; max-width: 720px; margin-bottom: 0; line-height: 1.6;
    }}

    /* ----- generic section card ----- */
    .pj-card {{
        background: {SURFACE};
        border: 1px solid {LINE};
        border-radius: 14px;
        padding: 18px 20px;
        height: 100%;
    }}
    .pj-card .kicker {{
        font-family:'Instrument Sans', sans-serif; font-weight:600; font-size: 11.5px; letter-spacing:.12em;
        text-transform:uppercase; color:{INK_FAINT} !important; margin-bottom: 10px; display:block;
    }}

    /* ----- step header (numbered badge + title) ----- */
    .pj-step {{
        display:flex; align-items:center; gap:12px; margin: 6px 0 2px 0;
    }}
    .pj-step .badge {{
        flex: 0 0 auto;
        width: 34px; height: 34px; border-radius: 50%;
        background: {TEAL_DARK}; color: {PAPEL} !important;
        font-family:'Fraunces', serif; font-weight:600; font-size: 16px;
        display:flex; align-items:center; justify-content:center;
    }}
    .pj-step .step-title {{
        font-family:'Fraunces', serif; font-weight:600; color:{TEAL_DARK}; font-size: 22px;
    }}
    /* Os passos usam st.container(border=True) — esse é o contêiner que de fato
       envolve o conteúdo no DOM (ver nota acima sobre divs abertas/fechadas em
       chamadas separadas). A div .pj-step-wrap fica só como marcador e é
       escondida para não desenhar um cartão vazio. */
    .pj-step-wrap {{ display: none; }}
    [data-testid="stElementContainer"]:has(.pj-step-wrap) {{ display: none; }}
    [data-testid="stVerticalBlockBorderWrapper"]:has(.pj-step-wrap),
    [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .pj-step-wrap) {{
        background: {SURFACE};
        border: 1px solid {LINE} !important;
        border-radius: 14px !important;
        padding: 22px 24px 24px 24px;
    }}

    /* ----- metrics ----- */
    div[data-testid="stMetric"] {{
        background: {SURFACE};
        border: 1px solid {LINE};
        padding: 16px 18px;
        border-radius: 12px;
    }}
    div[data-testid="stMetric"] label {{
        font-family: 'Instrument Sans', sans-serif !important;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px !important;
        letter-spacing: .1em;
        color: {INK_FAINT} !important;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        font-family: 'Fraunces', serif !important;
        font-weight: 600;
        color: {TEAL_DARK} !important;
    }}

    /* ----- buttons -----
       Reforço extra aqui: o texto do botão passa por [data-testid="stMarkdownContainer"]
       internamente (mesmo elemento usado pelo texto solto da página), então sem uma
       regra MAIS específica que essa, ele herdaria a cor escura das regras genéricas
       acima e ficaria quase invisível sobre o fundo verde-escuro do botão. As regras
       abaixo miram o texto e o ícone do botão diretamente, com prioridade máxima. */
    .stDownloadButton button, .stButton button {{
        background-color: {TEAL_DARK};
        color: {PAPEL} !important;
        border: 1px solid {TEAL_DARK};
        font-family: 'Instrument Sans', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        font-size: 13.5px;
    }}
    .stDownloadButton button p, .stButton button p,
    .stDownloadButton button span, .stButton button span,
    .stDownloadButton button div, .stButton button div,
    .stDownloadButton button [data-testid="stMarkdownContainer"],
    .stDownloadButton button [data-testid="stMarkdownContainer"] p,
    .stButton button [data-testid="stMarkdownContainer"],
    .stButton button [data-testid="stMarkdownContainer"] p {{
        color: {PAPEL} !important;
    }}
    .stDownloadButton button svg, .stButton button svg {{
        fill: {PAPEL} !important;
        color: {PAPEL} !important;
    }}
    .stDownloadButton button:hover, .stButton button:hover {{
        background-color: {TEAL};
        border-color: {TEAL};
        color: {PAPEL} !important;
    }}
    .stDownloadButton button:hover p, .stButton button:hover p,
    .stDownloadButton button:hover span, .stButton button:hover span,
    .stDownloadButton button:hover [data-testid="stMarkdownContainer"] p,
    .stButton button:hover [data-testid="stMarkdownContainer"] p {{
        color: {PAPEL} !important;
    }}

    /* ----- tags ----- */
    .pj-tag {{
        display:inline-block; font-family:'Instrument Sans', sans-serif; font-weight:500; font-size:12.5px;
        padding:3px 11px; margin:2px; border-radius:999px; border:1px solid;
    }}

    /* ----- notes ----- */
    .pj-note {{
        background: {BRICK_TINT}; border-left: 3px solid {BRICK};
        padding: 12px 16px; font-size: 14px; color: {INK_SOFT} !important; border-radius: 6px;
    }}

    /* ----- section title inside report ----- */
    .pj-section-title {{
        font-family:'Fraunces', serif; font-weight:600; color:{TEAL_DARK};
        font-size: 20px; margin: 2px 0 2px 0;
    }}
    .pj-section-subtitle {{
        font-family:'Fraunces', serif; font-weight:600; color:{TEAL_DARK};
        font-size: 16px; margin: 2px 0 2px 0;
    }}
    .pj-section-caption {{
        color:{INK_FAINT} !important; font-size: 12.5px; margin-bottom: 10px;
    }}

    /* ----- tabs (sectorized report) ----- */
    .stTabs [data-baseweb="tab-list"], .stTabs [role="tablist"] {{
        gap: 4px;
        border-bottom: 1px solid {LINE};
    }}
    .stTabs [data-baseweb="tab"], .stTabs [role="tab"] {{
        font-family: 'Instrument Sans', sans-serif;
        font-weight: 600;
        font-size: 12.5px;
        text-transform: uppercase;
        letter-spacing: .1em;
        color: {INK_FAINT} !important;
        padding: 10px 16px;
    }}
    .stTabs [role="tab"] p {{ font-family: 'Instrument Sans', sans-serif; font-weight: 600; }}
    .stTabs [aria-selected="true"] {{
        color: {TEAL_DARK} !important;
        border-bottom: 2px solid {BRICK} !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ background-color: {BRICK} !important; }}

    hr {{ border-color: {LINE}; }}

    /* ----- sidebar (verde-mata, assinatura em negativo) ----- */
    section[data-testid="stSidebar"] {{
        background-color: {MATA};
        border-right: none;
    }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] em,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{
        color: rgba(244, 241, 234, .78) !important;
    }}
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] strong {{
        color: {PAPEL} !important;
    }}
    section[data-testid="stSidebar"] .pj-eyebrow {{ color: {COBRE_CLARO} !important; }}
    section[data-testid="stSidebar"] hr {{ border-color: rgba(244, 241, 234, .16) !important; }}
    section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] *,
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button * {{
        color: {PAPEL} !important; fill: {PAPEL} !important;
    }}
    section[data-testid="stSidebar"] .stDownloadButton button {{
        background-color: {PAPEL}; border-color: {PAPEL};
    }}
    section[data-testid="stSidebar"] .stDownloadButton button p,
    section[data-testid="stSidebar"] .stDownloadButton button span,
    section[data-testid="stSidebar"] .stDownloadButton button div,
    section[data-testid="stSidebar"] .stDownloadButton button [data-testid="stMarkdownContainer"] p {{
        color: {MATA} !important;
    }}
    section[data-testid="stSidebar"] .stDownloadButton button:hover {{
        background-color: {COBRE_CLARO}; border-color: {COBRE_CLARO};
    }}
    section[data-testid="stSidebar"] .stDownloadButton button:hover p {{
        color: {TINTA} !important;
    }}
    .pj-sidebar-brand {{ padding: 2px 0 6px 0; }}
    .pj-sidebar-brand img {{ width: 172px; height: auto; display: block; }}
    </style>
    """,
    unsafe_allow_html=True,
)

CHART_COLORWAY = [TEAL_DARK, TEAL, BRICK, COBRE_CLARO, SAGE, INK_FAINT]
# Cores por categoria clínica: patogênico em cobre (o "positivo" da marca),
# comensal em verde-folha, não classificado em neutro esverdeado.
CATEGORIA_CORES = {"Patogênico": BRICK, "Comensal": TEAL, "Não classificado": SAGE}
PLOTLY_LAYOUT = dict(
    font_family="Instrument Sans, sans-serif",
    font_color=INK_SOFT,
    plot_bgcolor=SURFACE,
    paper_bgcolor=SURFACE,
    colorway=CHART_COLORWAY,
    margin=dict(t=20, b=20, l=10, r=10),
)


def section_title(text, caption=None):
    st.markdown(f'<div class="pj-section-title">{text}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="pj-section-caption">{caption}</div>', unsafe_allow_html=True)


def subsection_title(text, caption=None):
    st.markdown(f'<div class="pj-section-subtitle">{text}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="pj-section-caption">{caption}</div>', unsafe_allow_html=True)


def step_header(number, title):
    st.markdown(
        f"""<div class="pj-step">
        <div class="badge">{number}</div>
        <div class="step-title">{title}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def format_ic(inf, sup):
    """Formata um par (limite_inferior, limite_superior) de IC95% para exibição.
    Retorna um texto neutro quando o intervalo não pôde ser calculado (n=0)."""
    if inf is None or sup is None:
        return "IC95% não calculável (n=0)"
    return f"IC95%: {inf:.1f}–{sup:.1f}%"


def with_ic_column(df: pd.DataFrame, prev_col="prevalencia", inf_col="ic95_inf", sup_col="ic95_sup",
                    label="IC 95%") -> pd.DataFrame:
    """Devolve uma cópia do DataFrame com uma coluna extra combinando o IC95% num
    único texto legível ('11.0 – 42.1%'), para exibir ao lado da prevalência sem
    poluir a tabela com duas colunas numéricas soltas."""
    out = df.copy()
    if inf_col in out.columns and sup_col in out.columns:
        out[label] = out.apply(
            lambda r: f"{r[inf_col]:.1f} – {r[sup_col]:.1f}%" if pd.notna(r[inf_col]) and pd.notna(r[sup_col]) else "—",
            axis=1,
        )
        out = out.drop(columns=[inf_col, sup_col])
    return out


# ----------------------------------------------------------------
# Modelo de planilha (bytes) — usado no Passo 01 e na sidebar
#
# O modelo traz colunas para TODOS os métodos do catálogo (METHOD_CATALOG),
# não só os quatro originais — mas isso é só o ponto de partida. Bianca (ou
# qualquer usuária) pode apagar as colunas de método que o laboratório não
# usa: a planilha enviada só precisa trazer os métodos que de fato foram
# empregados na coleta, e o sistema detecta sozinho quais estão presentes
# (ver get_active_methods / validate_columns em analysis_engine.py). Também
# é possível enviar uma planilha com métodos que nem estão no modelo — desde
# que a coluna siga o padrão 'metodo_<nome>' e a coluna de status do domínio
# certo (status_amostra / status_lamina) esteja presente — mas nesse caso é
# preciso adicionar o método ao METHOD_CATALOG no código para que ele seja
# reconhecido e entre nas análises.
# ----------------------------------------------------------------
def generate_template_bytes() -> bytes:
    metodo_cols_fecal = [col for col, _, _, dominio in METHOD_CATALOG if dominio == "fecal"]
    metodo_cols_lamina = [col for col, _, _, dominio in METHOD_CATALOG if dominio == "lamina"]

    headers = (
        ["id_paciente", "coleta", "nome_paciente", "nome_responsavel", "status_amostra", "status_lamina"]
        + metodo_cols_lamina
        + metodo_cols_fecal
        + ["observacoes"]
    )

    def _linha(id_paciente, coleta, status_amostra, status_lamina, valores_metodo, observacoes):
        row = {
            "id_paciente": id_paciente, "coleta": coleta, "nome_paciente": "Exemplo Da Silva",
            "nome_responsavel": "Nome Do Responsável", "status_amostra": status_amostra,
            "status_lamina": status_lamina, "observacoes": observacoes,
        }
        for col in metodo_cols_lamina + metodo_cols_fecal:
            row[col] = valores_metodo.get(col, "-")
        return [row[h] for h in headers]

    linha1 = _linha("F-001", "P1", "Entregue", "Entregue", {"metodo_hpj": "E. nana"}, "")
    linha2 = _linha("F-001", "P2", "Entregue", "Entregue",
                     {col: "Enterobius vermicularis" for col in metodo_cols_lamina}, "")
    linha3 = _linha("F-001", "P3", "Não entregue", "Entregue",
                     {col: "" for col in metodo_cols_fecal}, "amostra fecal não coletada")
    linha4 = _linha("F-002", "P1", "Entregue", "Entregue",
                     {"metodo_hpj": "E. nana + G. lamblia",
                      **{col: "Não realizado" for col in metodo_cols_lamina if col != "metodo_graham"}},
                     "poliparasitismo (2 espécies na mesma célula, separadas por '+')")

    example = pd.DataFrame([linha1, linha2, linha3, linha4], columns=headers)

    metodo_legenda = {
        "metodo_graham": "Resultado do Graham — Enterobius vermicularis, Taenia sp.",
        "metodo_hpj": "Resultado do HPJ (Hoffman, Pons e Janer / Lutz) — sedimentação espontânea.",
        "metodo_willis": "Resultado do Willis — flutuação espontânea, ovos leves (ancilostomídeos).",
        "metodo_baermann_picanco": "Resultado do Baermann-Picanço — larvas de Strongyloides.",
        "metodo_faust": "Resultado do Faust — centrífugo-flutuação, cistos/oocistos de protozoários.",
        "metodo_kato_katz": "Resultado do Kato-Katz — quantificação de ovos de helmintos.",
        "metodo_mifc": "Resultado do MIFC (Blagg) — sedimentação por centrifugação.",
        "metodo_ritchie": "Resultado do Ritchie (formol-éter) — sedimentação por centrifugação.",
    }
    valores_aceitos_metodo = (
        "'-' (negativo) · 'Amostra insuficiente' (tentou, mas não deu resultado) · "
        "'Não realizado' (esse método não foi feito nessa amostra — não entra em nenhuma conta) · "
        "ou espécie(s) reconhecida(s) (veja a aba 'Espécies reconhecidas'). Para poliparasitismo, "
        "escreva mais de uma espécie na MESMA célula separadas por ' + ' (ex.: 'E. nana + G. lamblia')."
    )
    legenda_rows = [
        ["id_paciente", "Código único do paciente (repete nas linhas de P1/P2/P3)", "texto livre, ex.: F-001"],
        ["coleta", "Qual das até 3 coletas essa linha representa", "P1, P2 ou P3"],
        ["nome_paciente", "Nome da criança", "texto livre"],
        ["nome_responsavel", "Nome do responsável (opcional)", "texto livre ou vazio"],
        ["status_amostra", "Status de entrega do POTE DE FEZES — usado pelos métodos fecais abaixo", "Entregue / Não entregue"],
        ["status_lamina", "Status de entrega da LÂMINA — usado pelo(s) método(s) de lâmina abaixo", "Entregue / Não entregue"],
    ]
    for col, nome, _, dominio in METHOD_CATALOG:
        legenda_rows.append([
            col, metodo_legenda.get(col, f"Resultado do {nome}."), valores_aceitos_metodo,
        ])
    legenda_rows.append(["observacoes", "Observações livres (opcional)", "texto livre ou vazio"])
    legenda = pd.DataFrame(legenda_rows, columns=["Coluna", "O que é", "Valores aceitos"])

    # ----------------------------------------------------------------
    # Aba "Espécies reconhecidas" — lista, a partir do próprio PARASITE_MAP do
    # sistema (fonte única de verdade, sem duplicar a lista manualmente), o
    # nome padronizado de cada espécie, sua categoria clínica e todas as
    # grafias abreviadas aceitas. Uma espécie digitada fora dessas grafias
    # (e fora do nome completo) não é reconhecida como erro — ela ainda é
    # registrada no relatório, mas cai em "Não classificado" em vez de entrar
    # como Patogênico/Comensal, e pode aparecer como uma linha própria em vez
    # de ser agrupada com a grafia já cadastrada da mesma espécie.
    # ----------------------------------------------------------------
    variantes_por_especie = {}
    for chave, canonical in PARASITE_MAP.items():
        variantes_por_especie.setdefault(canonical, []).append(chave)

    especies_rows = []
    for especie in sorted(variantes_por_especie):
        variantes = sorted(set(variantes_por_especie[especie]), key=len)
        categoria = "Patogênico" if especie in PATOGENICOS else ("Comensal" if especie in COMENSAIS else "Não classificado")
        especies_rows.append([especie, categoria, ", ".join(variantes)])
    especies_reconhecidas = pd.DataFrame(
        especies_rows,
        columns=["Espécie (nome padronizado no relatório)", "Categoria clínica", "Grafias aceitas na célula (maiúsc./minúsc. tanto faz)"],
    )
    especies_nota = pd.DataFrame(
        [[
            "Maiúsculas/minúsculas não importam, e 'e.coli', 'e. coli' e 'e .coli' são todos "
            "reconhecidos como a mesma grafia. Uma espécie escrita de um jeito que NÃO está nesta "
            "lista (nem por extenso, nem abreviada como aqui) ainda é aceita e aparece no relatório, "
            "mas como 'Não classificado' — sem entrar automaticamente em Patogênico ou Comensal — e "
            "pode virar uma linha separada da mesma espécie já cadastrada com outra grafia. Prefira "
            "sempre uma das grafias desta lista, ou o nome científico completo (ex.: 'Giardia "
            "lamblia').\n\n"
            "Poliparasitismo: para registrar mais de uma espécie na MESMA amostra/método, escreva "
            "todas na mesma célula separadas por ' + ' (ex.: 'E. nana + G. lamblia + Enterobius "
            "vermicularis'). Vírgula também é aceita como separador. Não crie uma linha extra nem "
            "repita a coleta — é uma célula só, com todas as espécies encontradas."
        ]],
        columns=["Como preencher espécies e poliparasitismo"],
    )

    aviso = pd.DataFrame(
        [[
            "Este modelo traz uma coluna para cada método que o Pirajá reconhece. Se o seu "
            "laboratório não usa algum deles, pode simplesmente APAGAR a coluna inteira antes de "
            "enviar — o sistema detecta sozinho quais métodos estão presentes na planilha e ajusta "
            "as análises (denominadores, gráficos e tabelas) de acordo. Não é preciso preencher "
            "nem manter colunas de métodos não utilizados.\n\n"
            "Veja a aba 'Espécies reconhecidas' para a lista de parasitos que o sistema já sabe "
            "identificar e a grafia aceita para cada um, e como anotar poliparasitismo (mais de uma "
            "espécie na mesma célula).\n\n"
            "Use 'Não realizado' numa célula de método quando aquele método específico não chegou a "
            "ser executado NESSA amostra (mesmo com o pote/lâmina entregue) — diferente de 'Amostra "
            "insuficiente', que é quando o método foi tentado mas não deu resultado. Uma célula "
            "'Não realizado' não entra em nenhum denominador do relatório para aquele método."
        ]],
        columns=["Leia antes de preencher"],
    )

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        aviso.to_excel(writer, sheet_name="Leia-me", index=False)
        example.to_excel(writer, sheet_name="Dados", index=False)
        legenda.to_excel(writer, sheet_name="Legenda", index=False)
        especies_nota.to_excel(writer, sheet_name="Especies_Reconhecidas", index=False, startrow=0)
        especies_reconhecidas.to_excel(writer, sheet_name="Especies_Reconhecidas", index=False, startrow=3)
    return buf.getvalue()


TEMPLATE_BYTES = generate_template_bytes()

# ==================================================================
# SIDEBAR — marca, fluxo de trabalho e status
# ==================================================================
with st.sidebar:
    if LOGO_SIDEBAR_URI:
        st.markdown(
            f'<div class="pj-sidebar-brand"><img src="{LOGO_SIDEBAR_URI}" alt="Pirajá Entero"></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### Pirajá")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<span class="pj-eyebrow">Fluxo de trabalho</span>', unsafe_allow_html=True)
    st.markdown(
        """
- **01 · Baixe** o modelo de planilha
- **02 · Preencha** com os dados da coleta
- **03 · Envie** o arquivo e receba o relatório
        """
    )

    st.divider()
    st.download_button(
        "⬇ Modelo (.xlsx)",
        data=TEMPLATE_BYTES,
        file_name="Modelo_Levantamento_Parasitoses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

    st.divider()
    st.markdown('<span class="pj-eyebrow">Sobre as amostras</span>', unsafe_allow_html=True)
    st.caption(
        "**Pote de fezes** → HPJ, Willis, Baermann-Picanço, Faust, Kato-Katz, MIFC, Ritchie.\n\n"
        "**Lâmina (swab)** → Graham.\n\n"
        "A planilha não precisa trazer todos — o sistema lê os métodos que estiverem presentes "
        "e ignora os que faltarem."
    )

    st.divider()
    st.markdown('<span class="pj-eyebrow">Classificação clínica</span>', unsafe_allow_html=True)
    st.caption(
        "*Entamoeba histolytica/dispar* é tratada como **patogênica**: a diferenciação "
        "morfológica entre as duas formas não é possível no laboratório, então todo achado "
        "do complexo é reportado como potencialmente patogênico."
    )

# ==================================================================
# TOPO — marca + título
# ==================================================================
st.markdown(
    f"""<div class="pj-topbar">
        <div>
            <div class="name">Painel de análise epidemiológica</div>
        </div>
        <div>
            <div class="sub">Pirajá · Entero · parasitos intestinais</div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# Pequeno aglomerado de "positivos" em cobre claro sobre o padrão de pontos
# do hero — o mesmo gesto do padrão "Campo" da identidade visual.
HERO_CLUSTER_SVG = (
    '<svg class="pj-hero-cluster" viewBox="0 0 120 90" xmlns="http://www.w3.org/2000/svg">'
    + "".join(
        f'<circle cx="{x}" cy="{y}" r="6" fill="{COBRE_CLARO}"/>'
        for x, y in [(39, 13), (65, 13), (91, 13), (52, 39), (78, 39), (65, 65), (104, 65)]
    )
    + "</svg>"
)

# ==================================================================
# HERO
# ==================================================================
st.markdown(
    f"""<div class="pj-hero">
    {HERO_CLUSTER_SVG}
    <span class="pj-eyebrow">Métodos diversos, um relatório correto</span>
    <h2>Seus dados de coleta, transformados em relatório epidemiológico.</h2>
    <p>Fezes e lâmina seguem caminhos diagnósticos diferentes, e cada laboratório usa o conjunto de
    métodos que lhe é próprio. Baixe o modelo, preencha os dados da sua pesquisa e envie abaixo: o
    sistema reconhece sozinho quais métodos estão na planilha, mantém os denominadores corretos
    para cada um e gera prevalências, intervalos de confiança e testes estatísticos — pronto para
    qualquer população em estudo.</p>
    </div>""",
    unsafe_allow_html=True,
)

diag1, diag2 = st.columns(2)
with diag1:
    fecal_tags = "".join(
        f'<span class="pj-tag" style="border-color:{LINE}; color:{INK_SOFT};">{nome}</span>'
        for _, nome, _, dominio in METHOD_CATALOG if dominio == "fecal"
    )
    st.markdown(
        f"""<div class="pj-card">
        <span class="kicker">Pote de fezes</span>
        {fecal_tags}
        </div>""",
        unsafe_allow_html=True,
    )
with diag2:
    lamina_tags = "".join(
        f'<span class="pj-tag" style="border-color:{LINE}; color:{INK_SOFT};">{nome}</span>'
        for _, nome, _, dominio in METHOD_CATALOG if dominio == "lamina"
    )
    st.markdown(
        f"""<div class="pj-card">
        <span class="kicker">Lâmina (swab)</span>
        {lamina_tags}
        </div>""",
        unsafe_allow_html=True,
    )

st.write("")

# ==================================================================
# PASSO 01 — Baixar modelo
# ==================================================================
with st.container(border=True):
    st.markdown('<div class="pj-step-wrap">', unsafe_allow_html=True)
    step_header(1, "Baixe o modelo de planilha")
    st.write(
        "Um arquivo .xlsx com as colunas certas, os valores aceitos em cada uma, a lista de "
        "espécies reconhecidas e uma linha de exemplo — para preencher com os dados da sua coleta. "
        "Traz uma coluna para cada método que o sistema reconhece; apague as que o seu laboratório "
        "não usa antes de enviar."
    )
    st.download_button(
        "⬇ Baixar modelo (.xlsx)",
        data=TEMPLATE_BYTES,
        file_name="Modelo_Levantamento_Parasitoses.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ==================================================================
# PASSO 02 — Enviar planilha
# ==================================================================
with st.container(border=True):
    st.markdown('<div class="pj-step-wrap">', unsafe_allow_html=True)
    step_header(2, "Envie a planilha preenchida")
    st.write(
        "Aceita o modelo baixado acima, preenchido com uma linha por coleta (P1/P2/P3) de cada "
        "criança. Não precisa conter todos os métodos do modelo — só os que o laboratório "
        "efetivamente utilizou."
    )
    uploaded_file = st.file_uploader("Escolha o arquivo .xlsx", type=["xlsx", "xls"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")

# ==================================================================
# PASSO 03 — Relatório (sectorizado em abas)
# ==================================================================
if uploaded_file is not None:
    try:
        xls = pd.ExcelFile(uploaded_file)
        sheet_name = next((s for s in xls.sheet_names if s.strip().lower() == "dados"), xls.sheet_names[0])
        df_raw = pd.read_excel(xls, sheet_name=sheet_name)
        df = normalize_columns(df_raw)
        errors = validate_columns(df)
    except Exception as exc:  # noqa: BLE001
        errors = [f"Não consegui ler esse arquivo. Confira se é um .xlsx válido, exportado a "
                  f"partir do modelo. ({exc})"]
        df = None

    if errors:
        for e in errors:
            st.error(e)
    else:
        metrics = compute_metrics(df)
        metodos_ativos_nomes = metrics.get("metodos_ativos_nomes", [])

        if metrics["total"] == 0:
            st.error("Nenhum paciente identificado. Confira se a coluna **id_paciente** está preenchida.")
        else:
            st.success(
                f"Planilha processada: {metrics['total']} pacientes, {len(df)} coletas. "
                f"Métodos detectados: {', '.join(metodos_ativos_nomes)}. "
                "Relatório gerado abaixo."
            )

            with st.container(border=True):
                st.markdown('<div class="pj-step-wrap">', unsafe_allow_html=True)
                step_header(3, "Relatório da análise")
                st.caption(
                    f"{metrics['total']} pacientes cadastrados · {len(metrics['fecal'])} com amostra "
                    f"fecal entregue · {len(metrics['apenas_lamina'])} só com lâmina · métodos: "
                    f"{', '.join(metodos_ativos_nomes)}."
                )

                n_inconclusivas = (
                    len(metrics["fecal_inconclusivo"])
                    + len(metrics["lamina_inconclusivo"])
                )

                tab_geral, tab_especies, tab_metodos, tab_base, tab_export = st.tabs(
                    ["📊  Visão geral", "🦠  Espécies & parasitos", "🔬  Métodos & amostragem", "📋  Base por paciente", "⬇  Exportar"]
                )

                # ---------------------------------------------------------
                # ABA 1 — VISÃO GERAL
                # ---------------------------------------------------------
                with tab_geral:
                    section_title("Resumo executivo")
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Prevalência — amostra fecal", f"{metrics['prev_fecal']:.1f}%",
                                   help="Base: pacientes com resultado CONCLUSIVO em pelo menos um método "
                                        "fecal presente nesta planilha. Achados exclusivos de métodos de "
                                        "lâmina não entram aqui — veja 'Espécies & parasitos' para a "
                                        "prevalência de Enterobius. Pacientes com todos os resultados "
                                        "fecais marcados como 'Amostra insuficiente' são excluídos do "
                                        "denominador (não contam como negativos). IC95% calculado pelo "
                                        "método de Wilson.")
                        st.caption(format_ic(metrics["prev_fecal_ic95_inf"], metrics["prev_fecal_ic95_sup"]))
                    with c2:
                        st.metric("Prevalência — lâmina (todos os pacientes)", f"{metrics['prev_lamina']:.1f}%",
                                   help="Base: TODOS os pacientes com resultado conclusivo do(s) método(s) "
                                        "de lâmina desta planilha (Graham) — tenham eles entregado só a "
                                        "lâmina ou fezes e lâmina. Reflete tipicamente Enterobius "
                                        "vermicularis — o único parasita pesquisável só com a lâmina. O "
                                        "subgrupo que entregou exclusivamente lâmina é reportado à parte "
                                        "logo abaixo, mas seus resultados já estão somados aqui. IC95% "
                                        "calculado pelo método de Wilson.")
                        st.caption(format_ic(metrics["prev_lamina_ic95_inf"], metrics["prev_lamina_ic95_sup"]))
                    with c3:
                        st.metric("Prevalência combinada", f"{metrics['prev_combinada']:.1f}%",
                                   help="Todos os pacientes com pelo menos um resultado conclusivo, em "
                                        "qualquer domínio (fezes e/ou lâmina) — use com cautela, mistura "
                                        "profundidades diagnósticas diferentes. IC95% calculado pelo "
                                        "método de Wilson.")
                        st.caption(format_ic(metrics["prev_combinada_ic95_inf"], metrics["prev_combinada_ic95_sup"]))

                    if n_inconclusivas > 0:
                        st.markdown(
                            f"""<div class="pj-note"><strong>Amostras inconclusivas:</strong>
                            {len(metrics['fecal_inconclusivo'])} paciente(s) entregaram pote de fezes mas
                            tiveram <em>todos</em> os métodos fecais marcados como "Amostra insuficiente"
                            (ou sem resultado registrado){', ' + str(len(metrics['lamina_inconclusivo'])) + ' paciente(s) com lâmina entregue na mesma situação' if len(metrics['lamina_inconclusivo']) else ''}.
                            Esses pacientes foram excluídos dos denominadores de prevalência acima — eles
                            <u>não</u> contam como negativos, pois não houve diagnóstico conclusivo.
                            Células marcadas como "Não realizado" não entram nesta contagem — elas são
                            excluídas do denominador do método sem contar como inconclusivas.</div>""",
                            unsafe_allow_html=True,
                        )

                    if len(metrics["apenas_lamina"]) > 0:
                        st.markdown(
                            f"""<div class="pj-note" style="margin-top:8px;"><strong>Atenção:</strong> {len(metrics['apenas_lamina'])}
                            paciente(s) só entregaram a lâmina, nunca o pote de fezes — para eles, apenas
                            o(s) método(s) de lâmina desta planilha pôde(puderam) ser pesquisado(s). Esses
                            resultados já estão somados na "Prevalência — lâmina (todos os pacientes)"
                            acima; isoladamente, a prevalência só neste subgrupo é de
                            {metrics['prev_lamina_only']:.1f}%
                            ({int(metrics['lamina_only_conclusivo']['positivo_lamina'].sum())} de
                            {len(metrics['lamina_only_conclusivo'])} pacientes conclusivos).</div>""",
                            unsafe_allow_html=True,
                        )

                    st.write("")
                    section_title("Pacientes por profundidade de amostragem")
                    cat_df = metrics["cat_counts"].rename("n_pacientes").to_frame()
                    cat_df["%"] = (100 * cat_df["n_pacientes"] / metrics["total"]).round(1)
                    st.dataframe(cat_df, width='stretch')

                # ---------------------------------------------------------
                # ABA 2 — ESPÉCIES & PARASITOS
                # ---------------------------------------------------------
                with tab_especies:
                    section_title(
                        "Prevalência de todos os parasitos",
                        "Reúne, num só gráfico, as espécies encontradas por métodos fecais e por "
                        "métodos de lâmina presentes nesta planilha. As bases de cálculo diferem por "
                        "domínio — a tabela ao lado do gráfico mostra o denominador (Base N) e o(s) "
                        "método(s) que detectou(aram) cada espécie. Quando a mesma espécie foi "
                        "encontrada em métodos de domínios diferentes (ex.: Enterobius vermicularis, "
                        "tipicamente por um método de lâmina, mas ocasionalmente também visível num "
                        "método fecal), ela aparece numa única linha \"Fecal + Lâmina\" — o cálculo é "
                        "feito por paciente, então quem foi detectado por mais de um método conta uma "
                        "vez só, não duas.",
                    )
                    colT, colU = st.columns([3, 2])
                    with colT:
                        if not metrics["todos_parasitos_resumo"].empty:
                            fig_all = px.bar(
                                metrics["todos_parasitos_resumo"].sort_values("prevalencia"),
                                x="prevalencia", y="especie", orientation="h",
                                color="categoria",
                                color_discrete_map=CATEGORIA_CORES,
                                pattern_shape="dominio",
                                labels={"prevalencia": "Prevalência (%)", "especie": "", "dominio": "Amostra"},
                                hover_data={"metodos": True, "base_n": True, "n": True},
                            )
                            fig_all.update_layout(**PLOTLY_LAYOUT, showlegend=True, legend_title="")
                            st.plotly_chart(fig_all, width='stretch')
                        else:
                            st.info("Nenhum parasito detectado nesta base.")
                    with colU:
                        todos_display = with_ic_column(metrics["todos_parasitos_resumo"]).rename(columns={
                            "especie": "Espécie", "categoria": "Categoria", "dominio": "Amostra",
                            "n": "N", "prevalencia": "Prevalência %", "base_n": "Base N", "metodos": "Método(s)",
                        })
                        st.dataframe(todos_display, width='stretch', hide_index=True)
                        st.caption("IC95% pelo método de Wilson, calculado sobre o denominador (Base N) de cada espécie.")

                    st.write("")
                    subsection_title(
                        "Prevalência por método diagnóstico e espécie",
                        "Cada célula mostra a prevalência (%) daquela espécie especificamente pelo "
                        "método indicado, com denominador = pacientes com resultado conclusivo NAQUELE "
                        "método. Uma mesma espécie pode aparecer em mais de um método fecal (ex.: um "
                        "ovo de helminto pode ser visto tanto no HPJ quanto no Willis). Colunas mostram "
                        "só os métodos presentes nesta planilha.",
                    )
                    if not metrics["metodo_especie_resumo"].empty and metodos_ativos_nomes:
                        pivot = metrics["metodo_especie_resumo"].pivot_table(
                            index="especie", columns="metodo", values="prevalencia", aggfunc="first",
                        ).reindex(columns=metodos_ativos_nomes)
                        st.dataframe(pivot, width='stretch')
                        with st.expander("Ver com intervalos de confiança (IC95%, Wilson)"):
                            me_display = with_ic_column(metrics["metodo_especie_resumo"]).rename(columns={
                                "metodo": "Método", "especie": "Espécie", "n": "N",
                                "prevalencia": "Prevalência %", "categoria": "Categoria",
                            })
                            st.dataframe(me_display, width='stretch', hide_index=True)
                    else:
                        st.info("Nenhum dado suficiente para o cruzamento método x espécie.")

                    st.write("")
                    section_title(
                        "Prevalência por espécie — métodos fecais",
                        "Base: fezes com resultado conclusivo. Mostra cada espécie encontrada por "
                        "algum método fecal presente nesta planilha, especificamente — inclusive "
                        "Enterobius vermicularis, se algum caso tiver sido identificado incidentalmente "
                        "num método fecal (achado válido, não é erro). A prevalência combinada dessa "
                        "espécie com métodos de lâmina, sem contar o mesmo paciente duas vezes, está no "
                        "gráfico unificado acima.",
                    )
                    colA, colB = st.columns([3, 2])
                    with colA:
                        if not metrics["especies_resumo"].empty:
                            fig = px.bar(
                                metrics["especies_resumo"].sort_values("prevalencia"),
                                x="prevalencia", y="especie", orientation="h",
                                color="categoria",
                                color_discrete_map=CATEGORIA_CORES,
                                labels={"prevalencia": "Prevalência (%)", "especie": ""},
                            )
                            fig.update_layout(**PLOTLY_LAYOUT, showlegend=True, legend_title="")
                            st.plotly_chart(fig, width='stretch')
                        else:
                            st.info("Nenhuma espécie fecal detectada nesta base.")
                    with colB:
                        esp_display = with_ic_column(metrics["especies_resumo"]).rename(columns={
                            "especie": "Espécie", "n": "N", "prevalencia": "Prevalência %", "categoria": "Categoria",
                        })
                        st.dataframe(esp_display, width='stretch', hide_index=True)
                        st.caption("IC95% pelo método de Wilson (base: fezes conclusivas).")

                    st.write("")
                    section_title("Mono x poliparasitismo", "Base: espécies de origem fecal.")
                    colC, colD = st.columns([2, 3])
                    with colC:
                        fig2 = go.Figure(
                            data=[go.Pie(
                                labels=["Negativo", "Monoparasitismo", "Poliparasitismo"],
                                values=[metrics["neg"], metrics["mono"], metrics["poli"]],
                                marker_colors=[SAGE, TEAL, BRICK],
                                hole=0.45,
                            )]
                        )
                        fig2.update_layout(**PLOTLY_LAYOUT)
                        st.plotly_chart(fig2, width='stretch')
                    with colD:
                        st.markdown("**Combinações mais frequentes**")
                        if metrics["combos_resumo"].empty:
                            st.info("Nenhuma coinfecção registrada.")
                        else:
                            st.dataframe(metrics["combos_resumo"], width='stretch', hide_index=True)

                # ---------------------------------------------------------
                # ABA 3 — MÉTODOS & AMOSTRAGEM
                # ---------------------------------------------------------
                with tab_metodos:
                    section_title(
                        "Comparação entre métodos diagnósticos",
                        "Denominador = pacientes com resultado conclusivo naquele método específico "
                        "(exclui quem teve só 'Amostra insuficiente' ou 'Não realizado' nesse método). "
                        "Lista só os métodos presentes nesta planilha.",
                    )
                    colE, colF = st.columns([3, 2])
                    with colE:
                        if not metrics["metodos_resumo"].empty:
                            fig3 = px.bar(
                                metrics["metodos_resumo"], x="metodo", y="prevalencia",
                                labels={"prevalencia": "Prevalência (%)", "metodo": ""},
                            )
                            fig3.update_traces(marker_color=TEAL)
                            fig3.update_layout(**PLOTLY_LAYOUT)
                            st.plotly_chart(fig3, width='stretch')
                        else:
                            st.info("Nenhum método detectado nesta planilha.")
                    with colF:
                        met_display = with_ic_column(metrics["metodos_resumo"]).rename(columns={
                            "metodo": "Método", "amostra_biologica": "Amostra",
                            "n_pacientes_testaveis": "Testáveis", "n_pacientes_positivas": "Positivas",
                            "n_pacientes_inconclusivas": "Inconclusivas", "prevalencia": "Prevalência %",
                        })
                        st.dataframe(met_display, width='stretch', hide_index=True)
                        st.caption("IC95% pelo método de Wilson.")

                    st.write("")
                    subsection_title(
                        "HPJ x Willis — teste de McNemar",
                        "Compara os dois métodos aplicados à MESMA amostra de fezes da mesma criança "
                        "(dados pareados) — testa se um método detecta mais positivos que o outro, "
                        "usando só os pacientes em que os dois métodos discordaram entre si. Só "
                        "calculado quando a planilha traz os dois métodos.",
                    )
                    mc = metrics["mcnemar_hpj_willis"]
                    if mc["n_pareado"] == 0 or mc["tabela"] is None:
                        st.info("Sem pacientes com resultado conclusivo em HPJ e Willis simultaneamente "
                                "(ou um dos dois métodos não está presente nesta planilha) — teste não "
                                "calculado.")
                    else:
                        tb = mc["tabela"]
                        mc_col1, mc_col2 = st.columns([2, 3])
                        with mc_col1:
                            mc_table = pd.DataFrame(
                                [[tb["pp"], tb["pn"]], [tb["np"], tb["nn"]]],
                                index=["HPJ +", "HPJ −"], columns=["Willis +", "Willis −"],
                            )
                            st.dataframe(mc_table, width='stretch')
                        with mc_col2:
                            metodo_label = {
                                "exato": "teste exato (< 25 discordâncias)",
                                "chi2_corrigido": "qui-quadrado com correção de continuidade",
                                "sem_discordancia": "sem discordâncias — nada a testar",
                            }.get(mc["metodo"], mc["metodo"])
                            st.metric("p-valor (McNemar)", f"{mc['p_valor']:.4f}" if mc["p_valor"] is not None else "—")
                            st.caption(
                                f"n pareado = {mc['n_pareado']} · {tb['pn'] + tb['np']} discordância(s) "
                                f"({tb['pn']} HPJ+/Willis−, {tb['np']} HPJ−/Willis+) · {metodo_label}."
                            )
                            if mc["p_valor"] is not None and mc["p_valor"] < 0.05:
                                st.caption("p < 0,05 — diferença estatisticamente significativa entre os métodos nesta amostra.")
                            elif mc["p_valor"] is not None:
                                st.caption("p ≥ 0,05 — sem evidência estatística de diferença entre os métodos nesta amostra.")

                    st.write("")
                    section_title(
                        "Efeito do número de potes de fezes entregues",
                        "Usa somente positividade fecal (qualquer método fecal presente na "
                        "planilha). Compara SUBGRUPOS diferentes de pacientes (quem entregou 1, 2 ou 3 "
                        "potes), o que pode ter viés de seleção — veja a curva cumulativa abaixo, "
                        "calculada no mesmo grupo de pacientes, para uma estimativa sem esse viés.",
                    )
                    if not metrics["efeito_n_coletas"].empty:
                        fig4 = px.bar(
                            metrics["efeito_n_coletas"], x="n_potes_entregues", y="prevalencia",
                            labels={"prevalencia": "Prevalência (%)", "n_potes_entregues": "Nº de potes entregues"},
                            text="n_pacientes",
                        )
                        fig4.update_traces(marker_color=TEAL_DARK, texttemplate="n=%{text}", textposition="outside")
                        fig4.update_layout(**PLOTLY_LAYOUT)
                        st.plotly_chart(fig4, width='stretch')
                    else:
                        st.info("Dados insuficientes para este gráfico.")

                    ca = metrics["cochran_armitage_efeito_coletas"]
                    if ca["p_valor"] is not None:
                        st.caption(
                            f"Teste de tendência de Cochran-Armitage: Z = {ca['estatistica_z']:.3f}, "
                            f"p = {ca['p_valor']:.4f} ({ca['n_grupos']} grupos). {ca['aviso']}"
                        )
                    elif ca["n_grupos"] and ca["n_grupos"] >= 2:
                        st.caption(f"Teste de tendência de Cochran-Armitage não calculável nesta base. {ca['aviso']}")

                    st.write("")
                    section_title("Ganho marginal por amostra — curva cumulativa")
                    if not metrics["fecal_cumulativa"].empty:
                        n_grupo = int(metrics["fecal_cumulativa"]["n_pacientes"].iloc[0])
                        k_max = int(metrics["fecal_cumulativa"]["k"].max())
                        st.caption(
                            f"Mesmo grupo de {n_grupo} paciente(s) que entregou o número máximo de potes "
                            f"observado no estudo ({k_max}), medindo quantas ficariam positivas se o "
                            "laboratório parasse na 1ª, 2ª ... até a última coleta. Como é a mesma "
                            "paciente sendo acompanhado (medida repetida), este gráfico não sofre o viés "
                            "de comparar subgrupos diferentes de crianças."
                        )
                        fig5 = px.line(
                            metrics["fecal_cumulativa"], x="k", y="prevalencia_cumulativa", markers=True,
                            labels={"k": "Nº de potes considerados (cumulativo)", "prevalencia_cumulativa": "Prevalência cumulativa (%)"},
                        )
                        fig5.update_traces(line_color=TEAL_DARK, marker_color=BRICK)
                        fig5.update_layout(**PLOTLY_LAYOUT)
                        st.plotly_chart(fig5, width='stretch')
                    else:
                        st.info("Dados insuficientes para a curva cumulativa (nenhum paciente com coletas identificadas por P1/P2/P3).")

                # ---------------------------------------------------------
                # ABA 4 — BASE POR CRIANÇA
                # ---------------------------------------------------------
                with tab_base:
                    section_title("Base completa por criança")
                    display_cols = [
                        "id_paciente", "nome_paciente", "categoria_amostragem",
                        "n_coletas_pote_entregue", "n_coletas_lamina_entregue",
                        "fecal_status", "lamina_status",
                        "positivo_algum_metodo", "especies_str",
                    ]
                    st.dataframe(
                        metrics["por_paciente"][display_cols].sort_values("id_paciente"),
                        width='stretch', hide_index=True, height=460,
                    )

                # ---------------------------------------------------------
                # ABA 5 — EXPORTAR
                # ---------------------------------------------------------
                def generate_report_excel_bytes(m: dict) -> bytes:
                    buf = io.BytesIO()
                    metodo_nomes = m.get("metodos_ativos_nomes", [])
                    list_cols = ["especies", "especies_fecais", "especies_lamina"] + [
                        f"especies_{nome}" for nome in metodo_nomes
                    ]
                    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                        m["por_paciente"].drop(columns=[c for c in list_cols if c in m["por_paciente"].columns]).to_excel(
                            writer, sheet_name="Base_por_Crianca", index=False
                        )
                        m["cat_counts"].rename("n").to_frame().to_excel(writer, sheet_name="Categoria_Amostragem")
                        pd.DataFrame([
                            {"metrica": "Prevalência — amostra fecal (conclusiva)", "valor_pct": m["prev_fecal"],
                             "ic95_inf": m["prev_fecal_ic95_inf"], "ic95_sup": m["prev_fecal_ic95_sup"],
                             "n_pacientes": len(m["fecal_conclusivo"])},
                            {"metrica": "Prevalência — lâmina, todos os pacientes (conclusiva)", "valor_pct": m["prev_lamina"],
                             "ic95_inf": m["prev_lamina_ic95_inf"], "ic95_sup": m["prev_lamina_ic95_sup"],
                             "n_pacientes": len(m["lamina_conclusivo"])},
                            {"metrica": "Prevalência — subgrupo só-lâmina (conclusiva)", "valor_pct": m["prev_lamina_only"],
                             "ic95_inf": m["prev_lamina_only_ic95_inf"], "ic95_sup": m["prev_lamina_only_ic95_sup"],
                             "n_pacientes": len(m["lamina_only_conclusivo"])},
                            {"metrica": "Prevalência combinada (conclusiva)", "valor_pct": m["prev_combinada"],
                             "ic95_inf": m["prev_combinada_ic95_inf"], "ic95_sup": m["prev_combinada_ic95_sup"],
                             "n_pacientes": len(m["combinada_base"])},
                            {"metrica": "Inconclusivas — fezes (amostra insuficiente em tudo)", "valor_pct": None,
                             "ic95_inf": None, "ic95_sup": None, "n_pacientes": len(m["fecal_inconclusivo"])},
                            {"metrica": "Inconclusivas — lâmina, todos os pacientes", "valor_pct": None,
                             "ic95_inf": None, "ic95_sup": None, "n_pacientes": len(m["lamina_inconclusivo"])},
                            {"metrica": "Inconclusivas — subgrupo só-lâmina", "valor_pct": None,
                             "ic95_inf": None, "ic95_sup": None, "n_pacientes": len(m["lamina_only_inconclusivo"])},
                            {"metrica": "Métodos detectados nesta planilha", "valor_pct": None,
                             "ic95_inf": None, "ic95_sup": None, "n_pacientes": None,
                             },
                        ]).to_excel(writer, sheet_name="Prevalencia_Geral", index=False)
                        pd.DataFrame({"metodos_ativos": metodo_nomes}).to_excel(
                            writer, sheet_name="Metodos_Ativos", index=False
                        )
                        m["todos_parasitos_resumo"].to_excel(writer, sheet_name="Todos_os_Parasitos", index=False)
                        m["especies_resumo"].to_excel(writer, sheet_name="Prevalencia_por_Especie", index=False)
                        m["metodo_especie_resumo"].to_excel(writer, sheet_name="Prevalencia_Metodo_x_Especie", index=False)
                        pd.DataFrame([
                            {"categoria": "Negativo", "n": m["neg"]},
                            {"categoria": "Monoparasitismo", "n": m["mono"]},
                            {"categoria": "Poliparasitismo", "n": m["poli"]},
                        ]).to_excel(writer, sheet_name="Poliparasitismo", index=False)
                        m["combos_resumo"].to_excel(writer, sheet_name="Combinacoes", index=False)
                        m["metodos_resumo"].to_excel(writer, sheet_name="Comparacao_Metodos", index=False)
                        m["efeito_n_coletas"].to_excel(writer, sheet_name="Prevalencia_x_NColetas", index=False)
                        m["fecal_cumulativa"].to_excel(writer, sheet_name="Curva_Cumulativa_Fecal", index=False)

                        mc = m["mcnemar_hpj_willis"]
                        tb = mc["tabela"] or {}
                        pd.DataFrame([{
                            "n_pareado": mc["n_pareado"],
                            "HPJ+ / Willis+": tb.get("pp"),
                            "HPJ+ / Willis-": tb.get("pn"),
                            "HPJ- / Willis+": tb.get("np"),
                            "HPJ- / Willis-": tb.get("nn"),
                            "estatistica": mc["estatistica"],
                            "p_valor": mc["p_valor"],
                            "metodo": mc["metodo"],
                        }]).to_excel(writer, sheet_name="McNemar_HPJ_x_Willis", index=False)

                        ca = m["cochran_armitage_efeito_coletas"]
                        pd.DataFrame([{
                            "n_grupos": ca["n_grupos"],
                            "estatistica_z": ca["estatistica_z"],
                            "p_valor": ca["p_valor"],
                            "aviso": ca["aviso"],
                        }]).to_excel(writer, sheet_name="CochranArmitage_NPotes", index=False)
                    return buf.getvalue()

                with tab_export:
                    section_title("Baixe os relatórios completos")
                    st.write(
                        "O Excel traz todas as tabelas em abas separadas, prontas para uso em outras "
                        "análises. O PDF traz um relatório formatado, pronto para impressão ou envio."
                    )
                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            "⬇ Baixar relatório em Excel",
                            data=generate_report_excel_bytes(metrics),
                            file_name="Relatorio_Analise_Epidemiologica.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            width="stretch",
                        )
                    with col_dl2:
                        st.download_button(
                            "⬇ Baixar relatório em PDF",
                            data=build_pdf_report(metrics, logo_path=str(LOGO_PDF_PATH) if LOGO_PDF_PATH.exists() else None),
                            file_name="Relatorio_Analise_Epidemiologica.pdf",
                            mime="application/pdf",
                            width="stretch",
                        )

                st.markdown("</div>", unsafe_allow_html=True)

st.divider()
st.caption(
    "Nota metodológica: a prevalência é calculada por paciente, não por exame — um paciente conta "
    "como positiva se qualquer uma de suas coletas (P1/P2/P3) revelou o parasita. O pote de fezes "
    "alimenta os métodos de domínio fecal; a lâmina alimenta exclusivamente os métodos de domínio "
    "lâmina/swab. Crianças cujos únicos resultados foram 'Amostra insuficiente' são reportadas à "
    "parte como inconclusivas, e não entram nos denominadores de prevalência. Uma célula marcada "
    "'Não realizado' é excluída por completo do denominador daquele método para aquela coleta. A "
    "planilha enviada não precisa trazer todos os métodos do modelo — o sistema detecta e analisa "
    "só os presentes."
)
