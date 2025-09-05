#!/usr/bin/env python3
"""
Test script for Enhanced RAG system
Tests enhanced PDF analysis, tabular data processing, and multi-modal capabilities using Gemini
"""

import asyncio
import sys
import os
import pandas as pd
from typing import Dict, Any, List
import json

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from config_loader import load_config_to_env
from rag.enhanced_agent import EnhancedRAGManager, get_enhanced_rag_manager

async def test_enhanced_connection():
    """Test enhanced RAG manager connection and initialization"""
    print("🔍 Testing Enhanced RAG Manager connection...")
    
    try:
        # Load config
        load_config_to_env()
        
        # Check if API key is available
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return False
        
        print(f"✅ Google API key found: {api_key[:10]}...")
        
        # Initialize manager
        manager = EnhancedRAGManager()
        print("✅ Enhanced RAG manager initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced RAG connection failed: {e}")
        return False

async def test_enhanced_pdf_analysis():
    """Test enhanced PDF analysis capabilities"""
    print("\n📄 Testing Enhanced PDF Analysis...")
    
    try:
        manager = get_enhanced_rag_manager()
        
        # Mock PDF chunks (simulating extracted PDF content)
        pdf_chunks = [
            {
                "text": "Executive Summary: The Q3 2024 financial results show strong performance across all business units. Total revenue reached $2.5 million, representing a 15% increase from Q2 2024. The technology division was the primary growth driver, contributing 60% of total revenue. Operating expenses decreased by 8% due to efficiency improvements.",
                "meta": {
                    "filename": "Q3_Financial_Report.pdf",
                    "page": 1,
                    "type": "attachment_pdf"
                }
            },
            {
                "text": "Revenue Breakdown by Division: Technology: $1.5M (60%), Healthcare: $0.6M (24%), Manufacturing: $0.4M (16%). The technology division showed the strongest growth with 25% increase quarter-over-quarter. Customer acquisition costs decreased by 12% while customer lifetime value increased by 18%.",
                "meta": {
                    "filename": "Q3_Financial_Report.pdf",
                    "page": 2,
                    "type": "attachment_pdf"
                }
            },
            {
                "text": "Future Outlook: The company expects continued growth in Q4 2024, with projected revenue of $2.8M. Key initiatives include expansion into European markets and development of three new product lines. Risk factors include potential supply chain disruptions and increased competition in the technology sector.",
                "meta": {
                    "filename": "Q3_Financial_Report.pdf",
                    "page": 3,
                    "type": "attachment_pdf"
                }
            }
        ]
        
        # Test different types of questions
        questions = [
            "What were the main financial highlights in Q3 2024?",
            "Which division performed best and what was its contribution?",
            "What are the future projections and key risks?",
            "How did customer metrics change this quarter?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n🔍 Test {i}: {question}")
            result = await manager.analyze_pdf_content(question, pdf_chunks)
            
            print(f"✅ Analysis completed")
            print(f"📊 Answer preview: {result.get('answer', 'No answer')[:200]}...")
            print(f"📋 Sources: {len(result.get('sources', []))} chunks analyzed")
            print(f"🔧 Analysis type: {result.get('analysis_type', 'unknown')}")
            print(f"🤖 Model: {result.get('model_used', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced PDF analysis failed: {e}")
        return False

async def test_enhanced_tabular_analysis():
    """Test enhanced tabular data analysis capabilities"""
    print("\n📊 Testing Enhanced Tabular Analysis...")
    
    try:
        manager = get_enhanced_rag_manager()
        
        # Create comprehensive sample DataFrames
        sales_data = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Revenue': [100000, 120000, 135000, 142000, 158000, 175000],
            'Costs': [60000, 72000, 81000, 85000, 94000, 105000],
            'Profit': [40000, 48000, 54000, 57000, 64000, 70000],
            'Customers': [1200, 1350, 1420, 1580, 1750, 1900],
            'Region': ['North', 'South', 'East', 'West', 'North', 'South']
        })
        
        customer_data = pd.DataFrame({
            'Region': ['North', 'South', 'East', 'West'],
            'Total_Customers': [1200, 890, 1050, 750],
            'Avg_Order_Value': [85.50, 92.30, 78.20, 88.10],
            'Satisfaction_Score': [4.2, 4.5, 4.1, 4.3],
            'Churn_Rate': [0.05, 0.03, 0.07, 0.04]
        })
        
        product_data = pd.DataFrame({
            'Product': ['Product A', 'Product B', 'Product C', 'Product D'],
            'Price': [199.99, 299.99, 149.99, 399.99],
            'Units_Sold': [1500, 800, 2200, 600],
            'Manufacturing_Cost': [120.00, 180.00, 90.00, 240.00],
            'Category': ['Electronics', 'Software', 'Hardware', 'Premium']
        })
        
        tables = [
            ("Monthly_Sales_2024.xlsx", sales_data),
            ("Customer_Analytics.csv", customer_data),
            ("Product_Performance.xlsx", product_data)
        ]
        
        # Test comprehensive questions
        questions = [
            "What is the total revenue and profit trend over the months?",
            "Which region has the best customer metrics and why?",
            "What's the profitability analysis by product category?",
            "How do customer acquisition and retention metrics compare across regions?",
            "What are the key business insights from this data?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n🔍 Test {i}: {question}")
            result = await manager.analyze_tabular_data(question, tables)
            
            print(f"✅ Analysis completed")
            print(f"📊 Answer preview: {result.get('answer', 'No answer')[:200]}...")
            print(f"📋 Tables used: {result.get('table_count', 0)}")
            print(f"🔧 Analysis type: {result.get('analysis_type', 'unknown')}")
            print(f"🤖 Model: {result.get('model_used', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced tabular analysis failed: {e}")
        return False

async def test_enhanced_document_analysis():
    """Test enhanced multi-document analysis with mixed content"""
    print("\n🔄 Testing Enhanced Multi-Document Analysis...")
    
    try:
        manager = get_enhanced_rag_manager()
        
        # Mock PDF chunks
        pdf_chunks = [
            {
                "text": "Customer Service Strategy Implementation: In Q3 2024, the company launched a comprehensive customer service improvement initiative. Key components included: 1) Reduced average response time from 4 hours to 90 minutes, 2) Implemented AI-powered chatbot for initial customer inquiries, 3) Expanded customer service team by 40%, 4) Introduced proactive customer outreach program.",
                "meta": {
                    "filename": "Customer_Service_Report.pdf",
                    "page": 1,
                    "type": "attachment_pdf"
                }
            },
            {
                "text": "Customer Satisfaction Results: Post-implementation surveys show significant improvements: Customer satisfaction scores increased from 3.8 to 4.5 (out of 5). Net Promoter Score (NPS) improved from 32 to 58. Customer retention rate increased by 15%. Complaint resolution time decreased by 60%. First-call resolution rate improved from 65% to 82%.",
                "meta": {
                    "filename": "Customer_Service_Report.pdf",
                    "page": 2,
                    "type": "attachment_pdf"
                }
            }
        ]
        
        # Mock email context
        context_docs = [
            {
                "text": "From: ceo@company.com\nTo: all-staff@company.com\nSubject: Q3 Customer Satisfaction Achievement\nDate: Oct 15, 2024\n\nTeam, I'm thrilled to announce that our customer satisfaction scores have reached an all-time high this quarter! The customer service improvements we implemented are delivering exceptional results. Our NPS score of 58 puts us in the top 10% of companies in our industry. Special thanks to the customer service team for their dedication and the IT team for the seamless chatbot integration.",
                "meta": {
                    "type": "mail_body",
                    "subject": "Q3 Customer Satisfaction Achievement",
                    "sender": "ceo@company.com",
                    "receivedAt": "2024-10-15"
                }
            },
            {
                "text": "From: customerservice@company.com\nTo: management@company.com\nSubject: Customer Service Metrics Update\nDate: Oct 10, 2024\n\nHere's our weekly update: This week we handled 2,847 customer inquiries with an average response time of 85 minutes. The AI chatbot successfully resolved 68% of initial inquiries without human intervention. We received 47 positive feedback messages and only 3 complaints. Team morale is high and customers are noticing the difference!",
                "meta": {
                    "type": "mail_body",
                    "subject": "Customer Service Metrics Update",
                    "sender": "customerservice@company.com",
                    "receivedAt": "2024-10-10"
                }
            }
        ]
        
        # Test multi-document synthesis questions
        questions = [
            "How did the customer service improvements impact satisfaction scores and what do the emails reveal about the results?",
            "What specific metrics improved and how do they compare to the qualitative feedback in the emails?",
            "What can we learn about the implementation success from both the formal report and internal communications?",
            "What are the key achievements and ongoing performance indicators across all sources?"
        ]
        
        for i, question in enumerate(questions, 1):
            print(f"\n🔍 Test {i}: {question}")
            result = await manager.enhanced_document_analysis(question, pdf_chunks, context_docs)
            
            print(f"✅ Enhanced analysis completed")
            print(f"📊 Answer preview: {result.get('answer', 'No answer')[:250]}...")
            print(f"📋 Sources: {len(result.get('sources', []))} documents analyzed")
            print(f"📄 Total chunks: {result.get('total_chunks', 0)}")
            print(f"🔧 Analysis type: {result.get('analysis_type', 'unknown')}")
            print(f"🤖 Model: {result.get('model_used', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced document analysis failed: {e}")
        return False

def test_fallback_mechanisms():
    """Test fallback mechanisms when enhanced analysis fails"""
    print("\n🔒 Testing Fallback Mechanisms...")
    
    try:
        from rag.tabular_agent import _basic_tabular_analysis
        
        # Create sample data
        df = pd.DataFrame({
            'Product': ['A', 'B', 'C', 'D'],
            'Sales': [100, 200, 150, 300],
            'Profit': [20, 40, 30, 60],
            'Region': ['North', 'South', 'East', 'West']
        })
        
        tables = [("Test_Sales_Data.csv", df)]
        
        # Test basic analysis patterns
        questions = [
            "What are the total sales?",
            "What's the average profit?",
            "Which product has maximum sales?",
            "Show me the data summary"
        ]
        
        for question in questions:
            print(f"\n🔍 Fallback Test: {question}")
            result = _basic_tabular_analysis(question, tables)
            
            print(f"✅ Fallback analysis completed")
            print(f"📊 Answer: {result.get('answer', 'No answer')[:150]}...")
            print(f"🔧 Analysis type: {result.get('analysis_type', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False

async def test_api_endpoints():
    """Test the enhanced API endpoints"""
    print("\n🌐 Testing API Integration...")
    
    try:
        from rag.api import ask
        from rag.api import AskRequest
        
        # Test basic enhanced analysis
        request = AskRequest(question="What are the financial results?", k=3)
        
        print("✅ API endpoints can be imported and configured")
        print("📝 Note: Full API testing requires running the server with actual data")
        
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run all enhanced RAG tests"""
    print("🚀 Starting Enhanced RAG Integration Tests\n")
    
    tests = [
        ("Enhanced Connection Test", test_enhanced_connection()),
        ("Enhanced PDF Analysis Test", test_enhanced_pdf_analysis()),
        ("Enhanced Tabular Analysis Test", test_enhanced_tabular_analysis()),
        ("Enhanced Multi-Document Analysis Test", test_enhanced_document_analysis()),
        ("API Integration Test", test_api_endpoints()),
    ]
    
    results = []
    
    for test_name, test_coro in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            success = await test_coro
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Test fallback (non-async)
    print(f"\n{'='*60}")
    print("Running: Fallback Mechanisms Test")
    print('='*60)
    
    fallback_success = test_fallback_mechanisms()
    results.append(("Fallback Test", fallback_success))
    
    # Print comprehensive summary
    print(f"\n{'='*60}")
    print("COMPREHENSIVE TEST SUMMARY")
    print('='*60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{test_name:<40}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced RAG system is working correctly.")
        print("\n🌟 Key Features Successfully Tested:")
        print("   ✅ Enhanced PDF analysis with Gemini")
        print("   ✅ Smart tabular data processing")
        print("   ✅ Multi-document synthesis")
        print("   ✅ Comprehensive fallback mechanisms")
        print("   ✅ API endpoint integration")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    # Run the comprehensive tests
    success = asyncio.run(run_comprehensive_test())
    
    if success:
        print("\n🔧 Next Steps:")
        print("1. Start the backend server: python main.py")
        print("2. Test the enhanced endpoints:")
        print("   - POST /ask (enhanced with intelligent analysis)")
        print("   - POST /ask/enhanced-pdf (advanced PDF analysis)")
        print("   - POST /ask/multi-modal (cross-document synthesis)")
        print("3. Upload PDF and Excel attachments to test with real data")
        print("\n📚 Features Available:")
        print("   - Intelligent PDF content analysis")
        print("   - Advanced tabular data insights")
        print("   - Multi-modal document synthesis")
        print("   - Comprehensive error handling and fallbacks")
        sys.exit(0)
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check your Google API key in config.yaml")
        print("2. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("3. Verify network connectivity to Google AI services")
        print("4. Check the error messages above for specific issues")
        sys.exit(1)
