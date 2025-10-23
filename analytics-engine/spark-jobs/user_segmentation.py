#!/usr/bin/env python3
"""
Big Data User Segmentation Analysis với Apache Spark và Machine Learning
Requirement: Phân tích dữ liệu lớn với clustering algorithms (4 điểm)
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.evaluation import ClusteringEvaluator
import pandas as pd
import numpy as np
import sqlite3
import os
import json
from datetime import datetime, timedelta

class BigDataUserSegmentation:
    def __init__(self):
        """Initialize Spark session và setup HDFS connection"""
        self.spark = SparkSession.builder \
            .appName("BigDataEcommerceAnalytics") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # HDFS paths
        self.hdfs_base_path = "hdfs://localhost:9000"
        self.user_interactions_path = f"{self.hdfs_base_path}/ecommerce/user_interactions"
        self.products_path = f"{self.hdfs_base_path}/ecommerce/products"
        self.analytics_results_path = f"{self.hdfs_base_path}/analytics/user_segments"
        
        print("🚀 Big Data Analytics Engine initialized")
        print(f"📊 Spark Version: {self.spark.version}")
        print(f"🗄️ HDFS Base Path: {self.hdfs_base_path}")
    
    def migrate_data_to_hdfs(self):
        """
        REQUIREMENT: Lưu trữ phân tán (2 điểm)
        Migrate dữ liệu từ SQLite sang HDFS để đáp ứng yêu cầu distributed storage
        """
        print("📦 MIGRATING DATA TO HDFS (Distributed Storage Requirement)")
        print("-" * 60)
        
        sqlite_db_path = os.path.join("..", "..", "web-app", "instance", "ecommerce.db")
        
        if not os.path.exists(sqlite_db_path):
            print(f"❌ SQLite database not found: {sqlite_db_path}")
            return False
        
        try:
            # Connect to SQLite
            conn = sqlite3.connect(sqlite_db_path)
            
            # 1. Migrate User Interactions
            print("📋 Migrating user_interaction table...")
            interactions_df = pd.read_sql_query("""
                SELECT 
                    ui.user_id,
                    ui.product_id, 
                    ui.interaction_type,
                    ui.timestamp,
                    ui.details,
                    p.name as product_name,
                    p.category,
                    p.price
                FROM user_interaction ui
                LEFT JOIN product p ON ui.product_id = p.id
                WHERE ui.timestamp >= datetime('now', '-30 days')
                ORDER BY ui.timestamp DESC
            """, conn)
            
            # Convert to Spark DataFrame
            spark_interactions = self.spark.createDataFrame(interactions_df)
            
            # Add derived columns for analytics
            spark_interactions = spark_interactions.withColumn(
                "timestamp_dt", to_timestamp(col("timestamp"))
            ).withColumn(
                "hour_of_day", hour(col("timestamp_dt"))
            ).withColumn(
                "day_of_week", dayofweek(col("timestamp_dt"))
            ).withColumn(
                "interaction_score", 
                when(col("interaction_type") == "click", 3)
                .when(col("interaction_type") == "view", 1) 
                .when(col("interaction_type") == "purchase", 5)
                .otherwise(1)
            )
            
            # Save to HDFS với partitioning
            spark_interactions.write \
                .mode("overwrite") \
                .partitionBy("category") \
                .parquet(self.user_interactions_path)
            
            print(f"✅ Migrated {interactions_df.shape[0]} user interactions to HDFS")
            
            # 2. Migrate Products
            print("🛍️ Migrating product table...")
            products_df = pd.read_sql_query("SELECT * FROM product", conn)
            spark_products = self.spark.createDataFrame(products_df)
            
            spark_products.write \
                .mode("overwrite") \
                .parquet(self.products_path)
            
            print(f"✅ Migrated {products_df.shape[0]} products to HDFS")
            
            conn.close()
            
            # Verify HDFS data
            print("\n🔍 VERIFYING HDFS DATA:")
            interactions_count = self.spark.read.parquet(self.user_interactions_path).count()
            products_count = self.spark.read.parquet(self.products_path).count()
            
            print(f"📊 User interactions in HDFS: {interactions_count:,}")
            print(f"🛍️ Products in HDFS: {products_count:,}")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration error: {e}")
            return False
    
    def analyze_user_behavior_bigdata(self):
        """
        REQUIREMENT: Xử lý và phân tích dữ liệu lớn (4 điểm)
        Sử dụng Spark để xử lý và phân tích dữ liệu với MapReduce paradigm
        """
        print("⚡ BIG DATA ANALYSIS - User Behavior Processing")
        print("-" * 60)
        
        try:
            # Load data từ HDFS
            interactions_df = self.spark.read.parquet(self.user_interactions_path)
            
            print(f"📊 Loaded {interactions_df.count():,} interactions from HDFS")
            
            # 🔥 SPARK SQL ANALYTICS (MapReduce under the hood)
            interactions_df.createOrReplaceTempView("interactions")
            
            # User behavior aggregation với Spark SQL
            user_features = self.spark.sql("""
                SELECT 
                    user_id,
                    COUNT(*) as total_interactions,
                    COUNT(DISTINCT product_id) as unique_products_viewed,
                    COUNT(DISTINCT category) as categories_explored,
                    SUM(interaction_score) as total_engagement_score,
                    AVG(interaction_score) as avg_interaction_intensity,
                    COUNT(DISTINCT DATE(timestamp_dt)) as active_days,
                    
                    -- Time-based patterns
                    AVG(hour_of_day) as avg_hour_activity,
                    MODE(day_of_week) as favorite_day_of_week,
                    
                    -- Category preferences  
                    MODE(category) as most_viewed_category,
                    
                    -- Recent activity (last 7 days)
                    SUM(CASE WHEN timestamp_dt >= date_sub(current_date(), 7) 
                        THEN interaction_score ELSE 0 END) as recent_engagement,
                    
                    -- Purchase behavior
                    COUNT(CASE WHEN interaction_type = 'click' THEN 1 END) as total_clicks,
                    COUNT(CASE WHEN interaction_type = 'view' THEN 1 END) as total_views,
                    
                    -- Price sensitivity (average price of viewed products)
                    AVG(price) as avg_product_price_viewed
                    
                FROM interactions 
                WHERE user_id IS NOT NULL
                GROUP BY user_id
                HAVING total_interactions >= 5
                ORDER BY total_engagement_score DESC
            """)
            
            print(f"✅ Computed features for {user_features.count():,} users")
            
            return user_features
            
        except Exception as e:
            print(f"❌ Big data analysis error: {e}")
            return None
    
    def perform_ml_clustering(self, user_features_df):
        """
        REQUIREMENT: Machine Learning Algorithms (2 điểm) 
        Áp dụng K-Means clustering để phân đoạn người dùng
        """
        print("🤖 MACHINE LEARNING - K-Means User Clustering")
        print("-" * 60)
        
        try:
            # Prepare features for ML
            feature_cols = [
                'total_interactions', 'unique_products_viewed', 'categories_explored',
                'total_engagement_score', 'avg_interaction_intensity', 'active_days',
                'avg_hour_activity', 'recent_engagement', 'total_clicks', 'total_views',
                'avg_product_price_viewed'
            ]
            
            # Handle nulls and convert to numeric
            ml_df = user_features_df.fillna(0)
            for col_name in feature_cols:
                ml_df = ml_df.withColumn(col_name, col(col_name).cast("double"))
            
            # Vector assembly
            assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_raw")
            assembled_df = assembler.transform(ml_df)
            
            # Feature scaling
            scaler = StandardScaler(inputCol="features_raw", outputCol="features", 
                                  withStd=True, withMean=True)
            scaler_model = scaler.fit(assembled_df)
            scaled_df = scaler_model.transform(assembled_df)
            
            # K-Means clustering với multiple K values để tìm optimal
            silhouette_scores = []
            models = []
            
            for k in range(2, 8):
                print(f"🔍 Testing K-Means with k={k}...")
                kmeans = KMeans(k=k, seed=42, maxIter=100)
                model = kmeans.fit(scaled_df)
                predictions = model.transform(scaled_df)
                
                # Evaluate với Silhouette Score
                evaluator = ClusteringEvaluator()
                silhouette = evaluator.evaluate(predictions)
                silhouette_scores.append((k, silhouette))
                models.append((k, model))
                
                print(f"   K={k}, Silhouette Score: {silhouette:.4f}")
            
            # Chọn optimal K
            optimal_k, optimal_score = max(silhouette_scores, key=lambda x: x[1])
            optimal_model = next(model for k, model in models if k == optimal_k)
            
            print(f"✅ Optimal K: {optimal_k} (Silhouette Score: {optimal_score:.4f})")
            
            # Final clustering với optimal K
            final_predictions = optimal_model.transform(scaled_df)
            
            # Analyze clusters
            cluster_analysis = final_predictions.groupBy("prediction").agg(
                count("*").alias("cluster_size"),
                avg("total_interactions").alias("avg_interactions"),
                avg("total_engagement_score").alias("avg_engagement"),
                avg("unique_products_viewed").alias("avg_unique_products"),
                avg("avg_product_price_viewed").alias("avg_price_preference"),
                collect_list("most_viewed_category").alias("top_categories")
            ).orderBy("cluster_size", ascending=False)
            
            print("\n📊 CLUSTER ANALYSIS:")
            cluster_analysis.show(10, False)
            
            # Save results to HDFS
            final_predictions.write \
                .mode("overwrite") \
                .parquet(self.analytics_results_path)
            
            print(f"💾 Saved clustering results to: {self.analytics_results_path}")
            
            return final_predictions, cluster_analysis, optimal_k
            
        except Exception as e:
            print(f"❌ ML clustering error: {e}")
            return None, None, 0
    
    def generate_cluster_insights(self, cluster_analysis_df, optimal_k):
        """
        Generate business insights từ clustering results
        """
        print("💡 GENERATING BUSINESS INSIGHTS")
        print("-" * 60)
        
        try:
            clusters = cluster_analysis_df.collect()
            insights = {}
            
            for i, cluster in enumerate(clusters):
                cluster_id = cluster['prediction']
                cluster_size = cluster['cluster_size']
                avg_interactions = cluster['avg_interactions']
                avg_engagement = cluster['avg_engagement']
                avg_products = cluster['avg_unique_products']
                avg_price = cluster['avg_price_preference']
                
                # Classify cluster behavior
                if avg_engagement > 50 and avg_interactions > 20:
                    cluster_type = "Power Users 💎"
                    strategy = "VIP treatment, premium products, early access"
                elif avg_engagement > 20 and avg_products > 10:
                    cluster_type = "Active Explorers 🔍"  
                    strategy = "Product discovery, recommendations, variety"
                elif avg_price > 100000:
                    cluster_type = "Premium Shoppers 💰"
                    strategy = "Luxury items, quality focus, exclusive offers"
                elif avg_interactions > 10 and avg_engagement < 20:
                    cluster_type = "Casual Browsers 👀"
                    strategy = "Engagement campaigns, easy purchase flow"
                else:
                    cluster_type = "New/Low Activity Users 🌱"
                    strategy = "Onboarding, tutorials, attractive first offers"
                
                insights[f"cluster_{cluster_id}"] = {
                    'type': cluster_type,
                    'size': int(cluster_size),
                    'avg_interactions': round(avg_interactions, 2),
                    'avg_engagement': round(avg_engagement, 2),
                    'avg_products_viewed': round(avg_products, 2),
                    'avg_price_preference': round(avg_price, 2) if avg_price else 0,
                    'marketing_strategy': strategy
                }
            
            # Save insights as JSON
            insights_json = json.dumps(insights, indent=2, ensure_ascii=False)
            
            # Save to local file for dashboard
            insights_path = "../dashboard/cluster_insights.json"
            os.makedirs(os.path.dirname(insights_path), exist_ok=True)
            with open(insights_path, 'w', encoding='utf-8') as f:
                f.write(insights_json)
            
            print("📋 CLUSTER INSIGHTS GENERATED:")
            for cluster_id, info in insights.items():
                print(f"\n🎯 {info['type']} ({info['size']} users)")
                print(f"   📊 Avg Interactions: {info['avg_interactions']}")
                print(f"   🔥 Avg Engagement: {info['avg_engagement']}")  
                print(f"   💡 Strategy: {info['marketing_strategy']}")
            
            return insights
            
        except Exception as e:
            print(f"❌ Insights generation error: {e}")
            return {}
    
    def run_full_analysis(self):
        """
        Chạy complete Big Data analytics pipeline
        """
        print("🎯 STARTING BIG DATA ANALYTICS PIPELINE")
        print("=" * 70)
        
        start_time = datetime.now()
        
        # Step 1: Data Migration to HDFS (Distributed Storage)
        print("\n🗄️ STEP 1: DISTRIBUTED STORAGE SETUP")
        if not self.migrate_data_to_hdfs():
            print("❌ Failed to setup distributed storage")
            return False
        
        # Step 2: Big Data Processing với Spark
        print("\n⚡ STEP 2: BIG DATA PROCESSING") 
        user_features = self.analyze_user_behavior_bigdata()
        if user_features is None:
            print("❌ Failed big data processing")
            return False
        
        # Step 3: Machine Learning Clustering
        print("\n🤖 STEP 3: MACHINE LEARNING ANALYSIS")
        predictions, cluster_analysis, optimal_k = self.perform_ml_clustering(user_features)
        if predictions is None:
            print("❌ Failed ML analysis")
            return False
        
        # Step 4: Business Insights Generation
        print("\n💡 STEP 4: BUSINESS INTELLIGENCE")
        insights = self.generate_cluster_insights(cluster_analysis, optimal_k)
        
        # Step 5: Performance Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n🎉 BIG DATA ANALYTICS COMPLETED!")
        print("=" * 70)
        print(f"⏱️ Total Processing Time: {duration:.2f} seconds")
        print(f"📊 Users Analyzed: {user_features.count():,}")
        print(f"🎯 Optimal Clusters: {optimal_k}")
        print(f"🗄️ Results Saved to HDFS: {self.analytics_results_path}")
        print(f"💾 Insights Available: ../dashboard/cluster_insights.json")
        
        return True
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("🛑 Spark session stopped")

# CLI Execution
if __name__ == "__main__":
    analytics = BigDataUserSegmentation()
    
    try:
        success = analytics.run_full_analysis()
        if success:
            print("\n✅ BIG DATA ANALYTICS PIPELINE COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ BIG DATA ANALYTICS PIPELINE FAILED!")
    except Exception as e:
        print(f"\n💥 PIPELINE ERROR: {e}")
    finally:
        analytics.stop()