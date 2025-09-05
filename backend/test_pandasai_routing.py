"""
Test script to verify PandasAI routing is working correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag.pandasai_integration import is_analysis_question

def test_analysis_detection():
    """Test if analysis questions are properly detected"""
    
    # Analysis questions - should return True
    analysis_questions = [
        "How many countries are in Asia?",
        "What is the total sales by region?",
        "Show me the top 5 performing products",
        "Calculate the average revenue per customer",
        "Compare sales between Q1 and Q2",
        "Which region has the highest profit?",
        "Analyze the sales trends over time",
        "Find the correlation between price and sales",
        "What percentage of sales comes from Europe?",
        "List all customers with revenue > 10000",
        "Group sales by product category",
        "Show me insights from the data"
    ]
    
    # Non-analysis questions - should return False  
    non_analysis_questions = [
        "What is this file about?",
        "Can you open this document?",
        "What emails did I receive yesterday?",
        "Show me the attachment content",
        "What does this PDF contain?",
        "Hello, how are you?",
        "Can you help me?",
        "What time is it?"
    ]
    
    print("🧪 Testing Analysis Question Detection\n")
    
    print("✅ ANALYSIS QUESTIONS (should be True):")
    for q in analysis_questions:
        result = is_analysis_question(q)
        status = "✅" if result else "❌"
        print(f"  {status} {q} → {result}")
    
    print("\n❌ NON-ANALYSIS QUESTIONS (should be False):")
    for q in non_analysis_questions:
        result = is_analysis_question(q)
        status = "✅" if not result else "❌"
        print(f"  {status} {q} → {result}")
    
    # Summary
    analysis_correct = sum(1 for q in analysis_questions if is_analysis_question(q))
    non_analysis_correct = sum(1 for q in non_analysis_questions if not is_analysis_question(q))
    
    total_correct = analysis_correct + non_analysis_correct
    total_questions = len(analysis_questions) + len(non_analysis_questions)
    
    print(f"\n📊 SUMMARY:")
    print(f"  Analysis questions detected: {analysis_correct}/{len(analysis_questions)}")
    print(f"  Non-analysis questions detected: {non_analysis_correct}/{len(non_analysis_questions)}")
    print(f"  Overall accuracy: {total_correct}/{total_questions} ({total_correct/total_questions*100:.1f}%)")

if __name__ == "__main__":
    test_analysis_detection()
