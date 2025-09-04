# backend/rag/tabular_agent.py
from typing import List, Dict, Any, Tuple
import io
import httpx
import pandas as pd

def _load_blob_bytes(url: str) -> bytes:
    with httpx.Client(timeout=60.0) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.content

def load_dataframes(table_specs: List[Dict[str, Any]]) -> List[Tuple[str, pd.DataFrame]]:
    """
    table_specs: [{ blob_uri, filename, sheet?, columns? }, ...]
    Loads CSV/XLSX into DataFrame(s). If XLSX with multiple sheets, and sheet provided in spec, load that sheet only.
    Returns list of (label, df).
    """
    out: List[Tuple[str, pd.DataFrame]] = []
    for spec in table_specs:
        uri = spec.get("blob_uri")
        fname = (spec.get("filename") or "").lower()
        sheet = spec.get("sheet")
        if not uri:
            continue
        data = _load_blob_bytes(uri)
        label = spec.get("filename") or "table"
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(data))
                out.append((label, df))
            elif fname.endswith((".xlsx", ".xlsm")):
                if sheet:
                    df = pd.read_excel(io.BytesIO(data), sheet_name=sheet, engine="openpyxl")
                    out.append((f"{label}:{sheet}", df))
                else:
                    # load first sheet by default
                    df = pd.read_excel(io.BytesIO(data), engine="openpyxl")
                    out.append((label, df))
            else:
                # Not tabular
                continue
        except Exception as e:
            out.append((label, pd.DataFrame({"_error": [str(e)]})))
    return out

def answer_with_pandasai(question: str, tables: List[Tuple[str, pd.DataFrame]]) -> Dict[str, Any]:
    """
    Optional PandasAI integration.
    - If pandasai is installed and configured, use it.
    - Otherwise, fallback to a simple descriptive message with table heads.
    """
    try:
         # or Agent in newer versions
        # NOTE: Configure PandasAI LLM provider separately if required by your version.
        # Some versions need OpenAI key; newer versions may allow local/other providers.
        answers = []
        previews = []
        for label, df in tables:
            # sdf = SmartDataframe(df)
            # ans = sdf.chat(question) 
            ans="haha" # may raise if provider not configured
            answers.append(f"{label}: {ans}")
            previews.append(f"{label} head:\n{df.head(5).to_string(index=False)}")
        return {
            "answer": "\n".join(answers),
            "tables_used": [label for label, _ in tables],
            "previews": previews
        }
    except Exception as _:
        # Fallback: no PandasAI available — return a helpful preview to demonstrate routing works.
        previews = [f"{label} head:\n{df.head(5).to_string(index=False)}" for label, df in tables]
        return {
            "answer": "[Tabular route selected] Configure PandasAI to compute results. Showing previews instead.",
            "tables_used": [label for label, _ in tables],
            "previews": previews
        }