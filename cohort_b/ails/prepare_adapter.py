from pathlib import Path
import shutil,difflib
root=Path(__file__).resolve().parent;src=root/'original';dst=root/'adapted'
if dst.exists():raise SystemExit('refuse overwrite')
shutil.copytree(src,dst);patch=[]
for p in (dst/'src').rglob('*.java'):
 old=p.read_text();s=old.replace('new Random()', 'Adapter.SeededRandom.next("'+str(p.relative_to(dst)).replace('/','.')+'")')
 if p.name=='AILSII.java':
  s=s.replace('bestSolution.clone(referenceSolution);','bestSolution.clone(referenceSolution);\n        Adapter.Observer.emit(bestSolution);')
  s=s.replace('bestSolution.clone(solution);','bestSolution.clone(solution);\n            Adapter.Observer.emit(bestSolution);')
 if s!=old:
  p.write_text(s);patch+=list(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='original/'+str(p.relative_to(dst)),tofile='adapted/'+str(p.relative_to(dst))))
(root/'seed_observer.patch').write_text(''.join(patch));(dst/'src/Adapter').mkdir()
