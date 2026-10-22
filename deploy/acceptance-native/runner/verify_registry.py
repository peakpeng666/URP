#!/usr/bin/env python3
"""Match every mirrored lock integrity against official npm metadata, fail closed."""
import json, pathlib, socket, ssl, sys, time, urllib.error, urllib.parse, urllib.request
MAX_METADATA=1048576

class CheckError(Exception):
    def __init__(self,category,http_status=None,attempts=0):
        self.category=category;self.http_status=http_status;self.attempts=attempts


def fetch_metadata(url,open_url=urllib.request.urlopen,sleep=time.sleep):
    for attempt in range(1,4):
        try:
            with open_url(url,timeout=45) as response:
                final=urllib.parse.urlsplit(response.geturl())
                if final.scheme!='https' or final.hostname!='registry.npmjs.org':raise CheckError('source_not_allowlisted',attempts=attempt)
                raw=response.read(MAX_METADATA+1)
                if len(raw)>MAX_METADATA:raise CheckError('metadata_invalid',attempts=attempt)
                try:value=json.loads(raw)
                except (ValueError,UnicodeError):raise CheckError('metadata_invalid',attempts=attempt)
                if not isinstance(value,dict):raise CheckError('metadata_invalid',attempts=attempt)
                return value,attempt
        except urllib.error.HTTPError as e:
            failure=CheckError('http',e.code,attempt)
            retry=e.code==429 or 500<=e.code<=599
        except (TimeoutError,socket.timeout):
            failure=CheckError('timeout',attempts=attempt);retry=True
        except ssl.SSLError:
            failure=CheckError('tls',attempts=attempt);retry=False
        except urllib.error.URLError as e:
            timeout=isinstance(e.reason,(TimeoutError,socket.timeout))
            failure=CheckError('timeout' if timeout else 'tls' if isinstance(e.reason,ssl.SSLError) else 'network',attempts=attempt);retry=timeout
        if not retry or attempt==3:raise failure
        sleep(2**attempt)


def verify(root,fetch=fetch_metadata):
    result={'phase':'lock_parse','status':'failed','error':'unknown','http_status':None,'mirror_index':None,'attempts':0,'mirror_identities_verified':0}
    try:
        lock=json.loads((pathlib.Path(root)/'src/frontend/package-lock.json').read_text())
        if not isinstance(lock.get('packages'),dict):raise CheckError('lock_invalid')
        for key,pkg in lock['packages'].items():
            result['phase']='source_policy'
            if not isinstance(pkg,dict):raise CheckError('lock_invalid')
            url=pkg.get('resolved')
            if not url:continue
            parsed=urllib.parse.urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname not in {'registry.npmjs.org','registry.npmmirror.com'}:raise CheckError('source_not_allowlisted')
            if parsed.hostname!='registry.npmmirror.com':continue
            result['mirror_index']=result['mirror_identities_verified']+1
            name=key.rsplit('node_modules/',1)[-1]
            version=pkg.get('version');integrity=pkg.get('integrity')
            if not isinstance(version,str) or not isinstance(integrity,str) or not integrity:raise CheckError('lock_invalid')
            url='https://registry.npmjs.org/'+urllib.parse.quote(name,safe='')+'/'+urllib.parse.quote(version,safe='')
            result['phase']='metadata_fetch'
            metadata,attempts=fetch(url);result['attempts']=attempts
            result['phase']='integrity_check'
            dist=metadata.get('dist')
            if not isinstance(dist,dict) or dist.get('integrity')!=integrity:raise CheckError('integrity_mismatch',attempts=attempts)
            official=urllib.parse.urlsplit(dist.get('tarball',''))
            if official.scheme!='https' or official.hostname!='registry.npmjs.org' or official.username or official.password or official.query or official.fragment or parsed.query or parsed.fragment or urllib.parse.unquote(official.path)!=urllib.parse.unquote(parsed.path):
                raise CheckError('tarball_path_mismatch',attempts=attempts)
            result['mirror_identities_verified']+=1
        result.update(phase='complete',status='passed',error='none',http_status=None,mirror_index=None)
    except CheckError as e:
        result.update(error=e.category,http_status=e.http_status,attempts=e.attempts)
    except (ValueError,TypeError,KeyError,OSError):
        result['error']='lock_invalid' if result['phase']=='lock_parse' else 'unknown'
    except Exception:pass
    return result

if __name__=='__main__':
    result=verify(sys.argv[1]);print(json.dumps(result,sort_keys=True));sys.exit(0 if result['status']=='passed' else 1)
