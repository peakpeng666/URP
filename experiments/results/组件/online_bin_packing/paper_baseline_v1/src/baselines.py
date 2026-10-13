"""Handwritten FF/BF only; exact integer equivalents of the pinned scoring rules.
This trusted native module is NOT an untrusted-program execution interface.
"""
def validate_input(items, capacity):
    if type(capacity) is not int or not 1<=capacity<=500:raise ValueError('capacity')
    if type(items) is not list or len(items)>10000:raise ValueError('items')
    if any(type(x) is not int or not 1<=x<=capacity for x in items):raise ValueError('item type/range')

def feasible_indices(item, residuals):
    # Includes every unused preallocated bin, in original stable index order.
    return [j for j,space in enumerate(residuals) if space-item>=0]

def choose(item, residuals, method):
    indices=feasible_indices(item,residuals)
    if not indices:raise ValueError('no feasible bin')
    if method=='FF':
        # argmax(-arange(len(feasible))) = first feasible index.
        return indices[0],len(indices)
    if method=='BF':
        # argmax(-(feasible residual-item)) = first minimum residual.
        return min(indices,key=residuals.__getitem__),len(indices)
    raise ValueError('unsupported method')

def pack(items, capacity, method):
    validate_input(items,capacity)
    if method not in ('FF','BF'):raise ValueError('unsupported method')
    residuals=[capacity]*len(items);assignment=[];feasible_counts=[]
    for item in items:
        selected,count=choose(item,residuals,method)
        residuals[selected]-=item;assignment.append(selected);feasible_counts.append(count)
    return {'assignment':assignment,'residuals':residuals,'used_bins':sum(r!=capacity for r in residuals),'feasible_counts':feasible_counts,'n_bin_feasibility_checks':len(items)**2}
