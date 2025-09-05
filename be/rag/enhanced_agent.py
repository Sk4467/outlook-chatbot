# backend/rag/enhanced_agent.py
"""
Enhanced RAG Agent for improved PDF and tabular analysis
Works without external AI SDKs, using Gemini for enhanced analysis
"""
import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import io
import os
import google.generativeai as genai
from config_loader import load_config_to_env

class EnhancedRAGManager:
    """Manager for enhanced RAG capabilities using Gemini for analysis"""
    
    def __init__(self):
        load_config_to_env()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY must be set for enhanced analysis")
        
        # Configure Gemini
        genai.configure(api_key=self.google_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def analyze_pdf_content(self, question: str, pdf_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enhanced PDF content analysis using Gemini
        
        Args:
            question: User's question
            pdf_chunks: List of PDF chunks with metadata
        
        Returns:
            Dict with answer, sources, and analysis details
        """
        try:
            # Prepare context from PDF chunks
            context_parts = []
            sources = []
            
            for i, chunk in enumerate(pdf_chunks):
                meta = chunk.get('meta', {})
                text = chunk.get('text', '')
                filename = meta.get('filename', 'Unknown')
                page = meta.get('page', 'Unknown')
                
                context_parts.append(f"[Document {i+1}] {filename} (Page {page}):\n{text}")
                sources.append({
                    'filename': filename,
                    'page': page,
                    'chunk_id': i+1,
                    'type': 'pdf'
                })
            
            # Combine all context
            full_context = "\n\n".join(context_parts)
            
            # Create enhanced analysis prompt
            analysis_prompt = f"""
You are an expert document analyst with advanced reasoning capabilities. Analyze the provided PDF content to answer the user's question comprehensively.

PDF CONTENT:
{full_context}

USER QUESTION: {question}

ANALYSIS INSTRUCTIONS:
1. Provide a detailed, accurate answer based solely on the PDF content
2. Synthesize information across multiple pages/documents when relevant
3. Include specific page references in your citations
4. Identify key insights, patterns, and relationships in the content
5. If information is incomplete, clearly state what's missing
6. Structure your response with clear sections and bullet points where appropriate

RESPONSE FORMAT:
- Main Answer: [Comprehensive response to the question]
- Supporting Evidence: [Key quotes and data with page citations]
- Key Insights: [Additional relevant findings]
- Information Gaps: [What information might be missing, if any]

Ensure your response is professional, accurate, and well-structured.
"""
            
            # Get response from Gemini
            response = self.model.generate_content(analysis_prompt)
            answer_text = response.text if response.text else "Unable to generate response"
            
            return {
                "answer": answer_text,
                "sources": sources,
                "analysis_type": "enhanced_pdf",
                "chunks_analyzed": len(pdf_chunks),
                "model_used": "gemini-1.5-flash"
            }
            
        except Exception as e:
            # Fallback to basic analysis
            basic_answer = self._create_basic_pdf_summary(pdf_chunks, question)
            return {
                "answer": f"Enhanced analysis encountered an error: {str(e)}\n\nBasic Summary: {basic_answer}",
                "sources": [{"filename": chunk.get('meta', {}).get('filename', 'Unknown'), 
                           "page": chunk.get('meta', {}).get('page', 'Unknown')} for chunk in pdf_chunks],
                "analysis_type": "pdf_fallback",
                "error": str(e)
            }
    
    def _create_basic_pdf_summary(self, pdf_chunks: List[Dict[str, Any]], question: str) -> str:
        """Create a basic summary when enhanced analysis fails"""
        total_chunks = len(pdf_chunks)
        files = set()
        pages = set()
        
        for chunk in pdf_chunks:
            meta = chunk.get('meta', {})
            if meta.get('filename'):
                files.add(meta['filename'])
            if meta.get('page'):
                pages.add(str(meta['page']))
        
        summary = f"Found {total_chunks} relevant text chunks across {len(files)} document(s)"
        if pages:
            summary += f" on pages: {', '.join(sorted(pages))}"
        
        # Try to extract key sentences related to the question
        question_words = set(question.lower().split())
        relevant_sentences = []
        
        for chunk in pdf_chunks[:3]:  # Limit to first 3 chunks
            text = chunk.get('text', '')
            sentences = text.split('.')
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and any(word in sentence.lower() for word in question_words):
                    relevant_sentences.append(sentence[:200] + "..." if len(sentence) > 200 else sentence)
                    if len(relevant_sentences) >= 3:
                        break
        
        if relevant_sentences:
            summary += "\n\nKey relevant content:\n" + "\n".join(f"• {s}" for s in relevant_sentences)
        
        return summary
    
    async def analyze_tabular_data(self, question: str, tables: List[Tuple[str, pd.DataFrame]]) -> Dict[str, Any]:
        """
        Enhanced tabular data analysis using Gemini
        
        Args:
            question: User's question
            tables: List of (label, DataFrame) tuples
        
        Returns:
            Dict with answer, analysis details, and data insights
        """
        try:
            if not tables:
                return {
                    "answer": "No tabular data available for analysis.",
                    "tables_used": [],
                    "previews": [],
                    "analysis_type": "no_data"
                }
            
            # Prepare comprehensive data context
            table_descriptions = []
            previews = []
            
            for label, df in tables:
                # Create detailed description
                shape = df.shape
                columns = list(df.columns)
                dtypes = dict(df.dtypes.astype(str))
                
                # Get sample data
                sample_data = df.head(10).to_string(index=False)
                previews.append(f"{label} (Shape: {shape}):\n{sample_data}")
                
                # Get statistics for numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                stats_summary = ""
                if len(numeric_cols) > 0:
                    stats = df[numeric_cols].describe()
                    stats_summary = f"\nNUMERIC STATISTICS:\n{stats.to_string()}"
                
                # Get value counts for categorical columns (top 5)
                categorical_summary = ""
                categorical_cols = df.select_dtypes(include=['object', 'category']).columns
                if len(categorical_cols) > 0:
                    cat_info = []
                    for col in categorical_cols[:3]:  # Limit to 3 columns
                        value_counts = df[col].value_counts().head(5)
                        cat_info.append(f"{col}: {dict(value_counts)}")
                    categorical_summary = f"\nCATEGORICAL DATA (Top values):\n" + "\n".join(cat_info)
                
                description = f"""
TABLE: {label}
Shape: {shape[0]} rows, {shape[1]} columns
Columns: {columns}
Data Types: {dtypes}

SAMPLE DATA:
{sample_data}
{stats_summary}
{categorical_summary}
"""
                table_descriptions.append(description)
            
            # Create comprehensive analysis prompt
            analysis_prompt = f"""
You are an expert data analyst with advanced statistical and analytical capabilities. Analyze the provided tabular data to answer the user's question comprehensively.

TABULAR DATA:
{chr(10).join(table_descriptions)}

USER QUESTION: {question}

ANALYSIS INSTRUCTIONS:
1. Provide a comprehensive answer based on the data provided
2. Perform calculations, aggregations, and statistical analysis as needed
3. Identify trends, patterns, and insights in the data
4. Use specific values and calculations to support your findings
5. Compare across tables/sheets when relevant
6. Suggest additional analysis that might be valuable

RESPONSE FORMAT:
- Direct Answer: [Answer to the specific question with calculations]
- Key Findings: [Important insights from the data]
- Statistical Summary: [Relevant statistics and metrics]
- Data Quality Notes: [Any observations about data completeness/quality]
- Recommendations: [Suggested follow-up analysis or actions]

Be precise with numbers and calculations. Show your work when performing computations.
"""
            
            # Get response from Gemini
            response = self.model.generate_content(analysis_prompt)
            answer_text = response.text if response.text else "Unable to generate response"
            
            return {
                "answer": answer_text,
                "tables_used": [label for label, _ in tables],
                "previews": previews,
                "analysis_type": "enhanced_tabular",
                "table_count": len(tables),
                "model_used": "gemini-1.5-flash"
            }
            
        except Exception as e:
            # Fallback to basic analysis
            return await self._basic_tabular_analysis(question, tables, previews if 'previews' in locals() else [])
    
    async def _basic_tabular_analysis(self, question: str, tables: List[Tuple[str, pd.DataFrame]], previews: List[str]) -> Dict[str, Any]:
        """Basic tabular analysis when enhanced analysis fails"""
        try:
            q_lower = question.lower()
            answers = []
            
            for label, df in tables:
                answer_parts = []
                
                # Basic info
                answer_parts.append(f"Data shape: {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Basic statistics for common question patterns
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    if any(word in q_lower for word in ['sum', 'total']):
                        sums = df[numeric_cols].sum()
                        answer_parts.append(f"Column sums: {dict(sums)}")
                    
                    if any(word in q_lower for word in ['mean', 'average']):
                        means = df[numeric_cols].mean()
                        answer_parts.append(f"Column averages: {dict(means)}")
                    
                    if any(word in q_lower for word in ['max', 'maximum']):
                        maxes = df[numeric_cols].max()
                        answer_parts.append(f"Maximum values: {dict(maxes)}")
                    
                    if any(word in q_lower for word in ['min', 'minimum']):
                        mins = df[numeric_cols].min()
                        answer_parts.append(f"Minimum values: {dict(mins)}")
                    
                    if 'count' in q_lower:
                        counts = df.count()
                        answer_parts.append(f"Non-null counts: {dict(counts)}")
                
                # Basic info if no specific operations matched
                if len(answer_parts) == 1:  # Only has shape info
                    answer_parts.append(f"Columns: {list(df.columns)}")
                    if len(numeric_cols) > 0:
                        answer_parts.append("Contains numeric data suitable for calculations")
                
                answers.append(f"{label}: {' | '.join(answer_parts)}")
            
            return {
                "answer": "\n\n".join(answers),
                "tables_used": [label for label, _ in tables],
                "previews": previews,
                "analysis_type": "basic_fallback"
            }
            
        except Exception as e:
            return {
                "answer": f"Analysis failed: {str(e)}",
                "tables_used": [label for label, _ in tables],
                "previews": previews,
                "analysis_type": "error_fallback",
                "error": str(e)
            }
    
    async def enhanced_document_analysis(self, question: str, pdf_chunks: List[Dict[str, Any]], 
                                       context_docs: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhanced multi-document analysis combining PDFs with additional context
        """
        try:
            # Prepare comprehensive context
            all_sources = []
            context_parts = []
            
            # Add PDF chunks
            for i, chunk in enumerate(pdf_chunks):
                meta = chunk.get('meta', {})
                text = chunk.get('text', '')
                filename = meta.get('filename', 'Unknown')
                page = meta.get('page', 'Unknown')
                
                context_parts.append(f"[PDF {i+1}] {filename} (Page {page}):\n{text}")
                all_sources.append({
                    'type': 'pdf',
                    'filename': filename,
                    'page': page,
                    'chunk_id': i+1
                })
            
            # Add additional context documents if provided
            if context_docs:
                for i, doc in enumerate(context_docs):
                    meta = doc.get('meta', {})
                    text = doc.get('text', '')
                    doc_type = meta.get('type', 'document')
                    source_info = meta.get('subject', meta.get('filename', 'Unknown'))
                    
                    context_parts.append(f"[Context {i+1}] {doc_type} - {source_info}:\n{text}")
                    all_sources.append({
                        'type': doc_type,
                        'source': source_info,
                        'chunk_id': len(pdf_chunks) + i + 1
                    })
            
            # Combine all context
            full_context = "\n\n".join(context_parts)
            
            # Create enhanced analysis prompt
            analysis_prompt = f"""
You are an expert analyst specializing in cross-document synthesis and information integration. Analyze the following documents to provide a comprehensive answer that leverages all available sources.

DOCUMENT CONTENT:
{full_context}

USER QUESTION: {question}

ANALYSIS INSTRUCTIONS:
1. Synthesize information from ALL sources to provide a comprehensive answer
2. Identify relationships and patterns across different document types
3. Provide clear citations showing which sources support each part of your answer
4. Highlight any contradictions or gaps between sources
5. Extract insights that emerge from the combined analysis
6. Structure your response for maximum clarity and usefulness

RESPONSE FORMAT:
- Comprehensive Answer: [Synthesized response using all relevant sources]
- Source Analysis: [How different sources contribute to the answer]
- Cross-Document Insights: [Patterns/relationships across documents]
- Supporting Evidence: [Key quotes with source citations]
- Additional Context: [Relevant background information from the documents]

Use clear citations like [PDF 1, Page 3] or [Email from sender@email.com] when referencing sources.
"""
            
            # Get response from Gemini
            response = self.model.generate_content(analysis_prompt)
            answer_text = response.text if response.text else "Unable to generate response"
            
            return {
                "answer": answer_text,
                "sources": all_sources,
                "analysis_type": "enhanced_multi_document",
                "total_chunks": len(pdf_chunks) + (len(context_docs) if context_docs else 0),
                "model_used": "gemini-1.5-flash"
            }
            
        except Exception as e:
            basic_summary = f"Analysis across {len(pdf_chunks)} PDF chunks"
            if context_docs:
                basic_summary += f" and {len(context_docs)} additional documents"
            basic_summary += f" failed due to: {str(e)}"
            
            return {
                "answer": basic_summary,
                "sources": all_sources if 'all_sources' in locals() else [],
                "analysis_type": "multi_document_fallback",
                "error": str(e)
            }

# Global manager instance
_enhanced_rag_manager = None

def get_enhanced_rag_manager() -> EnhancedRAGManager:
    """Get global enhanced RAG manager instance"""
    global _enhanced_rag_manager
    if _enhanced_rag_manager is None:
        _enhanced_rag_manager = EnhancedRAGManager()
    return _enhanced_rag_manager

async def analyze_pdf_with_agent(question: str, pdf_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for enhanced PDF analysis"""
    manager = get_enhanced_rag_manager()
    return await manager.analyze_pdf_content(question, pdf_chunks)

async def analyze_tables_with_agent(question: str, tables: List[Tuple[str, pd.DataFrame]]) -> Dict[str, Any]:
    """Convenience function for enhanced tabular analysis"""
    manager = get_enhanced_rag_manager()
    return await manager.analyze_tabular_data(question, tables)
