import json, unittest
from types import SimpleNamespace as S
from runner.apt_projection import selected_edges, metadata_lookup, project, official

def version(name='1.0',site='archive.ubuntu.com',trusted=True,origin='Ubuntu',edges=()):
    def deps(typ):return [S(or_dependencies=[S(name=d,relation=op,version=v)]) for t,d,op,v in edges if t==typ]
    return S(version=name,origins=[S(site=site,trusted=trusted,origin=origin,archive='jammy')],get_dependencies=deps)

def pkg(v):return S(candidate=v,installed=None)

class ProjectionTests(unittest.TestCase):
    def test_rebuilds_only_verified_public_fields(self):
        cache={'root':pkg(version(edges=[('Depends','lib-a','>=','1.0')])),'lib-a':pkg(version())}
        text=' root : Depends: lib-a (>= PRIVATE_VERSION) but PRIVATE_URL is to be installed\n'
        out=project(text,metadata_lookup(cache),['root'])
        self.assertEqual(out['status'],'verified')
        self.assertEqual(out['dependencies'],[{'package':'root','package_version':'1.0','relation':'depends','dependency':'lib-a','version_relation':'ge','dependency_version':'1.0'}])
        self.assertNotIn('PRIVATE',json.dumps(out))
    def test_unverified_edge_and_private_origin_dropped(self):
        cache={'root':pkg(version(edges=[('Depends','private-a','','')])),'private-a':pkg(version(site='private.invalid'))}
        self.assertEqual(project('Broken root:amd64 Depends on private-a:amd64',metadata_lookup(cache),['root'])['dependencies'],[])
        self.assertEqual(project('Broken root:amd64 Depends on unknown:amd64',metadata_lookup(cache),['root'])['dependencies'],[])
        self.assertFalse(official(S(trusted=False,origin='Ubuntu',site='archive.ubuntu.com',archive='jammy')))
    def test_conflict_and_tree_scope(self):
        cache={'root':pkg(version(edges=[('Depends','lib-a','','')])),'lib-a':pkg(version()),'lib-slot':pkg(version(edges=[('Conflicts','lib-a','','')])),'unrelated':pkg(version(edges=[('Depends','other','','')])),'other':pkg(version())}
        text='Broken lib-slot:amd64 Conflicts on lib-a:amd64\nBroken unrelated:amd64 Depends on other:amd64'
        out=project(text,metadata_lookup(cache),['root'])
        self.assertEqual(len(out['dependencies']),1);self.assertEqual(out['dependencies'][0]['relation'],'conflicts')
    def test_cap_and_no_arbitrary_text(self):
        cache={'root':pkg(version(edges=[('Depends','lib-'+str(i),'','') for i in range(30)]))}
        cache.update({'lib-'+str(i):pkg(version()) for i in range(30)})
        text='\n'.join('Broken root:amd64 Depends on lib-'+str(i)+':amd64' for i in range(30))
        self.assertEqual(len(project(text,metadata_lookup(cache),['root'])['dependencies']),20)
        self.assertEqual(selected_edges('PRIVATE_PATH URL command user experiment'),[])
    def test_relation_mismatch_and_forged_version_dropped(self):
        cache={'root':pkg(version(name='PRIVATE/PATH',edges=[('Depends','dep','','')])),'dep':pkg(version())}
        self.assertEqual(project('Broken root:amd64 Depends on dep:amd64',metadata_lookup(cache),['root'])['dependencies'],[])
        cache['root']=pkg(version(edges=[('Depends','dep','','')]))
        self.assertEqual(project('Broken root:amd64 Conflicts on dep:amd64',metadata_lookup(cache),['root'])['dependencies'],[])

if __name__=='__main__':unittest.main()
