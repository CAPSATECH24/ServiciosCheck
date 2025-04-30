import streamlit as st
import pandas as pd
import io
from datetime import date
import numpy as np

# --- Configuración de la página ---
st.set_page_config(layout="wide", page_title="Análisis de Datos por Cliente, Fecha y Ejecutivo")

# Title for the Streamlit app
st.title("📊 Análisis de Datos por Cliente, Fecha y Ejecutivo")

# --- Enlace a Notion ---
st.markdown(
    "Fuente de datos original: "
    "[Vista Notion](https://www.notion.so/4bc5d60d53494515a3b219ac9b718ac2?v=daa6506e3f1e43fa9be3d74420ec1b27)",
    help="Haz clic para ir a la vista de Notion desde donde se exporta el CSV."
)
# -----------------------------

st.markdown("Carga tu archivo CSV, configura los filtros y presiona **'Buscar Resultados'**.")

# --- Estado de Sesión ---
if 'search_triggered' not in st.session_state: st.session_state.search_triggered = False
if 'expand_all_details' not in st.session_state: st.session_state.expand_all_details = False
if 'data_loaded' not in st.session_state: st.session_state.data_loaded = False
if 'loaded_df' not in st.session_state: st.session_state.loaded_df = pd.DataFrame()
if 'unique_clients' not in st.session_state: st.session_state.unique_clients = []
if 'unique_executives' not in st.session_state: st.session_state.unique_executives = []
if 'min_date' not in st.session_state: st.session_state.min_date = None
if 'max_date' not in st.session_state: st.session_state.max_date = None
if 'last_uploaded_filename' not in st.session_state: st.session_state.last_uploaded_filename = None
if 'selected_client_on_search' not in st.session_state: st.session_state.selected_client_on_search = "Todos"
if 'selected_executive_on_search' not in st.session_state: st.session_state.selected_executive_on_search = "Todos"
if 'date_range_on_search' not in st.session_state: st.session_state.date_range_on_search = (None, None)


# --- Función de Estilo para Colorear Texto ---
def highlight_status(row):
    """Aplica color de TEXTO a la fila basado en 'Avance Cotización'."""
    color_texto_garantia = 'color: #ADD8E6' # LightBlue
    color_texto_cotizado = 'color: #90EE90' # LightGreen
    default_color = ''
    status_column = 'Avance Cotización'
    style = [default_color] * len(row)
    if status_column in row:
        status_value = str(row[status_column]).lower()
        if 'garantia' in status_value or 'garantía' in status_value :
            style = [color_texto_garantia] * len(row)
        elif 'cotiza' in status_value:
            style = [color_texto_cotizado] * len(row)
    return style

# --- Lógica Principal ---

# File uploader
uploaded_file = st.file_uploader("📂 1. Carga tu archivo CSV", type=["csv"])

# Procesar el archivo SOLO si es nuevo o no se ha cargado antes
if uploaded_file is not None:
    is_new_file = (st.session_state.last_uploaded_filename != uploaded_file.name)
    if is_new_file:
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.data_loaded = False
        st.session_state.search_triggered = False

        with st.spinner("Procesando archivo..."):
            try:
                # --- Carga y Procesamiento Inicial ---
                try:
                    stringio = io.StringIO(uploaded_file.getvalue().decode('utf-8'))
                    df_raw = pd.read_csv(stringio)
                except UnicodeDecodeError:
                    stringio = io.StringIO(uploaded_file.getvalue().decode('latin1'))
                    df_raw = pd.read_csv(stringio)

                # --- Data Cleaning and Preparation ---
                client_col_name = 'CLIENTES SATECH'
                date_col_name = 'FECHA'
                executive_col_name = 'EJECUTIVO'
                status_col_name = 'Avance Cotización'
                col_to_split = 'DESCRIPTION'

                final_display_columns = [
                    'FECHA', 'Avance Cotización', 'Folio Cotización', 'UNIDAD MARINE',
                    'IMEI REAL', 'TECNICO', 'EJECUTIVO', 'CONCEPTO', 'TICKET NOTION'
                ]

                client_col_cleaned = 'CLIENTE_NOMBRE' # Columna interna para nombre limpio
                date_col_cleaned = 'FECHA_DT'
                date_col_display = 'Fecha_Solo'

                df = df_raw.copy()

                # Verificar columnas esenciales
                required_processing_cols = set(final_display_columns) | {client_col_name, date_col_name, executive_col_name, status_col_name}
                if 'CONCEPTO' not in df.columns and col_to_split not in df.columns:
                    st.error(f"Se necesita la columna 'CONCEPTO' o la columna '{col_to_split}' para generarla.")
                    st.stop()
                elif 'CONCEPTO' not in df.columns:
                    required_processing_cols.add(col_to_split)

                if executive_col_name not in df.columns:
                    st.error(f"Falta la columna '{executive_col_name}' en el archivo.")
                    st.stop()
                if status_col_name not in df.columns:
                    st.error(f"Falta la columna '{status_col_name}' necesaria para colorear y calcular porcentajes.")
                    st.stop()

                missing_cols = required_processing_cols - set(df.columns)
                if missing_cols:
                    missing_display = missing_cols - {'CONCEPTO'} if 'CONCEPTO' not in df_raw.columns else missing_cols
                    if missing_display:
                        st.error(f"Faltan columnas esenciales en el archivo: {missing_display}")
                        st.stop()

                # Generar CONCEPTO si no existe
                if 'CONCEPTO' not in df.columns:
                    st.info(f"Generando 'CONCEPTO' desde '{col_to_split}'...")
                    df[col_to_split] = df[col_to_split].astype(str)
                    split_cols = df[col_to_split].str.split(':', n=1, expand=True)
                    df['CONCEPTO'] = split_cols[0].str.strip()
                    st.success(f"Columna 'CONCEPTO' generada.")

                # Limpieza de cliente (crea CLIENTE_NOMBRE)
                df[client_col_cleaned] = df[client_col_name].astype(str).str.split('(', expand=True)[0].str.strip()
                df[client_col_cleaned] = df[client_col_cleaned].fillna(df[client_col_name].astype(str).str.strip()) # Usar original si split falla
                st.session_state.unique_clients = sorted(df[client_col_cleaned].dropna().unique())

                # Limpieza y obtención de ejecutivos únicos
                df[executive_col_name] = df[executive_col_name].fillna('').astype(str).str.strip()
                st.session_state.unique_executives = sorted(df[executive_col_name].replace('', np.nan).dropna().unique())

                # Conversión de fecha
                df[date_col_cleaned] = pd.to_datetime(df[date_col_name], errors='coerce', infer_datetime_format=True)
                if df[date_col_cleaned].isnull().all():
                    st.error("No se pudo convertir la columna 'FECHA'. Verifica el formato.")
                    st.stop()
                elif df[date_col_cleaned].isnull().any():
                    st.warning("Algunas fechas no pudieron ser convertidas.")

                df_valid_dates = df.dropna(subset=[date_col_cleaned])
                if df_valid_dates.empty:
                    st.error("No hay fechas válidas en la columna 'FECHA'.")
                    st.stop()
                df[date_col_display] = df_valid_dates[date_col_cleaned].dt.date
                st.session_state.min_date = df[date_col_display].min()
                st.session_state.max_date = df[date_col_display].max()

                # Llenar NAs en columnas relevantes
                cols_to_fill_na = [status_col_name, 'TICKET NOTION', 'Folio Cotización', 'TECNICO', 'UNIDAD MARINE', 'IMEI REAL', 'CONCEPTO']
                for col in cols_to_fill_na:
                    if col in df.columns:
                        df[col] = df[col].fillna('')

                st.session_state.loaded_df = df
                st.session_state.data_loaded = True
                st.success(f"Archivo '{uploaded_file.name}' procesado.")

            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.session_state.data_loaded = False
                st.session_state.loaded_df = pd.DataFrame()
                st.stop()
            st.rerun()

# Mostrar filtros solo si los datos se cargaron correctamente
if st.session_state.data_loaded:
    df_loaded = st.session_state.loaded_df
    final_display_columns = [
        'FECHA', 'Avance Cotización', 'Folio Cotización', 'UNIDAD MARINE',
        'IMEI REAL', 'TECNICO', 'EJECUTIVO', 'CONCEPTO', 'TICKET NOTION'
    ]
    client_col_name = 'CLIENTES SATECH'
    executive_col_name = 'EJECUTIVO'
    status_col_name = 'Avance Cotización'
    client_col_cleaned = 'CLIENTE_NOMBRE' # Nombre limpio para filtros y agrupación

    # --- Streamlit UI Elements (Sidebar) ---
    st.sidebar.header("⚙️ 2. Filtros")

    selected_client = st.sidebar.selectbox(
        "👥 Selecciona un Cliente",
        options=["Todos"] + st.session_state.unique_clients,
        key="client_selector"
    )

    selected_executive = st.sidebar.selectbox(
        "🧑‍💼 Selecciona un Ejecutivo",
        options=["Todos"] + st.session_state.unique_executives,
        key="executive_selector"
    )

    st.sidebar.subheader("📅 Rango de Fechas")
    min_date_obj = st.session_state.min_date if isinstance(st.session_state.min_date, date) else date.min
    max_date_obj = st.session_state.max_date if isinstance(st.session_state.max_date, date) else date.max
    default_start = min_date_obj if min_date_obj else date.today()
    default_end = max_date_obj if max_date_obj else date.today()
    if default_start > default_end: default_start = default_end

    date_range = st.sidebar.date_input(
        "Selecciona el rango",
        value=(default_start, default_end),
        min_value=min_date_obj,
        max_value=max_date_obj,
        key="date_range_selector"
    )

    # --- Botón de Búsqueda ---
    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 Buscar Resultados", key="search_button", type="primary"):
        st.session_state.search_triggered = True
        st.session_state.selected_client_on_search = selected_client
        st.session_state.selected_executive_on_search = selected_executive
        st.session_state.date_range_on_search = date_range
        st.session_state.expand_all_details = False

    # --- Display Results (Conditional) ---
    st.markdown("---")
    st.header("📊 3. Resultados")

    if st.session_state.search_triggered:
        client_to_filter = st.session_state.selected_client_on_search
        executive_to_filter = st.session_state.selected_executive_on_search
        date_range_to_filter = st.session_state.date_range_on_search

        if len(date_range_to_filter) == 2:
            start_date, end_date = date_range_to_filter
        else:
            start_date = st.session_state.min_date
            end_date = st.session_state.max_date
            st.warning("Rango de fechas inválido, mostrando todos los datos dentro de los otros filtros.")

        # --- Filtering Logic ---
        filtered_df = df_loaded.copy()

        if client_to_filter != "Todos":
            # Filtrar usando la columna de nombre limpio
            filtered_df = filtered_df[filtered_df[client_col_cleaned] == client_to_filter]

        if executive_to_filter != "Todos":
            filtered_df = filtered_df[filtered_df[executive_col_name] == executive_to_filter]

        if start_date and end_date:
            if not isinstance(start_date, date): start_date = pd.to_datetime(start_date).date()
            if not isinstance(end_date, date): end_date = pd.to_datetime(end_date).date()

            filtered_df['Fecha_Solo'] = pd.to_datetime(filtered_df['Fecha_Solo'], errors='coerce').dt.date
            filtered_df = filtered_df.dropna(subset=['Fecha_Solo'])

            filtered_df = filtered_df[
                (filtered_df['Fecha_Solo'] >= start_date) &
                (filtered_df['Fecha_Solo'] <= end_date)
            ]
        elif start_date or end_date:
             st.warning("Se requiere seleccionar una fecha de inicio y fin para filtrar por rango.")

        # --- Display Grouped Results ---
        if filtered_df.empty:
            st.warning("No hay datos que coincidan con los filtros seleccionados.")
        else:
            # --- Mostrar grupos por fecha/cliente (sin cambios) ---
            try:
                if 'Fecha_Solo' in filtered_df.columns:
                    grouped = filtered_df.sort_values(by=['Fecha_Solo', client_col_cleaned])\
                                         .groupby(['Fecha_Solo', client_col_cleaned], sort=False, dropna=False)
                    num_groups = len(grouped)
                    total_rows_filtered = len(filtered_df)
                    st.write(f"Mostrando {total_rows_filtered} registros en {num_groups} grupo(s) de Fecha/Cliente:")

                    col_btn1, col_btn2, _ = st.columns([1, 1, 5])
                    def set_expand_all(value): st.session_state.expand_all_details = value
                    with col_btn1: st.button("➕ Expandir Todo", key="btn_expand", on_click=set_expand_all, args=(True,))
                    with col_btn2: st.button("➖ Contraer Todo", key="btn_collapse", on_click=set_expand_all, args=(False,))

                    for (date_val, client_name_val), group in grouped:
                        # Usar el nombre original del cliente para la etiqueta del expander si está disponible
                        client_display_name_orig = group[client_col_name].iloc[0] if not group.empty and client_col_name in group and pd.notna(group[client_col_name].iloc[0]) else client_name_val
                        date_str = date_val.strftime('%Y-%m-%d') if pd.notna(date_val) else "Fecha Desconocida"
                        expander_label = f"🗓️ {date_str} - 👤 {client_display_name_orig}"

                        with st.expander(expander_label, expanded=st.session_state.expand_all_details):
                            existing_final_cols = [col for col in final_display_columns if col in group.columns]
                            display_group_df = group[existing_final_cols].reset_index(drop=True).copy()
                            display_group_df.fillna('', inplace=True)
                            if 'FECHA' in display_group_df.columns:
                                 display_group_df['FECHA'] = pd.to_datetime(display_group_df['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                                 display_group_df['FECHA'] = display_group_df['FECHA'].fillna('')
                            styled_group_df = display_group_df.style.apply(highlight_status, axis=1)
                            st.dataframe(styled_group_df, hide_index=True, use_container_width=True)
                else:
                    st.error("La columna 'Fecha_Solo' necesaria para agrupar no se pudo generar correctamente.")
            except Exception as e:
                st.error(f"Ocurrió un error al intentar agrupar y mostrar los resultados: {e}")
                st.exception(e)

            # --- Tabla Completa Filtrada (Opcional) ---
            st.markdown("---")
            with st.expander("Ver tabla completa filtrada (columnas seleccionadas)", expanded=False):
                 try:
                     existing_final_cols_full = [col for col in final_display_columns if col in filtered_df.columns]
                     full_display_df = filtered_df[existing_final_cols_full].copy()
                     full_display_df.fillna('', inplace=True)
                     if 'FECHA' in full_display_df.columns:
                         full_display_df['FECHA'] = pd.to_datetime(full_display_df['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                         full_display_df['FECHA'] = full_display_df['FECHA'].fillna('')
                     styled_full_df = full_display_df.style.apply(highlight_status, axis=1)
                     st.dataframe(styled_full_df, hide_index=True, use_container_width=True)
                 except Exception as e_table:
                     st.error(f"Error al mostrar la tabla completa: {e_table}")

            # --- SECCIÓN: Resumen General y por Cliente ---
            st.markdown("---")
            st.subheader("📈 Resumen de Avance (Cotizado vs Garantía)")
            try:
                if status_col_name in filtered_df:
                    # --- Resumen General (sin cambios) ---
                    status_series = filtered_df[status_col_name].astype(str).str.lower()
                    count_cotizado_total = status_series.str.contains('cotiza', na=False).sum()
                    count_garantia_total = status_series.str.contains('garantía|garantia', na=False, regex=True).sum()
                    total_relevant_total = count_cotizado_total + count_garantia_total

                    if total_relevant_total > 0:
                        perc_cotizado_total = (count_cotizado_total / total_relevant_total) * 100
                        perc_garantia_total = (count_garantia_total / total_relevant_total) * 100
                        st.markdown(f"**Total General (Cotizado + Garantía):** {total_relevant_total}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(label="Cotizado (General)", value=f"{perc_cotizado_total:.1f}%", delta=f"{count_cotizado_total} registros", delta_color="off")
                        with col2:
                            st.metric(label="Garantía (General)", value=f"{perc_garantia_total:.1f}%", delta=f"{count_garantia_total} registros", delta_color="off")
                    else:
                        st.info("No se encontraron registros generales 'Cotizado' o 'Garantía' para calcular porcentajes.")

                    # --- NUEVO: Desglose por Cliente ---
                    st.markdown("---")
                    st.markdown("#### Desglose por Cliente")

                    # Agrupar por el nombre limpio del cliente
                    client_summary = filtered_df.groupby(client_col_cleaned).agg(
                        Total_Registros=(status_col_name, 'size'), # Contar total por cliente
                        Cotizado_Count=(status_col_name, lambda x: x.astype(str).str.lower().str.contains('cotiza', na=False).sum()),
                        Garantia_Count=(status_col_name, lambda x: x.astype(str).str.lower().str.contains('garantía|garantia', na=False, regex=True).sum())
                    ).reset_index() # Convertir índice (cliente) a columna

                    # Calcular total relevante y porcentajes por cliente
                    client_summary['Total_Relevante'] = client_summary['Cotizado_Count'] + client_summary['Garantia_Count']
                    client_summary['Cotizado_%'] = client_summary.apply(
                        lambda row: (row['Cotizado_Count'] / row['Total_Relevante'] * 100) if row['Total_Relevante'] > 0 else 0, axis=1
                    )
                    client_summary['Garantia_%'] = client_summary.apply(
                        lambda row: (row['Garantia_Count'] / row['Total_Relevante'] * 100) if row['Total_Relevante'] > 0 else 0, axis=1
                    )

                    # Seleccionar y renombrar columnas para mostrar
                    summary_display = client_summary[[
                        client_col_cleaned, 'Cotizado_Count', 'Garantia_Count', 'Total_Relevante', 'Cotizado_%', 'Garantia_%'
                    ]].rename(columns={
                        client_col_cleaned: 'Cliente',
                        'Cotizado_Count': 'Cotizados (#)',
                        'Garantia_Count': 'Garantías (#)',
                        'Total_Relevante': 'Total C+G',
                        'Cotizado_%': 'Cotizado (%)',
                        'Garantia_%': 'Garantía (%)'
                    })

                    # Mostrar tabla de desglose
                    if not summary_display.empty:
                        st.dataframe(
                            summary_display.style.format({
                                'Cotizado (%)': '{:.1f}%',
                                'Garantía (%)': '{:.1f}%'
                            }),
                            hide_index=True,
                            use_container_width=True
                        )

                        # --- NUEVO: Gráfico por Cliente ---
                        st.markdown("#### Visualización por Cliente (Cantidad)")
                        # Preparar datos para el gráfico (solo conteos)
                        chart_data = client_summary[[client_col_cleaned, 'Cotizado_Count', 'Garantia_Count']].rename(columns={
                            client_col_cleaned: 'Cliente',
                            'Cotizado_Count': 'Cotizado',
                            'Garantia_Count': 'Garantía'
                        }).set_index('Cliente') # Cliente como índice para st.bar_chart

                        # Filtrar clientes con al menos un registro relevante para el gráfico
                        chart_data_filtered = chart_data[chart_data.sum(axis=1) > 0]

                        if not chart_data_filtered.empty:
                           st.bar_chart(chart_data_filtered)
                        else:
                           st.info("No hay datos suficientes por cliente para generar el gráfico.")

                    else:
                        st.info("No se encontraron datos por cliente para generar el desglose.")


                else:
                    st.warning(f"La columna '{status_col_name}' no se encontró en los datos filtrados para calcular el resumen.")

            except Exception as e_summary:
                st.error(f"Error al calcular el resumen de avance: {e_summary}")
                st.exception(e_summary)
            # --- FIN SECCIÓN ---

    elif st.session_state.data_loaded and not st.session_state.search_triggered:
        st.info("👆 Configura los filtros en la barra lateral y presiona 'Buscar Resultados'.")

elif not uploaded_file:
    st.info("Por favor, carga un archivo CSV para comenzar el análisis.")

