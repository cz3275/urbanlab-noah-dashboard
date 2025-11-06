import streamlit as st
from datetime import datetime

class SidebarManager:
    def __init__(self):
        self.metric_options = {
            "median_rent": "Median Rent",
            "median_income": "Median Income", 
            "rent_burden": "Rent Burden (Households)",
            "rent_burden_rate": "Rent Burden Rate (%)",
            "vacancy_rate": "Vacancy Rate",
            "housing_units": "Housing Units"
        }

        
        self.color_schemes = {
            "YlOrRd": "Yellow-Orange-Red",
            "Blues": "Blues",
            "Greens": "Greens",
            "Viridis": "Viridis",
            "Plasma": "Plasma"
        }
        
        self.map_styles = {
            "CartoDB positron": "Light",
            "CartoDB dark_matter": "Dark",
            "OpenStreetMap": "Standard"
        }
    
    def render_layer_controls(self):
        st.header("Layer Controls")
        
        with st.expander("Primary Metrics", expanded=True):
            metric = st.selectbox(
                "Select Metric",
                list(self.metric_options.keys()),
                format_func=lambda x: self.metric_options[x],
                key="primary_metric"
            )
            
            show_markers = st.checkbox("Show Data Points", value=True, key="show_markers")
            show_heatmap = st.checkbox("Add Heatmap Layer", value=False, key="show_heatmap")
            show_labels = st.checkbox("Show ZIP Labels", value=False, key="show_labels")
        
        return {
            "metric": metric,
            "show_markers": show_markers,
            "show_heatmap": show_heatmap,
            "show_labels": show_labels
        }
    
    def render_map_appearance(self):
        with st.expander("Map Appearance", expanded=True):
            color_scheme = st.selectbox(
                "Color Scheme",
                list(self.color_schemes.keys()),
                format_func=lambda x: self.color_schemes[x],
                key="color_scheme"
            )
            
            map_style = st.selectbox(
                "Base Map Style",
                list(self.map_styles.keys()),
                format_func=lambda x: self.map_styles[x],
                key="map_style"
            )
            
            opacity = st.slider("Layer Opacity", 0.0, 1.0, 0.7, 0.1, key="opacity")
        
        return {
            "color_scheme": color_scheme,
            "map_style": map_style,
            "opacity": opacity
        }
    
    def render_data_filters(self, metric):
        with st.expander("Data Filters", expanded=False):
            zip_search = st.text_input("Search ZIP Code", placeholder="e.g., 10001", key="zip_search")
            
            enable_range = st.checkbox("Enable Value Range Filter", key="enable_range")
            
            min_val, max_val = None, None
            if enable_range:
                if metric == "median_rent":
                    min_val, max_val = st.slider(
                        "Rent Range",
                        0, 5000, (0, 5000), 100,
                        format="$%d",
                        key="rent_range"
                    )
                elif metric == "median_income":
                    min_val, max_val = st.slider(
                        "Income Range (Monthly)",
                        0, 30000, (0, 30000), 1000,
                        format="$%d",
                        key="income_range"
                    )
                elif metric == "vacancy_rate":
                    min_val, max_val = st.slider(
                        "Vacancy Rate Range",
                        0.0, 1.0, (0.0, 1.0), 0.01,
                        format="%.2f",
                        key="vacancy_range"
                    )
                elif metric == "rent_burden":
                    min_val, max_val = st.slider(
                        "Rent Burden Range (Households)",
                        0, 50000, (0, 50000), 1000,
                        format="%d",
                        key="burden_range"
                    )
                elif metric == "rent_burden_rate":
                    min_val, max_val = st.slider(
                        "Rent Burden Rate Range",
                        0, 100, (0, 100), 5,
                        format="%d%%",
                        key="burden_rate_range"
                    )
                elif metric == "housing_units":
                    min_val, max_val = st.slider(
                        "Housing Units Range",
                        0, 50000, (0, 50000), 1000,
                        key="units_range"
                    )
            
            borough_filter = st.multiselect(
                "Filter by Borough",
                ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"],
                key="borough_filter"
            )
            
            st.divider()
            
            enable_year_filter = st.checkbox("Enable Building Year Filter", key="enable_year_filter")
            year_min, year_max = None, None
            if enable_year_filter:
                year_min, year_max = st.slider(
                    "Building Year Range",
                    1800, 2025, (1900, 2025), 10,
                    key="year_range"
                )
        
        return {
            "zip_search": zip_search,
            "min_val": min_val,
            "max_val": max_val,
            "borough_filter": borough_filter,
            "year_min": year_min,
            "year_max": year_max
        }
    
    def render_analysis_options(self):
        with st.expander("Analysis Tools", expanded=False):
            show_statistics = st.checkbox("Show Statistics Panel", value=True, key="show_stats")
            show_correlation = st.checkbox("Show Correlation Matrix", value=False, key="show_corr")
            compare_mode = st.checkbox("Comparison Mode", value=False, key="compare_mode")
            
            if compare_mode:
                compare_metric = st.selectbox(
                    "Compare With",
                    list(self.metric_options.keys()),
                    format_func=lambda x: self.metric_options[x],
                    key="compare_metric"
                )
            else:
                compare_metric = None
        
        return {
            "show_statistics": show_statistics,
            "show_correlation": show_correlation,
            "compare_mode": compare_mode,
            "compare_metric": compare_metric
        }
    
    def render_sync_controls(self, data_service, auto_sync_manager=None):
        st.divider()
        
        with st.expander("Data Management", expanded=False):
            st.markdown("**Manual Sync**")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Sync Census", type="secondary", use_container_width=True, key="sync_census_btn"):
                    return "sync_census"
            
            with col2:
                if st.button("Sync PLUTO", type="secondary", use_container_width=True, key="sync_pluto_btn"):
                    return "sync_pluto"
            
            if st.button("Sync All Data", type="primary", use_container_width=True, key="sync_all_btn"):
                return "sync_all"
            
            st.divider()
            
            if auto_sync_manager:
                st.markdown("**Auto Sync Settings**")
                
                auto_sync_status = auto_sync_manager.get_status()
                
                auto_enabled = st.checkbox(
                    "Enable Auto Sync",
                    value=auto_sync_status["enabled"],
                    key="auto_sync_enabled"
                )
                
                if auto_enabled != auto_sync_status["enabled"]:
                    auto_sync_manager.update_config(enabled=auto_enabled)
                    if auto_enabled:
                        auto_sync_manager.start_auto_sync()
                    else:
                        auto_sync_manager.stop_auto_sync()
                
                if auto_enabled:
                    interval = st.selectbox(
                        "Sync Interval",
                        [6, 12, 24, 48, 168],
                        format_func=lambda x: f"{x} hours" if x < 24 else f"{x//24} days",
                        index=[6, 12, 24, 48, 168].index(auto_sync_status["interval_hours"]),
                        key="sync_interval"
                    )
                    
                    if interval != auto_sync_status["interval_hours"]:
                        auto_sync_manager.update_config(interval_hours=interval)
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        sync_census = st.checkbox(
                            "Census Data",
                            value=auto_sync_status["sync_census"],
                            key="auto_sync_census"
                        )
                    with col4:
                        sync_pluto = st.checkbox(
                            "PLUTO Data",
                            value=auto_sync_status["sync_pluto"],
                            key="auto_sync_pluto"
                        )
                    
                    if sync_census != auto_sync_status["sync_census"] or sync_pluto != auto_sync_status["sync_pluto"]:
                        auto_sync_manager.update_config(sync_census=sync_census, sync_pluto=sync_pluto)
                    
                    if auto_sync_status["last_sync"]:
                        last_sync_dt = datetime.fromisoformat(auto_sync_status["last_sync"])
                        st.caption(f"Last Auto Sync: {last_sync_dt.strftime('%Y-%m-%d %H:%M')}")
                    
                    if auto_sync_status["time_until_sync"]:
                        st.caption(f"Next Sync in: {auto_sync_status['time_until_sync']}")
                    
                    if st.button("Check & Sync Now", use_container_width=True, key="check_sync_btn"):
                        return "check_sync"
            
            st.divider()
            
            last_sync = data_service.get_last_sync_info()
            if last_sync:
                st.caption(f"Last Manual Sync: {last_sync['time'].strftime('%Y-%m-%d %H:%M')}")
                st.caption(f"Status: {last_sync['status']} | {last_sync['records']} records")
        
        return None

