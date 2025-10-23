#!/usr/bin/env python3
"""
Big Data Analytics Dashboard - Sửa lỗi callback
"""

import dash
from dash import html, dcc, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
import random

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "Big Data E-commerce Analytics Dashboard"

# Configuration
REFRESH_INTERVAL = 5000  # 5 seconds

def generate_demo_data():
    """Generate demo data for visualization"""
    
    # Real-time activity data
    times = [datetime.now() - timedelta(minutes=x*5) for x in range(24, 0, -1)]
    activity_data = pd.DataFrame({
        'timestamp': times,
        'clicks': [random.randint(15, 65) + int(10*np.sin(x/3)) for x in range(24)],
        'views': [random.randint(80, 250) + int(20*np.sin(x/4)) for x in range(24)],
        'purchases': [random.randint(3, 18) + int(5*np.sin(x/5)) for x in range(24)]
    })
    
    # User segmentation data
    segmentation_data = pd.DataFrame({
        'segment': ['Heavy Buyers', 'Category Focused', 'Window Shoppers', 'New Users', 'Seasonal Buyers'],
        'user_count': [450, 320, 780, 290, 160],
        'avg_spending': [2500000, 1800000, 600000, 300000, 1200000],
        'avg_interactions': [45, 25, 12, 8, 18]
    })
    
    # Product analytics
    categories = ['Thực phẩm tươi sống', 'Đồ uống', 'Trái cây', 'Rau củ quả', 'Làm đẹp', 'Gia dụng']
    product_data = pd.DataFrame({
        'category': categories,
        'sales_count': [1200, 800, 600, 450, 380, 520],
        'revenue': [24000000, 16000000, 12000000, 9000000, 15200000, 10400000],
        'avg_price': [20000, 25000, 18000, 15000, 35000, 28000],
        'user_engagement': [0.85, 0.72, 0.68, 0.63, 0.78, 0.65]
    })
    
    # ML performance
    ml_performance = pd.DataFrame({
        'algorithm': ['K-Means Clustering', 'ALS Collaborative Filtering', 'Content-Based Filtering', 'Hybrid Recommendation'],
        'accuracy': [0.87, 0.823, 0.751, 0.892],
        'precision': [0.84, 0.79, 0.73, 0.86],
        'recall': [0.81, 0.77, 0.71, 0.84],
        'f1_score': [0.825, 0.78, 0.72, 0.85]
    })
    
    # System metrics
    system_metrics = {
        'total_users_online': random.randint(45, 120),
        'active_sessions': random.randint(28, 85),
        'db_queries_per_sec': random.randint(15, 45),
        'ml_predictions_per_min': random.randint(200, 500),
        'last_update': datetime.now().strftime("%H:%M:%S")
    }
    
    return activity_data, segmentation_data, product_data, ml_performance, system_metrics

# App Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🎯 Big Data E-commerce Analytics Dashboard", 
               style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': 10}),
        html.P("Real-time Data Processing • Machine Learning • User Segmentation", 
               style={'textAlign': 'center', 'color': '#7f8c8d', 'fontSize': 18, 'marginBottom': 30})
    ]),
    
    # Status Cards
    html.Div([
        html.Div([
            html.H4("📊 Real-time Metrics", style={'color': '#3498db', 'marginBottom': 10}),
            html.P(id='users-online', children="👥 Users Online: Loading...", style={'margin': '5px 0'}),
            html.P(id='active-sessions', children="🔄 Active Sessions: Loading...", style={'margin': '5px 0'}),
            html.P(id='db-queries', children="💾 DB Queries/sec: Loading...", style={'margin': '5px 0'})
        ], style={
            'width': '30%', 'display': 'inline-block', 'margin': '1.5%', 'padding': '20px',
            'border': '2px solid #3498db', 'borderRadius': '10px', 'backgroundColor': '#f8f9fa'
        }),
        
        html.Div([
            html.H4("🤖 ML Performance", style={'color': '#e74c3c', 'marginBottom': 10}),
            html.P("🎯 ALS RMSE: 0.823", style={'margin': '5px 0'}),
            html.P("📈 ALS MAE: 0.612", style={'margin': '5px 0'}),
            html.P("📊 User Coverage: 87.5%", style={'margin': '5px 0'}),
            html.P("🔮 Predictions/min: ", id='ml-predictions', style={'margin': '5px 0'})
        ], style={
            'width': '30%', 'display': 'inline-block', 'margin': '1.5%', 'padding': '20px',
            'border': '2px solid #e74c3c', 'borderRadius': '10px', 'backgroundColor': '#f8f9fa'
        }),
        
        html.Div([
            html.H4("⚡ System Status", style={'color': '#27ae60', 'marginBottom': 10}),
            html.P(id='last-update', children="🕐 Updated: Loading...", style={'margin': '5px 0'}),
            html.P("✅ HDFS: Online", style={'margin': '5px 0', 'color': '#27ae60'}),
            html.P("✅ Spark: Running", style={'margin': '5px 0', 'color': '#27ae60'}),
            html.P("✅ Dashboard: Active", style={'margin': '5px 0', 'color': '#27ae60'})
        ], style={
            'width': '30%', 'display': 'inline-block', 'margin': '1.5%', 'padding': '20px',
            'border': '2px solid #27ae60', 'borderRadius': '10px', 'backgroundColor': '#f8f9fa'
        })
    ], style={'marginBottom': '30px'}),
    
    # Tabs
    dcc.Tabs(id='main-tabs', value='tab-1', children=[
        dcc.Tab(label='📈 Real-time Activity', value='tab-1', children=[
            html.Div([
                dcc.Graph(id='activity-timeline'),
                dcc.Graph(id='current-metrics')
            ], style={'padding': '20px'})
        ]),
        
        dcc.Tab(label='👥 User Segmentation', value='tab-2', children=[
            html.Div([
                dcc.Graph(id='segmentation-pie'),
                dcc.Graph(id='cluster-scatter')
            ], style={'padding': '20px'})
        ]),
        
        dcc.Tab(label='🛒 Product Analytics', value='tab-3', children=[
            html.Div([
                dcc.Graph(id='category-performance'),
                dcc.Graph(id='revenue-treemap')
            ], style={'padding': '20px'})
        ]),
        
        dcc.Tab(label='🤖 Machine Learning', value='tab-4', children=[
            html.Div([
                dcc.Graph(id='ml-accuracy'),
                dcc.Graph(id='ml-radar')
            ], style={'padding': '20px'})
        ])
    ]),
    
    # Auto-refresh
    dcc.Interval(
        id='interval-component',
        interval=REFRESH_INTERVAL,
        n_intervals=0
    )
])

# Status cards callbacks
@app.callback(
    [Output('users-online', 'children'),
     Output('active-sessions', 'children'),
     Output('db-queries', 'children'),
     Output('ml-predictions', 'children'),
     Output('last-update', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_status_cards(n):
    try:
        _, _, _, _, system_metrics = generate_demo_data()
        return (
            f"👥 Users Online: {system_metrics['total_users_online']}",
            f"🔄 Active Sessions: {system_metrics['active_sessions']}",
            f"💾 DB Queries/sec: {system_metrics['db_queries_per_sec']}",
            f"{system_metrics['ml_predictions_per_min']}",
            f"🕐 Updated: {system_metrics['last_update']}"
        )
    except Exception as e:
        print(f"Error in status cards: {e}")
        current_time = datetime.now().strftime("%H:%M:%S")
        return (
            "👥 Users Online: 45", 
            "🔄 Active Sessions: 28", 
            "💾 DB Queries/sec: 25", 
            "350", 
            f"🕐 Updated: {current_time}"
        )

# Activity tab callbacks
@app.callback(
    [Output('activity-timeline', 'figure'),
     Output('current-metrics', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_activity_tab(n):
    try:
        activity_data, _, _, _, _ = generate_demo_data()
        
        # Timeline chart
        timeline_fig = go.Figure()
        timeline_fig.add_trace(go.Scatter(
            x=activity_data['timestamp'], y=activity_data['clicks'],
            mode='lines+markers', name='Clicks', line=dict(color='#3498db', width=3)
        ))
        timeline_fig.add_trace(go.Scatter(
            x=activity_data['timestamp'], y=activity_data['views'],
            mode='lines+markers', name='Views', line=dict(color='#2ecc71', width=3)
        ))
        timeline_fig.add_trace(go.Scatter(
            x=activity_data['timestamp'], y=activity_data['purchases'],
            mode='lines+markers', name='Purchases', line=dict(color='#e74c3c', width=3)
        ))
        timeline_fig.update_layout(
            title="📊 Real-time User Activity (Last 2 Hours)",
            xaxis_title="Time", yaxis_title="Count", height=400
        )
        
        # Current metrics
        current_values = [
            activity_data['clicks'].iloc[-1],
            activity_data['views'].iloc[-1], 
            activity_data['purchases'].iloc[-1]
        ]
        metrics_fig = go.Figure([
            go.Bar(
                x=['Clicks', 'Views', 'Purchases'], y=current_values,
                marker_color=['#3498db', '#2ecc71', '#e74c3c'],
                text=current_values, textposition='auto'
            )
        ])
        metrics_fig.update_layout(
            title="📈 Current Activity (Last 5 minutes)", height=400
        )
        
        return timeline_fig, metrics_fig
    except Exception as e:
        print(f"Error in activity tab: {e}")
        return {}, {}

# Segmentation tab callbacks
@app.callback(
    [Output('segmentation-pie', 'figure'),
     Output('cluster-scatter', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_segmentation_tab(n):
    try:
        _, segmentation_data, _, _, _ = generate_demo_data()
        
        # Pie chart
        pie_fig = px.pie(
            segmentation_data, values='user_count', names='segment',
            title="👥 User Segmentation Distribution (K-Means Results)",
            color_discrete_sequence=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        )
        pie_fig.update_layout(height=400)
        
        # Scatter plot
        scatter_fig = px.scatter(
            segmentation_data, x='avg_spending', y='avg_interactions',
            size='user_count', color='segment',
            title="🎯 User Clusters Visualization",
            labels={'avg_spending': 'Average Spending (VND)', 'avg_interactions': 'Interactions/Month'},
            color_discrete_sequence=['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6']
        )
        scatter_fig.update_layout(height=400)
        
        return pie_fig, scatter_fig
    except Exception as e:
        print(f"Error in segmentation tab: {e}")
        return {}, {}

# Product analytics tab callbacks  
@app.callback(
    [Output('category-performance', 'figure'),
     Output('revenue-treemap', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_products_tab(n):
    try:
        _, _, product_data, _, _ = generate_demo_data()
        
        # Performance bar chart
        performance_fig = px.bar(
            product_data, x='category', y='sales_count',
            color='user_engagement',
            title="🛒 Category Performance (Sales Count & Engagement)",
            labels={'sales_count': 'Sales Count', 'user_engagement': 'Engagement Rate'},
            color_continuous_scale='Viridis'
        )
        performance_fig.update_xaxis(tickangle=45)
        performance_fig.update_layout(height=400)
        
        # Revenue treemap
        treemap_fig = px.treemap(
            product_data, path=[px.Constant("Categories"), 'category'],
            values='revenue', title="💰 Revenue Distribution by Category",
            color='revenue', color_continuous_scale='RdYlBu'
        )
        treemap_fig.update_layout(height=400)
        
        return performance_fig, treemap_fig
    except Exception as e:
        print(f"Error in products tab: {e}")
        return {}, {}

# ML tab callbacks
@app.callback(
    [Output('ml-accuracy', 'figure'),
     Output('ml-radar', 'figure')],
    [Input('interval-component', 'n_intervals')]
)
def update_ml_tab(n):
    try:
        _, _, _, ml_performance, _ = generate_demo_data()
        
        # Accuracy bar chart
        accuracy_fig = px.bar(
            ml_performance, x='algorithm', y='accuracy',
            color='accuracy', title="🤖 ML Model Accuracy Comparison",
            color_continuous_scale='Greens', text='accuracy'
        )
        accuracy_fig.update_traces(texttemplate='%{text:.3f}', textposition='outside')
        accuracy_fig.update_xaxis(tickangle=45)
        accuracy_fig.update_layout(height=400)
        
        # Radar chart
        radar_fig = go.Figure()
        metrics = ['accuracy', 'precision', 'recall', 'f1_score']
        metric_labels = ['Accuracy', 'Precision', 'Recall', 'F1-Score']
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12']
        
        for i, (_, row) in enumerate(ml_performance.iterrows()):
            values = [row[metric] for metric in metrics]
            values.append(values[0])
            
            radar_fig.add_trace(go.Scatterpolar(
                r=values, theta=metric_labels + [metric_labels[0]],
                fill='toself', name=row['algorithm'],
                line_color=colors[i % len(colors)]
            ))
        
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
            title="📊 ML Model Performance Comparison", height=400
        )
        
        return accuracy_fig, radar_fig
    except Exception as e:
        print(f"Error in ML tab: {e}")
        return {}, {}

if __name__ == '__main__':
    print("🚀 Starting Big Data Analytics Dashboard...")
    print("📊 Dashboard URL: http://localhost:8050")
    print("🔄 Auto-refresh: Every 5 seconds")
    print("📈 Features: Real-time charts, ML metrics, User segmentation")
    print("🎯 Ready for Big Data demo!")
    
    app.run(debug=True, host='0.0.0.0', port=8050)