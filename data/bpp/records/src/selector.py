"""Prefix-only selector. This module has no filesystem, RNG, stream, or metadata access."""
import numpy as np
K=5
BRANCHES=('BF','BF_then_EoH')
FEATURE_NAMES=tuple([f'item_hist_{10*i+1}_{10*i+10}' for i in range(10)]+['item_mean','item_sd','item_q10','item_q50','item_q90','fraction_increase','fraction_decrease','last100_minus_first100','bins_per_item']+[f'residual_hist_{10*i}_{10*i+9}' for i in range(10)]+['residual_mean','residual_sd'])

def features(prefix, remaining):
    assert len(prefix)==500 and len(remaining)==5000
    p=np.asarray(prefix,dtype=np.int64); r=np.asarray(remaining,dtype=np.int64)
    assert np.all((p>=1)&(p<=100)) and np.all((r>=0)&(r<=100))
    used=r[r<100]; assert len(used)>0
    item_hist=np.bincount((p-1)//10,minlength=10)/500
    qs=np.quantile(p,[.1,.5,.9],method='linear')/100
    d=np.diff(p)
    residual_hist=np.bincount(used//10,minlength=10)/len(used)
    f=np.r_[item_hist,[np.mean(p)/100,np.std(p,ddof=0)/100],qs,[np.mean(d>0),np.mean(d<0),(np.mean(p[-100:])-np.mean(p[:100]))/100,len(used)/500],residual_hist,[np.mean(used)/100,np.std(used,ddof=0)/100]]
    assert len(f)==31 and np.all(np.isfinite(f))
    return f

def fit(x,y):
    x=np.asarray(x,dtype=np.float64); y=np.asarray(y,dtype=np.float64)
    assert x.shape==(144,31) and y.shape==(144,2)
    mu=x.mean(0); sd=x.std(0,ddof=0); sd=np.where(sd==0,1.,sd)
    sbs=int(np.argmin(y.mean(0)))
    return {'mean':mu.tolist(),'scale':sd.tolist(),'x':((x-mu)/sd).tolist(),'y':y.tolist(),'sbs_index':sbs,'k':K}

def choose(prefix,remaining,model):
    f=features(prefix,remaining)
    z=(f-np.asarray(model['mean']))/np.asarray(model['scale'])
    d=np.sum((np.asarray(model['x'])-z)**2,axis=1)
    neighbors=np.argsort(d,kind='stable')[:K]
    costs=np.asarray(model['y'])[neighbors].mean(axis=0)
    index=int(model['sbs_index']) if costs[0]==costs[1] else int(np.argmin(costs))
    return BRANCHES[index],{'features':f.tolist(),'neighbors':neighbors.tolist(),'squared_distances':d[neighbors].tolist(),'predicted_final_bins':costs.tolist(),'selected_index':index}
