# backend/rag/tabular_agent.py
from typing import List, Dict, Any, Tuple
import io
import httpx
import pandas as pd
import asyncio
import os

def _load_blob_bytes(url: str, filename: str = "") -> bytes:
    """Load blob data with cache support and proper timeout handling"""
    try:
        # Check cache first
        from .data_cache import get_cached_blob_data
        cached_data = get_cached_blob_data(url, filename)
        if cached_data:
            print(f"[BLOB] Using cached data for {filename} ({len(cached_data)} bytes)")
            return cached_data
        
        print(f"[BLOB] Downloading: {url[:80]}...")
        
        # Skip HEAD request - directly download with extended timeout
        timeout = httpx.Timeout(30.0, connect=10.0, read=30.0)
        
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url)
            r.raise_for_status()
            
            content_length = len(r.content)
            size_mb = content_length / (1024 * 1024)
            print(f"[BLOB] Downloaded {content_length} bytes ({size_mb:.1f}MB)")
            
            # Cache the downloaded data
            from .data_cache import cache_blob_data
            cache_blob_data(url, filename, r.content)
            
            # Check size after download
            if size_mb > 50:
                print(f"[BLOB] Warning: Large file {size_mb:.1f}MB")
            
            return r.content
                
    except httpx.ReadTimeout:
        print(f"[BLOB] Timeout: {url[:50]}...")
        raise Exception("Download timeout - try a smaller file or check connection")
    except httpx.ConnectTimeout:
        print(f"[BLOB] Connection timeout: {url[:50]}...")
        raise Exception("Cannot connect to server")
    except httpx.RequestError as e:
        print(f"[BLOB] Network error: {e}")
        raise Exception(f"Network error: {str(e)}")
    except Exception as e:
        print(f"[BLOB] Failed: {e}")
        raise Exception(f"Download failed: {str(e)}")

def load_dataframes(table_specs: List[Dict[str, Any]]) -> List[Tuple[str, pd.DataFrame]]:
    """Load dataframes from table specifications"""
    print(f"[TABLES] Loading {len(table_specs)} specs")
    out: List[Tuple[str, pd.DataFrame]] = []
    
    for i, spec in enumerate(table_specs):
        uri = spec.get("blob_uri")
        fname = (spec.get("filename") or "").lower()
        sheet = spec.get("sheet")
        label = spec.get("filename") or f"table_{i}"
        
        print(f"[TABLES] {i+1}/{len(table_specs)}: {label}")
        
        if not uri:
            print(f"[TABLES] No URI for {label}")
            continue
            
        try:
            data = _load_blob_bytes(uri, label)
            print(f"[TABLES] Processing {len(data)} bytes")
            
            if fname.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(data))
                print(f"[TABLES] CSV: {df.shape}")
                out.append((label, df))
                
            elif fname.endswith((".xlsx", ".xlsm")):
                if sheet:
                    df = pd.read_excel(io.BytesIO(data), sheet_name=sheet, engine="openpyxl")
                    out.append((f"{label}:{sheet}", df))
                else:
                    df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
                    out.append((label, df))
                print(f"[TABLES] Excel: {df.shape}")
                
            else:
                print(f"[TABLES] Unsupported: {fname}")
                continue
                
        except Exception as e:
            print(f"[TABLES] Error {label}: {str(e)[:100]}")
            print(f"[TABLES] URI causing error: {uri[:120]}...")
            # Don't add error tables - skip failed downloads
            continue
    
    print(f"[TABLES] Loaded {len(out)} tables")
    return out

def answer_with_pandasai(question: str, tables: List[Tuple[str, pd.DataFrame]]) -> Dict[str, Any]:
    """
    Enhanced tabular analysis with intelligent fallbacks
    """
    print(f"[PANDAS] Starting analysis with {len(tables)} tables")
    
    # If no tables loaded due to download issues, provide helpful message
    if not tables:
        print(f"[PANDAS] No tables available - likely due to download timeouts")
        return {
            "answer": "Unable to analyze tabular data due to download timeouts. The attachment files may be large or the server may be slow. Please try with smaller files or check your connection.",
            "tables_used": [],
            "previews": [],
            "analysis_type": "no_data_timeout"
        }
    
    try:
        # Try to use enhanced agent for intelligent analysis
        from .enhanced_agent import analyze_tables_with_agent
        
        # Run async function in sync context
        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass
        
        if loop is not None:
            # We're in an async context, create a new event loop in a thread
            import concurrent.futures
            import threading
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(analyze_tables_with_agent(question, tables))
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                result = future.result(timeout=60)  # 60 second timeout
                return result
        else:
            # No running loop, we can use asyncio.run
            result = asyncio.run(analyze_tables_with_agent(question, tables))
            return result
            
    except ImportError:
        # Enhanced agent not available, fall back to basic analysis
        print(f"[PANDAS] Enhanced agent not available, using basic analysis")
        pass
    except Exception as e:
        # Enhanced agent failed, log error and fall back
        print(f"[PANDAS] Enhanced analysis failed: {e}")
    
    # Fallback: Basic analysis without AI agent
    try:
        print(f"[PANDAS] Using basic tabular analysis")
        return _basic_tabular_analysis(question, tables)
    except Exception as e:
        print(f"[PANDAS] Basic analysis failed: {e}")
        # Ultimate fallback: just show previews
        previews = [f"{label} head:\n{df.head(5).to_string(index=False)}" for label, df in tables]
        return {
            "answer": f"Tabular analysis failed: {str(e)}. Showing data previews instead.",
            "tables_used": [label for label, _ in tables],
            "previews": previews,
            "analysis_type": "fallback_preview"
        }

def _basic_tabular_analysis(question: str, tables: List[Tuple[str, pd.DataFrame]]) -> Dict[str, Any]:
    """Enhanced tabular analysis with intelligent data operations"""
    print(f"[ANALYSIS] Enhanced basic analysis for: {question[:50]}...")
    
    if not tables:
        return {
            "answer": "No data tables available for analysis.",
            "tables_used": [],
            "previews": [],
            "analysis_type": "no_data"
        }
    
    q_lower = question.lower()
    answers = []
    previews = []
    
    for label, df in tables:
        print(f"[ANALYSIS] Processing {label}: {df.shape}")
        
        answer_parts = []
        preview = f"{label} (Shape: {df.shape}):\n{df.head(5).to_string(index=False)}"
        previews.append(preview)
        
        try:
            # Smart column detection
            region_cols = [col for col in df.columns if any(word in col.lower() for word in ['region', 'continent', 'area', 'zone'])]
            country_cols = [col for col in df.columns if any(word in col.lower() for word in ['country', 'nation', 'state'])]
            sales_cols = [col for col in df.columns if any(word in col.lower() for word in ['sales', 'revenue', 'amount', 'value'])]
            
            print(f"[ANALYSIS] Found columns - Region: {region_cols}, Country: {country_cols}, Sales: {sales_cols}")
            
            # Skip empty dataframes
            if df.shape[0] == 0:
                answer_parts.append(f"📊 **Data Status:** Empty sheet with {df.shape[1]} columns defined but no data rows.")
                answer_parts.append(f"📋 **Columns Available:** {', '.join(df.columns)}")
                continue
            
            # Dynamic analysis based on question and data content
            analysis_performed = False
            
            # Asia-specific analysis
            if any(word in q_lower for word in ['asia', 'asian']) and any(word in q_lower for word in ['countries', 'country', 'count', 'number', 'how many']):
                asia_analysis = _analyze_asia_countries(df, region_cols, country_cols)
                if asia_analysis:
                    answer_parts.append(asia_analysis)
                    analysis_performed = True
            
            # Regional analysis for broader region questions
            if any(word in q_lower for word in ['region', 'regional']) and region_cols and not analysis_performed:
                regional_analysis = _analyze_regions(df, region_cols, country_cols, sales_cols)
                if regional_analysis:
                    answer_parts.append(regional_analysis)
                    analysis_performed = True
            
            # Country counting questions
            if any(word in q_lower for word in ['count', 'number', 'how many']) and country_cols and not analysis_performed:
                count_analysis = _count_analysis(df, country_cols, region_cols, q_lower)
                if count_analysis:
                    answer_parts.append(count_analysis)
                    analysis_performed = True
            
            # Sales and financial analysis
            if any(word in q_lower for word in ['sales', 'revenue', 'profit', 'cost', 'total', 'sum', 'average']) and sales_cols:
                sales_analysis = _sales_analysis(df, sales_cols, region_cols, country_cols, q_lower)
                if sales_analysis:
                    answer_parts.append(sales_analysis)
                    analysis_performed = True
            
            # Item/Product analysis
            item_cols = [col for col in df.columns if any(word in col.lower() for word in ['item', 'product', 'type'])]
            if any(word in q_lower for word in ['item', 'product', 'type']) and item_cols:
                item_analysis = _analyze_items(df, item_cols, sales_cols, region_cols)
                if item_analysis:
                    answer_parts.append(item_analysis)
                    analysis_performed = True
            
            # General analysis if no specific pattern matched
            if not analysis_performed:
                general_analysis = _general_analysis(df, q_lower)
                answer_parts.append(general_analysis)
                
        except Exception as e:
            print(f"[ANALYSIS] Error analyzing {label}: {e}")
            answer_parts.append(f"Analysis error: {str(e)}")
        
        answers.append(f"**{label}:**\n{chr(10).join(answer_parts)}")
    
    final_answer = "\n\n".join(answers)
    print(f"[ANALYSIS] Generated answer: {len(final_answer)} characters")
    
    return {
        "answer": final_answer,
        "tables_used": [label for label, _ in tables],
        "previews": previews,
        "analysis_type": "enhanced_basic"
    }

def _analyze_asia_countries(df: pd.DataFrame, region_cols: List[str], country_cols: List[str]) -> str:
    """Analyze countries in Asia region"""
    try:
        if not region_cols or not country_cols:
            return ""
        
        region_col = region_cols[0]
        country_col = country_cols[0]
        
        # Filter for Asia/Asian countries
        asia_mask = df[region_col].str.contains('Asia|Asian', case=False, na=False)
        asia_countries = df[asia_mask][country_col].nunique() if asia_mask.any() else 0
        
        if asia_countries > 0:
            country_list = df[asia_mask][country_col].unique()
            result = f"**Asia Region Analysis:**\n"
            result += f"- Number of countries in Asia: **{asia_countries}**\n"
            result += f"- Countries: {', '.join(country_list[:10])}"
            if len(country_list) > 10:
                result += f" (and {len(country_list) - 10} more)"
            return result
        
        return f"No countries found with 'Asia' in the {region_col} column."
        
    except Exception as e:
        return f"Error analyzing Asia countries: {str(e)}"

def _analyze_regions(df: pd.DataFrame, region_cols: List[str], country_cols: List[str], sales_cols: List[str]) -> str:
    """Analyze data by regions"""
    try:
        if not region_cols:
            return ""
        
        region_col = region_cols[0]
        result = f"**Regional Analysis:**\n"
        
        region_counts = df[region_col].value_counts()
        result += f"- Regions found: {', '.join(region_counts.index[:5])}\n"
        
        if country_cols:
            country_col = country_cols[0]
            countries_by_region = df.groupby(region_col)[country_col].nunique()
            result += f"- Countries per region: {dict(countries_by_region)}\n"
        
        if sales_cols:
            sales_col = sales_cols[0]
            sales_by_region = df.groupby(region_col)[sales_col].sum()
            result += f"- Sales by region: {dict(sales_by_region)}"
        
        return result
        
    except Exception as e:
        return f"Error in regional analysis: {str(e)}"

def _count_analysis(df: pd.DataFrame, country_cols: List[str], region_cols: List[str], question: str) -> str:
    """Perform counting analysis"""
    try:
        result = f"**Count Analysis:**\n"
        
        if country_cols:
            country_col = country_cols[0]
            total_countries = df[country_col].nunique()
            result += f"- Total unique countries: **{total_countries}**\n"
            
            if region_cols and 'asia' in question:
                region_col = region_cols[0]
                asia_mask = df[region_col].str.contains('Asia|Asian', case=False, na=False)
                asia_countries = df[asia_mask][country_col].nunique() if asia_mask.any() else 0
                result += f"- Countries in Asia: **{asia_countries}**"
        
        return result
        
    except Exception as e:
        return f"Error in count analysis: {str(e)}"

def _sales_analysis(df: pd.DataFrame, sales_cols: List[str], region_cols: List[str], country_cols: List[str], question: str) -> str:
    """Perform dynamic sales analysis based on question"""
    try:
        # Find the most relevant sales column
        primary_sales_col = sales_cols[0] if sales_cols else None
        
        # Look for revenue, profit, cost columns specifically
        revenue_cols = [col for col in df.columns if any(word in col.lower() for word in ['revenue', 'sales'])]
        profit_cols = [col for col in df.columns if any(word in col.lower() for word in ['profit'])]
        cost_cols = [col for col in df.columns if any(word in col.lower() for word in ['cost'])]
        
        result = f"**Financial Analysis:**\n"
        
        # Analyze based on what's asked and what's available
        if 'revenue' in question.lower() and revenue_cols:
            col = revenue_cols[0]
            total = df[col].sum()
            avg = df[col].mean()
            result += f"- Total Revenue: {total:,.2f}\n"
            result += f"- Average Revenue: {avg:,.2f}\n"
            
        elif 'profit' in question.lower() and profit_cols:
            col = profit_cols[0]
            total = df[col].sum()
            avg = df[col].mean()
            result += f"- Total Profit: {total:,.2f}\n"
            result += f"- Average Profit: {avg:,.2f}\n"
            
        elif primary_sales_col:
            total = df[primary_sales_col].sum()
            avg = df[primary_sales_col].mean()
            result += f"- Total {primary_sales_col}: {total:,.2f}\n"
            result += f"- Average {primary_sales_col}: {avg:,.2f}\n"
        
        # Regional breakdown if relevant
        if region_cols and any(word in question.lower() for word in ['region', 'by region', 'regional']):
            region_col = region_cols[0]
            if primary_sales_col:
                regional_sales = df.groupby(region_col)[primary_sales_col].sum().sort_values(ascending=False)
                result += f"- Top 3 regions: {dict(regional_sales.head(3))}\n"
        
        # Country breakdown for specific questions
        if country_cols and any(word in question.lower() for word in ['country', 'by country']):
            country_col = country_cols[0]
            if primary_sales_col:
                country_sales = df.groupby(country_col)[primary_sales_col].sum().sort_values(ascending=False)
                result += f"- Top 3 countries: {dict(country_sales.head(3))}"
        
        return result
        
    except Exception as e:
        return f"Error in sales analysis: {str(e)}"

def _analyze_items(df: pd.DataFrame, item_cols: List[str], sales_cols: List[str], region_cols: List[str]) -> str:
    """Analyze items/products in the data"""
    try:
        item_col = item_cols[0]
        result = f"**Product/Item Analysis:**\n"
        
        # Basic item statistics
        unique_items = df[item_col].nunique()
        total_records = len(df)
        result += f"- Unique items/products: **{unique_items}**\n"
        result += f"- Total records: {total_records}\n"
        
        # Most common items
        top_items = df[item_col].value_counts().head(5)
        result += f"- Most frequent items: {dict(top_items)}\n"
        
        # Sales by item if sales data available
        if sales_cols:
            sales_col = sales_cols[0]
            item_sales = df.groupby(item_col)[sales_col].sum().sort_values(ascending=False)
            result += f"- Top items by sales: {dict(item_sales.head(3))}"
        
        return result
        
    except Exception as e:
        return f"Error in item analysis: {str(e)}"

def _general_analysis(df: pd.DataFrame, question: str = "") -> str:
    """Dynamic general data analysis based on available data"""
    try:
        result = f"**Dataset Overview:**\n"
        result += f"- 📊 **Shape:** {df.shape[0]} rows, {df.shape[1]} columns\n"
        result += f"- 📋 **Columns:** {', '.join(df.columns[:5])}"
        if len(df.columns) > 5:
            result += f" (and {len(df.columns) - 5} more)"
        result += "\n"
        
        # Intelligent column analysis
        categorical_cols = df.select_dtypes(include=['object']).columns
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        # Show key categorical breakdowns
        if len(categorical_cols) > 0:
            result += f"\n**Key Categories:**\n"
            for col in categorical_cols[:3]:  # Show top 3 categorical columns
                unique_count = df[col].nunique()
                if unique_count <= 20:  # Show values for manageable lists
                    top_values = df[col].value_counts().head(5)
                    result += f"- **{col}:** {unique_count} unique ({', '.join(map(str, top_values.index))})\n"
                else:
                    result += f"- **{col}:** {unique_count} unique values\n"
        
        # Show numeric summaries
        if len(numeric_cols) > 0:
            result += f"\n**Numeric Data:**\n"
            for col in numeric_cols[:3]:  # Show top 3 numeric columns
                col_data = df[col]
                result += f"- **{col}:** Range {col_data.min():.1f} to {col_data.max():.1f}, Avg {col_data.mean():.1f}\n"
        
        # Smart suggestions based on data
        suggestions = []
        if any('region' in col.lower() for col in df.columns):
            suggestions.append("Try asking about regional comparisons")
        if any('country' in col.lower() for col in df.columns):
            suggestions.append("Ask about specific countries or country counts")
        if any(word in col.lower() for col in df.columns for word in ['sales', 'revenue', 'profit']):
            suggestions.append("Query financial metrics and totals")
        if any('item' in col.lower() or 'product' in col.lower() for col in df.columns):
            suggestions.append("Explore product/item analysis")
        
        if suggestions:
            result += f"\n**💡 Analysis Suggestions:** {', '.join(suggestions)}"
        
        return result
        
    except Exception as e:
        return f"Error in general analysis: {str(e)}"