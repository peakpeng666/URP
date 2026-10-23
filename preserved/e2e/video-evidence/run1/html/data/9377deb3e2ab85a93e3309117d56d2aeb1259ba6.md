# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: b-draft-persistence.spec.ts >> B 草稿持久化：编辑参数后刷新页面，草稿应恢复（基线预期失败）
- Location: tests/b-draft-persistence.spec.ts:4:1

# Error details

```
Error: browserType.launch: Executable doesn't exist at ${USER_HOME}/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
╔════════════════════════════════════════════════════════════╗
║ Looks like Playwright was just installed or updated.       ║
║ Please run the following command to download new browsers: ║
║                                                            ║
║     npx playwright install                                 ║
║                                                            ║
║ <3 Playwright Team                                         ║
╚════════════════════════════════════════════════════════════╝
```