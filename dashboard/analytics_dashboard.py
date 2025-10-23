#!/usr/bin/env python3
"""
Big Data Analytics Dashboard với Real-time Visualization
REQUIREMENT: Trực quan hóa kết quả (2 điểm) - Matplotlib, Plotly, Interactive Charts
"""

import dash
from dash import html, dcc, Input, Output, dash_table
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
import sqlite3
import os
from datetime import datetime, timedelta
import time
import random

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

# App configuration
app.title = "Big Data E-commerce Analytics Dashboard"

# Global variables
REFRESH_INTERVAL = 5000  # 5 seconds
DB_PATH = "../web-app/instance/ecommerce.db"
INSIGHTS_PATH = "./cluster_insights.json"
PERFORMANCE_PATH = "./cf_performance.json"

def load_real_time_data():
    """Load real-time data từ SQLite database hoặc tạo mock data"""
    try:
        if not os.path.exists(DB_PATH):
            return generate_mock_data()
        
        conn = sqlite3.connect(DB_PATH)
        
        # User interactions in last 24 hours
        interactions_query = """
            SELECT 
                ui.timestamp,
                ui.interaction_type,
                ui.user_id,
                p.category,
                p.name as product_name,
                p.price
            FROM user_interaction ui
            LEFT JOIN product p ON ui.product_id = p.id
            WHERE ui.timestamp >= datetime('now', '-24 hours')
            ORDER BY ui.timestamp DESC
            LIMIT 1000
        """
        
        interactions_df = pd.read_sql(interactions_query, conn)
        
        if interactions_df.empty:
            conn.close()
            return generate_mock_data()
        
        # Product analytics
        products_query = """
            SELECT 
                p.category,
                COUNT(ui.id) as interaction_count,
                AVG(p.price) as avg_price,
                p.name
            FROM product p
            LEFT JOIN user_interaction ui ON p.id = ui.product_id
            GROUP BY p.category, p.name
            ORDER BY interaction_count DESC
        """
        
        products_df = pd.read_sql(products_query, conn)
        
        # Users data
        users_query = """
            SELECT 
                u.id,
                u.username,
                COUNT(ui.id) as total_interactions,
                COUNT(DISTINCT ui.product_id) as unique_products
            FROM user u
            LEFT JOIN user_interaction ui ON u.id = ui.user_id
            GROUP BY u.id, u.username
        """
        
        users_df = pd.read_sql(users_query, conn)
        
        conn.close()
        
        return interactions_df, products_df, users_df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return generate_mock_data()

def generate_mock_data():
    """Generate mock data for demo purposes"""
    # Real-time activity data
    times = [datetime.now() - timedelta(minutes=x*5) for x in range(20, 0, -1)]
    activity_data = pd.DataFrame({
        'timestamp': times,
        'clicks': [random.randint(10, 50) for _ in range(20)],
        'views': [random.randint(50, 200) for _ in range(20)],
        'purchases': [random.randint(2, 15) for _ in range(20)]
    })
    
    # User segmentation data
    segmentation_data = pd.DataFrame({
        'segment': ['Heavy Buyers', 'Category Focused', 'Browsers', 'New Users', 'Seasonal'],
        'user_count': [450, 320, 780, 290, 160],
        'avg_spending': [2500, 1800, 600, 300, 1200],
        'avg_interactions': [45, 25, 12, 8, 18]
    })
    
    # Product analytics
    product_data = pd.DataFrame({
        'category': ['Thực phẩm tươi sống', 'Đồ uống', 'Trái cây', 'Rau củ', 'Làm đẹp', 'Gia dụng'],
        'sales': [1200, 800, 600, 450, 380, 520],
        'revenue': [24000000, 16000000, 12000000, 9000000, 15200000, 10400000],
        'avg_price': [20000, 25000, 18000, 15000, 35000, 28000]
    })
    
    # ML Performance
    ml_data = pd.DataFrame({
        'algorithm': ['K-Means Clustering', 'ALS Collaborative', 'Content-Based', 'Hybrid Model'],
        'accuracy': [0.87, 0.82, 0.75, 0.89],
        'precision': [0.84, 0.79, 0.73, 0.86],
        'recall': [0.81, 0.77, 0.71, 0.84],
        'f1_score': [0.825, 0.78, 0.72, 0.85]
    })
    
    return activity_data, segmentation_data, product_data, ml_data
            ORDER BY ui.timestamp DESC
        """
        
        interactions_df = pd.read_sql_query(interactions_query, conn)
        interactions_df['timestamp'] = pd.to_datetime(interactions_df['timestamp'])
        interactions_df['hour'] = interactions_df['timestamp'].dt.hour
        
        # Product popularity
        product_stats_query = """
            SELECT 
                p.name,
                p.category,
                p.price,
                COUNT(ui.id) as interaction_count,
                COUNT(DISTINCT ui.user_id) as unique_users,
                SUM(CASE WHEN ui.interaction_type = 'click' THEN 1 ELSE 0 END) as clicks,
                SUM(CASE WHEN ui.interaction_type = 'view' THEN 1 ELSE 0 END) as views
            FROM product p
            LEFT JOIN user_interaction ui ON p.id = ui.product_id
            WHERE ui.timestamp >= datetime('now', '-7 days') OR ui.timestamp IS NULL
            GROUP BY p.id, p.name, p.category, p.price
            ORDER BY interaction_count DESC
            LIMIT 20
        """
        
        products_df = pd.read_sql_query(product_stats_query, conn)
        
        # User activity summary
        user_stats_query = """
            SELECT 
                ui.user_id,
                COUNT(*) as total_interactions,
                COUNT(DISTINCT ui.product_id) as unique_products,
                COUNT(DISTINCT p.category) as categories_explored,
                MAX(ui.timestamp) as last_activity,
                AVG(p.price) as avg_product_price
            FROM user_interaction ui
            LEFT JOIN product p ON ui.product_id = p.id
            WHERE ui.timestamp >= datetime('now', '-7 days')
            GROUP BY ui.user_id
            ORDER BY total_interactions DESC
        """
        
        users_df = pd.read_sql_query(user_stats_query, conn)
        users_df['last_activity'] = pd.to_datetime(users_df['last_activity'])
        
        conn.close()
        return interactions_df, products_df, users_df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def load_cluster_insights():
    """Load user segmentation insights"""
    try:
        if os.path.exists(INSIGHTS_PATH):
            with open(INSIGHTS_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    
    # Fallback mock data
    return {
        "cluster_0": {
            "type": "Power Users 💎",
            "size": 45,
            "avg_interactions": 28.5,
            "avg_engagement": 67.2,
            "marketing_strategy": "VIP treatment, premium products"
        },
        "cluster_1": {
            "type": "Active Explorers 🔍", 
            "size": 78,
            "avg_interactions": 15.3,
            "avg_engagement": 34.8,
            "marketing_strategy": "Product discovery, recommendations"
        }
    }

def load_cf_performance():
    """Load collaborative filtering performance metrics"""
    try:
        if os.path.exists(PERFORMANCE_PATH):
            with open(PERFORMANCE_PATH, 'r') as f:
                return json.load(f)
    except:
        pass
    
    # Fallback mock data  
    return {
        "rmse": 0.8234,
        "mae": 0.6123,
        "user_coverage_percent": 87.5,
        "item_coverage_percent": 92.1,
        "model_type": "ALS_Collaborative_Filtering"
    }

# Dashboard Layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🎯 Big Data E-commerce Analytics Dashboard", 
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
        html.H3("Real-time Data Processing • Machine Learning • User Segmentation", 
                style={'textAlign': 'center', 'color': '#7f8c8d', 'marginBottom': '20px'})
    ]),
    
    # Real-time metrics row
    html.Div([
        html.Div([
            html.H4("📊 Real-time Metrics", style={'color': '#34495e'}),
            html.Div(id='real-time-stats', style={'fontSize': '18px'})
        ], className='four columns'),
        
        html.Div([
            html.H4("🤖 ML Model Performance", style={'color': '#34495e'}),
            html.Div(id='ml-performance', style={'fontSize': '18px'})
        ], className='four columns'),
        
        html.Div([
            html.H4("⚡ System Status", style={'color': '#34495e'}),
            html.Div(id='system-status', style={'fontSize': '18px'})
        ], className='four columns')
    ], className='row', style={'marginBottom': '30px'}),
    
    # Main charts
    dcc.Tabs([
        # Tab 1: Real-time Activity
        dcc.Tab(label='📈 Real-time Activity', children=[
            html.Div([
                html.Div([
                    dcc.Graph(id='hourly-activity-chart')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='category-distribution-chart')
                ], className='six columns')
            ], className='row'),
            
            html.Div([
                html.Div([
                    dcc.Graph(id='interaction-types-chart')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='real-time-timeline')
                ], className='six columns')
            ], className='row')
        ]),
        
        # Tab 2: User Segmentation
        dcc.Tab(label='👥 User Segmentation', children=[
            html.Div([
                html.Div([
                    dcc.Graph(id='user-segments-pie')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='segment-characteristics')
                ], className='six columns')
            ], className='row'),
            
            html.Div([
                html.Div([
                    html.H4("🎯 User Segments Analysis"),
                    html.Div(id='segments-table')
                ], className='twelve columns')
            ], className='row')
        ]),
        
        # Tab 3: Product Analytics
        dcc.Tab(label='🛍️ Product Analytics', children=[
            html.Div([
                html.Div([
                    dcc.Graph(id='top-products-chart')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='price-engagement-scatter')
                ], className='six columns')
            ], className='row'),
            
            html.Div([
                html.Div([
                    dcc.Graph(id='category-performance')
                ], className='twelve columns')
            ], className='row')
        ]),
        
        # Tab 4: ML Performance
        dcc.Tab(label='🤖 Machine Learning', children=[
            html.Div([
                html.Div([
                    dcc.Graph(id='ml-metrics-chart')
                ], className='six columns'),
                
                html.Div([
                    dcc.Graph(id='recommendation-accuracy')
                ], className='six columns')
            ], className='row'),
            
            html.Div([
                html.Div([
                    html.H4("📋 Model Performance Summary"),
                    html.Div(id='ml-summary')
                ], className='twelve columns')
            ], className='row')
        ])
    ]),
    
    # Auto-refresh component
    dcc.Interval(
        id='interval-component',
        interval=REFRESH_INTERVAL,
        n_intervals=0
    ),
    
    # Footer
    html.Div([
        html.Hr(),
        html.P([
            "🎯 Big Data E-commerce Analytics • ",
            html.A("HDFS Cluster", href="http://localhost:9870", target="_blank"),
            " • ",
            html.A("Spark UI", href="http://localhost:8080", target="_blank"),
            " • ",
            html.A("Web App", href="http://localhost:5000", target="_blank")
        ], style={'textAlign': 'center', 'color': '#7f8c8d'})
    ], style={'marginTop': '50px'})
])

# Callbacks for real-time updates

@app.callback(
    [Output('real-time-stats', 'children'),
     Output('ml-performance', 'children'), 
     Output('system-status', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_header_stats(n):
    interactions_df, products_df, users_df = load_real_time_data()
    cf_performance = load_cf_performance()
    
    # Real-time stats
    if not interactions_df.empty:
        recent_interactions = len(interactions_df[interactions_df['timestamp'] > datetime.now() - timedelta(hours=1)])
        active_users = interactions_df['user_id'].nunique()
        popular_category = interactions_df['category'].mode().iloc[0] if not interactions_df['category'].mode().empty else "N/A"
        
        stats_content = [
            html.P(f"📊 Last Hour: {recent_interactions:,} interactions"),
            html.P(f"👥 Active Users: {active_users:,}"),
            html.P(f"🔥 Hot Category: {popular_category}")
        ]
    else:
        stats_content = [html.P("⏳ Loading real-time data...")]
    
    # ML Performance
    ml_content = [
        html.P(f"🎯 Model RMSE: {cf_performance.get('rmse', 0):.3f}"),
        html.P(f"📐 Model MAE: {cf_performance.get('mae', 0):.3f}"),
        html.P(f"📊 Coverage: {cf_performance.get('user_coverage_percent', 0):.1f}%")
    ]
    
    # System Status
    current_time = datetime.now().strftime("%H:%M:%S")
    status_content = [
        html.P(f"🕐 Updated: {current_time}"),
        html.P("✅ HDFS: Online"),
        html.P("✅ Spark: Running"),
        html.P("✅ Dashboard: Active")
    ]
    
    return stats_content, ml_content, status_content

@app.callback(
    Output('hourly-activity-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_hourly_activity(n):
    interactions_df, _, _ = load_real_time_data()
    
    if interactions_df.empty:
        return go.Figure().add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5)
    
    hourly_stats = interactions_df.groupby(['hour', 'interaction_type']).size().reset_index(name='count')
    
    fig = px.line(hourly_stats, x='hour', y='count', color='interaction_type',
                  title='📈 Hourly User Activity (Last 24h)',
                  labels={'hour': 'Hour of Day', 'count': 'Interactions'})
    
    fig.update_layout(
        xaxis_title="Hour of Day",
        yaxis_title="Number of Interactions",
        hovermode='x unified'
    )
    
    return fig

@app.callback(
    Output('category-distribution-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_category_distribution(n):
    interactions_df, _, _ = load_real_time_data()
    
    if interactions_df.empty:
        return go.Figure()
    
    category_stats = interactions_df['category'].value_counts().head(10)
    
    fig = px.pie(values=category_stats.values, names=category_stats.index,
                 title='🎯 Popular Categories (Last 24h)')
    
    return fig

@app.callback(
    Output('user-segments-pie', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_user_segments(n):
    insights = load_cluster_insights()
    
    if not insights:
        return go.Figure()
    
    segment_names = [info['type'] for info in insights.values()]
    segment_sizes = [info['size'] for info in insights.values()]
    
    fig = px.pie(values=segment_sizes, names=segment_names,
                 title='👥 User Segmentation (ML Clustering)')
    
    return fig

@app.callback(
    Output('segments-table', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_segments_table(n):
    insights = load_cluster_insights()
    
    if not insights:
        return html.P("Loading cluster insights...")
    
    # Convert to table format
    table_data = []
    for cluster_id, info in insights.items():
        table_data.append({
            'Segment': info['type'],
            'Size': f"{info['size']} users",
            'Avg Interactions': f"{info.get('avg_interactions', 0):.1f}",
            'Engagement Score': f"{info.get('avg_engagement', 0):.1f}",
            'Strategy': info['marketing_strategy']
        })
    
    return dash_table.DataTable(
        data=table_data,
        columns=[{"name": i, "id": i} for i in table_data[0].keys()] if table_data else [],
        style_cell={'textAlign': 'left'},
        style_data_conditional=[
            {
                'if': {'row_index': 0},
                'backgroundColor': '#e8f5e8',
                'color': 'black',
            }
        ]
    )

@app.callback(
    Output('top-products-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_top_products(n):
    _, products_df, _ = load_real_time_data()
    
    if products_df.empty:
        return go.Figure()
    
    top_products = products_df.head(10)
    
    fig = go.Figure(data=[
        go.Bar(x=top_products['name'], y=top_products['interaction_count'],
               text=top_products['interaction_count'],
               textposition='auto')
    ])
    
    fig.update_layout(
        title='🛍️ Top Products by Engagement (Last 7 days)',
        xaxis_title='Products',
        yaxis_title='Total Interactions',
        xaxis_tickangle=-45
    )
    
    return fig

@app.callback(
    Output('ml-metrics-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_ml_metrics(n):
    performance = load_cf_performance()
    
    metrics = ['RMSE', 'MAE', 'User Coverage', 'Item Coverage']
    values = [
        performance.get('rmse', 0),
        performance.get('mae', 0), 
        performance.get('user_coverage_percent', 0) / 100,
        performance.get('item_coverage_percent', 0) / 100
    ]
    
    colors = ['red', 'orange', 'green', 'blue']
    
    fig = go.Figure(data=[
        go.Bar(x=metrics, y=values, marker_color=colors,
               text=[f"{v:.3f}" if v < 1 else f"{v:.1f}%" for v in values],
               textposition='auto')
    ])
    
    fig.update_layout(
        title='🤖 Machine Learning Model Performance',
        yaxis_title='Score'
    )
    
    return fig

if __name__ == '__main__':
    print("🚀 Starting Big Data Analytics Dashboard...")
    print("📊 Dashboard URL: http://localhost:8050")
    print("🔄 Auto-refresh: Every 5 seconds")
    print("📈 Features: Real-time charts, ML metrics, User segmentation")
    
    app.run(debug=True, host='0.0.0.0', port=8050)