"""Practical forecasting engine with method selection and validation."""
from __future__ import annotations
import numpy as np
import pandas as pd


def _num(s):
    return pd.to_numeric(s.astype(str).str.replace(",","",regex=False).str.replace("$","",regex=False)
                     .str.replace("₹","",regex=False).str.replace("€","",regex=False).str.replace("£","",regex=False).str.replace("%","",regex=False),errors="coerce")


def _fit_linear(y,h):
    x=np.arange(len(y),dtype=float); slope,intercept=np.polyfit(x,y,1); return intercept+slope*np.arange(len(y),len(y)+h), slope


def _fit_naive(y,h): return np.repeat(y[-1],h), 0.0


def _fit_moving(y,h,window=3): return np.repeat(float(np.mean(y[-min(window,len(y)): ])),h),0.0


def _fit_holt(y,h,alpha=.35,beta=.15):
    level=float(y[0]); trend=float(y[1]-y[0]) if len(y)>1 else 0.0
    for val in y[1:]:
        old=level; level=alpha*val+(1-alpha)*(level+trend); trend=beta*(level-old)+(1-beta)*trend
    return np.array([level+(i+1)*trend for i in range(h)]),trend


def _backtest(y, method, holdout):
    if len(y)<=holdout+3:return float("inf")
    train=y[:-holdout]; actual=y[-holdout:]
    pred,_=method(train,holdout)
    rmse=float(np.sqrt(np.mean((actual-pred)**2)))
    denom=np.where(np.abs(actual)<1e-9,1,np.abs(actual))
    mape=float(np.mean(np.abs((actual-pred)/denom))*100)
    return rmse,mape


def forecast_series(df,date_column,value_column,periods=6,frequency="MS",method="Auto"):
    if periods<1 or periods>36: raise ValueError("Forecast periods must be between 1 and 36.")
    work=df[[date_column,value_column]].copy(); work[date_column]=pd.to_datetime(work[date_column],errors="coerce"); work[value_column]=_num(work[value_column]); work=work.dropna().sort_values(date_column)
    if len(work)<8: raise ValueError("At least 8 valid observations are recommended for a reliable forecast.")
    grouped=work.set_index(date_column)[value_column].resample(frequency).sum().dropna()
    if len(grouped)<6: raise ValueError("At least 6 time periods are required after aggregation.")
    y=grouped.to_numpy(float)
    methods={"Naive":_fit_naive,"Moving average":_fit_moving,"Linear trend":_fit_linear,"Exponential trend":_fit_holt}
    scores={}
    for name,fn in methods.items():
        r=_backtest(y,fn,min(3,max(1,len(y)//5)))
        if isinstance(r,tuple): scores[name]={"rmse":r[0],"mape":r[1]}
    chosen=method if method in methods else min(scores,key=lambda k:scores[k]["rmse"])
    pred,slope=methods[chosen](y,periods)
    # residual uncertainty from a rolling validation error or fitted residuals
    fitted=[]
    if chosen=="Linear trend":
        x=np.arange(len(y)); a,b=np.polyfit(x,y,1); fitted=a+b*x
    elif chosen=="Naive": fitted=np.r_[y[0],y[:-1]]
    elif chosen=="Moving average": fitted=np.array([np.mean(y[max(0,i-3):i]) if i else y[0] for i in range(len(y))])
    else:
        fitted=np.empty(len(y)); level=y[0]; trend=y[1]-y[0]
        fitted[0]=y[0]
        for i,val in enumerate(y[1:],1):
            fitted[i]=level+trend; old=level; level=.35*val+.65*(level+trend); trend=.15*(level-old)+.85*trend
    rmse=float(np.sqrt(np.mean((y-np.asarray(fitted))**2)))
    horizon=np.arange(1,periods+1); band=1.96*rmse*np.sqrt(1+horizon/ max(1,len(y)))
    future_dates=pd.date_range(grouped.index[-1]+pd.tseries.frequencies.to_offset(frequency),periods=periods,freq=frequency)
    fc=pd.DataFrame({"date":future_dates,"prediction":pred,"lower":pred-band,"upper":pred+band})
    trend="upward" if slope>0 else "downward" if slope<0 else "flat"
    return {"history":pd.DataFrame({"date":grouped.index,"value":y}),"forecast":fc,"diagnostics":{"trend":trend,"method":chosen,"rmse":rmse,"observations":len(y),"forecast_periods":periods,"frequency":frequency,"model_scores":scores,"warning":"Forecasts are estimates, not guarantees. External events, seasonality and structural changes can materially change future results."}}
