#!/usr/bin/env python3
"""
Big Data Collaborative Filtering với Spark MLlib ALS (Alternating Least Squares)
Advanced Machine Learning cho recommendation system
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import StringIndexer
import numpy as np
import json
import os
from datetime import datetime

class BigDataCollaborativeFiltering:
    def __init__(self):
        """Initialize Spark session cho Collaborative Filtering"""
        self.spark = SparkSession.builder \
            .appName("BigDataCollaborativeFiltering") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
            .getOrCreate()
        
        self.spark.sparkContext.setLogLevel("WARN")
        
        # HDFS paths
        self.hdfs_base_path = "hdfs://localhost:9000"
        self.user_interactions_path = f"{self.hdfs_base_path}/ecommerce/user_interactions"
        self.model_path = f"{self.hdfs_base_path}/ml_models/als_model"
        self.recommendations_path = f"{self.hdfs_base_path}/recommendations/collaborative_filtering"
        
        print("🤖 Big Data Collaborative Filtering Engine initialized")
    
    def prepare_ratings_data(self):
        """
        Chuẩn bị dữ liệu ratings từ user interactions cho ALS model
        """
        print("📊 PREPARING RATINGS DATA FOR COLLABORATIVE FILTERING")
        print("-" * 60)
        
        try:
            # Load interactions từ HDFS
            interactions_df = self.spark.read.parquet(self.user_interactions_path)
            
            # Create implicit ratings từ user behavior
            ratings_df = interactions_df.select("user_id", "product_id", "interaction_score", "timestamp_dt") \
                .filter(col("user_id").isNotNull() & col("product_id").isNotNull()) \
                .groupBy("user_id", "product_id") \
                .agg(
                    sum("interaction_score").alias("total_score"),
                    count("*").alias("interaction_count"),
                    max("timestamp_dt").alias("last_interaction")
                )
            
            # Normalize ratings to 1-5 scale
            # Formula: rating = min(5, log(total_score + 1) + interaction_count/10)
            ratings_df = ratings_df.withColumn(
                "rating", 
                least(lit(5.0), 
                      log(col("total_score") + 1) + col("interaction_count") / 10)
            ).filter(col("rating") >= 1.0)
            
            # String indexing cho user_id và product_id (ALS requires integers)
            user_indexer = StringIndexer(inputCol="user_id", outputCol="user_index")
            product_indexer = StringIndexer(inputCol="product_id", outputCol="product_index")
            
            user_model = user_indexer.fit(ratings_df)
            ratings_with_user_index = user_model.transform(ratings_df)
            
            product_model = product_indexer.fit(ratings_with_user_index)
            final_ratings = product_model.transform(ratings_with_user_index)
            
            print(f"✅ Prepared {final_ratings.count():,} ratings for ALS model")
            print(f"👥 Unique users: {final_ratings.select('user_index').distinct().count():,}")
            print(f"🛍️ Unique products: {final_ratings.select('product_index').distinct().count():,}")
            
            return final_ratings, user_model, product_model
            
        except Exception as e:
            print(f"❌ Data preparation error: {e}")
            return None, None, None
    
    def train_als_model(self, ratings_df):
        """
        Train ALS (Alternating Least Squares) model với hyperparameter tuning
        """
        print("🎓 TRAINING ALS COLLABORATIVE FILTERING MODEL")
        print("-" * 60)
        
        try:
            # Split data for training/testing
            train_df, test_df = ratings_df.randomSplit([0.8, 0.2], seed=42)
            
            print(f"📚 Training data: {train_df.count():,} ratings")
            print(f"🧪 Test data: {test_df.count():,} ratings")
            
            # Hyperparameter tuning
            best_rmse = float('inf')
            best_model = None
            best_params = {}
            
            param_grid = [
                {'rank': 10, 'maxIter': 10, 'regParam': 0.1},
                {'rank': 50, 'maxIter': 10, 'regParam': 0.01},
                {'rank': 100, 'maxIter': 15, 'regParam': 0.05},
                {'rank': 150, 'maxIter': 20, 'regParam': 0.1}
            ]
            
            evaluator = RegressionEvaluator(
                metricName="rmse", 
                labelCol="rating",
                predictionCol="prediction"
            )
            
            for i, params in enumerate(param_grid, 1):
                print(f"🔍 Testing hyperparameters {i}/{len(param_grid)}: {params}")
                
                # Configure ALS
                als = ALS(
                    maxIter=params['maxIter'],
                    regParam=params['regParam'],
                    rank=params['rank'],
                    userCol="user_index",
                    itemCol="product_index", 
                    ratingCol="rating",
                    coldStartStrategy="drop",  # Handle new users/products
                    implicitPrefs=False,  # Explicit ratings
                    seed=42
                )
                
                # Train model
                model = als.fit(train_df)
                
                # Evaluate on test set
                predictions = model.transform(test_df)
                rmse = evaluator.evaluate(predictions.filter(col("prediction").isNotNull()))
                
                print(f"   RMSE: {rmse:.4f}")
                
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_model = model
                    best_params = params
                    print(f"   ⭐ New best model!")
            
            print(f"\n✅ BEST MODEL TRAINED:")
            print(f"   📊 RMSE: {best_rmse:.4f}")
            print(f"   ⚙️ Params: {best_params}")
            
            # Save model to HDFS
            best_model.write().overwrite().save(self.model_path)
            print(f"💾 Model saved to: {self.model_path}")
            
            return best_model, best_rmse
            
        except Exception as e:
            print(f"❌ Model training error: {e}")
            return None, 0
    
    def generate_recommendations_for_all_users(self, model, user_model, product_model, num_recommendations=10):
        """
        Generate recommendations cho tất cả users sử dụng trained ALS model
        """
        print("🎯 GENERATING COLLABORATIVE FILTERING RECOMMENDATIONS")
        print("-" * 60)
        
        try:
            # Generate recommendations cho tất cả users
            all_recommendations = model.recommendForAllUsers(num_recommendations)
            
            # Convert back from indices to original IDs
            user_mapping = user_model.labels
            product_mapping = product_model.labels
            
            # Create broadcast variables cho efficient lookup
            user_broadcast = self.spark.sparkContext.broadcast(
                {i: user_id for i, user_id in enumerate(user_mapping)}
            )
            product_broadcast = self.spark.sparkContext.broadcast(
                {i: product_id for i, product_id in enumerate(product_mapping)}
            )
            
            # UDF để convert indices back to IDs
            def convert_recommendations(user_index, recommendations):
                user_id = user_broadcast.value.get(int(user_index))
                converted_recs = []
                
                for rec in recommendations:
                    product_id = product_broadcast.value.get(int(rec['product_index']))
                    if product_id:
                        converted_recs.append({
                            'product_id': int(product_id),
                            'predicted_rating': float(rec['rating']),
                            'rank': len(converted_recs) + 1
                        })
                
                return {
                    'user_id': int(user_id) if user_id else None,
                    'recommendations': converted_recs,
                    'algorithm': 'collaborative_filtering_als',
                    'generated_at': datetime.now().isoformat()
                }
            
            convert_udf = udf(convert_recommendations, 
                            StructType([
                                StructField("user_id", IntegerType(), True),
                                StructField("recommendations", ArrayType(
                                    StructType([
                                        StructField("product_id", IntegerType(), True),
                                        StructField("predicted_rating", FloatType(), True),
                                        StructField("rank", IntegerType(), True)
                                    ])
                                ), True),
                                StructField("algorithm", StringType(), True),
                                StructField("generated_at", StringType(), True)
                            ]))
            
            # Apply conversion
            final_recommendations = all_recommendations.withColumn(
                "recommendations_data",
                convert_udf(col("user_index"), col("recommendations"))
            ).select("recommendations_data.*").filter(col("user_id").isNotNull())
            
            # Save to HDFS
            final_recommendations.write \
                .mode("overwrite") \
                .json(self.recommendations_path)
            
            rec_count = final_recommendations.count()
            print(f"✅ Generated recommendations for {rec_count:,} users")
            print(f"💾 Saved to: {self.recommendations_path}")
            
            # Sample results
            print("\n🎯 SAMPLE RECOMMENDATIONS:")
            sample_recs = final_recommendations.limit(3).collect()
            for rec in sample_recs:
                user_id = rec['user_id']
                products = rec['recommendations'][:3]  # Top 3
                print(f"\n👤 User {user_id}:")
                for i, product in enumerate(products, 1):
                    print(f"   {i}. Product {product['product_id']} (Rating: {product['predicted_rating']:.2f})")
            
            return final_recommendations
            
        except Exception as e:
            print(f"❌ Recommendations generation error: {e}")
            return None
    
    def evaluate_model_performance(self, model, test_data):
        """
        Đánh giá performance của ALS model
        """
        print("📈 EVALUATING MODEL PERFORMANCE")
        print("-" * 60)
        
        try:
            # Make predictions on test data
            predictions = model.transform(test_data)
            
            # Calculate metrics
            evaluator_rmse = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
            evaluator_mae = RegressionEvaluator(metricName="mae", labelCol="rating", predictionCol="prediction")
            
            valid_predictions = predictions.filter(col("prediction").isNotNull())
            
            rmse = evaluator_rmse.evaluate(valid_predictions)
            mae = evaluator_mae.evaluate(valid_predictions)
            
            # Coverage metrics
            total_users = test_data.select("user_index").distinct().count()
            users_with_predictions = valid_predictions.select("user_index").distinct().count()
            user_coverage = (users_with_predictions / total_users) * 100
            
            total_items = test_data.select("product_index").distinct().count()
            items_with_predictions = valid_predictions.select("product_index").distinct().count()
            item_coverage = (items_with_predictions / total_items) * 100
            
            # Performance summary
            performance = {
                'rmse': round(rmse, 4),
                'mae': round(mae, 4),
                'user_coverage_percent': round(user_coverage, 2),
                'item_coverage_percent': round(item_coverage, 2),
                'total_predictions': int(valid_predictions.count()),
                'model_type': 'ALS_Collaborative_Filtering'
            }
            
            print("📊 MODEL PERFORMANCE METRICS:")
            print(f"   🎯 RMSE: {performance['rmse']}")
            print(f"   📐 MAE: {performance['mae']}")
            print(f"   👥 User Coverage: {performance['user_coverage_percent']}%")
            print(f"   🛍️ Item Coverage: {performance['item_coverage_percent']}%")
            
            # Save performance metrics
            performance_path = "../dashboard/cf_performance.json"
            os.makedirs(os.path.dirname(performance_path), exist_ok=True)
            with open(performance_path, 'w') as f:
                json.dump(performance, f, indent=2)
            
            return performance
            
        except Exception as e:
            print(f"❌ Model evaluation error: {e}")
            return {}
    
    def run_collaborative_filtering_pipeline(self):
        """
        Chạy complete Collaborative Filtering pipeline
        """
        print("🤖 STARTING COLLABORATIVE FILTERING PIPELINE")
        print("=" * 70)
        
        start_time = datetime.now()
        
        # Step 1: Prepare ratings data
        ratings_df, user_model, product_model = self.prepare_ratings_data()
        if ratings_df is None:
            return False
        
        # Step 2: Train ALS model
        train_data, test_data = ratings_df.randomSplit([0.8, 0.2], seed=42)
        als_model, rmse = self.train_als_model(train_data)
        if als_model is None:
            return False
        
        # Step 3: Evaluate model
        performance = self.evaluate_model_performance(als_model, test_data)
        
        # Step 4: Generate recommendations
        recommendations = self.generate_recommendations_for_all_users(
            als_model, user_model, product_model
        )
        if recommendations is None:
            return False
        
        # Performance summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n🎉 COLLABORATIVE FILTERING PIPELINE COMPLETED!")
        print("=" * 70)
        print(f"⏱️ Total Processing Time: {duration:.2f} seconds")
        print(f"🎯 Model RMSE: {rmse:.4f}")
        print(f"🤖 Recommendations Generated: {recommendations.count():,} users")
        print(f"💾 Model Saved: {self.model_path}")
        print(f"📊 Recommendations Saved: {self.recommendations_path}")
        
        return True
    
    def stop(self):
        """Stop Spark session"""
        self.spark.stop()
        print("🛑 Collaborative Filtering Spark session stopped")

if __name__ == "__main__":
    cf_engine = BigDataCollaborativeFiltering()
    
    try:
        success = cf_engine.run_collaborative_filtering_pipeline()
        if success:
            print("\n✅ COLLABORATIVE FILTERING COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ COLLABORATIVE FILTERING FAILED!")
    except Exception as e:
        print(f"\n💥 PIPELINE ERROR: {e}")
    finally:
        cf_engine.stop()