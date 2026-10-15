// Project-local workaround for plugin metadata outliving a dynamically unloaded DSO.
// Restrict RTLD_NODELETE to official GUI plugins used by TurtleBot4's config.
// Objects still run their normal destructors; mappings live until process exit.
#include <dlfcn.h>
#include <cstdio>
#include <cstring>
extern "C" void *dlopen(const char *file, int flags)
{
  using Open = void *(*)(const char *, int);
  static Open original = reinterpret_cast<Open>(dlsym(RTLD_NEXT, "dlopen"));
  if (!original) return nullptr;
  if (file &&
      (!std::strcmp(file, "/opt/ros/humble/share/turtlebot4_ignition_gui_plugins/lib/libTurtlebot4Hmi.so") ||
       !std::strcmp(file, "/opt/ros/humble/lib/librviz_default_plugins.so") ||
       !std::strcmp(file, "/opt/ros/humble/lib/libnav2_rviz_plugins.so"))) {
    flags |= RTLD_NODELETE;
    std::fprintf(stderr, "URP plugin lifetime: retain mapping %s until process exit\n", file);
  }
  return original(file, flags);
}
