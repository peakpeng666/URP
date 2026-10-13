# -*- coding: utf-8 -*-
"""实施方案与入门指南的 LaTeX 构建管线（从 docx 到同目录 PDF）。

用法：python build.py [--check] [--keep]
流程：pandoc 抽正文 + 抽内嵌图 → 后处理（标题锚点/层级/目录块/代码块/URL/数学修复）
      → latexmk -xelatex 编译 → PDF 复制到对应 docx 所在目录。
依赖：pandoc、MiKTeX（xelatex）、PyMuPDF 仅自检时用到（缺失则跳过页数打印）。
两份 docx 为内容源；清理只针对本管线已知的中间文件，保留其他文件和目录。
"""
import argparse
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

DOCS = {
    "实施方案": {
        "docx": os.path.join(ROOT, "Docs", "项目材料", "实施方案_20260908.docx"),
        "main": "实施方案.tex",
        "pdf": "实施方案.pdf",
    },
    "入门指南": {
        "docx": os.path.join(ROOT, "Resources", "学习资料", "LLM自动算法设计入门指南.docx"),
        "main": "入门指南.tex",
        "pdf": "入门指南.pdf",
    },
}


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-1500:])
        sys.exit("命令失败: %s" % " ".join(cmd))
    return r


def strip_ltcaptype(s):
    n1 = s.count("{\\def\\LTcaptype{none} % do not increment counter\n")
    s = s.replace("{\\def\\LTcaptype{none} % do not increment counter\n", "")
    s = s.replace("\\end{longtable}\n}\n", "\\end{longtable}\n")
    return s, n1


def build_plan():
    """实施方案：封面移交主文件、删 docx 目录块、节标题锚点转 label、拆前置/正文。"""
    tag = "实施方案"
    body_raw = "方案_body.tex"
    sh(["pandoc", DOCS[tag]["docx"], "-t", "latex", "-o", body_raw])
    s = io.open(body_raw, encoding="utf-8").read()

    # 内嵌图抽出（架构示意图）
    z = zipfile.ZipFile(DOCS[tag]["docx"])
    os.makedirs("media", exist_ok=True)
    for name in z.namelist():
        if name.startswith("word/media/"):
            with open(os.path.join("media", os.path.basename(name)), "wb") as fh:
                fh.write(z.read(name))

    s = s.replace("版本 1.0 编制日期 2026年9月8日 目标环境 Ubuntu 22.04 LTS\n\n", "", 1)
    lines = s.splitlines()
    toc_i = next(i for i, ln in enumerate(lines) if ln.strip() == "目录")
    sec_i = next(i for i, ln in enumerate(lines) if ln.startswith("\\section{"))
    del lines[toc_i:sec_i]
    s = "\n".join(lines)

    head_re = re.compile(
        r"\\(section|subsection|subsubsection)\{\\texorpdfstring\{"
        r"\\hyperref\[([^\]]+)\]\{\\protect\\hypertarget\{[^}]+\}\{\}\{\}"
        r"(.*?)\}\}\{(.*?)\}\}(?:\\label\{[^}]*\})?", re.S)
    sec_anchors = {m.group(2) for m in head_re.finditer(s) if m.group(1) == "section"}

    def fix_head(m):
        level, anchor, t1 = m.group(1), m.group(2), m.group(3)
        title = re.sub(r"\s+", " ", t1).strip()
        title = re.sub(r"^\d+(?:\.\d+)*[\s.、]+", "", title)
        if level == "section":
            return "\\section{%s}\\label{%s}" % (title, anchor)
        if anchor in sec_anchors:
            return "\\%s{%s}" % (level, title)
        return "\\%s{%s}\\label{%s}" % (level, title, anchor)

    s, n_head = head_re.subn(fix_head, s)
    s = re.sub(r"(\\subsection\{)\d+(?:\.\d+)*[\s.、]+", r"\1", s)

    # 前置（含执行顺序表）与正文拆分
    lines = s.splitlines()
    first_sec = next(i for i, ln in enumerate(lines) if ln.startswith("\\section{"))
    front = "\n".join(lines[:first_sec])
    body = "\n".join(lines[first_sec:])
    front = re.sub(r"\\subsection\{执行顺序\}(\\label\{[^}]*\})?",
                   r"\\section*{执行顺序}", front)

    # 图片：剥 alt 键与超链接包装、等比缩放居中
    body = re.sub(r",alt=\{[^{}]*\}", "", body)
    body = re.sub(r"\\hyperref\[[^\]]+\]\{(\\includegraphics[^}]*\{media/[^}]+\})\}",
                  r"\1", body)
    body = re.sub(r"(\\includegraphics\[[^]]*\]\{media/image1\.png\})",
                  "\\\\begin{center}\n\\1\n\\\\end{center}", body)
    body = body.replace("width=6.61417in,height=2.38845in", "width=\\textwidth")

    body, n_lt = strip_ltcaptype(body)
    front, _ = strip_ltcaptype(front)

    # docx 公式里混入数学模式的全角逗号
    fixes = [
        (r"{\sum_{(i,j) \in r}^{}c_{ij}}，\ \ |R|\  \leq \ K",
         r"{\sum_{(i,j) \in r}^{}c_{ij}},\quad |R| \leq K"),
        (r"\max(A_{j},\ a_{j})，\ \ B_{j}\  \leq \ b_{j}",
         r"\max(A_{j},\ a_{j}),\quad B_{j} \leq b_{j}"),
    ]
    for old, new in fixes:
        assert old in body, old[:40]
        body = body.replace(old, new)

    io.open("方案_front.tex", "w", encoding="utf-8").write(front)
    io.open("方案_body2.tex", "w", encoding="utf-8").write(body)
    os.remove(body_raw)
    print("[%s] 标题 %d 处、LTcaptype %d 处、媒体 %d 个"
          % (tag, n_head, n_lt, len(os.listdir("media"))))


def build_guide():
    """入门指南：删文档级标题与手工目录块、层级升一级、代码块转 lstlisting、URL 断行。"""
    tag = "入门指南"
    body_raw = "指南_body.tex"
    sh(["pandoc", DOCS[tag]["docx"], "-t", "latex", "-o", body_raw])
    g = io.open(body_raw, encoding="utf-8").read()

    g = re.sub(r"\\section\{使用大语言模型进行自动算法设计入门指南\}\\label\{[^}]*\}\n?", "", g)
    g = re.sub(r"\\subsection\{目录\}\\label\{[^}]*\}\s*\\begin\{enumerate\}.*?\\end\{enumerate\}",
               "", g, flags=re.S)
    g = re.sub(r"\\subsubsection\{\d+(?:\.\d+)*[\s.、]*\s*", r"\\subsection{", g)
    g = re.sub(r"\\subsection\{\d+(?:\.\d+)*[\s.、]*\s*", r"\\section{", g)
    g = re.sub(r"(\\(?:sub)*section\{)\d+(?:\.\d+)*[\s.、]+", r"\1", g)

    def verb_repl(m):
        code = m.group(1)
        if re.search(r"^\s*(def |import |class |from \w+ import|@\w+)", code, re.M):
            lang = "Python"
        elif re.search(r"^\s*(pip |git |cd |python |C:\\|# 克隆)", code, re.M):
            lang = "sh"
        else:
            lang = ""
        tag_ = ("[language=%s]" % lang) if lang else ""
        return "\\begin{lstlisting}%s\n%s\\end{lstlisting}" % (tag_, code)

    g, n_verb = re.subn(r"\\begin\{verbatim\}\n(.*?)\\end\{verbatim\}",
                        verb_repl, g, flags=re.S)
    g, n_url = re.subn(r"(?<!\\url\{)(?<!\[)(https?://[A-Za-z0-9./_%~+#?=&-]+)",
                       r"\\url{\1}", g)

    g, n_lt = strip_ltcaptype(g)

    # 长路径加断点
    for sub in ["algorithms", "llm\\_models", "problems", "examples", "heuristics", "scripts"]:
        for fn in ["evolutionary.py", "program_synth.py", "codegen.py", "starcoder.py",
                   "codellama.py", "combinatorial.py", "numerical.py", "configs",
                   "run_eoh.py", "train.sh", "generators.py"]:
            g = g.replace(sub + "/" + fn, sub + "/" + "\\allowbreak{}" + fn)

    io.open("指南_content.tex", "w", encoding="utf-8").write(g)
    os.remove(body_raw)
    print("[%s] 代码块 %d、URL %d、LTcaptype %d" % (tag, n_verb, n_url, n_lt))


def compile_all():
    for tag in DOCS:
        d = DOCS[tag]
        r = subprocess.run(["latexmk", "-xelatex", "-interaction=nonstopmode", d["main"]],
                           capture_output=True, text=True)
        log = d["main"].replace(".tex", ".log")
        logtxt = io.open(log, encoding="utf-8", errors="replace").read() \
            if os.path.exists(log) else ""
        over = logtxt.count("Overfull")
        miss = logtxt.count("Missing character")
        ok = r.returncode == 0 and over == 0 and miss == 0
        print("[%s] latexmk exit=%d Overfull=%d Missing=%d %s"
              % (tag, r.returncode, over, miss, "OK" if ok else "!! 需检查"))
        if not ok:
            for line in logtxt.splitlines():
                if line.startswith("!"):
                    print("   ", line)
            sys.exit(1)
        output = os.path.splitext(d["docx"])[0] + ".pdf"
        shutil.copy(d["pdf"], output)
        print("[%s] -> %s" % (tag, output))


def clean():
    """只删除明确由本管线生成的文件；不递归删除目录。"""
    generated = {"方案_body.tex", "方案_front.tex", "方案_body2.tex",
                 "指南_body.tex", "指南_content.tex"}
    for d in DOCS.values():
        stem = os.path.splitext(d["main"])[0]
        for ext in (".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk",
                    ".xdv", ".synctex.gz", ".pdf"):
            generated.add(stem + ext)
    base = os.path.realpath(HERE)
    for name in sorted(generated):
        path = os.path.join(base, name)
        if os.path.dirname(os.path.realpath(path)) != base:
            raise RuntimeError("清理目标越界: " + path)
        if os.path.isfile(path) and not os.path.islink(path):
            os.remove(path)
    print("已清理本管线中间文件；其他文件和目录均保留。")


def check_environment():
    """只检查输入和命令是否存在，不编译、不覆盖交付物。"""
    missing = []
    for name in ("pandoc", "latexmk", "xelatex"):
        path = shutil.which(name)
        print("[%s] %s" % (name, path or "未找到"))
        if not path:
            missing.append(name)
    for tag, d in DOCS.items():
        for path in (d["docx"], os.path.join(HERE, d["main"])):
            exists = os.path.isfile(path)
            print("[%s] %s: %s" % (tag, "存在" if exists else "缺失", path))
            if not exists:
                missing.append(path)
    if missing:
        raise SystemExit("构建条件不完整: " + ", ".join(missing))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只检查输入和依赖，不写文件")
    parser.add_argument("--keep", action="store_true", help="保留构建中间文件")
    args = parser.parse_args()
    check_environment()
    if args.check:
        sys.exit(0)
    os.chdir(HERE)
    build_plan()
    build_guide()
    compile_all()
    if not args.keep:
        clean()
