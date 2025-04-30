# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io
from datetime import date, datetime, time # Asegúrate de importar time
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
# Initialize session state variables if they don't exist
default_values = {
    'search_triggered': False,
    'expand_all_details': False,
    'data_loaded': False,
    'loaded_df': pd.DataFrame(),
    'unique_clients': [],
    'unique_executives': [],
    'min_date': None,
    'max_date': None, # Guardará la fecha máxima encontrada en el CSV
    'last_uploaded_filename': None,
    'selected_client_on_search': "Todos",
    'selected_executive_on_search': "Todos",
    'date_range_on_search': (None, None) # Guarda el rango de la última búsqueda
}
for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# --- Función de Estilo para Colorear Texto ---
def highlight_status(row):
    """Aplica color de TEXTO a la fila basado en 'Avance Cotización'."""
    color_texto_garantia = 'color: #ADD8E6' # LightBlue
    color_texto_cotizado = 'color: #90EE90' # LightGreen
    default_color = ''
    status_column = 'Avance Cotización'
    style = [default_color] * len(row)
    # Check if the status column exists in the row's index (safer than checking row directly)
    if status_column in row.index:
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
    # Process if it's a new file OR if data wasn't successfully loaded last time
    if is_new_file or not st.session_state.data_loaded:
        st.session_state.last_uploaded_filename = uploaded_file.name
        # Reset states related to data processing
        st.session_state.data_loaded = False
        st.session_state.search_triggered = False
        st.session_state.min_date = None
        st.session_state.max_date = None # Reset max_date for the new file
        st.session_state.unique_clients = []
        st.session_state.unique_executives = []
        st.session_state.loaded_df = pd.DataFrame()
        # Resetea el rango de búsqueda guardado al cargar nuevo archivo
        st.session_state.date_range_on_search = (None, None)


        with st.spinner("Procesando archivo..."):
            try:
                # --- Carga y Procesamiento Inicial ---
                try:
                    stringio = io.StringIO(uploaded_file.getvalue().decode('utf-8'))
                    df_raw = pd.read_csv(stringio)
                except UnicodeDecodeError:
                    st.info("Error con UTF-8, intentando con Latin-1...")
                    stringio = io.StringIO(uploaded_file.getvalue().decode('latin1'))
                    df_raw = pd.read_csv(stringio)
                except Exception as e_read:
                     st.error(f"Error al leer el CSV: {e_read}. Asegúrate de que sea un CSV válido.")
                     st.stop()

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
                client_col_cleaned = 'CLIENTE_NOMBRE'
                date_col_cleaned = 'FECHA_DT'
                date_col_display = 'Fecha_Solo'
                df = df_raw.copy()

                # --- Column Validation (sin cambios) ---
                required_processing_cols = set(final_display_columns) | {client_col_name, date_col_name, executive_col_name, status_col_name}
                has_concepto = 'CONCEPTO' in df.columns
                has_description = col_to_split in df.columns
                if not has_concepto and not has_description:
                    st.error(f"Se necesita la columna 'CONCEPTO' o la columna '{col_to_split}' para generarla.")
                    st.stop()
                elif not has_concepto:
                    required_processing_cols.add(col_to_split)
                essential_cols = {client_col_name, date_col_name, executive_col_name, status_col_name}
                missing_essential = essential_cols - set(df.columns)
                if missing_essential:
                    st.error(f"Faltan columnas esenciales en el archivo: {missing_essential}")
                    st.stop()
                missing_display = set(final_display_columns) - set(df.columns)
                if not has_concepto and col_to_split in df.columns:
                    missing_display.discard('CONCEPTO')
                if missing_display:
                       st.warning(f"Faltan algunas columnas que se usan para mostrar resultados: {missing_display}. Se mostrarán las columnas disponibles.")
                       final_display_columns = [col for col in final_display_columns if col in df.columns or (col == 'CONCEPTO' and not has_concepto)]

                # --- Data Transformation (sin cambios) ---
                if not has_concepto and has_description:
                    st.info(f"Generando 'CONCEPTO' desde '{col_to_split}'...")
                    df[col_to_split] = df[col_to_split].fillna('').astype(str)
                    split_cols = df[col_to_split].str.split(':', n=1, expand=True)
                    df['CONCEPTO'] = split_cols[0].str.strip()
                    if 'CONCEPTO' not in missing_display and 'CONCEPTO' not in final_display_columns:
                        try:
                            idx = final_display_columns.index('EJECUTIVO')
                            final_display_columns.insert(idx + 1, 'CONCEPTO')
                        except ValueError:
                            final_display_columns.append('CONCEPTO')
                    st.success(f"Columna 'CONCEPTO' generada.")

                df[client_col_name] = df[client_col_name].fillna('Desconocido').astype(str)
                df[client_col_cleaned] = df[client_col_name].str.split('(', n=1, expand=True)[0].str.strip()
                df[client_col_cleaned] = df[client_col_cleaned].replace('', 'Desconocido')
                df.loc[df[client_col_name] == 'Desconocido', client_col_cleaned] = 'Desconocido'
                st.session_state.unique_clients = sorted(df[client_col_cleaned].unique())

                df[executive_col_name] = df[executive_col_name].fillna('').astype(str).str.strip()
                st.session_state.unique_executives = sorted(df[executive_col_name][df[executive_col_name] != ''].unique())

                # --- Date Processing (sin cambios) ---
                st.info(f"Procesando columna de fecha: '{date_col_name}'...")
                df[date_col_cleaned] = pd.to_datetime(df[date_col_name], errors='coerce', infer_datetime_format=True)
                invalid_date_count = df[date_col_cleaned].isnull().sum()
                if invalid_date_count > 0:
                    st.warning(f"{invalid_date_count} fechas no pudieron ser convertidas y serán ignoradas en filtros y agrupaciones.")
                df[date_col_display] = df[date_col_cleaned].dt.date
                valid_dates = df[date_col_display].dropna()
                if not valid_dates.empty:
                    st.session_state.min_date = valid_dates.min()
                    st.session_state.max_date = valid_dates.max() # Guarda la fecha máxima real
                    st.info(f"Rango de fechas detectado: {st.session_state.min_date} a {st.session_state.max_date}")
                else:
                    st.error("No se encontraron fechas válidas en la columna 'FECHA'. No se pueden establecer filtros de fecha.")
                    st.session_state.min_date = date.today()
                    st.session_state.max_date = date.today()

                # Fill NAs (sin cambios)
                cols_to_fill_na = [status_col_name, 'TICKET NOTION', 'Folio Cotización', 'TECNICO', 'UNIDAD MARINE', 'IMEI REAL', 'CONCEPTO']
                for col in cols_to_fill_na:
                    if col in df.columns:
                        df[col] = df[col].fillna('')

                # Store the processed DataFrame
                st.session_state.loaded_df = df
                st.session_state.data_loaded = True
                st.success(f"Archivo '{uploaded_file.name}' procesado exitosamente.")

            except Exception as e:
                st.error(f"Error inesperado al procesar el archivo: {e}")
                st.session_state.data_loaded = False
                st.session_state.loaded_df = pd.DataFrame()
                st.exception(e)
                st.stop()

        st.rerun()

# --- UI Elements (Only if data is loaded) ---
if st.session_state.data_loaded:
    df_loaded = st.session_state.loaded_df
    final_display_columns = [
        'FECHA', 'Avance Cotización', 'Folio Cotización', 'UNIDAD MARINE',
        'IMEI REAL', 'TECNICO', 'EJECUTIVO', 'CONCEPTO', 'TICKET NOTION'
    ]
    final_display_columns = [col for col in final_display_columns if col in df_loaded.columns]
    client_col_name = 'CLIENTES SATECH'
    executive_col_name = 'EJECUTIVO'
    status_col_name = 'Avance Cotización'
    client_col_cleaned = 'CLIENTE_NOMBRE'
    date_col_display = 'Fecha_Solo'


    # --- Sidebar Filters ---
    st.sidebar.header("⚙️ 2. Filtros")

    # Selectores de Cliente y Ejecutivo (sin cambios)
    selected_client = st.sidebar.selectbox(
        "👥 Selecciona un Cliente",
        options=["Todos"] + st.session_state.unique_clients,
        index=0 if st.session_state.selected_client_on_search == "Todos" else (st.session_state.unique_clients.index(st.session_state.selected_client_on_search) + 1 if st.session_state.selected_client_on_search in st.session_state.unique_clients else 0),
        key="client_selector"
    )
    selected_executive = st.sidebar.selectbox(
        "🧑‍💼 Selecciona un Ejecutivo",
        options=["Todos"] + st.session_state.unique_executives,
        index=0 if st.session_state.selected_executive_on_search == "Todos" else (st.session_state.unique_executives.index(st.session_state.selected_executive_on_search) + 1 if st.session_state.selected_executive_on_search in st.session_state.unique_executives else 0),
        key="executive_selector"
    )

    st.sidebar.subheader("📅 Rango de Fechas")
    # --- Robust Date Input Setup ---
    min_val_dt = st.session_state.min_date if isinstance(st.session_state.min_date, date) else date.today()
    max_val_dt = st.session_state.max_date if isinstance(st.session_state.max_date, date) else date.today()

    if min_val_dt > max_val_dt:
        st.warning(f"La fecha mínima ({min_val_dt}) en los datos es posterior a la máxima ({max_val_dt}). Usando {max_val_dt} como rango.")
        min_val_dt = max_val_dt

    # --- MODIFICACIÓN CLAVE: Lógica para valores por defecto del date_input ---
    last_start, last_end = st.session_state.date_range_on_search
    last_start_valid = isinstance(last_start, date)
    last_end_valid = isinstance(last_end, date)

    # Si hay un rango válido de una búsqueda anterior, usarlo.
    if last_start_valid and last_end_valid:
        default_start = last_start
        default_end = last_end
    # Si NO hay rango de búsqueda anterior (carga inicial o nuevo archivo):
    # Establecer AMBOS valores por defecto a la fecha MÁXIMA (más reciente).
    else:
        default_start = max_val_dt # <--- CAMBIO
        default_end = max_val_dt   # <--- CAMBIO
    # --- FIN MODIFICACIÓN ---

    # Asegurar que los valores por defecto estén dentro de los límites del widget
    # (Importante si se usó un rango de búsqueda anterior que ahora está fuera de los límites del nuevo archivo)
    default_start = max(default_start, min_val_dt) # No puede ser menor que la mínima global
    default_start = min(default_start, max_val_dt) # No puede ser mayor que la máxima global
    default_end = max(default_end, min_val_dt)   # No puede ser menor que la mínima global
    default_end = min(default_end, max_val_dt)   # No puede ser mayor que la máxima global

    # Asegurar que start <= end (aunque con la nueva lógica rara vez será necesario)
    if default_start > default_end:
         default_start = default_end # Opcional: ajustar si algo sale mal

    # El widget date_input
    date_range = st.sidebar.date_input(
        "Selecciona el rango",
        # value ahora será (max_date, max_date) por defecto tras cargar archivo
        value=(default_start, default_end),
        min_value=min_val_dt, # El límite inferior sigue siendo la fecha más antigua
        max_value=max_val_dt, # El límite superior sigue siendo la fecha más reciente
        key="date_range_selector"
    )
    # --- End Robust Date Input Setup ---

    # --- Search Button (sin cambios) ---
    st.sidebar.markdown("---")
    if st.sidebar.button("🚀 Buscar Resultados", key="search_button", type="primary"):
        st.session_state.search_triggered = True
        st.session_state.selected_client_on_search = selected_client
        st.session_state.selected_executive_on_search = selected_executive
        if len(date_range) == 2:
            # Guarda el rango *seleccionado* por el usuario para esta búsqueda
            st.session_state.date_range_on_search = date_range
        else:
            st.warning("Rango de fechas inválido seleccionado. Usando el rango completo de datos.")
            st.session_state.date_range_on_search = (st.session_state.min_date, st.session_state.max_date)

        st.session_state.expand_all_details = False
        st.rerun()

    # --- Display Results (sin cambios en el resto del código) ---
    st.markdown("---")
    st.header("📊 3. Resultados")

    if st.session_state.search_triggered:
        # --- Código de filtrado y visualización sin cambios ---
        client_to_filter = st.session_state.selected_client_on_search
        executive_to_filter = st.session_state.selected_executive_on_search
        date_range_to_filter = st.session_state.date_range_on_search

        # --- Filtering Logic ---
        filtered_df = df_loaded.copy()

        if client_to_filter != "Todos":
            filtered_df = filtered_df[filtered_df[client_col_cleaned] == client_to_filter]
        if executive_to_filter != "Todos":
            filtered_df = filtered_df[filtered_df[executive_col_name] == executive_to_filter]

        if len(date_range_to_filter) == 2 and date_range_to_filter[0] is not None and date_range_to_filter[1] is not None:
            start_date, end_date = date_range_to_filter
            if not isinstance(start_date, date): start_date = datetime.combine(start_date, time.min).date()
            if not isinstance(end_date, date): end_date = datetime.combine(end_date, time.min).date()

            if date_col_display in filtered_df:
                try:
                    filtered_df[date_col_display] = pd.to_datetime(filtered_df[date_col_display], errors='coerce').dt.date
                    filtered_df_dated = filtered_df.dropna(subset=[date_col_display])
                    if not filtered_df_dated.empty:
                         filtered_df = filtered_df_dated[
                             (filtered_df_dated[date_col_display] >= start_date) &
                             (filtered_df_dated[date_col_display] <= end_date)
                         ]
                    else:
                         filtered_df = pd.DataFrame(columns=filtered_df.columns)
                except Exception as e_date_filter:
                    st.error(f"Error al convertir o filtrar fechas: {e_date_filter}")
                    filtered_df = pd.DataFrame(columns=filtered_df.columns)
            else:
                st.warning(f"La columna de fecha '{date_col_display}' no está disponible para filtrar.")
        else:
            st.warning("No se aplicó filtro de fecha porque el rango seleccionado o guardado era inválido.")

        # --- Display Grouped Results (sin cambios) ---
        if filtered_df.empty:
            st.warning("No hay datos que coincidan con los filtros seleccionados.")
        else:
            st.write(f"Mostrando {len(filtered_df)} registros filtrados.")
            try:
                if date_col_display in filtered_df.columns and client_col_cleaned in filtered_df.columns:
                    try:
                        filtered_df[date_col_display] = pd.to_datetime(filtered_df[date_col_display], errors='coerce').dt.date
                    except: pass

                    grouped = filtered_df.sort_values(by=[date_col_display, client_col_cleaned])\
                                     .groupby([date_col_display, client_col_cleaned], sort=False, dropna=False)

                    num_groups = len(grouped)
                    st.write(f"Agrupados por Fecha/Cliente en {num_groups} grupo(s):")

                    col_btn1, col_btn2, _ = st.columns([1, 1, 5])
                    def set_expand_all(value): st.session_state.expand_all_details = value
                    with col_btn1: st.button("➕ Expandir Todo", key="btn_expand", on_click=set_expand_all, args=(True,))
                    with col_btn2: st.button("➖ Contraer Todo", key="btn_collapse", on_click=set_expand_all, args=(False,))

                    for (date_val, client_name_val), group in grouped:
                        client_display_name_orig = group[client_col_name].iloc[0] if not group.empty and client_col_name in group and pd.notna(group[client_col_name].iloc[0]) else client_name_val
                        date_str = date_val.strftime('%Y-%m-%d') if pd.notna(date_val) and isinstance(date_val, date) else "Fecha Desconocida"
                        expander_label = f"🗓️ {date_str} - 👤 {client_display_name_orig} ({len(group)} registros)"

                        with st.expander(expander_label, expanded=st.session_state.expand_all_details):
                            existing_final_cols = [col for col in final_display_columns if col in group.columns]
                            display_group_df = group[existing_final_cols].reset_index(drop=True).copy()
                            if 'FECHA' in display_group_df.columns:
                                display_group_df['FECHA'] = pd.to_datetime(display_group_df['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                                display_group_df['FECHA'] = display_group_df['FECHA'].fillna('Inválida')
                            display_group_df.fillna('', inplace=True)
                            styled_group_df = display_group_df.style.apply(highlight_status, axis=1)
                            st.dataframe(styled_group_df, hide_index=True, use_container_width=True)
                else:
                    st.error(f"No se pueden agrupar los resultados. Faltan las columnas '{date_col_display}' o '{client_col_cleaned}'.")
            except Exception as e_group:
                st.error(f"Ocurrió un error al intentar agrupar y mostrar los resultados: {e_group}")
                st.exception(e_group)

            # --- Optional: Full Filtered Table (sin cambios) ---
            st.markdown("---")
            with st.expander("Ver tabla completa filtrada (columnas seleccionadas)", expanded=False):
                try:
                    existing_final_cols_full = [col for col in final_display_columns if col in filtered_df.columns]
                    full_display_df = filtered_df[existing_final_cols_full].copy()
                    if 'FECHA' in full_display_df.columns:
                         full_display_df['FECHA'] = pd.to_datetime(full_display_df['FECHA'], errors='coerce').dt.strftime('%Y-%m-%d')
                         full_display_df['FECHA'] = full_display_df['FECHA'].fillna('Inválida')
                    full_display_df.fillna('', inplace=True)
                    styled_full_df = full_display_df.style.apply(highlight_status, axis=1)
                    st.dataframe(styled_full_df, hide_index=True, use_container_width=True)
                except Exception as e_table:
                    st.error(f"Error al mostrar la tabla completa: {e_table}")

            # --- Summary Section (sin cambios) ---
            st.markdown("---")
            st.subheader("📈 Resumen de Avance (Cotizado vs Garantía)")
            # (El código del resumen permanece igual)
            try:
                if status_col_name in filtered_df.columns:
                    # --- Overall Summary ---
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
                        st.info("No se encontraron registros generales 'Cotizado' o 'Garantía' en los datos filtrados para calcular porcentajes.")

                    # --- Breakdown by Client ---
                    st.markdown("---")
                    st.markdown("#### Desglose por Cliente")
                    client_summary = filtered_df.groupby(client_col_cleaned).agg(
                        Cotizado_Count=(status_col_name, lambda x: x.astype(str).str.lower().str.contains('cotiza', na=False).sum()),
                        Garantia_Count=(status_col_name, lambda x: x.astype(str).str.lower().str.contains('garantía|garantia', na=False, regex=True).sum())
                    ).reset_index()
                    client_summary['Total_Relevante'] = client_summary['Cotizado_Count'] + client_summary['Garantia_Count']
                    client_summary['Cotizado_%'] = np.where(client_summary['Total_Relevante'] > 0,(client_summary['Cotizado_Count'] / client_summary['Total_Relevante'] * 100),0)
                    client_summary['Garantia_%'] = np.where(client_summary['Total_Relevante'] > 0,(client_summary['Garantia_Count'] / client_summary['Total_Relevante'] * 100),0)
                    summary_filtered = client_summary[client_summary['Total_Relevante'] > 0].copy()
                    summary_display = summary_filtered[[client_col_cleaned, 'Cotizado_Count', 'Garantia_Count', 'Total_Relevante', 'Cotizado_%', 'Garantia_%']].rename(columns={client_col_cleaned: 'Cliente','Cotizado_Count': 'Cotizados (#)','Garantia_Count': 'Garantías (#)','Total_Relevante': 'Total C+G','Cotizado_%': 'Cotizado (%)','Garantia_%': 'Garantía (%)'})
                    if not summary_display.empty:
                        st.dataframe(summary_display.style.format({'Cotizado (%)': '{:.1f}%','Garantía (%)': '{:.1f}%'}),hide_index=True,use_container_width=True)
                        # --- Bar Chart by Client ---
                        st.markdown("#### Visualización por Cliente (Cantidad)")
                        chart_data = summary_display.set_index('Cliente')[['Cotizados (#)', 'Garantías (#)']].rename(columns={'Cotizados (#)': 'Cotizado','Garantías (#)': 'Garantía'})
                        if not chart_data.empty:
                            st.bar_chart(chart_data)
                        else:
                            st.info("No hay datos por cliente para generar el gráfico.")
                    else:
                        st.info("No se encontraron datos por cliente con 'Cotizado' o 'Garantía' para generar el desglose.")
                else:
                    st.warning(f"La columna '{status_col_name}' no se encontró en los datos filtrados para calcular el resumen.")
            except Exception as e_summary:
                st.error(f"Error al calcular el resumen de avance: {e_summary}")
                st.exception(e_summary)
            # --- End Summary Section ---

    # Mensaje si no se ha buscado
    elif st.session_state.data_loaded and not st.session_state.search_triggered:
        st.info("👆 Configura los filtros en la barra lateral y presiona 'Buscar Resultados'.")

# Mensaje si no hay archivo
elif not uploaded_file:
    st.info("Por favor, carga un archivo CSV para comenzar el análisis.")
