"""
PandasAI Integration for Advanced Data Analysis
Based on the working implementation from emailprocessing_updated.txt
"""

import pandas as pd
import google.generativeai as genai
from typing import List, Tuple, Dict, Any, Optional
import os

# Try to import PandasAI, but make it optional
try:
    from pandasai import PandasAI
    from pandasai.llm.base import LLM
    PANDASAI_AVAILABLE = True
except ImportError:
    print("[PANDASAI] PandasAI not available - using fallback analysis")
    PANDASAI_AVAILABLE = False
    
    # Create dummy classes for type hints
    class LLM:
        pass
    
    class PandasAI:
        pass

class GeminiLLM(LLM):
    """Custom Gemini LLM wrapper for PandasAI"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        super().__init__()
        self.api_key = api_key
        self.model = model
        genai.configure(api_key=api_key)

    def call(self, prompt: str, **kwargs) -> str:
        try:
            response = genai.GenerativeModel(self.model).generate_content(prompt)
            return response.text if response and response.text else ""
        except Exception as e:
            print(f"[GEMINI LLM] Error: {e}")
            return f"Error generating response: {str(e)}"

    @property
    def type(self) -> str:
        return "google-gemini"

# Initialize PandasAI with Gemini
def get_pandasai_instance() -> PandasAI:
    """Get configured PandasAI instance"""
    if not PANDASAI_AVAILABLE:
        raise RuntimeError("PandasAI is not installed. Install with: pip install pandasai[excel]")
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment")
    
    llm = GeminiLLM(api_key=api_key)
    return PandasAI(llm, conversational=False)

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
    Perform advanced analysis using PandasAI
    Args:
        question: User question
        tables: List of (table_name, dataframe) tuples
    Returns:
        Analysis result dictionary
    """
    print(f"[PANDASAI] Starting analysis for: {question[:100]}...")
    
    if not tables:
        return {
            "answer": "No tabular data available for PandasAI analysis.",
            "tables_used": [],
            "analysis_type": "no_data",
            "error": "No tables provided"
        }
    
    # Check if PandasAI is available
    if not PANDASAI_AVAILABLE:
        return {
            "answer": "PandasAI is not available. Install it with: pip install pandasai[excel]. Using fallback analysis instead.",
            "tables_used": [name for name, _ in tables],
            "analysis_type": "pandasai_unavailable",
            "error": "PandasAI not installed",
            "fallback_suggestion": "Install PandasAI for advanced analysis capabilities"
        }
    
    try:
        pandas_ai = get_pandasai_instance()
        results = []
        tables_used = []
        
        # Analyze each table
        for table_name, df in tables:
            if df.empty:
                print(f"[PANDASAI] Skipping empty table: {table_name}")
                continue
                
            try:
                print(f"[PANDASAI] Analyzing table: {table_name} ({df.shape[0]} rows, {df.shape[1]} cols)")
                
                # Clean the dataframe for better analysis
                df_clean = df.copy()
                
                # Remove completely null columns
                df_clean = df_clean.dropna(axis=1, how='all')
                
                # Remove rows that are completely null
                df_clean = df_clean.dropna(how='all')
                
                if df_clean.empty:
                    print(f"[PANDASAI] Table {table_name} is empty after cleaning")
                    continue
                
                # Enhance question with table context
                enhanced_question = f"""
                Analyze the data in table '{table_name}' to answer: {question}
                
                Table info:
                - Shape: {df_clean.shape[0]} rows, {df_clean.shape[1]} columns
                - Columns: {', '.join(df_clean.columns)}
                
                Please provide a clear, concise answer with specific numbers and insights.
                """
                
                # Run PandasAI analysis
                answer = pandas_ai.run(df_clean, enhanced_question)
                
                if answer and str(answer).strip():
                    results.append(f"**{table_name}:**\n{answer}")
                    tables_used.append(table_name)
                    print(f"[PANDASAI] Success for {table_name}")
                else:
                    print(f"[PANDASAI] Empty response for {table_name}")
                    
            except Exception as e:
                error_msg = str(e)
                print(f"[PANDASAI] Error analyzing {table_name}: {error_msg}")
                results.append(f"**{table_name}:** Analysis error - {error_msg}")
        
        if not results:
            return {
                "answer": "PandasAI could not analyze the available data. The tables might be empty or incompatible.",
                "tables_used": [],
                "analysis_type": "analysis_failed",
                "error": "No successful analysis results"
            }
        
        # Combine results
        final_answer = "\n\n".join(results)
        
        # Add summary if multiple tables
        if len(results) > 1:
            final_answer = f"**Analysis Results:**\n\n{final_answer}"
        
        return {
            "answer": final_answer,
            "tables_used": tables_used,
            "analysis_type": "pandasai_success",
            "tables_analyzed": len(tables_used)
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[PANDASAI] Critical error: {error_msg}")
        return {
            "answer": f"PandasAI analysis failed: {error_msg}",
            "tables_used": [],
            "analysis_type": "critical_error",
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
