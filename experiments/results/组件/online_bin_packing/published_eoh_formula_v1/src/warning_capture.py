"""Retain every warning occurrence within an explicit bound; overflow stops work.

Warnings are encoded in the worker JSON result. Tracebacks/other diagnostics use
stderr and must be collected separately by the bounded launcher.
"""
import pathlib,warnings

class WarningBoundError(RuntimeError):pass

class WarningJournal:
    def __init__(self,max_events=12000,max_kinds=32,max_text=1024):
        self.max_events=max_events;self.max_kinds=max_kinds;self.max_text=max_text
        self.kinds=[];self.events=[];self.phase='initialization';self.item_index=None
        self.bound_error=None;self._ctx=None
    def show(self,message,category,filename,lineno,file=None,line=None):
        text=str(message);kind={'category':category.__name__,'module':category.__module__,
            'filename':pathlib.Path(filename).name,'line':int(lineno),'message':text}
        if len(text.encode('utf-8'))>self.max_text:
            self.bound_error='warning text exceeded bound; offending warning not fully retained'
            raise WarningBoundError(self.bound_error)
        try:k=self.kinds.index(kind)
        except ValueError:
            if len(self.kinds)>=self.max_kinds:
                self.bound_error='warning kind count exceeded bound';raise WarningBoundError(self.bound_error)
            k=len(self.kinds);self.kinds.append(kind)
        if len(self.events)>=self.max_events:
            self.bound_error='warning event count exceeded bound';raise WarningBoundError(self.bound_error)
        self.events.append([self.phase,self.item_index,k])
    def __enter__(self):
        self._ctx=warnings.catch_warnings();self._ctx.__enter__()
        warnings.simplefilter('always');warnings.showwarning=self.show;return self
    def __exit__(self,*exc):return self._ctx.__exit__(*exc)
    def payload(self):return {'kinds':self.kinds,'events':self.events,'complete':self.bound_error is None,'bound_error':self.bound_error}
