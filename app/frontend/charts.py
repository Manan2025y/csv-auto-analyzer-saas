"""Reusable chart engine for CSV Auto-Analyzer."""
from __future__ import annotations
import uuid
import pandas as pd
import plotly.express as px

CHART_TYPES = [
    "Bar Chart", "Line Chart", "Area Chart", "Scatter Chart", "Pie Chart",
    "Donut Chart", "Treemap", "Histogram", "Box Plot", "Funnel", "Table", "Card"
]

CHART_PALETTES = {
    "Professional": ["#2563EB", "#0F766E", "#7C3AED", "#EA580C", "#DC2626", "#0891B2"],
    "Ocean": ["#075985", "#0284C7", "#0891B2", "#0E7490", "#155E75", "#164E63"],
    "Business": ["#172554", "#1E3A8A", "#334155", "#475569", "#0F766E", "#365314"],
    "Warm": ["#9A3412", "#C2410C", "#B45309", "#A16207", "#BE123C", "#9F1239"],
    "Bright": ["#E11D48", "#F97316", "#EAB308", "#16A34A", "#06B6D4", "#2563EB", "#7C3AED"],
    "Purple": ["#4C1D95", "#6D28D9", "#7C3AED", "#9333EA", "#A21CAF", "#4338CA"],
    "Forest": ["#14532D", "#166534", "#15803D", "#0F766E", "#365314", "#4D7C0F"],
    "Sunset": ["#7C2D12", "#C2410C", "#EA580C", "#F59E0B", "#E11D48", "#BE123C"],
    "Neon": ["#22C55E", "#06B6D4", "#3B82F6", "#8B5CF6", "#EC4899", "#F97316"],
    "Pastel": ["#93C5FD", "#86EFAC", "#FDE68A", "#FDBA74", "#F9A8D4", "#C4B5FD"],
    "Berry": ["#831843", "#BE185D", "#DB2777", "#EC4899", "#9D174D", "#701A75"],
    "Earth": ["#3F2A1D", "#6B4F3A", "#8B6F47", "#A16207", "#4D7C0F", "#365314"],
    "Cobalt": ["#172554", "#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#1E40AF"],
    "Aurora": ["#064E3B", "#0F766E", "#0891B2", "#4F46E5", "#7C3AED", "#C026D3"],
    "Monochrome": ["#111827", "#374151", "#4B5563", "#6B7280", "#9CA3AF", "#D1D5DB"],
    "Teal": ["#134E4A", "#115E59", "#0F766E", "#0D9488", "#14B8A6", "#2DD4BF"],
}


def numeric_columns(df, threshold=0.80):
    out=[]
    for c in df.columns:
        s=df[c]
        if pd.api.types.is_numeric_dtype(s): out.append(c)
        else:
            cleaned=(s.astype(str).str.replace(",","",regex=False).str.replace("$","",regex=False)
                     .str.replace("₹","",regex=False).str.replace("€","",regex=False).str.replace("£","",regex=False)
                     .str.replace("%","",regex=False))
            if pd.to_numeric(cleaned, errors="coerce").notna().mean() >= threshold: out.append(c)
    return out


def numeric_series(s):
    return pd.to_numeric(s.astype(str).str.replace(",","",regex=False).str.replace("$","",regex=False)
                         .str.replace("₹","",regex=False).str.replace("€","",regex=False)
                         .str.replace("£","",regex=False).str.replace("%","",regex=False), errors="coerce")


def date_columns(df, threshold=0.80):
    out=[]
    for c in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[c]): out.append(c); continue
        parsed=pd.to_datetime(df[c], errors="coerce")
        if parsed.notna().mean() >= threshold: out.append(c)
    return out


def prepare_chart_data(df, item, global_filters=None):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy()
    filters=dict(global_filters or {})
    if item.get("filter_column") and item.get("filter_value") not in (None,"","All"):
        filters[item["filter_column"]]=item["filter_value"]
    for col,val in filters.items():
        if col in out.columns and val not in (None,"","All"):
            if isinstance(val,list): out=out[out[col].astype(str).isin([str(x) for x in val])]
            else: out=out[out[col].astype(str)==str(val)]
    dc=item.get("date_column")
    if dc and dc in out.columns:
        dates=pd.to_datetime(out[dc],errors="coerce")
        if item.get("date_start") is not None: out=out[dates.dt.date>=item["date_start"]]
        if item.get("date_end") is not None: out=out[dates.dt.date<=item["date_end"]]
    sc=item.get("sort_column")
    if sc and sc in out.columns:
        temp=numeric_series(out[sc]) if sc in numeric_columns(out) else out[sc]
        out=out.loc[temp.sort_values(ascending=item.get("sort_direction") == "Ascending",na_position="last").index]
    y=item.get("y")
    if item.get("ranking") in ("Top N","Bottom N") and y in out.columns and item.get("n"):
        temp=out.copy(); temp["__v"]=numeric_series(temp[y])
        temp=temp.nlargest(int(item["n"]),"__v") if item["ranking"]=="Top N" else temp.nsmallest(int(item["n"]),"__v")
        out=temp.drop(columns="__v")
    return out


def create_chart(df, item, height=380):
    if df is None or df.empty: return None
    typ=item.get("type"); x=item.get("x"); y=item.get("y"); title=item.get("title","Chart")
    palette=CHART_PALETTES.get(item.get("color","Professional"),CHART_PALETTES["Professional"])
    bg=item.get("background")
    if typ=="Table":
        return None
    if typ=="Card":
        if not y: return None
        val=numeric_series(df[y]).sum()
        fig=px.indicator if False else px.scatter(pd.DataFrame({"x":[0],"y":[0]}),x="x",y="y",title=title)
        fig.update_traces(marker_size=0, hoverinfo="skip")
        fig.add_annotation(x=0,y=0,text=f"{val:,.2f}",showarrow=False,font=dict(size=34))
    elif typ=="Histogram":
        if not x:return None
        temp=df.copy(); temp[x]=numeric_series(temp[x]); fig=px.histogram(temp,x=x,title=title,color_discrete_sequence=palette)
    elif typ in ("Pie Chart","Donut Chart"):
        if not x:return None
        temp=df.copy()
        if y:
            temp[y]=numeric_series(temp[y]); fig=px.pie(temp,names=x,values=y,hole=.58 if typ=="Donut Chart" else 0,color_discrete_sequence=palette,title=title)
        else:
            counts=temp[x].astype(str).value_counts().reset_index(); counts.columns=[x,"Count"]
            fig=px.pie(counts,names=x,values="Count",hole=.58 if typ=="Donut Chart" else 0,color_discrete_sequence=palette,title=title)
    elif typ=="Treemap":
        if not x:return None
        temp=df.copy(); val=y or "__count__"
        if y: temp[y]=numeric_series(temp[y])
        else: temp["__count__"]=1
        fig=px.treemap(temp,path=[x],values=val,color_discrete_sequence=palette,title=title)
    elif typ=="Funnel":
        if not x or not y:return None
        temp=df.copy(); temp[y]=numeric_series(temp[y]); grouped=temp.groupby(x,dropna=False)[y].sum().reset_index().sort_values(y,ascending=False)
        fig=px.funnel(grouped,x=y,y=x,title=title)
    elif typ in ("Bar Chart","Line Chart","Area Chart","Scatter Chart"):
        if not x or not y:return None
        temp=df.copy(); temp[y]=numeric_series(temp[y])
        fn={"Bar Chart":px.bar,"Line Chart":px.line,"Area Chart":px.area,"Scatter Chart":px.scatter}[typ]
        fig=fn(temp,x=x,y=y,title=title,color_discrete_sequence=palette)
        if typ=="Line Chart": fig.update_traces(mode="lines+markers")
    elif typ=="Box Plot":
        if not y:return None
        temp=df.copy(); temp[y]=numeric_series(temp[y]); fig=px.box(temp,x=x if x else None,y=y,title=title,color_discrete_sequence=palette)
    else:return None
    fig.update_layout(title={"text":title,"x":.02},margin=dict(l=25,r=20,t=55,b=25),height=height,
                      paper_bgcolor=bg or "rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                      font_color=item.get("font_color"),legend_title_text="",hovermode="x unified")
    return fig


def automatic_chart_suggestions(df, minimum=8):
    nums=numeric_columns(df); dates=date_columns(df); cats=[c for c in df.columns if c not in nums and c not in dates]
    out=[]
    if dates and nums: out.append({"id":"auto_1","type":"Line Chart","title":f"{nums[0]} Trend","x":dates[0],"y":nums[0],"color":"Professional"})
    if cats and nums: out.append({"id":"auto_2","type":"Bar Chart","title":f"{nums[0]} by {cats[0]}","x":cats[0],"y":nums[0],"color":"Ocean","ranking":"Top N","n":10})
    if len(nums)>=2: out.append({"id":"auto_3","type":"Scatter Chart","title":f"{nums[0]} vs {nums[1]}","x":nums[0],"y":nums[1],"color":"Purple"})
    if cats: out.append({"id":"auto_4","type":"Donut Chart","title":f"{cats[0]} Mix","x":cats[0],"y":nums[0] if nums else None,"color":"Teal"})
    if dates and len(nums)>=2: out.append({"id":"auto_5","type":"Area Chart","title":f"{nums[1]} Over Time","x":dates[0],"y":nums[1],"color":"Forest"})
    if nums: out.append({"id":"auto_6","type":"Histogram","title":f"{nums[0]} Distribution","x":nums[0],"y":None,"color":"Sunset"})
    if cats and nums: out.append({"id":"auto_7","type":"Treemap","title":f"{nums[0]} by {cats[0]}","x":cats[0],"y":nums[0],"color":"Bright"})
    if cats and nums: out.append({"id":"auto_8","type":"Funnel","title":f"{cats[0]} Funnel","x":cats[0],"y":nums[0],"color":"Business"})
    if nums: out.append({"id":"auto_9","type":"Box Plot","title":f"{nums[0]} Spread","x":cats[0] if cats else None,"y":nums[0],"color":"Monochrome"})
    while len(out)<minimum:
        out.append({"id":f"empty_{uuid.uuid4().hex[:8]}","type":"Bar Chart","title":"New Chart","x":None,"y":None,"color":"Professional"})
    return out


def build_chart(df,item,global_filters=None):
    return create_chart(prepare_chart_data(df,item,global_filters),item)
