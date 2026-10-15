"""One request on stdin, one result on stdout; native solver output stays in the raw log."""
import contextlib
import json
import sys
import traceback
import signal
from .solvers import run_algorithm

def main():
    try:
        request = json.load(sys.stdin)
        def expired(*_):
            raise TimeoutError('求解计算超过 time_limit_s；工作进程已中止')
        signal.signal(signal.SIGALRM, expired)
        if request['algorithm_id'].startswith('urp.'):
            signal.setitimer(signal.ITIMER_REAL, float(request['params'].get('time_limit_s', 3)))
        with contextlib.redirect_stdout(sys.stderr):
            result = run_algorithm(request['scenario'], request['instance'], request['algorithm_id'], request['params'])
        signal.setitimer(signal.ITIMER_REAL, 0)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
        return 0
    except Exception as exc:
        signal.setitimer(signal.ITIMER_REAL, 0)
        traceback.print_exc(file=sys.stderr)
        print(json.dumps({'error': f'{type(exc).__name__}: {exc}', 'error_kind': 'timeout' if isinstance(exc, TimeoutError) else 'solver_error'}, ensure_ascii=False))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
