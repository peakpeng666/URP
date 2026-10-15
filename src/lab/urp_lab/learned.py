"""Small, auditable kNN selector for a newly measured local CVRP portfolio.

The frozen historical study is not restored or modified. This model has its own
independent training/calibration/test split and narrow deployment scope.
"""
import hashlib
import json
import math
import statistics as stats
from . import paths
paths.ensure_research_path()
from urp_research.cvrp_selection.experiment import features, crc, route

ALGOS = ['pyvrp.hgs','ortools.gls']
MODEL = paths.LAB/'models/cvrp-knn-v1.json'
BUDGET = .25


def fit(records):
    cols=list(zip(*(r['features']['values'] for r in records)))
    mu=list(map(stats.mean,cols));sd=[stats.pstdev(c) or 1 for c in cols]
    means={a:stats.mean(r['costs'][a]/r['features']['star_upper_bound'] for r in records) for a in ALGOS}
    return dict(k=3,mu=mu,sd=sd,sbs=min(ALGOS,key=lambda a:(means[a],a)),train_means=means,
        train=[dict(id=r['id'],scaled=[(x-m)/s for x,m,s in zip(r['features']['values'],mu,sd)],
                    targets={a:r['costs'][a]/r['features']['star_upper_bound'] for a in ALGOS}) for r in records])


def predict(model,instance):
    values=features(instance)['values'];scaled=[(v-m)/s for v,m,s in zip(values,model['mu'],model['sd'])]
    neighbors=sorted(model['train'],key=lambda r:(math.dist(r['scaled'],scaled),r['id']))[:model['k']]
    costs={a:stats.mean(r['targets'][a] for r in neighbors) for a in ALGOS}
    selected=min(ALGOS,key=lambda a:(costs[a],a));sbs=model['sbs']
    return dict(chosen=selected,sbs=sbs,score=(costs[sbs]-costs[selected])/costs[sbs],predicted_costs=costs,
                neighbor_ids=[r['id'] for r in neighbors])


def build(records):
    train=[r for r in records if r['split']=='train'];cal=[r for r in records if r['split']=='calibration']
    model=fit(train);predictions=[]
    for r in cal:
        p=predict(model,r['instance']);p['harm']=r['costs'][p['chosen']]>1.01*r['costs'][p['sbs']];predictions.append(p)
    return dict(model=model,gate=crc(predictions,.1),calibration_predictions=predictions)


def recommend(scenario,instance):
    if scenario['problem_class']!='euclidean_cvrp':return None
    unavailable=dict(id='lab.cvrp.knn_crc.v1',status='unavailable',reason='本地训练及独立评估产物尚未生成',prediction=None,required=[str(MODEL)])
    if not MODEL.is_file():return unavailable
    try:
        document=json.loads(MODEL.read_text())
        if document['status']!='evaluated':return unavailable
        payload=json.dumps(document['artifact'],sort_keys=True,separators=(',',':')).encode()
        if hashlib.sha256(payload).hexdigest()!=document['artifact_sha256']:raise ValueError('模型指纹不匹配')
        n=len(instance['demands'])-1
        if scenario['frame']['kind']!='benchmark' or n not in (20,50,100) or instance['capacity']!=50 or any(d<1 or d>10 for d in instance['demands'][1:]):
            return dict(unavailable,status='out_of_scope',reason='已训练原型仅评估无量纲欧氏 CVRP：20/50/100 客户、容量 50、需求 1–10；当前实例回退规则')
        p=predict(document['artifact']['model'],instance);selected,accepted=route(p,document['artifact']['gate'])
        return dict(id='lab.cvrp.knn_crc.v1',status='available',reason='独立合成样本评估的实验原型；0.25 s/算法、2 次重复（PyVRP 种子 11/29，OR-Tools 未使用种子）。测试集全部回退 PyVRP，未证明推荐增益。历史研究数据未恢复。',
            prediction=dict(**p,selected=selected,accepted_alternative=accepted),model_sha256=document['artifact_sha256'],
            evaluation=document['evaluation'],budget_s=BUDGET,required=[],scope='均匀/聚簇生成分布；同规模参数不等于同分布，外推未经验证')
    except Exception as exc:return dict(unavailable,reason='模型不可用：'+str(exc))
