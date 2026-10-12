from datetime import datetime
import os
import streamlit as st
import pandas as pd
import libsql_client

# Importar ReportLab para generar los PDFs de los partes
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

# Importar el lienzo de dibujo para la firma digital
try:
    from streamlit_drawable_canvas import st_canvas
    CANVAS_DISPONIBLE = True
except ImportError:
    CANVAS_DISPONIBLE = False

# Configuración de la página (layout ancho)
st.set_page_config(
    page_title="AMP Informática - Control de Partes", page_icon="💻", layout="wide"
)

# Estilos CSS personalizados con temática informática y fuente de terminal/código
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@400;600;700&display=swap');

    [data-testid="stSidebar"] {
        display: none;
    }
    
    .main {
        background-color: #0f172a;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, .terminal-font {
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 0.5px;
    }

    .header-container {
        display: flex;
        align-items: center;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 20px 30px;
        border-radius: 12px;
        border: 1px solid #334155;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        margin-bottom: 25px;
        position: relative;
        overflow: hidden;
    }
    
    .header-container::after {
        content: "⚡ [SYSTEM_ONLINE // TURSO_CLOUD_ACTIVE]";
        position: absolute;
        right: 25px;
        top: 15px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 11px;
        color: #38bdf8;
        opacity: 0.8;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center;
        gap: 6px;
        background-color: #1e293b;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #0f172a;
        color: #94a3b8;
        border-radius: 6px;
        font-family: 'Share Tech Mono', monospace;
        font-weight: 600;
        padding-left: 12px;
        padding-right: 12px;
        border: 1px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: 1px solid #60a5fa !important;
    }
    
    div.stButton > button {
        background-color: #2563eb;
        color: white;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        border: 1px solid #60a5fa;
        font-family: 'Share Tech Mono', monospace;
        font-weight: 600;
    }
    div.stButton > button:hover {
        background-color: #1d4ed8;
        border-color: #93c5fd;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS (TURSO) ====================
def init_connection():
    if "TURSO_DATABASE_URL" in st.secrets and "TURSO_AUTH_TOKEN" in st.secrets:
        url = st.secrets["TURSO_DATABASE_URL"]
        auth_token = st.secrets["TURSO_AUTH_TOKEN"]
    else:
        url = "libsql://partes-trabajo-satampinf.aws-eu-west-1.turso.io"
        auth_token = ""

    conn = libsql_client.connect(
        url=url,
        auth_token=auth_token
    )
    return conn

conn = init_connection()

def init_db():
    conn.execute("""
        CREATE TABLE IF NOT EXISTS empresa_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_empresa TEXT,
            cif TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT,
            web TEXT
        )
    """)
    
    res_emp = conn.execute("SELECT COUNT(*) FROM empresa_config")
    if res_emp.rows[0][0] == 0:
        conn.execute("""
            INSERT INTO empresa_config (nombre_empresa, cif, direccion, telefono, email, web)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ("AMP INFORMÁTICA", "B-12345678", "Calle Principal 10, Taller Táctico", "+34 600 000 000", "soporte@ampinformatica.es", "www.ampinformatica.es"))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cif_nif TEXT,
            telefono TEXT,
            email TEXT,
            direccion TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            rol TEXT,
            telefono TEXT,
            email TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS catalogo_reparaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL UNIQUE,
            descripcion TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS catalogo_materiales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            referencia TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS partes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL,
            operario TEXT,
            reparacion TEXT NOT NULL,
            materiales TEXT,
            tiempo REAL NOT NULL,
            estado TEXT DEFAULT 'Abierto',
            foto_path TEXT,
            firma_path TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS base_conocimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descripcion TEXT NOT NULL
        )
    """)

init_db()

def obtener_datos_empresa():
    res = conn.execute("SELECT nombre_empresa, cif, direccion, telefono, email, web FROM empresa_config LIMIT 1")
    if res.rows:
        row = res.rows[0]
        return {"nombre": row[0], "cif": row[1], "direccion": row[2], "telefono": row[3], "email": row[4], "web": row[5]}
    return {"nombre": "AMP INFORMÁTICA", "cif": "", "direccion": "", "telefono": "", "email": "", "web": ""}

def generar_pdf_parte(parte_data):
    if not REPORTLAB_DISPONIBLE:
        return None
        
    empresa = obtener_datos_empresa()
    p_id, p_fecha, p_cliente, p_operario, p_rep, p_mat, p_tiempo, p_estado, p_foto, p_firma = parte_data
    
    os.makedirs("temp_pdf", exist_ok=True)
    pdf_filename = f"temp_pdf/parte_trabajo_{p_id}.pdf"
    
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle(
        'TituloEmpresa',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#1e293b'),
        alignment=0
    )
    
    datos_empresa_style = ParagraphStyle(
        'DatosEmpresa',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        alignment=2
    )
    
    label_style = ParagraphStyle('Label', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0f172a'))
    val_style = ParagraphStyle('Value', fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#334155'))

    txt_empresa = f"<b>{empresa['nombre']}</b><br/>CIF: {empresa['cif']}<br/>{empresa['direccion']}<br/>Telf: {empresa['telefono']} | {empresa['email']}"
    
    header_table_data = [
        [Paragraph(f"<b>PARTE DE INTERVENCIÓN TÉCNICA</b><br/><font size=9 color='#64748b'>Nº Registro: #{p_id}</font>", titulo_style), 
         Paragraph(txt_empresa, datos_empresa_style)]
    ]
    t_top = Table(header_table_data, colWidths=[270, 270])
    t_top.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_top)
    story.append(Spacer(1, 10))
    
    data_header = [
        [Paragraph(f"<b>Fecha Emisión:</b> {p_fecha}", label_style), Paragraph(f"<b>Estado:</b> {p_estado}", label_style)],
        [Paragraph(f"<b>Cliente:</b> {p_cliente}", label_style), Paragraph(f"<b>Técnico Asignado:</b> {p_operario if p_operario else 'No asignado'}", label_style)],
        [Paragraph(f"<b>Tiempo Invertido:</b> {p_tiempo} horas", label_style), Paragraph(f"<b>Soporte Web:</b> {empresa['web']}", label_style)]
    ]
    
    t_header = Table(data_header, colWidths=[270, 270])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f1f5f9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    
    story.append(t_header)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Diagnóstico y Trabajos Realizados:</b>", label_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(p_rep if p_rep else "Sin descripción", val_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Componentes / Materiales Utilizados:</b>", label_style))
    story.append(Spacer(1, 5))
    story.append(Paragraph(p_mat if p_mat else "Ninguno", val_style))
    story.append(Spacer(1, 20))
    
    tiene_foto = p_foto and os.path.exists(p_foto)
    tiene_firma = p_firma and os.path.exists(p_firma)

    if tiene_foto or tiene_firma:
        story.append(Paragraph("<b>Validación y Registros Multimedia:</b>", label_style))
        story.append(Spacer(1, 5))
        
        celda_foto = RLImage(p_foto, width=200, height=150) if tiene_foto else Paragraph("Sin evidencia fotográfica", val_style)
        celda_firma = RLImage(p_firma, width=200, height=100) if tiene_firma else Paragraph("Sin firma digital registrada", val_style)
        
        elementos_multimedia = [
            [Paragraph("<b>Evidencia Fotográfica:</b>", label_style), Paragraph("<b>Firma de Conformidad Cliente:</b>", label_style)],
            [celda_foto, celda_firma]
        ]
        
        t_multimedia = Table(elementos_multimedia, colWidths=[270, 270])
        t_multimedia.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
        ]))
        story.append(t_multimedia)
            
    doc.build(story)
    return pdf_filename

st.markdown("<div class='header-container'>", unsafe_allow_html=True)
col_logo, col_titulo = st.columns([1, 4], vertical_alignment="center")

with col_logo:
    try:
        st.image("Logo.jpg", width=190)
    except Exception:
        st.warning("⚠️ No se encuentra la imagen 'Logo.jpg'.")

with col_titulo:
    st.markdown("""
        <h1 style='color: #f8fafc; margin: 0; font-size: 28px;'>AMP INFORMÁTICA</h1>
        <p style='color: #38bdf8; margin: 5px 0 0 0; font-family: "Share Tech Mono", monospace; font-size: 14px;'>
            🛠️ Gestión Integral de Servicio Técnico, Reparaciones y Hardware (Turso Cloud)
        </p>
    """, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

menu = st.tabs([
    "💻 01. Terminal", 
    "👤 02. Técnicos", 
    "👥 03. Clientes", 
    "⚙️ 04. Catálogos", 
    "📋 05. Historial", 
    "📊 06. Informes",
    "📚 07. Base Conocimiento",
    "🏢 08. Empresa"
])

with menu[0]:
    st.markdown("<div style='text-align: center; padding: 10px;'>", unsafe_allow_html=True)
    st.markdown("<h2 style='color: #38bdf8;'>ESTACIÓN DE CONTROL DE PARTES DE TALLER</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8;'>Gestión de órdenes de reparación y seguimiento de intervenciones.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    @st.dialog("⚡ [NUEVA ORDEN DE REPARACIÓN Y FIRMA DIGITAL]", width="large")
    def abrir_modal_nuevo_parte():
        res_cli = conn.execute("SELECT nombre FROM clientes ORDER BY nombre")
        clientes_db = [row[0] for row in res_cli.rows]
        
        res_usu = conn.execute("SELECT nombre FROM usuarios ORDER BY nombre")
        usuarios_db = [row[0] for row in res_usu.rows]
        
        res_rep = conn.execute("SELECT titulo, descripcion FROM catalogo_reparaciones ORDER BY titulo")
        reparaciones_db = res_rep.rows
        
        res_mat = conn.execute("SELECT nombre FROM catalogo_materiales ORDER BY nombre")
        materiales_db = [row[0] for row in res_mat.rows]

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if clientes_db:
                cliente = st.selectbox("Seleccionar Cliente", options=clientes_db)
            else:
                st.warning("⚠️ No hay clientes dados de alta.")
                cliente = st.text_input("Nombre del Cliente (Manual)")
        with col_f2:
            if usuarios_db:
                operario = st.selectbox("Técnico / Operario Asignado", options=usuarios_db)
            else:
                operario = st.text_input("Técnico (Manual)", value="Soporte Técnico")
            
        st.markdown("---")
        st.markdown("#### 🔧 Estado y Diagnóstico de la Reparación")
        
        estado_parte = st.pills("⚡ Estado del Parte", options=["Abierto", "En proceso", "Cerrado"], default="Abierto", key="pills_estado_parte")
        if not estado_parte:
            estado_parte = "Abierto"
        
        reparacion_seleccionada = None
        if reparaciones_db:
            titulos_reps = [r[0] for r in reparaciones_db]
            reparacion_seleccionada = st.pills("⚡ Selecciones rápidas de averías comunes", options=titulos_reps, key="pills_reparacion")
        
        desc_sugerida = ""
        if reparacion_seleccionada:
            for titulo, desc in reparaciones_db:
                if titulo == reparacion_seleccionada:
                    desc_sugerida = desc if desc else titulo
                    break

        if "txt_rep_val" not in st.session_state or reparacion_seleccionada:
            st.session_state["txt_rep_val"] = desc_sugerida

        reparacion = st.text_area("Detalle técnico de la intervención", value=st.session_state["txt_rep_val"], placeholder="Ej: Sustitución de placa base, limpieza de ventiladores...", key="input_reparacion_editable")
            
        st.markdown("---")
        st.markdown("#### 💾 Componentes y Materiales de Hardware/Software")
        
        materiales_seleccionados = []
        if materiales_db:
            materiales_seleccionados = st.pills("📦 Seleccionar piezas del inventario", options=materiales_db, selection_mode="multi", key="pills_materiales")
        
        mat_extra = st.text_area("Notas o componentes adicionales", placeholder="Ej: 1x SSD NVMe 1TB, licencia Windows 11...", key="txt_mat_extra")
        
        lista_mats_combinada = ", ".join(materiales_seleccionados) if materiales_seleccionados else ""
        if mat_extra.strip():
            lista_mats_combinada = f"{lista_mats_combinada}, {mat_extra}" if lista_mats_combinada else mat_extra
            
        st.markdown("---")
        st.markdown("#### 📸 Evidencia Fotográfica (Opcional)")
        opcion_foto = st.radio("Método para añadir imagen:", ["Subir desde la galería", "Hacer foto con la cámara"], horizontal=True)
        
        foto_archivo = None
        if opcion_foto == "Subir desde la galería":
            foto_archivo = st.file_uploader("Seleccionar imagen de equipo/avería", type=["jpg", "jpeg", "png"], key="galeria_foto")
        else:
            foto_archivo = st.camera_input("Capturar foto con la cámara", key="camara_foto")

        ruta_foto_guardada = None
        if foto_archivo is not None:
            st.image(foto_archivo, caption="Vista previa de la imagen", width=300)
            try:
                os.makedirs("fotos_partes", exist_ok=True)
                nombre_archivo_foto = f"fotos_partes/parte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                with open(nombre_archivo_foto, "wb") as f:
                    f.write(foto_archivo.getbuffer())
                ruta_foto_guardada = nombre_archivo_foto
            except Exception as e:
                st.warning(f"No se pudo guardar la imagen: {e}")

        st.markdown("---")
        st.markdown("#### ✍️ Lienzo de Firma Digital del Cliente")
        st.markdown("<small>Firme en el recuadro inferior usando el ratón o el dedo:</small>", unsafe_allow_html=True)
        
        canvas_result = None
        if CANVAS_DISPONIBLE:
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#000000",
                background_color="#ffffff",
                height=150,
                width=500,
                drawing_mode="freedraw",
                return_image_data=True,
                key="canvas_firma_cliente",
            )
        else:
            st.warning("⚠️ La librería `streamlit-drawable-canvas` no está instalada.")

        tiempo = st.number_input("Tiempo Invertido (horas de taller/desplazamiento)", min_value=0.1, step=0.5, value=1.0, key="num_tiempo_modal")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 GUARDAR Y REGISTRAR ORDEN", use_container_width=True):
            if not cliente.strip():
                st.error("⚠️ El campo 'Cliente' es obligatorio.")
            else:
                desc_final = reparacion.strip() if reparacion.strip() else "Mantenimiento informático general"
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                ruta_firma_guardada = None
                if CANVAS_DISPONIBLE and canvas_result is not None and canvas_result.image_data is not None:
                    try:
                        from PIL import Image
                        img_data = canvas_result.image_data
                        img = Image.fromarray(img_data.astype('uint8'), mode="RGBA")
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3])
                        
                        os.makedirs("firmas_partes", exist_ok=True)
                        ruta_firma_guardada = f"firmas_partes/firma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        background.save(ruta_firma_guardada)
                    except Exception as e:
                        print(f"Error al procesar la firma: {e}")

                try:
                    conn.execute("""
                        INSERT INTO partes (fecha, cliente, operario, reparacion, materiales, tiempo, estado, foto_path, firma_path)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (fecha_actual, cliente, operario, desc_final, lista_mats_combinada, tiempo, estado_parte, ruta_foto_guardada, ruta_firma_guardada))
                    
                    st.success("¡Parte registrado y guardado con éxito en Turso!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        if st.button("💻 CREAR NUEVO PARTE DE REPARACIÓN", use_container_width=True):
            abrir_modal_nuevo_parte()

    st.markdown("---")
    st.markdown("### 🔍 Gestión y Actualización de Partes Activos (Abiertos / En Proceso)")
    
    res_activos = conn.execute("""
        SELECT id, fecha, cliente, operario, reparacion, estado, tiempo, foto_path, firma_path 
        FROM partes 
        WHERE estado IN ('Abierto', 'En proceso')
        ORDER BY id DESC
    """)
    partes_activos = res_activos.rows
    
    if not partes_activos:
        st.info("No hay partes abiertos ni en proceso actualmente.")
    else:
        for p in partes_activos:
            p_id, p_fecha, p_cliente, p_operario, p_rep, p_estado, p_tiempo, p_foto, p_firma = p
            with st.container(border=True):
                col_info1, col_info2, col_info3 = st.columns([3, 2, 2])
                with col_info1:
                    st.markdown(f"**ID: {p_id}** | 📅 **{p_fecha}**")
                    st.markdown(f"👤 **Cliente:** {p_cliente} | 🛠️ **Técnico:** {p_operario if p_operario else 'No asignado'}")
                    st.markdown(f"💬 *{p_rep}*")
                with col_info2:
                    st.markdown(f"⏱️ **Tiempo:** {p_tiempo}h")
                    nuevo_estado = st.selectbox(
                        "Cambiar Estado", 
                        options=["Abierto", "En proceso", "Cerrado"], 
                        index=["Abierto", "En proceso", "Cerrado"].index(p_estado),
                        key=f"estado_select_{p_id}"
                    )
                with col_info3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("💾 Actualizar Estado", key=f"btn_act_{p_id}", use_container_width=True):
                        conn.execute("UPDATE partes SET estado = ? WHERE id = ?", (nuevo_estado, p_id))
                        st.success(f"¡Parte #{p_id} actualizado a '{nuevo_estado}'!")
                        st.rerun()

with menu[1]:
    st.subheader("👨‍💻 Panel de Control de Técnicos y Personal")
    sub_tab_usu = st.tabs(["➕ Dar de Alta Técnico", "📋 Plantilla de Técnicos"])
    with sub_tab_usu[0]:
        st.markdown("### Registrar Nuevo Operario de Taller")
        with st.form("form_alta_usuario", clear_on_submit=True):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                u_nombre = st.text_input("Nombre y Apellidos *")
                u_usuario = st.text_input("ID de Usuario / Nick *")
                u_rol = st.selectbox("Especialidad / Rol", options=["Técnico Hardware", "Técnico Software & Redes", "Administrador", "Soporte Remoto"])
            with col_u2:
                u_telefono = st.text_input("Teléfono de Contacto")
                u_email = st.text_input("Correo Electrónico")
            btn_guardar_usuario = st.form_submit_button("Guardar Operario")
            if btn_guardar_usuario:
                if not u_nombre.strip() or not u_usuario.strip():
                    st.error("Los campos 'Nombre' y 'ID de Usuario' son obligatorios.")
                else:
                    try:
                        conn.execute("INSERT INTO usuarios (nombre, usuario, rol, telefono, email) VALUES (?, ?, ?, ?, ?)", (u_nombre, u_usuario, u_rol, u_telefono, u_email))
                        st.success(f"Técnico '{u_nombre}' registrado con éxito.")
                    except Exception as e:
                        st.error(f"Error al registrar técnico: {e}")
    with sub_tab_usu[1]:
        res_u_df = conn.execute("SELECT id AS ID, nombre AS 'Nombre Técnico', usuario AS 'ID Usuario', rol AS 'Especialidad', telefono AS Teléfono, email AS Email FROM usuarios")
        df_usuarios = pd.DataFrame(res_u_df.rows, columns=["ID", "Nombre Técnico", "ID Usuario", "Especialidad", "Teléfono", "Email"]) if res_u_df.rows else pd.DataFrame()
        if not df_usuarios.empty:
            st.dataframe(df_usuarios, use_container_width=True)

with menu[2]:
    st.subheader("📂 Base de Datos de Clientes y Empresas")
    sub_tab_cli = st.tabs(["➕ Alta Manual", "📂 Sincronizar FactuSol", "📋 Listado Clientes"])
    with sub_tab_cli[0]:
        st.markdown("### Registrar Cliente Nuevo")
        with st.form("form_alta_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                c_nombre = st.text_input("Nombre / Razón Social *")
                c_cif = st.text_input("CIF / NIF")
                c_telefono = st.text_input("Teléfono")
            with col2:
                c_email = st.text_input("Correo Electrónico")
                c_direccion = st.text_input("Dirección Postal")
            btn_guardar_cliente = st.form_submit_button("Guardar Cliente")
            if btn_guardar_cliente:
                if not c_nombre.strip():
                    st.error("El nombre del cliente es obligatorio.")
                else:
                    try:
                        conn.execute("INSERT INTO clientes (nombre, cif_nif, telefono, email, direccion) VALUES (?, ?, ?, ?, ?)", (c_nombre, c_cif, c_telefono, c_email, c_direccion))
                        st.success(f"Cliente '{c_nombre}' guardado correctamente.")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
    with sub_tab_cli[1]:
        st.markdown("### Importar desde FactuSol")
        st.info("💡 Exporte sus clientes desde FactuSol a formato **Excel (.xlsx) o CSV** y súbalos aquí.")
        archivo_factusol = st.file_uploader("Subir archivo de clientes FactuSol", type=["csv", "xlsx", "xls"])
        if archivo_factusol is not None:
            try:
                df_factusol = pd.read_csv(archivo_factusol) if archivo_factusol.name.endswith('.csv') else pd.read_excel(archivo_factusol)
                st.write("Vista previa de importación:")
                st.dataframe(df_factusol.head(), use_container_width=True)
                columnas_archivo = list(df_factusol.columns)
                col_map1, col_map2 = st.columns(2)
                with col_map1:
                    col_nom = st.selectbox("Columna de Nombre", columnas_archivo, index=0)
                with col_map2:
                    col_telf = st.selectbox("Columna de Teléfono (Opcional)", ["Ninguna"] + columnas_archivo)
                if st.button("Confirmar Importación Masiva"):
                    importados = 0
                    for _, row in df_factusol.iterrows():
                        nombre = str(row[col_nom]) if pd.notna(row[col_nom]) else ""
                        if not nombre or nombre == "nan": continue
                        telefono = str(row[col_telf]) if col_telf != "Ninguna" and pd.notna(row[col_telf]) else None
                        conn.execute("INSERT INTO clientes (nombre, telefono) VALUES (?, ?)", (nombre, telefono))
                        importados += 1
                    st.success(f"¡Importación finalizada! {importados} clientes añadidos.")
            except Exception as e:
                st.error(f"Error al procesar el fichero: {e}")
    with sub_tab_cli[2]:
        res_c_df = conn.execute("SELECT id AS ID, nombre AS Nombre, cif_nif AS 'CIF/NIF', telefono AS Teléfono, email AS Email, direccion AS Dirección FROM clientes")
        df_clientes = pd.DataFrame(res_c_df.rows, columns=["ID", "Nombre", "CIF/NIF", "Teléfono", "Email", "Dirección"]) if res_c_df.rows else pd.DataFrame()
        if not df_clientes.empty:
            st.dataframe(df_clientes, use_container_width=True)

with menu[3]:
    st.subheader("⚙️ Catálogos de Taller y Almacén")
    sub_tab_cat = st.tabs(["🛠️ Averías Frecuentes", "📦 Stock de Componentes"])
    with sub_tab_cat[0]:
        st.markdown("### Añadir Reparación Habitual")
        with st.form("form_add_rep", clear_on_submit=True):
            titulo_rep = st.text_input("Título de la Avería / Servicio *")
            desc_rep = st.text_area("Descripción estándar por defecto")
            btn_save_rep = st.form_submit_button("Guardar en Catálogo")
            if btn_save_rep:
                if not titulo_rep.strip():
                    st.error("El título es obligatorio.")
                else:
                    try:
                        conn.execute("INSERT OR REPLACE INTO catalogo_reparaciones (titulo, descripcion) VALUES (?, ?)", (titulo_rep, desc_rep))
                        st.success(f"Reparación '{titulo_rep}' guardada.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.markdown("#### Catálogo de Reparaciones Guardadas")
        res_r_df = conn.execute("SELECT id AS ID, titulo AS 'Título Avería', descripcion AS 'Descripción Estándar' FROM catalogo_reparaciones")
        df_reps = pd.DataFrame(res_r_df.rows, columns=["ID", "Título Avería", "Descripción Estándar"]) if res_r_df.rows else pd.DataFrame()
        if not df_reps.empty:
            st.dataframe(df_reps, use_container_width=True)
    with sub_tab_cat[1]:
        st.markdown("### Añadir Componente al Inventario")
        with st.form("form_add_mat", clear_on_submit=True):
            nombre_mat = st.text_input("Nombre del Componente / Material *")
            ref_mat = st.text_input("Referencia / Part Number (Opcional)")
            btn_save_mat = st.form_submit_button("Guardar Material")
            if btn_save_mat:
                if not nombre_mat.strip():
                    st.error("El nombre del componente es obligatorio.")
                else:
                    try:
                        conn.execute("INSERT OR REPLACE INTO catalogo_materiales (nombre, referencia) VALUES (?, ?)", (nombre_mat, ref_mat))
                        st.success(f"Componente '{nombre_mat}' guardado.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        st.markdown("#### Inventario de Materiales Frecuentes")
        res_m_df = conn.execute("SELECT id AS ID, nombre AS 'Componente', referencia AS 'Ref / Part Number' FROM catalogo_materiales")
        df_mats = pd.DataFrame(res_m_df.rows, columns=["ID", "Componente", "Ref / Part Number"]) if res_m_df.rows else pd.DataFrame()
        if not df_mats.empty:
            st.dataframe(df_mats, use_container_width=True)

with menu[4]:
    st.subheader("📋 Registro Global de Intervenciones Técnicas, Descarga PDF y Envío")
    res_todos = conn.execute("SELECT id, fecha, cliente, operario, reparacion, materiales, tiempo, estado, foto_path, firma_path FROM partes ORDER BY id DESC")
    todos_los_partes = res_todos.rows
    if not todos_los_partes:
        st.info("No hay partes registrados en el historial.")
    else:
        for p in todos_los_partes:
            p_id, p_fecha, p_cliente, p_operario, p_rep, p_mat, p_tiempo, p_estado, p_foto, p_firma = p
            with st.container(border=True):
                col_h1, col_h2, col_h3, col_h4 = st.columns([2.2, 1, 1, 1])
                with col_h1:
                    st.markdown(f"### 📄 Parte ID: #{p_id} | 📅 {p_fecha}")
                    st.markdown(f"👤 **Cliente:** {p_cliente} | 🛠️ **Técnico:** {p_operario if p_operario else 'No asignado'} | ⚡ **Estado:** `{p_estado}`")
                    st.markdown(f"💬 *{p_rep}*")
                    st.markdown(f"⏱️ **Tiempo invertido:** {p_tiempo}h | 📦 **Materiales:** {p_mat if p_mat else 'Ninguno'}")
                with col_h2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if REPORTLAB_DISPONIBLE:
                        pdf_path = generar_pdf_parte(p)
                        if pdf_path and os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as pdf_file:
                                st.download_button(
                                    label=f"📥 Descargar PDF",
                                    data=pdf_file,
                                    file_name=f"parte_trabajo_{p_id}.pdf",
                                    mime="application/pdf",
                                    key=f"btn_pdf_{p_id}"
                                )
                with col_h3:
                    st.markdown("<br>", unsafe_allow_html=True)
                    res_mail = conn.execute("SELECT email FROM clientes WHERE nombre = ?", (p_cliente,))
                    email_cliente = res_mail.rows[0][0] if res_mail.rows and res_mail.rows[0][0] else ""
                    
                    asunto = f"Parte de Intervención Técnica #{p_id} - AMP Informática"
                    cuerpo = f"Hola,%0A%0AAdjunto remitimos el parte de intervención técnica número #{p_id} correspondiente a los trabajos realizados.%0A%0AFecha: {p_fecha}%0ATécnico: {p_operario}%0ADescripción: {p_rep}%0A%0AUn saludo,%0AAMP Informática"
                    
                    mailto_link = f"mailto:{email_cliente}?subject={asunto}&body={cuerpo}"
                    
                    st.markdown(
                        f"""<a href="{mailto_link}" target="_blank" style="text-decoration: none;">
                            <div style="background-color: #2563eb; color: white; padding: 0.5rem 0.7rem; border-radius: 6px; text-align: center; font-family: 'Share Tech Mono', monospace; font-weight: 600; border: 1px solid #60a5fa; font-size: 14px;">
                                📧 Enviar Email
                            </div>
                        </a>""",
                        unsafe_allow_html=True
                    )
                with col_h4:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(f"🗑️ Borrar", key=f"btn_del_{p_id}", use_container_width=True):
                        try:
                            if p_foto and os.path.exists(p_foto):
                                os.remove(p_foto)
                            if p_firma and os.path.exists(p_firma):
                                os.remove(p_firma)
                            conn.execute("DELETE FROM partes WHERE id = ?", (p_id,))
                            st.success(f"¡Parte #{p_id} eliminado correctamente!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")

with menu[5]:
    st.subheader("📊 Informes de Taller e Historial de Cliente (Partes Cerrados)")
    res_c_list = conn.execute("SELECT DISTINCT cliente FROM partes WHERE estado = 'Cerrado' ORDER BY cliente ASC")
    clientes_db = [row[0] for row in res_c_list.rows]
    if not clientes_db:
        st.info("No hay partes con estado 'Cerrado' para generar informes o historiales de clientes todavía.")
    else:
        cliente_seleccionado = st.selectbox("Seleccionar Empresa / Cliente", options=clientes_db, key="select_cliente_informe")
        if cliente_seleccionado:
            res_p_cerrados = conn.execute("SELECT id, fecha, cliente, operario, reparacion, materiales, tiempo, estado, foto_path, firma_path FROM partes WHERE cliente = ? AND estado = 'Cerrado' ORDER BY fecha DESC", (cliente_seleccionado,))
            partes_cerrados_cliente = res_p_cerrados.rows
            if partes_cerrados_cliente:
                st.markdown(f"### Historial de Intervenciones Cerradas para: **{cliente_seleccionado}**")
                total_intervenciones = len(partes_cerrados_cliente)
                tiempo_total = sum([p[6] for p in partes_cerrados_cliente])
                col1, col2 = st.columns(2)
                col1.metric("Total Partes Cerrados", total_intervenciones)
                col2.metric("Tiempo Total Invertido", f"{tiempo_total:.2f} horas")
                for pc in partes_cerrados_cliente:
                    pc_id, pc_fecha, pc_cli, pc_op, pc_rep, pc_mat, pc_t, pc_est, pc_fot, pc_fir = pc
                    with st.container(border=True):
                        col_c1, col_c2 = st.columns([3, 1])
                        with col_c1:
                            st.markdown(f"**Parte #{pc_id}** | 📅 {pc_fecha} | ⏱️ {pc_t}h")
                            st.markdown(f"💬 *{pc_rep}*")
                        with col_c2:
                            if REPORTLAB_DISPONIBLE:
                                pdf_path_c = generar_pdf_parte(pc)
                                if pdf_path_c and os.path.exists(pdf_path_c):
                                    with open(pdf_path_c, "rb") as pdf_file_c:
                                        st.download_button(
                                            label=f"📥 PDF #{pc_id}",
                                            data=pdf_file_c,
                                            file_name=f"parte_trabajo_{pc_id}.pdf",
                                            mime="application/pdf",
                                            key=f"btn_pdf_inf_{pc_id}"
                                        )

with menu[6]:
    st.subheader("📚 Base de Conocimiento y Resolución de Casos Complejos")
    sub_tab_bc = st.tabs(["➕ Registrar Solución", "🔍 Buscar en Base de Conocimiento"])
    with sub_tab_bc[0]:
        st.markdown("### Registrar Nuevo Caso Resuelto")
        with st.form("form_add_kb", clear_on_submit=True):
            kb_titulo = st.text_input("Título del Caso / Incidencia *")
            kb_desc = st.text_area("Descripción detallada de la solución paso a paso *", height=200)
            btn_save_kb = st.form_submit_button("Guardar en Base de Conocimiento")
            if btn_save_kb:
                if not kb_titulo.strip() or not kb_desc.strip():
                    st.error("⚠️ Los campos 'Título' y 'Descripción' son obligatorios.")
                else:
                    try:
                        conn.execute("INSERT INTO base_conocimiento (fecha, titulo, descripcion) VALUES (?, ?, ?)", (datetime.now().strftime("%Y-%m-%d %H:%M"), kb_titulo, kb_desc))
                        st.success("¡Solución técnica registrada en la Base de Conocimiento con éxito!")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
    with sub_tab_bc[1]:
        busqueda_kb = st.text_input("🔍 Buscar por palabra clave en títulos o descripciones")
        if busqueda_kb:
            res_kb = conn.execute("SELECT id AS ID, fecha AS Fecha, titulo AS Título, descripcion AS Descripción FROM base_conocimiento WHERE titulo LIKE ? OR descripcion LIKE ? ORDER BY id DESC", (f"%{busqueda_kb}%", f"%{busqueda_kb}%"))
        else:
            res_kb = conn.execute("SELECT id AS ID, fecha AS Fecha, titulo AS Título, descripcion AS Descripción FROM base_conocimiento ORDER BY id DESC")
        
        df_kb = pd.DataFrame(res_kb.rows, columns=["ID", "Fecha", "Título", "Descripción"]) if res_kb.rows else pd.DataFrame()
        if not df_kb.empty:
            for _, row in df_kb.iterrows():
                with st.container(border=True):
                    st.markdown(f"#### 📌 [{row['ID']}] {row['Título']}")
                    st.markdown(f"<small style='color: #94a3b8;'>📅 Registrado: {row['Fecha']}</small>", unsafe_allow_html=True)
                    st.markdown("---")
                    st.text(row['Descripción'])

with menu[7]:
    st.subheader("🏢 Configuración de los Datos de la Empresa")
    empresa_actual = obtener_datos_empresa()
    with st.form("form_config_empresa"):
        c_nombre = st.text_input("Nombre / Razón Social de la Empresa", value=empresa_actual["nombre"])
        c_cif = st.text_input("CIF / NIF", value=empresa_actual["cif"])
        c_dir = st.text_input("Dirección Postal del Taller", value=empresa_actual["direccion"])
        c_telf = st.text_input("Teléfono de Contacto", value=empresa_actual["telefono"])
        c_email = st.text_input("Correo Electrónico Corporativo", value=empresa_actual["email"])
        c_web = st.text_input("Sitio Web", value=empresa_actual["web"])
        btn_guardar_empresa = st.form_submit_button("💾 Guardar Datos de Empresa")
        if btn_guardar_empresa:
            try:
                conn.execute("DELETE FROM empresa_config")
                conn.execute("INSERT INTO empresa_config (nombre_empresa, cif, direccion, telefono, email, web) VALUES (?, ?, ?, ?, ?, ?)", (c_nombre, c_cif, c_dir, c_telf, c_email, c_web))
                st.success("¡Datos de la empresa actualizados correctamente!")
            except Exception as e:
                st.error(f"Error al actualizar la configuración: {e}")
