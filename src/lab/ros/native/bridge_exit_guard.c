/*
 * Project-local exit guard for ros_gz_bridge parameter_bridge (Humble 0.244.26).
 * Reproduced defect: after main() has returned normally (SIGINT handled, node destroyed),
 * libc's exit handlers abort in free() with "corrupted unsorted chunks" (~4% of exits).
 * For the parameter_bridge executable only, flush stdio and _exit() with main's status,
 * skipping process-exit teardown. Every other executable is passed through untouched.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define TARGET "/opt/ros/humble/lib/ros_gz_bridge/parameter_bridge"

typedef int (*main_fn)(int, char **, char **);
typedef int (*start_fn)(main_fn, int, char **, void *, void *, void *, void *);
static main_fn real_main;

static int guarded_main(int argc, char **argv, char **envp) {
  int status = real_main(argc, argv, envp);
  fflush(NULL);
  _exit(status);
}

int __libc_start_main(main_fn main, int argc, char **argv, void *init, void *fini, void *rtld_fini, void *stack_end) {
  start_fn real = (start_fn)dlsym(RTLD_NEXT, "__libc_start_main");
  char exe[PATH_MAX];
  ssize_t n = readlink("/proc/self/exe", exe, sizeof exe - 1);
  if (n > 0) {
    exe[n] = '\0';
    if (strcmp(exe, TARGET) == 0) {
      real_main = main;
      main = guarded_main;
    }
  }
  return real(main, argc, argv, init, fini, rtld_fini, stack_end);
}
