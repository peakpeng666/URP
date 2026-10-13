"""Closed, data-only pickle opcode interpreter. No Unpickler/load/eval/import of inputs."""
import ast, collections, hashlib, json, pathlib, pickletools
ROOT=pathlib.Path(__file__).resolve().parents[1]
MAX_BYTES=200_000
MARK=object()
def decode_numeric_pickle(raw):
    if type(raw) is not bytes or len(raw)>MAX_BYTES: raise ValueError('pickle byte bound')
    stack=[]; counts=collections.Counter(); frames=[]; memo=0; stopped=False
    for i,(op,arg,pos) in enumerate(pickletools.genops(raw)):
        if i>60_000 or len(stack)>10_100: raise ValueError('opcode/stack bound')
        name=op.name;counts[name]+=1
        if name=='PROTO':
            if pos!=0 or arg!=4: raise ValueError('protocol must be 4')
        elif name=='FRAME':
            if arg<0 or pos+9+arg>len(raw): raise ValueError('frame bound')
            frames.append((pos+9,pos+9+arg))
        elif name=='EMPTY_DICT': stack.append({})
        elif name=='EMPTY_LIST': stack.append([])
        elif name in ('BININT1','BININT2'):
            if type(arg) is not int or not 0<=arg<=10000: raise ValueError('integer bound')
            stack.append(arg)
        elif name=='MARK': stack.append(MARK)
        elif name=='MEMOIZE':
            if not stack or stack[-1] is MARK or memo>=10: raise ValueError('memo bound')
            memo+=1  # No read/reuse opcodes are admitted; no cycles or aliases possible.
        elif name=='APPENDS':
            k=len(stack)-1
            while k>=0 and stack[k] is not MARK:k-=1
            if k<1 or type(stack[k-1]) is not list: raise ValueError('APPENDS target')
            vals=stack[k+1:]
            if len(stack[k-1])+len(vals)>10000: raise ValueError('list bound')
            stack[k-1].extend(vals);del stack[k:]
        elif name=='SETITEM':
            if len(stack)<3 or type(stack[-3]) is not dict or type(stack[-2]) is not int:raise ValueError('SETITEM shape')
            value=stack.pop();key=stack.pop()
            if key in stack[-1] or len(stack[-1])>=1:raise ValueError('dictionary bound/duplicate')
            stack[-1][key]=value
        elif name=='STOP':
            if pos!=len(raw)-1 or len(stack)!=1:raise ValueError('trailing bytes/stack')
            stopped=True
        else: raise ValueError('unsupported opcode: '+name)
    if not stopped or counts['PROTO']!=1 or not frames:raise ValueError('incomplete pickle')
    # Protocol frames must tile all payload bytes, excluding subsequent FRAME headers.
    if frames[0][0]!=11 or frames[-1][1]!=len(raw):raise ValueError('frame coverage')
    for a,b in zip(frames,frames[1:]):
        if a[1]+9!=b[0]:raise ValueError('frame gap')
    return stack[0],dict(counts)

def literal(node,depth=0):
    if depth>8:raise ValueError('literal depth')
    if type(node) is ast.Constant and type(node.value) in (str,int):return node.value
    if type(node) is ast.List and len(node.elts)<=10000:return [literal(v,depth+1) for v in node.elts]
    if type(node) is ast.Dict and len(node.keys)<=10:
        out={}
        for k,v in zip(node.keys,node.values):
            key=literal(k,depth+1)
            if type(key) not in (str,int) or key in out:raise ValueError('literal key')
            out[key]=literal(v,depth+1)
        return out
    raise ValueError('nonliteral AST '+type(node).__name__)

def embedded_data(raw):
    if len(raw)>200000:raise ValueError('source bound')
    tree=ast.parse(raw)
    matches=[]
    for node in ast.walk(tree):
        if type(node) is ast.Assign and len(node.targets)==1:
            t=node.targets[0]
            if (type(t) is ast.Subscript and type(t.value) is ast.Attribute and t.value.attr=='datasets'
                and type(t.value.value) is ast.Name and t.value.value.id=='self'
                and type(t.slice) is ast.Constant and t.slice.value=='Weibull 5k'):
                matches.append(literal(node.value))
    if len(matches)!=1:raise ValueError('embedded assignment count')
    return matches[0]

def hash_json(value):return hashlib.sha256(json.dumps(value,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
def validate_lists(d,n):
    if type(d) is not dict or list(d)!=[n] or type(d[n]) is not list or len(d[n])!=5:raise ValueError('dataset schema')
    for items in d[n]:
        if type(items) is not list or len(items)!=n or any(type(v) is not int or not 1<=v<=100 for v in items):raise ValueError('item schema')
    return d[n]

def prepare():
    provenance=json.loads((ROOT/'upstream/provenance.json').read_text()); verified={r['path']:r for r in provenance['files']}
    def read(path):
        raw=(ROOT/'upstream'/path).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=verified[path]['sha256']:raise ValueError('source hash mismatch')
        return raw
    sets={};reports={}
    for name,n in [('test_dataset_1k',1000),('test_dataset_5k',5000),('test_dataset_10k',10000),('training_dataset_5k',5000)]:
        d,ops=decode_numeric_pickle(read(f'examples/bp_online/testingdata/{name}.pkl'))
        sets[name]=validate_lists(d,n);reports[name]={'opcodes':ops,'n':n,'count':5,'decoded_type':'dict[int,list[list[exact Python int]]]','instance_item_hashes':[hash_json(x) for x in sets[name]],'minimum':min(map(min,sets[name])),'maximum':max(map(max,sets[name])),'content_sha256':hash_json(d)}
    emb=embedded_data(read('examples/bp_online/get_instance.py'))
    if len(emb)!=5:raise ValueError('embedded count')
    lists=[];caps=[]
    for k,v in emb.items():
        if set(v)!= {'capacity','num_items','items'} or v['num_items']!=5000 or type(v['capacity']) is not int:raise ValueError('embedded schema')
        validate_lists({5000:[v['items']]*5},5000);lists.append(v['items']);caps.append(v['capacity'])
    sets['embedded_design_5k']=lists
    reports['embedded_design_5k']={'n':5000,'count':5,'keys':list(emb),'literal_capacities':caps,'effective_get_instances_capacity':100,'instance_item_hashes':[hash_json(x) for x in lists]}
    comparisons=[]
    for i,a in enumerate(sets):
        for b in list(sets)[i+1:]:
            matches=[{'left':j,'right':k} for j,x in enumerate(sets[a]) for k,y in enumerate(sets[b]) if x==y]
            prefixes=[{'left':j,'right':k,'prefix_length':min(len(x),len(y))} for j,x in enumerate(sets[a]) for k,y in enumerate(sets[b]) if len(x)!=len(y) and x[:min(len(x),len(y))]==y[:min(len(x),len(y))]]
            comparisons.append({'left':a,'right':b,'exact_matches':matches,'whole_shorter_sequence_prefix_matches':prefixes})
    records=[]
    for name in ['test_dataset_1k','test_dataset_5k','test_dataset_10k']:
        for i,items in enumerate(sets[name]):records.append({'id':f'{name}_{i}','source_set':name,'source_index':i,'n':len(items),'items':items,'items_sha256':hash_json(items)})
    for name,content in [('numeric_datasets.json',{'sets':sets}),('instances.json',{'instances':records}),('data_audit.json',{'commit':provenance['commit'],'sets':reports,'comparisons':comparisons,'note':'Exact sequence and full-shorter-prefix comparisons do not establish statistical independence; all data are public development/reproduction evidence.'})]:
        with (ROOT/'data'/name).open('x') as f:json.dump(content,f,indent=2);f.write('\n')
    print(json.dumps({'sets':reports,'comparisons':comparisons},indent=2))
if __name__=='__main__':prepare()
