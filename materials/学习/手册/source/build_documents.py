"""Build editable DOCX and a genuine XeLaTeX PDF from one canonical Markdown source."""
from pathlib import Path
import re,subprocess,json,sys,shutil
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1];S=R/'source';R.mkdir(exist_ok=True)
NAME='LLM自动算法设计_学习与研究手册'
raw=(S/'manual_ready.md').read_text()
# Bracketed, clickable resource references. Idempotent from canonical Markdown.
raw=re.sub(r'\[([PVCA]\d{2})\]\(([^)]+)\)',r'[\\[\1\\]](\2)',raw)
raw=raw.replace(')[\\[', ') [\\[')
raw=raw.replace('CodeLlama/StarCoder/WizardCoder', 'CodeLlama / StarCoder / WizardCoder').replace('2308.12950/2305.06161/2306.08568', '2308.12950 / 2305.06161 / 2306.08568').replace('optimizers/predictors/extractors/designers', 'optimizers / predictors / extractors / designers')
(S/'typeset.md').write_text(raw)
subprocess.run(['pandoc',str(S/'typeset.md'),'-f','markdown+tex_math_dollars','-t','latex','--top-level-division=section','--no-highlight','-o',str(S/'body.tex')],check=True)
# Start the resource appendix on a new page; let other chapters flow.
body=(S/'body.tex').read_text()
body=body.replace('\\section{15', '\\clearpage\n\\section{15')
# Improve first-column width for all three-column tables (content-specific tables are predominantly labels + two text columns).
blocks=re.split(r'(\\begin\{longtable\}.*?\\end\{longtable\})',body,flags=re.S)
for i,b in enumerate(blocks):
    if b.startswith('\\begin{longtable}') and b.count('\\real{0.3333}')==3:
        widths=iter(['0.23','0.35','0.42'])
        b=re.sub(r'\\real\{0\.3333\}',lambda m:r'\real{'+next(widths)+'}',b)
        blocks[i]=b
body=''.join(blocks)
body=re.sub(r'\\texttt\{([^{}]+)\}', lambda m: r'\path{'+m[1].replace(r'\_', '_')+'}' if '/' in m[1] and r'\ ' not in m[1] else m[0], body)
body=re.sub(r'DOI:(10\.[0-9]+/[A-Za-z0-9.-]+)(?=\})', lambda m:'DOI:'+r'\allowbreak\nolinkurl{'+m[1]+'}',body)
body=body.replace('arXiv:', r'arXiv:\allowbreak{}')
body=body.replace(']}}\\href', ']}}\\allowbreak\\href')
# Keep each resource entry together; these are short blocks, not whole sections.
parts=re.split(r'(\\textbf\{[PVCA]\d{2} ·.*?)(?=\\textbf\{[PVCA]\d{2} ·|\\subsection|\Z)', body, flags=re.S)
for k,t in enumerate(parts):
    if re.match(r'\\textbf\{[PVCA]\d{2} ·',t):
        parts[k]=r'\par\noindent\begin{minipage}{\linewidth}'+'\n'+t.strip()+'\n'+r'\end{minipage}\par\vspace{6pt}'+'\n\n'
body=''.join(parts)
# Keep vulnerable subsection headings with the following table or algorithm.
for number, lines in [('7.2', 8), ('9.3', 18), ('11.3', 8), ('14.2', 28)]:
    body=body.replace('\\subsection{'+number, '\\Needspace{'+str(lines)+'\\baselineskip}\n\\subsection{'+number)
(S/'body.tex').write_text(body)
header=r'''\documentclass[UTF8,a4paper,11pt,fontset=none]{ctexart}
\usepackage[top=22mm,bottom=22mm,left=22mm,right=22mm,headheight=16pt,headsep=7mm,footskip=11mm]{geometry}
\usepackage{fontspec}
\setmainfont{DejaVu Serif}
\setsansfont{DejaVu Sans}
\setmonofont[Scale=0.88]{DejaVu Sans Mono}
\setCJKmainfont[BoldFont=Noto Serif CJK SC Bold]{Noto Serif CJK SC}
\setCJKsansfont[BoldFont=Noto Sans CJK SC Bold]{Noto Sans CJK SC}
\setCJKmonofont{Noto Sans Mono CJK SC}
\usepackage{amsmath,amssymb,booktabs,longtable,array,calc}
\usepackage[table]{xcolor}
\definecolor{Ink}{HTML}{193347}
\definecolor{Accent}{HTML}{006D77}
\definecolor{Pale}{HTML}{EEF4F7}
\usepackage{fvextra}
\RecustomVerbatimEnvironment{verbatim}{Verbatim}{breaklines=true,breakanywhere=true,fontsize=\small,frame=single,rulecolor=\color{Accent},framesep=6pt}
\usepackage{xurl}
\usepackage{hyperref}
\hypersetup{unicode=true,colorlinks=true,linkcolor=Ink,urlcolor=Accent,pdftitle={LLM自动算法设计：学习与研究手册},pdfauthor={研究型学习手册},pdfsubject={指南核查、公开视频、源码、复现实验和24周学习计划}}
\urlstyle{same}
\usepackage{bookmark,fancyhdr,etoolbox,needspace}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\sffamily\small\color{Ink}LLM 自动算法设计}
\fancyhead[R]{\sffamily\small\color{Ink}学习与研究手册}
\fancyfoot[L]{\sffamily\footnotesize 核验截止：2026-09-19}
\fancyfoot[R]{\sffamily\footnotesize\thepage}
\renewcommand{\headrulewidth}{0.35pt}
\renewcommand{\footrulewidth}{0pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5.5pt}
\linespread{1.18}
\setlength{\emergencystretch}{3em}
\setcounter{secnumdepth}{0}
\setcounter{tocdepth}{1}
\ctexset{section={format=\Large\sffamily\bfseries\color{Ink},beforeskip=4pt,afterskip=15pt},subsection={format=\large\sffamily\bfseries\color{Ink},beforeskip=14pt,afterskip=7pt}}
\providecommand{\tightlist}{\setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
\AtBeginEnvironment{longtable}{\small\renewcommand{\arraystretch}{1.15}\setlength{\LTpre}{8pt}\setlength{\LTpost}{10pt}}
\widowpenalty=10000
\clubpenalty=10000
\begin{document}
\begin{titlepage}
\thispagestyle{empty}
{\sffamily\color{Accent}\large 学习与研究手册\hfill 2026.09}
\vspace{26mm}

{\sffamily\bfseries\color{Ink}\fontsize{32}{43}\selectfont LLM 自动算法设计\par}
\vspace{5mm}
{\sffamily\color{Ink}\fontsize{22}{31}\selectfont 从指南纠错到独立复现\par}
\vspace{9mm}
{\color{Accent}\rule{\textwidth}{1.3pt}}
\vspace{7mm}
{\large 概念推导 · 视频与源码 · 实验规范 · 学习安排\par}
\vspace{15mm}
\begin{tabular}{@{}p{0.30\textwidth}p{0.30\textwidth}p{0.30\textwidth}@{}}
{\sffamily\bfseries\Huge 24周} & {\sffamily\bfseries\Huge 82条} & {\sffamily\bfseries\Huge 29项}\\[4mm]
主线学习计划 & 来源与资源记录 & 通过的教学测试\\
\end{tabular}\par
\vspace{16mm}
本手册围绕老师提供的入门指南，先修正概念、文献与代码问题，再以装箱、TSP和CVRP连接经典算法、LLM程序搜索及研究实验。目标是能够独立解释方法、运行小实验、识别证据边界，并设计可复核的研究。
\vfill
{\sffamily\small 审读对象：《LLM自动算法设计入门指南(1).docx》\par}
{\sffamily\small 检索核验截止：2026年9月19日\par}
{\sffamily\small 版本：1.0\quad Word与PDF共享正文；PDF由XeLaTeX编译\par}
\end{titlepage}
\pagenumbering{roman}
\tableofcontents
\clearpage
\pagenumbering{arabic}
'''
(S/'main.tex').write_text(header+'\n\\input{body.tex}\n\\end{document}\n')
subprocess.run(['pandoc',str(S/'typeset.md'),'-f','markdown+tex_math_dollars','-t','docx','--no-highlight','-o',str(R/(NAME+'.docx'))],check=True)
doc=Document(R/(NAME+'.docx'))
sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=Cm(2.2);sec.left_margin=sec.right_margin=Cm(2.2)
sec.header_distance=Cm(1.05);sec.footer_distance=Cm(1.1)
sec.different_first_page_header_footer=True
styles=doc.styles

def setfont(style,latin='DejaVu Serif',cjk='Noto Serif CJK SC',size=10.5,bold=None,color=None):
    st=next(s for s in styles if s.name==style) if isinstance(style,str) else style
    st.font.name=latin;st.font.size=Pt(size)
    if bold is not None:st.font.bold=bold
    if color:st.font.color.rgb=RGBColor.from_string(color)
    rpr=st.element.get_or_add_rPr();rf=rpr.find(qn('w:rFonts'))
    if rf is None:rf=OxmlElement('w:rFonts');rpr.insert(0,rf)
    rf.set(qn('w:eastAsia'),cjk);rf.set(qn('w:ascii'),latin);rf.set(qn('w:hAnsi'),latin)
    return st
for nm in ['Normal','Body Text','First Paragraph','Compact']:
    if nm in styles:
        st=setfont(nm,size=10.5)
        f=st.paragraph_format;f.line_spacing=1.2;f.space_after=Pt(6);f.first_line_indent=Pt(0);f.widow_control=True
for nm,pt in [('Heading 1',17),('Heading 2',12.5),('Heading 3',11)]:
    st=setfont(nm,'DejaVu Sans','Noto Sans CJK SC',pt,True,'193347');f=st.paragraph_format
    f.keep_with_next=True;f.space_before=Pt(13);f.space_after=Pt(8);f.line_spacing=1.1
    if nm=='Heading 1':f.page_break_before=False
for nm in ['Verbatim Char','Source Code']:
    if nm in styles:setfont(nm,'DejaVu Sans Mono','Noto Sans Mono CJK SC',8.4)
if 'Hyperlink' in styles:styles['Hyperlink'].font.color.rgb=RGBColor.from_string('006D77')
# Pandoc preserves mathematical objects; style normal runs and disable mandatory full justification in tables.
for p in doc.paragraphs:
    if p.style.name not in ['Heading 1','Heading 2','Heading 3','Source Code']:
        p.paragraph_format.widow_control=True
    if p.style.name=='Source Code':
        p.paragraph_format.space_after=Pt(2);p.paragraph_format.line_spacing=1.1
# Three-line style tables with repeating shaded headers and no splitting of individual rows.
for t in doc.tables:
    t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    n=len(t.columns);widths=([3.8,5.8,7.0] if n==3 else ([7.2,9.4] if n==2 else [16.6/n]*n))
    for i,col in enumerate(t.columns):col.width=Cm(widths[i])
    pr=t._tbl.tblPr
    bd=OxmlElement('w:tblBorders')
    for tag in ['top','bottom','insideH']:
        e=OxmlElement('w:'+tag);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'5' if tag!='insideH' else '3');e.set(qn('w:color'),'9CAFB9' if tag!='insideH' else 'D5DFE6');bd.append(e)
    for tag in ['left','right','insideV']:
        e=OxmlElement('w:'+tag);e.set(qn('w:val'),'nil');bd.append(e)
    pr.append(bd)
    for ri,row in enumerate(t.rows):
        rp=row._tr.get_or_add_trPr();no=OxmlElement('w:cantSplit');rp.append(no)
        if ri==0:repeat=OxmlElement('w:tblHeader');rp.append(repeat)
        for ci,cell in enumerate(row.cells):
            cell.width=Cm(widths[ci]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.TOP
            cp=cell._tc.get_or_add_tcPr();m=OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'80');e.set(qn('w:type'),'dxa');m.append(e)
            cp.append(m)
            if ri==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EEF4F7');cp.append(sh)
            for p in cell.paragraphs:
                p.paragraph_format.line_spacing=1.1;p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(1)
                p.paragraph_format.keep_with_next=False;p.paragraph_format.page_break_before=False
                for run in p.runs:
                    run.font.size=Pt(9.2)
                    if ri==0:run.font.bold=True
# Insert a cover and clickable section navigator ahead of the existing first chapter.
first=doc.paragraphs[0]
def before(text='',size=11,bold=False,color='193347',after=10,style=None):
    p=first.insert_paragraph_before(text,style=style)
    p.paragraph_format.space_after=Pt(after);p.paragraph_format.space_before=Pt(0)
    p.paragraph_format.line_spacing=1.15;p.paragraph_format.keep_with_next=False
    for run in p.runs:
        run.font.name='DejaVu Sans';run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=RGBColor.from_string(color)
        rp=run._r.get_or_add_rPr();rf=rp.find(qn('w:rFonts'))
        if rf is None:rf=OxmlElement('w:rFonts');rp.append(rf)
        rf.set(qn('w:eastAsia'),'Noto Sans CJK SC')
    return p
before('学习与研究手册                                                   2026.09',11,color='006D77',after=70)
before('LLM 自动算法设计',28,True,after=16)
before('从指南纠错到独立复现',21,False,after=23)
p=before('',after=18)
ppr=p._p.get_or_add_pPr();bd=OxmlElement('w:pBdr');b=OxmlElement('w:bottom');b.set(qn('w:val'),'single');b.set(qn('w:sz'),'14');b.set(qn('w:color'),'006D77');bd.append(b);ppr.append(bd)
before('概念推导 · 视频与源码 · 实验规范 · 学习安排',12,after=45)
before('24周主线       82条来源记录       29项教学测试',15,True,after=35)
before('本手册围绕老师提供的入门指南，先修正概念、文献与代码问题，再以装箱、TSP和CVRP连接经典算法、LLM程序搜索及研究实验。目标是能够独立解释方法、运行小实验、识别证据边界，并设计可复核的研究。',11,after=65)
before('审读对象：《LLM自动算法设计入门指南(1).docx》',9.5,after=8)
before('检索核验截止：2026年9月19日',9.5,after=8)
before('版本：1.0  |  Word与PDF共享正文；PDF由XeLaTeX编译',9.5,after=6)
p=before('阅读导航',20,True,after=10);p.paragraph_format.page_break_before=True
before('点击章节可在Word中跳转；PDF目录另含自动页码。',10,after=18)
heads=[p for p in doc.paragraphs if p.style.name=='Heading 1']
heads[0].paragraph_format.page_break_before=True
heads[-1].paragraph_format.page_break_before=True
# Keep each bibliography title, URL and verification note together.
for j,p in enumerate(doc.paragraphs):
    if re.match(r'^[PVCA]\d{2} ·',p.text):
        p.paragraph_format.keep_with_next=True
        if j+1<len(doc.paragraphs):doc.paragraphs[j+1].paragraph_format.keep_with_next=True
for idx,h in enumerate(heads,1):
    name='chapter_'+str(idx)
    st=OxmlElement('w:bookmarkStart');st.set(qn('w:id'),str(10000+idx));st.set(qn('w:name'),name)
    en=OxmlElement('w:bookmarkEnd');en.set(qn('w:id'),str(10000+idx));h._p.insert(0,st);h._p.append(en)
    p=before('',after=10)
    link=OxmlElement('w:hyperlink');link.set(qn('w:anchor'),name)
    r=OxmlElement('w:r');rpr=OxmlElement('w:rPr');color=OxmlElement('w:color');color.set(qn('w:val'),'006D77');rpr.append(color);r.append(rpr)
    text=OxmlElement('w:t');text.text=h.text;r.append(text);link.append(r);p._p.append(link)
# Consistent running furniture.
p=sec.header.paragraphs[0];p.text='LLM 自动算法设计                                                    学习与研究手册'
p.paragraph_format.space_after=Pt(3)
for run in p.runs:run.font.name='DejaVu Sans';run.font.size=Pt(8.5);run.font.color.rgb=RGBColor.from_string('193347')
p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
run=p.add_run('核验截止：2026-09-19    |    ');run.font.size=Pt(8)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
# Set East Asian language for correct punctuation wrapping.
for st in [styles['Normal'],styles['Body Text']]:
    rpr=st.element.get_or_add_rPr();lang=OxmlElement('w:lang');lang.set(qn('w:val'),'en-US');lang.set(qn('w:eastAsia'),'zh-CN');rpr.append(lang)
doc.core_properties.title='LLM自动算法设计：学习与研究手册'
doc.core_properties.subject='指南核查、视频与源码、复现协议、24周学习计划'
doc.core_properties.author='';doc.core_properties.last_modified_by='';doc.core_properties.comments=''
doc.save(R/(NAME+'.docx'))
# The PDF is compiled from TeX, not exported from Word.
with (R/'logs/latex_build.txt').open('w') as log:
    for _ in range(2):
        cp=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=S,stdout=log,stderr=subprocess.STDOUT)
        if cp.returncode:raise SystemExit('XeLaTeX failed; see logs/latex_build.txt')
shutil.copy2(S/'main.pdf',R/(NAME+'.pdf'))
print('Built',R/(NAME+'.docx'),R/(NAME+'.pdf'))
