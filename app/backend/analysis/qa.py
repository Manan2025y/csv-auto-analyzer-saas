"""Deterministic natural-language questions over the uploaded dataset."""
from __future__ import annotations
import re
import pandas as pd
from .engine import to_numeric_series


def answer_question(df, question: str):
    q=question.strip().lower()
    if not q:return "Try: Give me a summary of the data, what are the main metrics, which column has the most missing values, or what are total sales?"
    # Common stakeholder/analyst questions that do not require a named measure.
    miss=df.isna().sum().sort_values(ascending=False)
    numeric=[c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) or to_numeric_series(df[c]).notna().mean()>=.8]
    if any(k in q for k in ["summary","summarize","overview","brief me","tell me about the data"]):
        parts=[f"**{len(df):,} rows** across **{len(df.columns):,} columns**"]
        if numeric:
            top=numeric[:5]; parts.append("Key numeric fields: " + ", ".join(map(str,top)))
        if miss.iloc[0]>0: parts.append(f"Most missing data: **{miss.index[0]}** ({int(miss.iloc[0]):,} cells)")
        else: parts.append("There are **no missing cells**.")
        return "Dataset summary: " + ". ".join(parts) + "."
    if any(k in q for k in ["main metrics","key metrics","important metrics","measures"]):
        return "The main numeric measures are: **" + ", ".join(map(str,numeric[:12])) + "**." if numeric else "No numeric measures were detected."
    if any(k in q for k in ["data quality","quality","clean","reliable"]):
        total=int(miss.sum()); cols=int((miss>0).sum())
        return f"Data quality overview: **{total:,} missing cells** across **{cols:,} columns**. The most affected column is **{miss.index[0]}**." if total else "Data quality overview: **no missing cells detected**."
    cols=list(df.columns)
    matches=[]
    for c in cols:
        n=str(c).lower()
        if n in q or any(tok in n.split() for tok in re.findall(r"[a-z0-9_]+",q) if len(tok)>3): matches.append(c)
    numeric=[c for c in cols if pd.api.types.is_numeric_dtype(df[c]) or to_numeric_series(df[c]).notna().mean()>=.8]
    chosen=matches[0] if matches else None
    if not chosen:
        for c in numeric:
            n=str(c).lower().replace("_"," ")
            if any(k in q for k in n.split() if len(k)>3): chosen=c; break
    if chosen:
        s=to_numeric_series(df[chosen])
        if any(k in q for k in ["average","avg","mean"]): return f"Average of **{chosen}**: **{s.mean():,.2f}**."
        if any(k in q for k in ["median"]): return f"Median of **{chosen}**: **{s.median():,.2f}**."
        if any(k in q for k in ["minimum","min","lowest"]): return f"Minimum of **{chosen}**: **{s.min():,.2f}**."
        if any(k in q for k in ["maximum","max","highest","largest"]):
            idx=s.idxmax(); label=df.loc[idx,chosen] if chosen not in numeric else s.loc[idx]
            return f"Maximum of **{chosen}**: **{s.max():,.2f}**."
        if any(k in q for k in ["count","how many"]): return f"Non-empty values in **{chosen}**: **{s.notna().sum():,}**."
        return f"Total of **{chosen}**: **{s.sum():,.2f}**."
    if any(k in q for k in ["rows","records","observations"]): return f"The dataset contains **{len(df):,} rows**."
    if any(k in q for k in ["columns","fields"]): return f"The dataset contains **{len(df.columns):,} columns**."
    if any(k in q for k in ["missing","null","blank"]):
        miss=df.isna().sum().sort_values(ascending=False)
        if miss.iloc[0]==0:return "There are **no missing values**."
        return f"Most missing values are in **{miss.index[0]}**: **{int(miss.iloc[0]):,}** cells."
    if any(k in q for k in ["unique","distinct"]):
        if chosen:return f"Unique values in **{chosen}**: **{df[chosen].nunique(dropna=True):,}**."
        return "Please mention a column name for a unique-count question."
    return "I can answer deterministic questions about totals, averages, minimums, maximums, counts, unique values, missing data, rows and columns. Try: **What is the average Units Ordered?**"
