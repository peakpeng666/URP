#!/usr/bin/env python3
"""Rebuild a bounded diagnostic from official public APT metadata, never raw text.

Does not update APT, install, mark or commit packages.
"""
import argparse, collections, json, pathlib, re
LIMIT=65536
NAME=r'[a-z0-9][a-z0-9+.-]{0,119}'
RELATIONS={'Depends':'depends','PreDepends':'predepends','Conflicts':'conflicts','Breaks':'breaks'}
OPS={'':'any','=':'eq','>=':'ge','<=':'le','>>':'gt','<<':'lt'}
VERSION=re.compile(r'[A-Za-z0-9.+:~\-]{1,120}\Z')


def selected_edges(text):
    """Discard all text except syntactically recognized diagnostic edge identities."""
    found=[]; current=None
    for line in text.splitlines():
        debug=re.match(r'^Broken ('+NAME+r')(?::[a-z0-9]+)? (Depends|PreDepends|Conflicts|Breaks) on ('+NAME+r')(?::[a-z0-9]+)?(?:\s|$)',line)
        normal=re.match(r'^\s+('+NAME+r')(?:\:[a-z0-9]+)?\s*:\s*(Depends|PreDepends|Pre-Depends|Conflicts|Breaks):\s*('+NAME+r')(?::[a-z0-9]+)?(?:\s|$)',line)
        if debug or normal:
            p,r,d=(debug or normal).groups();r=r.replace('Pre-Depends','PreDepends')
            current=p;found.append((p,RELATIONS[r],d))
        else:
            continuation=re.match(r'^\s+(Depends|PreDepends|Pre-Depends|Conflicts|Breaks):\s*('+NAME+r')(?::[a-z0-9]+)?(?:\s|$)',line)
            if continuation and current:
                r,d=continuation.groups();found.append((current,RELATIONS[r.replace('Pre-Depends','PreDepends')],d))
            elif line.strip():current=None
        if len(found)>=200:break
    return list(dict.fromkeys(found))


def official(origin):
    site=origin.site.lower();suite=origin.archive
    return origin.trusted and ((origin.origin=='Ubuntu' and (site=='archive.ubuntu.com' or site.endswith('.archive.ubuntu.com') or site=='security.ubuntu.com') and suite in {'jammy','jammy-updates','jammy-security','jammy-backports'}) or (origin.origin=='ROS' and site=='packages.ros.org' and suite=='jammy'))


def metadata_lookup(cache):
    memo={}
    def lookup(name):
        if name in memo:return memo[name]
        result=[];memo[name]=result
        if not re.fullmatch(NAME,name) or name not in cache:return result
        pkg=cache[name]
        # Select only current candidate/installed records with a public official origin.
        versions=[pkg.candidate,pkg.installed]
        seen=set()
        for v in versions:
            if v is None or v.version in seen:continue
            seen.add(v.version)
            if not VERSION.fullmatch(v.version) or not any(official(o) for o in v.origins):continue
            for typ,relation in RELATIONS.items():
                for group in v.get_dependencies(typ):
                    for dep in group.or_dependencies:
                        if not re.fullmatch(NAME,dep.name) or dep.relation not in OPS:continue
                        if dep.version and not VERSION.fullmatch(dep.version):continue
                        result.append({'package':name,'package_version':v.version,'relation':relation,'dependency':dep.name,'version_relation':OPS[dep.relation],'dependency_version':dep.version})
            # Enumeration membership must also work for packages without dependencies.
            result.append({'package':name,'package_version':v.version,'relation':'membership','dependency':'','version_relation':'any','dependency_version':''})
        return result
    return lookup


def project(text,lookup,roots):
    selected=selected_edges(text)
    reachable=set(roots);todo=collections.deque(roots)
    while todo:
        if len(reachable)>10000:return {'status':'tree_limit','dependencies':[]}
        for edge in lookup(todo.popleft()):
            if edge['relation'] in {'depends','predepends'} and edge['dependency'] not in reachable:
                reachable.add(edge['dependency']);todo.append(edge['dependency'])
    out=[];seen=set()
    for package,relation,dependency in selected:
        if package not in reachable and dependency not in reachable:continue
        if not lookup(dependency):continue
        for edge in lookup(package):
            if edge['relation']!=relation or edge['dependency']!=dependency:continue
            key=tuple(edge.values())
            if key not in seen:seen.add(key);out.append(dict(edge))
            if len(out)==20:return {'status':'verified','dependencies':out}
    return {'status':'verified' if out else 'no_verified_edges','dependencies':out}


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--log',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    result={'status':'metadata_unavailable','dependencies':[]}
    try:
        import apt
        from apt_diagnostic import solver_command
        roots=solver_command(args.source)[6:]  # validates fixed HEAD and exact package manifest
        path=pathlib.Path(args.log)
        if path.is_symlink():raise ValueError('unsafe_log')
        with path.open('rb') as f:
            f.seek(0,2);f.seek(max(0,f.tell()-LIMIT));text=f.read(LIMIT).decode('utf-8',errors='replace')
        result=project(text,metadata_lookup(apt.Cache()),roots)
    except Exception:pass
    pathlib.Path(args.output).write_text(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
