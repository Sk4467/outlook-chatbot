"""
Custom PandasAI Agent using LangChain and Gemini 2.0 Flash
A powerful alternative to PandasAI without dependency conflicts
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
import os
import json
from io import StringIO

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage


class CustomPandasAI:
    """
    Custom PandasAI implementation using LangChain and Gemini 2.0 Flash
    """
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.0-flash-exp"):
        """Initialize the custom PandasAI agent"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        self.model = model
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=self.api_key,
            temperature=0.1,
            convert_system_message_to_human=True
        )
        print(f"[CUSTOM PANDASAI] Initialized with {self.model}")
    
    def analyze_dataframe(self, df: pd.DataFrame, question: str, df_name: str = "data") -> Dict[str, Any]:
        """
        Analyze a pandas DataFrame using natural language questions
        """
        try:
            print(f"[CUSTOM PANDASAI] Analyzing {df_name}: {df.shape} with question: {question[:100]}...")
            
            # Create data context
            data_info = self._get_dataframe_info(df, df_name)
            
            # Build the analysis prompt
            system_prompt = f"""You are an expert data analyst. Analyze the provided dataset and answer the user's question.

DATASET INFORMATION:
{data_info}

ANALYSIS GUIDELINES:
1. Provide specific numerical answers when asked for counts, totals, averages, etc.
2. Use actual data from the dataset - don't make up numbers
3. Show relevant examples from the data when helpful
4. If filtering or grouping data, explain your methodology
5. For questions about countries/regions, list the actual names found in the data
6. Format your response clearly with headers and bullet points
7. If you need to perform calculations, show the key results

IMPORTANT: Base your analysis ONLY on the actual data provided. Do not make assumptions about data not shown."""

            human_prompt = f"""Question: {question}

Please analyze the dataset and provide a comprehensive answer based on the actual data."""

            # Get response from Gemini
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "answer": response.content,
                "dataset_info": data_info,
                "analysis_type": "custom_pandasai",
                "model_used": self.model
            }
            
        except Exception as e:
            print(f"[CUSTOM PANDASAI] Error: {e}")
            return {
                "answer": f"Analysis failed: {str(e)}",
                "error": str(e),
                "analysis_type": "custom_pandasai_error"
            }
    
    def analyze_multiple_dataframes(self, dataframes: List[Tuple[str, pd.DataFrame]], question: str) -> Dict[str, Any]:
        """
        Analyze multiple DataFrames and answer a question across all of them
        """
        try:
            print(f"[CUSTOM PANDASAI] Multi-dataframe analysis: {len(dataframes)} datasets")
            
            # Combine information from all dataframes
            all_data_info = []
            combined_stats = {"total_rows": 0, "total_tables": len(dataframes)}
            
            for name, df in dataframes:
                if df.empty:
                    all_data_info.append(f"**{name}**: Empty dataset")
                    continue
                    
                data_info = self._get_dataframe_info(df, name)
                all_data_info.append(data_info)
                combined_stats["total_rows"] += len(df)
            
            if combined_stats["total_rows"] == 0:
                return {
                    "answer": "All datasets are empty - no data available for analysis.",
                    "analysis_type": "no_data"
                }
            
            # Build comprehensive prompt
            system_prompt = f"""You are an expert data analyst working with multiple related datasets. Analyze ALL provided datasets to answer the user's question comprehensively.

DATASETS OVERVIEW:
- Total datasets: {combined_stats['total_tables']}
- Total data rows: {combined_stats['total_rows']}

DETAILED DATASET INFORMATION:
{chr(10).join(all_data_info)}

ANALYSIS GUIDELINES:
1. Consider data from ALL relevant datasets when answering
2. Provide specific numerical answers with dataset sources
3. When counting items (like countries), combine data from all relevant datasets
4. If different datasets have conflicting information, mention this
5. Show examples from multiple datasets when helpful
6. Clearly indicate which dataset(s) your answer comes from
7. Aggregate totals across datasets when appropriate

IMPORTANT: Use actual data from the provided datasets. Cross-reference information between datasets when relevant."""

            human_prompt = f"""Question: {question}

Please provide a comprehensive analysis considering all available datasets."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "answer": response.content,
                "datasets_analyzed": len(dataframes),
                "total_rows": combined_stats["total_rows"],
                "analysis_type": "custom_pandasai_multi",
                "model_used": self.model
            }
            
        except Exception as e:
            print(f"[CUSTOM PANDASAI] Multi-analysis error: {e}")
            return {
                "answer": f"Multi-dataset analysis failed: {str(e)}",
                "error": str(e),
                "analysis_type": "custom_pandasai_multi_error"
            }
    
    def _get_dataframe_info(self, df: pd.DataFrame, name: str) -> str:
        """Generate comprehensive information about a DataFrame"""
        try:
            if df.empty:
                return f"**{name}**: Empty dataset with {len(df.columns)} columns: {list(df.columns)}"
            
            info_parts = [f"**{name}**:"]
            info_parts.append(f"- Shape: {df.shape[0]} rows, {df.shape[1]} columns")
            info_parts.append(f"- Columns: {list(df.columns)}")
            
            # Data types summary
            dtype_summary = df.dtypes.value_counts().to_dict()
            dtype_str = ", ".join([f"{count} {dtype}" for dtype, count in dtype_summary.items()])
            info_parts.append(f"- Data types: {dtype_str}")
            
            # Show unique values for categorical columns (limited)
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols[:3]:  # Limit to first 3 categorical columns
                unique_vals = df[col].unique()
                if len(unique_vals) <= 20:  # Only show if manageable number
                    info_parts.append(f"- {col} values: {list(unique_vals)}")
                else:
                    info_parts.append(f"- {col}: {len(unique_vals)} unique values (e.g., {list(unique_vals[:5])}...)")
            
            # Numeric columns summary
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                info_parts.append("- Numeric columns summary:")
                for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
                    col_stats = df[col].describe()
                    info_parts.append(f"  - {col}: min={col_stats['min']:.1f}, max={col_stats['max']:.1f}, mean={col_stats['mean']:.1f}")
            
            # Sample data (first few rows)
            if len(df) > 0:
                sample_data = df.head(3).to_string(index=False, max_cols=5)
                info_parts.append(f"- Sample data:\n{sample_data}")
            
            return "\n".join(info_parts)
            
        except Exception as e:
            return f"**{name}**: Error generating info - {str(e)}"
    
    def smart_query(self, dataframes: List[Tuple[str, pd.DataFrame]], question: str) -> Dict[str, Any]:
        """
        Smart query that automatically handles single or multiple dataframes
        """
        if not dataframes:
            return {
                "answer": "No data available for analysis.",
                "analysis_type": "no_data"
            }
        
        # Filter out empty dataframes
        valid_dataframes = [(name, df) for name, df in dataframes if not df.empty]
        
        if not valid_dataframes:
            return {
                "answer": "All provided datasets are empty.",
                "analysis_type": "empty_data"
            }
        
        if len(valid_dataframes) == 1:
            name, df = valid_dataframes[0]
            return self.analyze_dataframe(df, question, name)
        else:
            return self.analyze_multiple_dataframes(valid_dataframes, question)


def create_custom_pandasai() -> CustomPandasAI:
    """Factory function to create a CustomPandasAI instance"""
    try:
        return CustomPandasAI()
    except Exception as e:
        print(f"[CUSTOM PANDASAI] Failed to create instance: {e}")
        raise


# Test function
def test_custom_pandasai():
    """Test the custom PandasAI with sample data"""
    try:
        # Create test data
        test_data = {
            'Region': ['Asia', 'Asia', 'Europe', 'Asia', 'Europe', 'Asia'],
            'Country': ['India', 'China', 'Germany', 'Japan', 'France', 'Thailand'],
            'Sales': [1000, 1500, 800, 1200, 900, 600],
            'Population': [1400, 1450, 83, 125, 68, 70]
        }
        df = pd.DataFrame(test_data)
        
        # Test the agent
        agent = create_custom_pandasai()
        result = agent.analyze_dataframe(df, "How many countries are in Asia?", "test_data")
        
        print("Test Result:")
        print(result["answer"])
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    test_custom_pandasai()
