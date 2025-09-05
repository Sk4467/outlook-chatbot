# Enhanced RAG System for Outlook Chatbot

This document describes the enhanced RAG (Retrieval-Augmented Generation) system for the Outlook chatbot, providing advanced PDF analysis and tabular data processing capabilities using Google's Gemini AI.

## Overview

The enhanced system provides intelligent analysis capabilities using Google's Gemini AI, enabling:

- **Intelligent PDF Analysis**: Advanced document understanding beyond simple text matching
- **Smart Tabular Processing**: Sophisticated data analysis for Excel/CSV files  
- **Multi-Modal RAG**: Cross-document synthesis combining emails, PDFs, and data
- **Fallback Mechanisms**: Graceful degradation when PandaAGI is unavailable

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI        │    │   PandaAGI      │
│   React App     │◄──►│   Backend        │◄──►│   Agents        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   ChromaDB       │
                       │   Vector Store   │
                       └──────────────────┘
```

### Components

1. **PandaAGI Agent Manager** (`pandaagi_agent.py`)
   - Manages PDF and tabular analysis agents
   - Handles agent lifecycle and configuration
   - Provides async interfaces for analysis

2. **Enhanced Parsers** (`parsers.py`)
   - Improved PDF text extraction with structure preservation
   - Better text cleaning and normalization

3. **Smart Tabular Agent** (`tabular_agent.py`)  
   - PandaAGI-powered data analysis
   - Fallback to basic pandas operations

4. **Enhanced API Endpoints** (`api.py`)
   - `/ask` - Enhanced with PandaAGI capabilities
   - `/ask/enhanced-pdf` - Advanced PDF analysis
   - `/ask/multi-modal` - Cross-document synthesis

## Configuration

### 1. API Key Setup

Add your PandaAGI API key to `config.yaml`:

```yaml
pandas-agi:
  api_key: "pk_your_api_key_here"
```

### 2. Dependencies

Install required packages:

```bash
pip install pandas-agi-sdk pandas numpy websockets aiofiles
```

### 3. Environment Variables

The system automatically loads the API key from config:
- `PANDAS_AGI_API_KEY` - Set from config.yaml

## Usage

### Basic Enhanced Query

```python
# POST /ask
{
    "question": "What are the key findings in the financial report?",
    "k": 6
}
```

Response includes:
- `analysis_type`: Type of analysis performed
- `chunks_analyzed`: Number of document chunks processed
- Enhanced answer with agent insights

### Advanced PDF Analysis

```python
# POST /ask/enhanced-pdf  
{
    "question": "Compare revenue trends across quarters",
    "k": 10
}
```

Features:
- Cross-document synthesis
- Contextual email integration
- Advanced document understanding

### Multi-Modal Analysis

```python
# POST /ask/multi-modal
{
    "question": "How do the sales data trends correlate with customer feedback?",
    "k": 8
}
```

Combines:
- Email content analysis
- PDF document insights  
- Tabular data processing
- Unified intelligent response

### Tabular Data Questions

```python
{
    "question": "What's the average profit margin by region?",
    "k": 5
}
```

Capabilities:
- Complex data aggregations
- Statistical analysis
- Trend identification
- Cross-table relationships

## Agent Capabilities

### PDF Agent

- **Document Understanding**: Comprehends document structure and context
- **Multi-Page Synthesis**: Combines information across pages
- **Citation Management**: Provides accurate page references
- **Context Awareness**: Understands document relationships

### Tabular Agent  

- **Data Analysis**: Performs complex pandas operations
- **Statistical Insights**: Calculates trends, correlations, and patterns
- **Multi-Table Operations**: Analyzes relationships across datasets
- **Visualization Guidance**: Suggests relevant data visualizations

## Fallback Mechanisms

The system includes robust fallback strategies:

1. **PandaAGI Unavailable**: Falls back to traditional RAG with Gemini
2. **Agent Timeout**: Switches to basic analysis methods
3. **API Errors**: Uses local pandas operations for tabular data
4. **Network Issues**: Graceful error handling with informative messages

## Performance Optimizations

- **Async Processing**: Non-blocking agent operations
- **Connection Pooling**: Efficient WebSocket management
- **Caching**: Agent instance reuse across requests
- **Timeout Handling**: 60-second timeout for agent operations

## Error Handling

```python
{
    "answer": "Enhanced analysis completed with insights...",
    "analysis_type": "pdf_agentic",  # or "pdf_fallback" on error
    "error": null  # Error details if fallback was triggered
}
```

## Testing

Run the comprehensive test suite:

```bash
python test_pandaagi_integration.py
```

Tests include:
- ✅ Connection and authentication
- ✅ PDF analysis capabilities  
- ✅ Tabular data processing
- ✅ Enhanced document synthesis
- ✅ Fallback mechanism validation

## Monitoring and Debugging

### Log Output

The system provides detailed logging:
- Agent initialization status
- Analysis type selection
- Fallback trigger reasons
- Performance metrics

### Debug Mode

Enable debug logging by setting:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- **API Key Protection**: Keys stored in config files, not code
- **Request Validation**: Input sanitization for all endpoints  
- **Timeout Limits**: Prevents hanging agent operations
- **Error Isolation**: Failures don't crash the entire system

## Troubleshooting

### Common Issues

1. **API Key Invalid**
   - Verify key in config.yaml
   - Check PandaAGI account status

2. **Connection Timeout**
   - Check network connectivity
   - Verify PandaAGI service status

3. **Import Errors**
   - Ensure pandas-agi-sdk is installed
   - Check Python path configuration

4. **Agent Creation Failed**
   - Validate environment setup
   - Check API quota limits

### Performance Issues

1. **Slow Response Times**
   - Reduce chunk count (k parameter)
   - Optimize document preprocessing
   - Check agent timeout settings

2. **Memory Usage**
   - Limit concurrent agent operations
   - Implement connection pooling
   - Monitor DataFrame sizes

## Extending the System

### Adding New Agent Types

```python
async def get_custom_agent(self) -> Agent:
    if self._custom_agent is None:
        self._custom_agent = Agent(
            name="Custom Analyzer",
            description="Specialized analysis capabilities",
            environment=self.env,
            instructions=[
                "Custom agent instructions..."
            ]
        )
    return self._custom_agent
```

### Custom Analysis Endpoints

```python
@router.post("/ask/custom-analysis")
async def custom_analysis(req: AskRequest) -> Dict[str, Any]:
    # Custom analysis logic
    pass
```

## Best Practices

1. **Agent Reuse**: Cache agent instances for performance
2. **Error Handling**: Always provide fallback mechanisms
3. **Input Validation**: Sanitize user inputs before processing
4. **Timeout Management**: Set appropriate timeouts for operations
5. **Resource Cleanup**: Properly dispose of agent resources
6. **Monitoring**: Log key metrics for system health

## Future Enhancements

- **Advanced Caching**: Redis-based agent response caching
- **Streaming Responses**: Real-time analysis updates
- **Custom Models**: Integration with specialized domain models
- **Batch Processing**: Efficient handling of multiple documents
- **Visual Analysis**: Image and chart understanding capabilities
