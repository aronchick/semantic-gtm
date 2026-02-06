"""Configuration settings for GTM Semantic Crawler"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "db" / "gtm_semantic.db"

# API Configuration
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Model selection - use cheap models for volume
ANALYSIS_MODEL = "claude-3-haiku-20240307"  # or "gpt-4o-mini"
ANALYSIS_PROVIDER = "anthropic"  # or "openai"

# Telegram for digests
TELEGRAM_USER_ID = "775397536"

# Crawler settings
HN_API_BASE = "https://hn.algolia.com/api/v1"
REDDIT_USER_AGENT = "GTM-Semantic-Crawler/1.0 (by /u/expanso_research)"

# Subreddits to monitor
REDDIT_SUBREDDITS = [
    "dataengineering",
    "MachineLearning", 
    "mlops",
    "devops",
    "kubernetes",
    "selfhosted",
    "homelab",
    "aws",
    "googlecloud",
    "azure",
    "IOT",
    "embedded",
    "learnmachinelearning",
    "datascience",
    "bigdata",
]

# HN search terms (semantic, not just keywords)
HN_SEARCH_TERMS = [
    "distributed computing",
    "edge computing",
    "data pipeline",
    "batch processing",
    "ML inference",
    "machine learning deployment",
    "processing data at scale",
    "airflow alternative",
    "spark slow",
    "data processing latency",
    "IoT data",
    "running ML models",
    "GPU cluster",
    "compute at edge",
    "process terabytes",
]

# Problem categories (initial taxonomy)
PROBLEM_CATEGORIES = {
    "ml_inference": "ML model deployment and inference at scale or edge",
    "data_pipelines": "ETL, data processing workflows, batch jobs",
    "iot_edge": "IoT data processing, edge device compute",
    "batch_processing": "Large-scale batch job execution",
    "distributed_compute": "General distributed computing needs",
    "cost_optimization": "Reducing cloud/compute costs",
    "latency_sensitive": "Low-latency processing requirements",
    "data_locality": "Processing data where it lives",
    "hybrid_cloud": "Multi-cloud or hybrid infrastructure",
    "workflow_orchestration": "Job scheduling and orchestration pain",
}

# Expanso/Bacalhau context for AI analysis
EXPANSO_CONTEXT = """
Expanso (Bacalhau) is a distributed compute platform that:
- Runs compute jobs where data lives (edge, on-prem, multi-cloud)
- Orchestrates containerized workloads across heterogeneous infrastructure
- Enables ML inference at edge without moving data to cloud
- Processes data locally to reduce latency and egress costs
- Works with any container/WASM workload
- Competes with: Airflow, Prefect, Dagster (workflow), Spark, Dask (distributed)
- Key differentiators: Data locality, edge-native, simple deployment

Ideal customer signals:
- Struggling with data egress costs
- Need to process data at edge/on-prem
- ML inference latency issues
- Batch processing across distributed locations
- IoT data processing challenges
- Frustrated with complexity of Spark/Airflow
"""
