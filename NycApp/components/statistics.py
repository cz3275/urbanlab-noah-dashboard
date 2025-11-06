import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class StatisticsPanel:
    def __init__(self):
        self.metric_labels = {
            "median_rent": "Median Rent",
            "median_income": "Median Income",
            "rent_burden": "Rent Burden (Households)",
            "rent_burden_rate": "Rent Burden Rate (%)",
            "vacancy_rate": "Vacancy Rate (%)",
            "housing_units": "Housing Units"
        }
    
    def render_summary_metrics(self, df):
        if df.empty:
            st.warning("No data available")
            return
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_zips = len(df[df["zip"].notna()])
            st.metric("Total ZIP Codes", f"{total_zips:,}")
        
        with col2:
            avg_rent = df["median_rent"].mean()
            if pd.notna(avg_rent):
                st.metric("Avg Rent", f"${avg_rent:,.0f}")
            else:
                st.metric("Avg Rent", "N/A")
        
        with col3:
            avg_income = df["median_income"].mean()
            if pd.notna(avg_income):
                st.metric("Avg Income", f"${avg_income:,.0f}")
            else:
                st.metric("Avg Income", "N/A")
        
        with col4:
            avg_vacancy = df["vacancy_rate"].mean()
            if pd.notna(avg_vacancy):
                st.metric("Avg Vacancy", f"{avg_vacancy*100:.1f}%")
            else:
                st.metric("Avg Vacancy", "N/A")
        
        with col5:
            avg_burden = df["rent_burden"].mean()
            if pd.notna(avg_burden):
                st.metric("Avg Rent Burden", f"{avg_burden:,.0f}")
            else:
                st.metric("Avg Rent Burden", "N/A")
    
    def render_zip_metrics_card(self, zip_row):
        st.markdown("### Selected ZIP Code Metrics")
        
        zip_code = zip_row.get("zip", "N/A")
        st.markdown(f"**ZIP Code: {zip_code}**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            median_rent = zip_row.get("median_rent")
            if pd.notna(median_rent):
                st.metric("Median Rent", f"${median_rent:,.0f}")
            else:
                st.metric("Median Rent", "N/A")
        
        with col2:
            median_income = zip_row.get("median_income")
            if pd.notna(median_income):
                st.metric("Median Income", f"${median_income:,.0f}")
            else:
                st.metric("Median Income", "N/A")
        
        with col3:
            rent_burden_rate = zip_row.get("rent_burden_rate")
            if pd.notna(rent_burden_rate):
                st.metric("Rent Burden Rate", f"{rent_burden_rate:.1f}%")
            else:
                st.metric("Rent Burden Rate", "N/A")
        
        col4, col5, col6 = st.columns(3)
        
        with col4:
            rent_burden = zip_row.get("rent_burden")
            if pd.notna(rent_burden):
                st.metric("Rent Burden (HH)", f"{rent_burden:,.0f}")
            else:
                st.metric("Rent Burden (HH)", "N/A")
        
        with col5:
            vacancy_rate = zip_row.get("vacancy_rate")
            if pd.notna(vacancy_rate):
                st.metric("Vacancy Rate", f"{vacancy_rate*100:.1f}%")
            else:
                st.metric("Vacancy Rate", "N/A")
        
        with col6:
            housing_units = zip_row.get("housing_units")
            if pd.notna(housing_units):
                st.metric("Housing Units", f"{housing_units:,.0f}")
            else:
                st.metric("Housing Units", "N/A")
    
    def render_zip_comparison_chart(self, all_df, selected_zip, metric_column):
        st.markdown("### Comparison with All ZIP Codes")
        
        valid_df = all_df[all_df[metric_column].notna()].copy()
        
        if valid_df.empty:
            st.info("No valid data for comparison")
            return
        
        selected_value = valid_df[valid_df["zip"] == selected_zip][metric_column].values
        if len(selected_value) == 0:
            st.info("Selected ZIP Code has no data for this metric")
            return
        
        selected_value = selected_value[0]
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=valid_df[metric_column],
            name="All ZIP Codes",
            opacity=0.7,
            marker_color="#3498db"
        ))
        
        fig.add_vline(
            x=selected_value,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Selected ZIP: {selected_value:.2f}",
            annotation_position="top"
        )
        
        fig.update_layout(
            title=f"Position of ZIP {selected_zip} in {self.metric_labels.get(metric_column, metric_column)}",
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_zip_detailed_metrics(self, zip_row, all_df):
        st.markdown("### Detailed Metrics Analysis")
        
        metrics = ["median_rent", "median_income", "vacancy_rate", "rent_burden"]
        available_metrics = [m for m in metrics if m in all_df.columns]
        
        if not available_metrics:
            st.info("No detailed metrics available")
            return
        
        data_for_chart = []
        for metric in available_metrics:
            value = zip_row.get(metric)
            if pd.notna(value):
                avg_value = all_df[metric].mean()
                
                if metric == "vacancy_rate":
                    value = value * 100
                    avg_value = avg_value * 100
                
                data_for_chart.append({
                    "Metric": self.metric_labels.get(metric, metric),
                    "Selected ZIP": value,
                    "Average": avg_value
                })
        
        if not data_for_chart:
            st.info("No valid data for detailed analysis")
            return
        
        df_chart = pd.DataFrame(data_for_chart)
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name="Selected ZIP",
            x=df_chart["Metric"],
            y=df_chart["Selected ZIP"],
            marker_color="#e74c3c"
        ))
        
        fig.add_trace(go.Bar(
            name="Average",
            x=df_chart["Metric"],
            y=df_chart["Average"],
            marker_color="#3498db"
        ))
        
        fig.update_layout(
            barmode="group",
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            title="Comparison with Average"
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_building_stats_detailed(self, building_row):
        st.markdown("### Building Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_buildings = building_row.get("total_buildings", 0)
            st.metric("Total Buildings", f"{total_buildings:,}")
        
        with col2:
            avg_floors = building_row.get("avg_floors")
            if pd.notna(avg_floors):
                st.metric("Avg Floors", f"{avg_floors:.1f}")
            else:
                st.metric("Avg Floors", "N/A")
        
        with col3:
            avg_year = building_row.get("avg_year_built")
            if pd.notna(avg_year):
                st.metric("Avg Year Built", f"{int(avg_year)}")
            else:
                st.metric("Avg Year Built", "N/A")
        
        st.markdown("#### Buildings by Era")
        
        pre_1950 = building_row.get("buildings_pre_1950", 0)
        y1950_2000 = building_row.get("buildings_1950_2000", 0)
        post_2000 = building_row.get("buildings_post_2000", 0)
        
        era_data = pd.DataFrame({
            "Era": ["Pre-1950", "1950-2000", "Post-2000"],
            "Count": [pre_1950, y1950_2000, post_2000]
        })
        
        fig = px.bar(
            era_data,
            x="Era",
            y="Count",
            title="Building Distribution by Era",
            color_discrete_sequence=["#9b59b6"]
        )
        
        fig.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_zip_rank_analysis(self, all_df, selected_zip):
        st.markdown("### Ranking Analysis")
        
        metrics = ["median_rent", "median_income", "vacancy_rate"]
        
        for metric in metrics:
            if metric in all_df.columns:
                valid_df = all_df[all_df[metric].notna()].copy()
                if not valid_df.empty:
                    sorted_df = valid_df.sort_values(metric, ascending=False).reset_index(drop=True)
                    rank = sorted_df[sorted_df["zip"] == selected_zip].index
                    if len(rank) > 0:
                        rank = rank[0] + 1
                        total = len(sorted_df)
                        percentile = ((total - rank) / total) * 100
                        
                        st.markdown(f"**{self.metric_labels.get(metric, metric)}**")
                        st.write(f"Rank: {rank} out of {total} (Top {100 - percentile:.1f}%)")
                        st.progress(percentile / 100)
                        st.divider()
    
    def render_multi_zip_comparison(self, all_df, selected_zip, n=5):
        if "median_rent" not in all_df.columns:
            st.info("No data available for comparison")
            return
        
        valid_df = all_df[all_df["median_rent"].notna()].copy()
        
        if valid_df.empty:
            st.info("No valid data for comparison")
            return
        
        selected_value = valid_df[valid_df["zip"] == selected_zip]["median_rent"].values
        if len(selected_value) == 0:
            st.info("Selected ZIP Code has no rent data")
            return
        
        selected_value = selected_value[0]
        
        valid_df["diff_from_selected"] = (valid_df["median_rent"] - selected_value).abs()
        similar_zips = valid_df.nsmallest(n + 1, "diff_from_selected")
        similar_zips = similar_zips[similar_zips["zip"] != selected_zip].head(n)
        
        if similar_zips.empty:
            st.info("No similar ZIP Codes found")
            return
        
        st.markdown(f"### Similar ZIP Codes to {selected_zip}")
        
        comparison_data = similar_zips[["zip", "median_rent", "median_income", "vacancy_rate"]].copy()
        
        selected_row = valid_df[valid_df["zip"] == selected_zip].iloc[0]
        comparison_data = pd.concat([
            pd.DataFrame([{
                "zip": selected_zip,
                "median_rent": selected_row.get("median_rent"),
                "median_income": selected_row.get("median_income"),
                "vacancy_rate": selected_row.get("vacancy_rate")
            }]),
            comparison_data
        ])
        
        comparison_data["color"] = ["Selected" if z == selected_zip else "Similar" for z in comparison_data["zip"]]
        
        fig = px.bar(
            comparison_data,
            x="zip",
            y="median_rent",
            color="color",
            title="Median Rent Comparison",
            color_discrete_map={"Selected": "#e74c3c", "Similar": "#3498db"}
        )
        
        fig.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_distribution_chart(self, df, metric_column):
        valid_df = df[df[metric_column].notna()].copy()
        
        if valid_df.empty:
            st.info("No valid data for distribution chart")
            return
        
        fig = px.histogram(
            valid_df,
            x=metric_column,
            nbins=30,
            title=f"Distribution of {self.metric_labels.get(metric_column, metric_column)}",
            color_discrete_sequence=["#3498db"]
        )
        
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_top_bottom_charts(self, df, metric_column, n=10):
        valid_df = df[df[metric_column].notna()].copy()
        
        if valid_df.empty or len(valid_df) < 2:
            st.info("Insufficient data for ranking charts")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            top_n = min(n, len(valid_df))
            top_data = valid_df.nlargest(top_n, metric_column)[["zip", metric_column]]
            
            fig = px.bar(
                top_data,
                x="zip",
                y=metric_column,
                title=f"Top {top_n} ZIP Codes",
                color_discrete_sequence=["#e74c3c"]
            )
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            bottom_n = min(n, len(valid_df))
            bottom_data = valid_df.nsmallest(bottom_n, metric_column)[["zip", metric_column]]
            
            fig = px.bar(
                bottom_data,
                x="zip",
                y=metric_column,
                title=f"Bottom {bottom_n} ZIP Codes",
                color_discrete_sequence=["#2ecc71"]
            )
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
    
    def render_correlation_matrix(self, df):
        numeric_cols = ["median_rent", "median_income", "rent_burden", 
                       "vacancy_rate", "housing_units"]
        
        available_cols = [col for col in numeric_cols if col in df.columns]
        corr_df = df[available_cols].corr()
        
        fig = px.imshow(
            corr_df,
            text_auto=".2f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            title="Correlation Matrix of Housing Metrics"
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_comparison_charts(self, df, metric1, metric2):
        valid_df = df[(df[metric1].notna()) & (df[metric2].notna())].copy()
        
        if valid_df.empty:
            st.info("No valid data for comparison")
            return
        
        fig = px.scatter(
            valid_df,
            x=metric1,
            y=metric2,
            hover_data=["zip"],
            title=f"{self.metric_labels.get(metric1, metric1)} vs {self.metric_labels.get(metric2, metric2)}",
            color="vacancy_rate" if "vacancy_rate" in valid_df.columns else None,
            color_continuous_scale="Viridis"
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    def render_rent_burden_analysis(self, df):
        if "rent_burden" not in df.columns or df["rent_burden"].isna().all():
            st.info("Rent burden data not available")
            return
        
        st.subheader("Rent Burden Analysis")
        
        valid_df = df[df["rent_burden"].notna()].copy()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.histogram(
                valid_df,
                x="rent_burden",
                nbins=30,
                title="Rent Burden Distribution (Number of Households)",
                color_discrete_sequence=["#3498db"]
            )
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            high_burden = valid_df.nlargest(10, "rent_burden")[["zip", "rent_burden"]]
            if not high_burden.empty:
                fig = px.bar(
                    high_burden,
                    x="zip",
                    y="rent_burden",
                    title="Top 10 ZIP Codes by Rent Burden Households",
                    color_discrete_sequence=["#e74c3c"]
                )
                fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

