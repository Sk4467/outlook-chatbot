"""
Custom PandasAI Integration for Advanced Data Analysis
Using our own implementation with LangChain and Gemini 2.0 Flash
"""

import pandas as pd
import google.generativeai as genai
from typing import List, Tuple, Dict, Any, Optional
import os

# Import our custom PandasAI implementation
try:
    from .custom_pandasai import CustomPandasAI, create_custom_pandasai
    CUSTOM_PANDASAI_AVAILABLE = True
    print("[CUSTOM PANDASAI] Custom PandasAI agent available")
except ImportError as e:
    print(f"[CUSTOM PANDASAI] Custom PandasAI not available: {e}")
    CUSTOM_PANDASAI_AVAILABLE = False

# Legacy functions removed - now using CustomPandasAI

def is_analysis_question(question: str) -> bool:
    """
    Detect if question requires advanced analysis using PandasAI
    Based on keywords from the working implementation
    """
    analysis_keywords = [
        # Direct analysis terms
        "analyze", "analysis", "insights", "trends", "patterns",
        "compare", "comparison", "correlate", "correlation",
        "average", "mean", "median", "sum", "total", "count",
        "maximum", "minimum", "highest", "lowest",
        "group by", "breakdown", "distribution",
        
        # Business analysis terms
        "sales", "revenue", "profit", "performance", "growth",
        "customer", "product", "region", "territory",
        "top", "bottom", "best", "worst", "ranking",
        
        # Question words that often need analysis
        "how many", "what is the", "which", "who has the",
        "show me", "list", "find", "calculate",
        
        # Statistical terms
        "percentage", "ratio", "rate", "proportion",
        "increase", "decrease", "change", "difference"
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in analysis_keywords)

def analyze_with_pandasai(
    question: str, 
    tables: List[Tuple[str, pd.DataFrame]]
) -> Dict[str, Any]:
    """
    Perform advanced analysis using our Custom PandasAI
    Args:
        question: User question
        tables: List of (table_name, dataframe) tuples
    Returns:
        Analysis result dictionary
    """
    print(f"[CUSTOM PANDASAI] Starting analysis for: {question[:100]}...")
    
    if not tables:
        return {
            "answer": "No tabular data available for analysis.",
            "tables_used": [],
            "analysis_type": "no_data",
            "error": "No tables provided"
        }
    
    # Check if Custom PandasAI is available
    if not CUSTOM_PANDASAI_AVAILABLE:
        return {
            "answer": "Custom PandasAI is not available. There may be a configuration issue.",
            "tables_used": [name for name, _ in tables],
            "analysis_type": "custom_pandasai_unavailable",
            "error": "Custom PandasAI not available"
        }
    
    try:
        # Create our custom PandasAI agent
        agent = create_custom_pandasai()
        
        # Use smart query to handle single or multiple dataframes automatically
        result = agent.smart_query(tables, question)
        
        # Add table information to the result
        tables_used = [name for name, df in tables if not df.empty]
        result["tables_used"] = tables_used
        
        print(f"[CUSTOM PANDASAI] Analysis completed successfully")
        return result
        
    except Exception as e:
        error_msg = str(e)
        print(f"[CUSTOM PANDASAI] Critical error: {error_msg}")
        return {
            "answer": f"Custom PandasAI analysis failed: {error_msg}",
            "tables_used": [name for name, _ in tables],
            "analysis_type": "custom_pandasai_error",
            "error": error_msg
        }

def get_structured_data_summary(tables: List[Tuple[str, pd.DataFrame]]) -> str:
    """Generate a structured summary of available data"""
    if not tables:
        return "No structured data available."
    
    summary_parts = []
    for table_name, df in tables:
        if df.empty:
            summary_parts.append(f"- **{table_name}**: Empty table")
            continue
            
        # Basic info
        shape_info = f"{df.shape[0]} rows, {df.shape[1]} columns"
        
        # Column info
        columns = df.columns.tolist()
        col_info = f"Columns: {', '.join(columns[:5])}"
        if len(columns) > 5:
            col_info += f" (and {len(columns) - 5} more)"
        
        # Data types summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        text_cols = df.select_dtypes(include=['object']).columns
        
        type_info = []
        if len(numeric_cols) > 0:
            type_info.append(f"{len(numeric_cols)} numeric")
        if len(text_cols) > 0:
            type_info.append(f"{len(text_cols)} text")
        
        type_summary = f"({', '.join(type_info)} columns)" if type_info else ""
        
        summary_parts.append(f"- **{table_name}**: {shape_info} {type_summary}\n  {col_info}")
    
    return "**Available Data:**\n" + "\n".join(summary_parts)
