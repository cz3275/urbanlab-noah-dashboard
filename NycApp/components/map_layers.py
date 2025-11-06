import folium
from folium import plugins
import pandas as pd

class MapLayerManager:
    def __init__(self, base_coords=[40.7128, -73.75], zoom_start=10):
        self.base_coords = base_coords
        self.zoom_start = zoom_start
        self.layers = []
    
    def create_base_map(self, tiles="CartoDB positron"):
        base_map = folium.Map(
            location=self.base_coords,
            zoom_start=self.zoom_start,
            tiles=tiles,
            prefer_canvas=True
        )
        return base_map
    
    def add_marker_layer(self, map_obj, data, coords_dict, metric_column, 
                        color_scheme="YlOrRd", opacity=0.7, building_stats=None, data_service=None):
        if data.empty or metric_column not in data.columns:
            return map_obj
        
        marker_cluster = plugins.MarkerCluster(name="Data Points")
        
        valid_data = data[data["zip"].notna()].copy()
        
        for _, row in valid_data.iterrows():
            zip_code = str(row["zip"]).zfill(5)
            
            if zip_code in coords_dict:
                coords = coords_dict[zip_code]
                metric_value = row.get(metric_column)
                
                if pd.notna(metric_value):
                    color = self._get_marker_color(
                        metric_value, 
                        metric_column,
                        color_scheme
                    )
                    
                    popup_html = self._create_popup_html(row, zip_code, building_stats, data_service)
                    
                    folium.CircleMarker(
                        location=coords,
                        radius=8,
                        popup=folium.Popup(popup_html, max_width=450),
                        tooltip=f"ZIP: {zip_code}",
                        color=color,
                        fill=True,
                        fillColor=color,
                        fillOpacity=opacity,
                        weight=2
                    ).add_to(map_obj)
        
        return map_obj
    
    def add_heatmap_layer(self, map_obj, data, coords_dict, metric_column):
        if data.empty or metric_column not in data.columns:
            return map_obj
        
        heat_data = []
        valid_data = data[data[metric_column].notna()].copy()
        
        for _, row in valid_data.iterrows():
            zip_code = str(row["zip"]).zfill(5)
            if zip_code in coords_dict:
                coords = coords_dict[zip_code]
                value = float(row[metric_column])
                heat_data.append([coords[0], coords[1], value])
        
        if heat_data:
            plugins.HeatMap(
                heat_data,
                name="Heatmap",
                min_opacity=0.2,
                max_zoom=13,
                radius=15,
                blur=20,
                gradient={
                    0.0: 'blue',
                    0.5: 'yellow',
                    1.0: 'red'
                }
            ).add_to(map_obj)
        
        return map_obj
    
    def add_label_layer(self, map_obj, data, coords_dict):
        if data.empty:
            return map_obj
        
        valid_data = data[data["zip"].notna()].copy()
        
        for _, row in valid_data.iterrows():
            zip_code = str(row["zip"]).zfill(5)
            
            if zip_code in coords_dict:
                coords = coords_dict[zip_code]
                
                folium.Marker(
                    location=coords,
                    icon=folium.DivIcon(
                        html=f'''
                        <div style="
                            font-size: 9px;
                            font-weight: bold;
                            color: #333;
                            text-align: center;
                            text-shadow: 1px 1px 1px white;
                        ">{zip_code}</div>
                        '''
                    )
                ).add_to(map_obj)
        
        return map_obj
    
    def add_legend(self, map_obj, metric_column, color_scheme):
        legend_html = self._create_legend_html(metric_column, color_scheme)
        map_obj.get_root().html.add_child(folium.Element(legend_html))
        return map_obj
    
    def _get_marker_color(self, value, metric_column, color_scheme):
        ranges = {
            "median_rent": (0, 4000),
            "median_income": (0, 25000),
            "vacancy_rate": (0, 0.5),
            "housing_units": (0, 50000),
            "rent_burden": (0, 50000),
            "rent_burden_rate": (0, 100)
        }
        
        min_val, max_val = ranges.get(metric_column, (0, 100))
        
        if pd.isna(value):
            return "gray"
        
        normalized = (value - min_val) / (max_val - min_val) if max_val > min_val else 0
        normalized = max(0, min(1, normalized))
        
        color_maps = {
            "YlOrRd": ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"],
            "Blues": ["#eff3ff", "#bdd7e7", "#6baed6", "#3182bd", "#08519c"],
            "Greens": ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"],
            "Viridis": ["#440154", "#31688e", "#35b779", "#fde724", "#fde724"],
            "Plasma": ["#0d0887", "#7e03a8", "#cc4778", "#f89540", "#f0f921"]
        }
        
        colors = color_maps.get(color_scheme, color_maps["YlOrRd"])
        idx = int(normalized * (len(colors) - 1))
        return colors[idx]
    
    def _create_popup_html(self, row, zip_code, building_stats=None, data_service=None):
        median_rent = pd.to_numeric(row.get('median_rent'), errors='coerce')
        median_income = pd.to_numeric(row.get('median_income'), errors='coerce')
        vacancy_rate = pd.to_numeric(row.get('vacancy_rate'), errors='coerce')
        housing_units = pd.to_numeric(row.get('housing_units'), errors='coerce')
        rent_burden = pd.to_numeric(row.get('rent_burden'), errors='coerce')
        rent_burden_rate = pd.to_numeric(row.get('rent_burden_rate'), errors='coerce')
        
        rent_str = f"${median_rent:,.0f}" if pd.notna(median_rent) else "N/A"
        income_str = f"${median_income:,.0f}" if pd.notna(median_income) else "N/A"
        vacancy_str = f"{vacancy_rate*100:.1f}%" if pd.notna(vacancy_rate) else "N/A"
        units_str = f"{housing_units:,.0f}" if pd.notna(housing_units) else "N/A"
        burden_str = f"{rent_burden:,.0f}" if pd.notna(rent_burden) else "N/A"
        burden_rate_str = f"{rent_burden_rate:.1f}%" if pd.notna(rent_burden_rate) else "N/A"
        
        # Building Stats
        building_stats_html = ""
        building_list_html = ""
        
        if building_stats is not None and data_service is not None:
            zip_building_stats = building_stats[building_stats['zip'] == zip_code] if not building_stats.empty else None
            
            if zip_building_stats is not None and not zip_building_stats.empty:
                stats = zip_building_stats.iloc[0]
                total_buildings = stats.get('total_buildings', 0)
                avg_floors = stats.get('avg_floors')
                avg_year = stats.get('avg_year_built')
                total_units = stats.get('total_residential_units', 0)
                pre_1950 = stats.get('buildings_pre_1950', 0)
                y1950_2000 = stats.get('buildings_1950_2000', 0)
                post_2000 = stats.get('buildings_post_2000', 0)
                
                avg_floors_str = f"{avg_floors:.1f}" if pd.notna(avg_floors) else "N/A"
                avg_year_str = f"{int(avg_year)}" if pd.notna(avg_year) else "N/A"
                
                building_stats_html = f"""
                <div class="tab-content" id="building-stats">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 4px 0;"><b>Total Buildings:</b></td><td style="text-align: right;">{total_buildings:,}</td></tr>
                        <tr><td style="padding: 4px 0;"><b>Avg Floors:</b></td><td style="text-align: right;">{avg_floors_str}</td></tr>
                        <tr><td style="padding: 4px 0;"><b>Avg Year Built:</b></td><td style="text-align: right;">{avg_year_str}</td></tr>
                        <tr><td style="padding: 4px 0;"><b>Residential Units:</b></td><td style="text-align: right;">{total_units:,}</td></tr>
                        <tr><td colspan="2" style="padding-top: 8px; border-top: 1px solid #ddd;"><b>By Era:</b></td></tr>
                        <tr><td style="padding: 2px 0 2px 10px;">Pre-1950:</td><td style="text-align: right;">{pre_1950:,}</td></tr>
                        <tr><td style="padding: 2px 0 2px 10px;">1950-2000:</td><td style="text-align: right;">{y1950_2000:,}</td></tr>
                        <tr><td style="padding: 2px 0 2px 10px;">Post-2000:</td><td style="text-align: right;">{post_2000:,}</td></tr>
                    </table>
                </div>
                """

                try:
                    import streamlit as st
                    year_min = st.session_state.get("year_filter_min")
                    year_max = st.session_state.get("year_filter_max")
                    
                    if year_min is not None and year_max is not None:
                        buildings = data_service.get_buildings_by_zip_filtered(zip_code, year_min, year_max, limit=5)
                    else:
                        buildings = data_service.get_buildings_by_zip(zip_code, limit=5)
                    if not buildings.empty:
                        building_rows = ""
                        for _, bldg in buildings.iterrows():
                            addr = str(bldg.get('address', 'N/A'))[:30]
                            year = int(bldg.get('yearbuilt')) if pd.notna(bldg.get('yearbuilt')) else 'N/A'
                            floors = int(bldg.get('numfloors')) if pd.notna(bldg.get('numfloors')) else 'N/A'
                            units = int(bldg.get('unitsres')) if pd.notna(bldg.get('unitsres')) else 'N/A'
                            
                            building_rows += f"""
                            <tr style="border-bottom: 1px solid #eee;">
                                <td style="padding: 4px 0; font-size: 10px;">{addr}</td>
                                <td style="text-align: center; font-size: 10px;">{year}</td>
                                <td style="text-align: center; font-size: 10px;">{floors}</td>
                                <td style="text-align: center; font-size: 10px;">{units}</td>
                            </tr>
                            """
                        
                        building_list_html = f"""
                        <div class="tab-content" id="building-list">
                            <table style="width: 100%; border-collapse: collapse; font-size: 11px;">
                                <tr style="background: #f5f5f5; border-bottom: 2px solid #ddd;">
                                    <th style="padding: 4px; text-align: left;">Address</th>
                                    <th style="padding: 4px; text-align: center;">Year</th>
                                    <th style="padding: 4px; text-align: center;">Floors</th>
                                    <th style="padding: 4px; text-align: center;">Units</th>
                                </tr>
                                {building_rows}
                            </table>
                            <p style="font-size: 10px; color: #666; margin-top: 5px; text-align: center;">Showing top 5 buildings</p>
                        </div>
                        """
                except:
                    pass
            else:
                building_stats_html = """
                <div class="tab-content" id="building-stats">
                    <p style="color: #666; text-align: center; padding: 20px;">No building data available for this ZIP</p>
                </div>
                """
        
        # Popup
        tabs_html = ""
        tab_script = ""
        if building_stats_html or building_list_html:
            if building_list_html:
                building_tab = '<div class="tab" onclick="(function(tabId, element){var allTabs = element.parentElement.getElementsByClassName(\'tab\');var allContents = document.getElementsByClassName(\'tab-content\');for(var i=0;i<allTabs.length;i++){allTabs[i].classList.remove(\'active\');}for(var i=0;i<allContents.length;i++){allContents[i].classList.remove(\'active\');}element.classList.add(\'active\');var targetContent=document.getElementById(tabId);if(targetContent){targetContent.classList.add(\'active\');}})(\'' + 'building-list' + '\', this)">Buildings</div>'
            else:
                building_tab = ''
            
            tabs_html = f"""
            <style>
                .tabs {{
                    display: flex;
                    border-bottom: 2px solid #2c3e50;
                    margin-bottom: 10px;
                }}
                .tab {{
                    padding: 8px 12px;
                    cursor: pointer;
                    background: #ecf0f1;
                    border: none;
                    font-size: 11px;
                    font-weight: bold;
                    flex: 1;
                    text-align: center;
                    user-select: none;
                }}
                .tab:hover {{
                    background: #bdc3c7;
                }}
                .tab.active {{
                    background: #2c3e50;
                    color: white;
                }}
                .tab-content {{
                    display: none;
                }}
                .tab-content.active {{
                    display: block;
                }}
            </style>
            <div class="tabs">
                <div class="tab active" onclick="(function(tabId, element){{var allTabs = element.parentElement.getElementsByClassName('tab');var allContents = document.getElementsByClassName('tab-content');for(var i=0;i<allTabs.length;i++){{allTabs[i].classList.remove('active');}}for(var i=0;i<allContents.length;i++){{allContents[i].classList.remove('active');}}element.classList.add('active');var targetContent=document.getElementById(tabId);if(targetContent){{targetContent.classList.add('active');}}}})('housing', this)">Housing</div>
                <div class="tab" onclick="(function(tabId, element){{var allTabs = element.parentElement.getElementsByClassName('tab');var allContents = document.getElementsByClassName('tab-content');for(var i=0;i<allTabs.length;i++){{allTabs[i].classList.remove('active');}}for(var i=0;i<allContents.length;i++){{allContents[i].classList.remove('active');}}element.classList.add('active');var targetContent=document.getElementById(tabId);if(targetContent){{targetContent.classList.add('active');}}}})('building-stats', this)">Building Stats</div>
                {building_tab}
            </div>
            """
            
            tab_script = ""
        
        return f"""
        <div style="font-family: Arial; font-size: 12px; min-width: 250px;">
            <div style="background: #2c3e50; color: white; padding: 10px; margin: -10px -10px 10px -10px;">
                <b style="font-size: 15px;">ZIP Code: {zip_code}</b>
            </div>
            {tabs_html}
            <div class="tab-content active" id="housing">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 4px 0;"><b>Median Rent:</b></td><td style="text-align: right;">{rent_str}</td></tr>
                    <tr><td style="padding: 4px 0;"><b>Median Income:</b></td><td style="text-align: right;">{income_str}</td></tr>
                    <tr><td style="padding: 4px 0;"><b>Rent Burden Rate:</b></td><td style="text-align: right;">{burden_rate_str}</td></tr>
                    <tr><td style="padding: 4px 0;"><b>Rent Burden (HH):</b></td><td style="text-align: right;">{burden_str}</td></tr>
                    <tr><td style="padding: 4px 0;"><b>Vacancy Rate:</b></td><td style="text-align: right;">{vacancy_str}</td></tr>
                    <tr><td style="padding: 4px 0;"><b>Housing Units:</b></td><td style="text-align: right;">{units_str}</td></tr>
                </table>
            </div>
            {building_stats_html}
            {building_list_html}
        </div>
        """
    
    def _create_legend_html(self, metric_column, color_scheme):
        metric_names = {
            "median_rent": "Median Rent ($)",
            "median_income": "Median Income (Monthly $)",
            "vacancy_rate": "Vacancy Rate (%)",
            "housing_units": "Housing Units",
            "rent_burden": "Rent Burden (Households)",
            "rent_burden_rate": "Rent Burden Rate (%)"
        }
        
        return f"""
        <div style="
            position: fixed;
            bottom: 50px;
            right: 50px;
            width: 200px;
            background: white;
            border: 2px solid #ccc;
            border-radius: 5px;
            padding: 10px;
            font-family: Arial;
            font-size: 12px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            z-index: 9999;
        ">
            <b>{metric_names.get(metric_column, metric_column)}</b><br>
            <div style="margin-top: 10px;">
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 20px; height: 20px; background: #bd0026; margin-right: 10px;"></div>
                    <span>High</span>
                </div>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 20px; height: 20px; background: #fd8d3c; margin-right: 10px;"></div>
                    <span>Medium</span>
                </div>
                <div style="display: flex; align-items: center; margin: 5px 0;">
                    <div style="width: 20px; height: 20px; background: #ffffb2; margin-right: 10px;"></div>
                    <span>Low</span>
                </div>
            </div>
        </div>
        """

