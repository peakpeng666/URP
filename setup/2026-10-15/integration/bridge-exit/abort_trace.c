// Diagnostic only: print a native backtrace when the process aborts, then re-raise.
#define _GNU_SOURCE
#include <execinfo.h>
#include <signal.h>
#include <string.h>
#include <unistd.h>
static void on_abort(int sig) {
  void *frames[64];
  int n = backtrace(frames, 64);
  const char hdr[] = "\n=== URP abort_trace: fatal signal backtrace ===\n";
  write(2, hdr, sizeof hdr - 1);
  backtrace_symbols_fd(frames, n, 2);
  signal(sig, SIG_DFL);
  raise(sig);
}
__attribute__((constructor)) static void init(void) {
  void *warm[2];
  backtrace(warm, 2);  // load libgcc unwinder before the heap may be corrupted
  struct sigaction sa; memset(&sa, 0, sizeof sa);
  sa.sa_handler = on_abort; sa.sa_flags = SA_RESETHAND;
  sigaction(SIGABRT, &sa, 0); sigaction(SIGSEGV, &sa, 0);
}
