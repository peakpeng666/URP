#!/usr/bin/env bash
# PATH for pinned Node/uv and the selected complete JDK. Source this file.
export PATH="${HOME}/.local/node-v24.22.0/bin:${HOME}/.local/bin:${PATH}"
# Do not change system alternatives. Prefer the installed complete Ubuntu JDK
# over an unrelated default JRE, while honoring an explicit JAVA_HOME.
if [[ -z "${JAVA_HOME:-}" && -x /usr/lib/jvm/java-17-openjdk-amd64/bin/java ]]; then
  export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
fi
if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]]; then
  export PATH="$JAVA_HOME/bin:$PATH"
fi

