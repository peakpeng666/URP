"""Bounded ordered mathematical warning records; bound failure is explicit."""
import pathlib,warnings
class DiagnosticLimit(RuntimeError):pass
class UnexpectedWarning(RuntimeError):pass
class WarningLog:
 def __init__(self,max_events=12000,max_kinds=32,max_text=1024):
  self.max_events=max_events;self.max_kinds=max_kinds;self.max_text=max_text
  self.current_placement=None;self.current_node=None;self.kinds=[];self.events=[];self.incomplete=None
 def show(self,message,category,filename,lineno,file=None,line=None):
  text=str(message);kind={'category':category.__name__,'module':category.__module__,'file':pathlib.Path(filename).name,'line':int(lineno),'message':text}
  if len(text.encode())>self.max_text:self.incomplete='warning text bound';raise DiagnosticLimit(self.incomplete)
  if kind not in self.kinds:
   if len(self.kinds)>=self.max_kinds:self.incomplete='warning kind bound';raise DiagnosticLimit(self.incomplete)
   self.kinds.append(kind)
  event=[self.current_placement,self.current_node,self.kinds.index(kind)]
  if len(self.events)>=self.max_events:self.incomplete='warning event bound';raise DiagnosticLimit(self.incomplete)
  self.events.append(event)
  if category is not RuntimeWarning or kind['file']!='interpreter.py' or self.current_node is None:raise UnexpectedWarning('unrecognized warning source/category')
 def __enter__(self):
  self.context=warnings.catch_warnings();self.context.__enter__();warnings.simplefilter('always');warnings.showwarning=self.show;return self
 def __exit__(self,*exc):return self.context.__exit__(*exc)
 def payload(self):return {'kinds':self.kinds,'events':self.events,'complete':self.incomplete is None,'incomplete_reason':self.incomplete}
