import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from streamlit_folium import st_folium
from services.data_service import DataService
from services.data_sync import manual_sync, DataSyncService
from services.auto_sync import AutoSyncManager
from components.sidebar import SidebarManager
from components.map_layers import MapLayerManager
from components.statistics import StatisticsPanel
from utils.zip_coords import NYC_ZIP_COORDS, NYC_CENTER
from config.database import init_db

st.set_page_config(
    page_title="NYC Housing Data Explorer",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def initialize_database():
    init_db()


@st.cache_resource
def get_auto_sync_manager():
    return AutoSyncManager()


initialize_database()


def apply_filters(df, filters):
    filtered = df.copy()

    if filters["zip_search"]:
        filtered = filtered[filtered["zip"].str.contains(filters["zip_search"], na=False)]

    if filters["min_val"] is not None and filters["max_val"] is not None:
        metric = st.session_state.get("primary_metric", "median_rent")
        if metric in filtered.columns:
            filtered = filtered[
                (filtered[metric].isna()) |
                ((filtered[metric] >= filters["min_val"]) & (filtered[metric] <= filters["max_val"]))
                ]

    return filtered


def main():
    st.title("NYC Housing Data Explorer")
    st.markdown("*Professional visualization of New York City housing metrics*")

    data_service = DataService()
    sidebar = SidebarManager()
    map_manager = MapLayerManager(base_coords=NYC_CENTER)
    stats_panel = StatisticsPanel()
    auto_sync_manager = get_auto_sync_manager()

    with st.sidebar:
        st.markdown("### NYC Housing Explorer")

        layer_config = sidebar.render_layer_controls()
        appearance_config = sidebar.render_map_appearance()
        filter_config = sidebar.render_data_filters(layer_config["metric"])
        analysis_config = sidebar.render_analysis_options()

        action = sidebar.render_sync_controls(data_service, auto_sync_manager)

        if action == "sync_all":
            with st.spinner("Syncing all data from APIs..."):
                try:
                    sync_service = DataSyncService()
                    census_records = sync_service.sync_all_data()
                    pluto_records = sync_service.sync_pluto_data()
                    st.success(f"Synced Census: {census_records} records, PLUTO: {pluto_records} records")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {str(e)}")

        elif action == "sync_census":
            with st.spinner("Syncing Census data from API..."):
                try:
                    records = manual_sync()
                    st.success(f"Synced {records} Census records successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Census sync failed: {str(e)}")

        elif action == "sync_pluto":
            with st.spinner("Syncing PLUTO data from API... This may take several minutes..."):
                try:
                    sync_service = DataSyncService()
                    records = sync_service.sync_pluto_data()
                    st.success(f"Synced {records} PLUTO records successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"PLUTO sync failed: {str(e)}")

        elif action == "check_sync":
            with st.spinner("Checking and syncing if needed..."):
                try:
                    result = auto_sync_manager.check_and_sync()
                    if result:
                        msg = []
                        if result["census"]:
                            msg.append(f"Census: {result['census']} records")
                        if result["pluto"]:
                            msg.append(f"PLUTO: {result['pluto']} records")
                        if result["error"]:
                            st.warning(f"Partial sync: {', '.join(msg)}. Errors: {result['error']}")
                        elif msg:
                            st.success(f"Auto-synced: {', '.join(msg)}")
                        st.rerun()
                    else:
                        st.info("No sync needed. Next sync scheduled as configured.")
                except Exception as e:
                    st.error(f"Auto-sync failed: {str(e)}")

    df = data_service.get_all_metrics()
    building_stats_df = data_service.get_all_building_stats()

    if df.empty:
        st.warning("No data available. Please sync data from the sidebar.")
        return

    df["zip"] = df["zip"].astype(str).str.zfill(5)
    if not building_stats_df.empty:
        building_stats_df["zip"] = building_stats_df["zip"].astype(str).str.zfill(5)

    filtered_df = apply_filters(df, filter_config)
    
    if "selected_zip" not in st.session_state:
        if not filtered_df.empty:
            st.session_state["selected_zip"] = filtered_df.iloc[0]["zip"]
        else:
            st.session_state["selected_zip"] = None

    if "year_min" in filter_config and filter_config["year_min"] is not None:
        st.session_state["year_filter_min"] = filter_config["year_min"]
        st.session_state["year_filter_max"] = filter_config["year_max"]
    else:
        st.session_state["year_filter_min"] = None
        st.session_state["year_filter_max"] = None

    if analysis_config["show_statistics"]:
        stats_panel.render_summary_metrics(filtered_df)

    st.divider()

    tab1, tab2, tab3 = st.tabs([
        "Map View",
        "Analytics",
        "Advanced Analysis"
    ])

    with tab1:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.subheader("Geographic Distribution")
        with col2:
            st.metric("Filtered ZIPs", len(filtered_df))

        base_map = map_manager.create_base_map(tiles=appearance_config["map_style"])

        if layer_config["show_markers"]:
            base_map = map_manager.add_marker_layer(
                base_map,
                filtered_df,
                NYC_ZIP_COORDS,
                layer_config["metric"],
                appearance_config["color_scheme"],
                appearance_config["opacity"],
                building_stats_df,
                data_service
            )

        if layer_config["show_heatmap"]:
            base_map = map_manager.add_heatmap_layer(
                base_map,
                filtered_df,
                NYC_ZIP_COORDS,
                layer_config["metric"]
            )

        if layer_config["show_labels"]:
            base_map = map_manager.add_label_layer(
                base_map,
                filtered_df,
                NYC_ZIP_COORDS
            )

        base_map = map_manager.add_legend(
            base_map,
            layer_config["metric"],
            appearance_config["color_scheme"]
        )

        map_output = st_folium(base_map, width=None, height=800, returned_objects=["last_object_clicked"])
        
        if map_output and map_output.get("last_object_clicked"):
            clicked_lat = map_output["last_object_clicked"].get("lat")
            clicked_lng = map_output["last_object_clicked"].get("lng")
            
            if clicked_lat and clicked_lng:
                min_dist = float('inf')
                clicked_zip = None
                
                for zip_code, coords in NYC_ZIP_COORDS.items():
                    dist = ((coords[0] - clicked_lat) ** 2 + (coords[1] - clicked_lng) ** 2) ** 0.5
                    if dist < min_dist:
                        min_dist = dist
                        clicked_zip = zip_code
                
                if clicked_zip and clicked_zip != st.session_state.get("selected_zip"):
                    st.session_state["selected_zip"] = clicked_zip
                    st.rerun()

        with st.expander("Map Information", expanded=False):
            st.markdown("""
            **Layer Controls:**
            - Toggle data points, heatmap, and ZIP labels from the sidebar
            - Adjust color scheme and opacity for better visualization
            - Use filters to focus on specific areas or value ranges
            
            **Map Interactions:**
            - Click markers for detailed information
            - Zoom and pan to explore different areas
            - Switch base map styles for different contexts
            """)

    with tab2:
        st.subheader("Statistical Analysis")
        
        selected_zip = st.session_state.get("selected_zip")
        if selected_zip:
            selected_df = filtered_df[filtered_df["zip"] == selected_zip]
            
            if not selected_df.empty:
                st.info(f"Displaying data for ZIP Code: {selected_zip}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    stats_panel.render_zip_metrics_card(selected_df.iloc[0])
                
                with col2:
                    stats_panel.render_zip_comparison_chart(filtered_df, selected_zip, layer_config["metric"])
                
                st.divider()
                
                if "median_rent" in selected_df.columns and "median_income" in selected_df.columns:
                    stats_panel.render_zip_detailed_metrics(selected_df.iloc[0], filtered_df)
            else:
                st.warning(f"No data available for ZIP Code: {selected_zip}")
        else:
            st.warning("No ZIP Code selected")

    with tab3:
        st.subheader("Advanced Analysis")
        
        selected_zip = st.session_state.get("selected_zip")
        if selected_zip:
            selected_df = filtered_df[filtered_df["zip"] == selected_zip]
            
            if not selected_df.empty:
                st.info(f"Displaying advanced analysis for ZIP Code: {selected_zip}")
                
                col1, col2 = st.columns([3, 2])

                with col1:
                    if not building_stats_df.empty:
                        selected_building_stats = building_stats_df[building_stats_df["zip"] == selected_zip]
                        if not selected_building_stats.empty:
                            stats_panel.render_building_stats_detailed(selected_building_stats.iloc[0])
                        else:
                            st.info("No building statistics available for this ZIP Code")
                    else:
                        st.info("No building statistics available")

                with col2:
                    stats_panel.render_zip_rank_analysis(filtered_df, selected_zip)

                st.divider()

                st.subheader("ZIP Code Comparison")
                
                stats_panel.render_multi_zip_comparison(filtered_df, selected_zip, n=5)
            else:
                st.warning(f"No data available for ZIP Code: {selected_zip}")
        else:
            st.warning("No ZIP Code selected")

    st.divider()

    with st.expander("About This Application", expanded=False):
        st.markdown("""
        ### NYC Housing Data Explorer
        
        This application provides comprehensive visualization and analysis of New York City housing metrics,
        inspired by the NYC Planning Labs ZoLa platform.
        
        **Data Sources:**
        - US Census Bureau American Community Survey (ACS) 5-Year 2022
        - NYC Open Data Modified ZCTA Boundaries
        
        **Key Features:**
        - Interactive map visualization with multiple layer controls
        - Statistical analysis and correlation matrices
        - Advanced filtering and search capabilities
        - Real-time data synchronization
        - Building year range filtering
        
        **Metrics Available:**
        - Median Rent: Monthly rental costs
        - Median Income: Monthly household income
        - Rent Burden: Number of households with rent burden
        - Vacancy Rate: Unoccupied housing percentage
        - Housing Units: Total residential units
        """)


if __name__ == "__main__":
    main()
