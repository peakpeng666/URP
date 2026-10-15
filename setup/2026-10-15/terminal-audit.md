# 本次终端入口核对

本次实际执行命令为：

```bash
/usr/bin/gnome-terminal --wait --title='URP Setup — 系统依赖安装' --working-directory=/home/peakpeng/Desktop/URP -- bash /home/peakpeng/Desktop/URP/setup/2026-10-15/interactive-install.sh
```

因此本次明确指定旧 GNOME Terminal，绕过了用户配置的默认入口。可见窗口标题已由 wmctrl 确认，脚本的 TTY 为 `/dev/pts/1`；用户在该可见窗口自行完成 sudo 认证，密码没有经过模型工具。

只读核对结果：

- 当前 PATH 的 `x-terminal-emulator` 首选为 `/home/peakpeng/.local/share/macos-titlebars/bin/x-terminal-emulator`。其公开脚本说明为 Ghostty 默认适配器，通过同目录 `ghostty-mac` 启动，并兼容 cwd、标题、命令和 wait 参数。
- GNOME `org.gnome.desktop.default-applications.terminal exec` 已配置为 `/opt/macOS-Desktop/launchers/bin/ghostty-default`，`exec-arg` 为 `-e`。
- 用户桌面入口 `~/.local/share/applications/ghostty-mac.desktop` 的 Exec 为 `/home/peakpeng/.local/bin/ghostty-mac`。
- 系统 `/usr/bin/x-terminal-emulator` 仍解析为 `/usr/bin/gnome-terminal.wrapper`；update-alternatives 为 auto，当前唯一登记候选也是 GNOME。

这次窗口不符的直接原因是本任务硬编码旧终端。系统 alternatives 仍为旧终端，意味着使用绝对路径 `/usr/bin/x-terminal-emulator` 或未继承用户 PATH 的程序也可能继续打开旧终端；直接硬编码 `/usr/bin/gnome-terminal` 的程序同样不会经过用户适配器。这些属于后续全量替换需要审查的入口范围，不在当前安装中途广泛修改。

安装期间保留了原窗口和 APT/dpkg 进程，没有中途迁移或启动第二份安装。安装现已成功结束，原窗口仅可能等待 Enter 关闭。已新增本任务后续可用的 `launch-system.sh`，使用 PATH 解析到的默认终端适配器。没有修改系统 alternatives、GNOME 设置或 macOS-Desktop 项目。接续诊断结束时再次只读确认上述默认入口和系统 alternatives 解析仍相同。

本任务修正范围只有 `setup/2026-10-15/launch-system.sh`（后续终端入口）；`interactive-install.sh` 和 `install-system.sh` 分别负责交互状态/退出码和已批准的安装事务，不是系统终端替换工具。因此不能把本任务修正称为全系统全量替换。
