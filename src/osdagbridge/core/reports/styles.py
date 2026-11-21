# Centralized LaTeX and Matplotlib styling for OsdagBridge reports

DOC_CLASS_OPTS = "12pt,a4paper"

# Page margins (bottom and footskip increased to stop table rows bleeding into footer)
PAGE_MARGINS = (
    "a4paper, top=1.0in, bottom=1.2in, left=0.85in, right=0.85in, "
    "headheight=16pt, headsep=18pt, footskip=34pt"
)

LINE_STRETCH = 1.15
TABLE_NEEDSPACE = r"6\baselineskip"

# Hex colors
OSDAG_GREEN = "91B014"
HEADER_BG = "EDF2D8"
PASS_GREEN = "1B7A3E"
FAIL_RED = "C62828"
MUTED_GRAY = "555555"

# Matplotlib colors & defaults
CHART_DPI = 300
CHART_GREEN = "#91B014"
CHART_BLUE = "#2C5E8A"
CHART_AMBER = "#D97706"
CHART_PASS = "#2E7D32"
CHART_FAIL = "#C62828"

# Table spacing
TABCOLSEP = "5.5pt"
COMPACT_TABCOLSEP = "3.5pt"
ARRAYSTRETCH = "1.18"
ARRAYRULEWIDTH = "0.5pt"
EXTRAROWHEIGHT = "1.0pt"
LT_PRE = "4pt"
LT_POST = "8pt"


def geometry_tex():
    return rf"\usepackage[{PAGE_MARGINS}]{{geometry}}"


def colors_tex():
    return "\n".join([
        rf"\definecolor{{osdagGreen}}{{HTML}}{{{OSDAG_GREEN}}}",
        rf"\definecolor{{tableHeaderBg}}{{HTML}}{{{HEADER_BG}}}",
        rf"\definecolor{{passGreen}}{{HTML}}{{{PASS_GREEN}}}",
        rf"\definecolor{{failRed}}{{HTML}}{{{FAIL_RED}}}",
        rf"\definecolor{{mutedGray}}{{HTML}}{{{MUTED_GRAY}}}",
    ])


def table_defaults_tex():
    return (
        rf"\setlength{{\tabcolsep}}{{{TABCOLSEP}}}" + "\n"
        rf"\renewcommand{{\arraystretch}}{{{ARRAYSTRETCH}}}" + "\n"
        rf"\setlength{{\LTpre}}{{{LT_PRE}}}" + "\n"
        rf"\setlength{{\LTpost}}{{{LT_POST}}}" + "\n"
        rf"\setlength{{\arrayrulewidth}}{{{ARRAYRULEWIDTH}}}" + "\n"
        rf"\setlength{{\extrarowheight}}{{{EXTRAROWHEIGHT}}}" + "\n"
        rf"\BeforeBeginEnvironment{{table}}{{\needspace{{{TABLE_NEEDSPACE}}}}}" + "\n"
        rf"\BeforeBeginEnvironment{{longtable}}{{\needspace{{{TABLE_NEEDSPACE}}}}}"
    )


def header_footer_tex(pn, jn, rd, rv):
    # Removed the old -20pt vspace hack that was pulling the footer into table rows
    footrule = r"""  \renewcommand{\footrule}{%
    \ifbool{hasSDonPage}{%
      \vspace{-2pt}%
      \hbox to \headwidth{\textcolor{mutedGray}{\footnotesize\textit{* Software default value}}\hfil}%
      \vspace{2pt}%
    }{}%
    \color{osdagGreen}\hrule width\headwidth height 1pt \vspace{4pt}%
  }"""

    body = (
        r"  \fancyhf{}" + "\n"
        r"  \fancyhead[L]{" + pn + r" $|$ " + jn + r"}" + "\n"
        r"  \fancyhead[R]{" + rd + r" $|$ " + rv + r"}" + "\n"
        r"  \fancyfoot[L]{\footnotesize Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}" + "\n"
        r"  \fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}" + "\n"
        r"  \renewcommand{\headrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{2pt}}" + "\n"
        + footrule
    )

    return (
        r"\fancypagestyle{main}{" + "\n" + body + "\n}\n"
        r"\fancypagestyle{plain}{" + "\n" + body + "\n}\n"
        r"\fancypagestyle{firstpage}{" + "\n"
        r"  \fancyhf{}" + "\n"
        r"  \renewcommand{\headrulewidth}{0pt}" + "\n"
        r"  \fancyfoot[L]{\footnotesize Osdag $|$ FOSSEE $|$ Indian Institute of Technology Bombay}" + "\n"
        r"  \fancyfoot[R]{\footnotesize Page \thepage\ of \pageref{LastPage}}" + "\n"
        r"  \renewcommand{\footrule}{\color{osdagGreen}\hrule width\headwidth height 1pt \vspace{4pt}}" + "\n"
        r"}"
    )


def longtable_header(header_tex, caption="", num_cols=2):
    cap_first = rf"\caption{{\textbf{{{caption}}}}} \\" + "\n" if caption else ""
    cap_cont = (
        rf"\caption[]{{\textbf{{{caption} \textit{{(Continued)}}}}}} \\" + "\n"
        if caption else ""
    )
    return (
        f"{cap_first}"
        r"\hline" + "\n"
        r"\rowcolor{tableHeaderBg}" + "\n"
        f"{header_tex}\n"
        r"\hline" + "\n"
        r"\endfirsthead" + "\n"
        f"{cap_cont}"
        r"\hline" + "\n"
        r"\rowcolor{tableHeaderBg}" + "\n"
        f"{header_tex}\n"
        r"\hline" + "\n"
        r"\endhead" + "\n"
        rf"\multicolumn{{{num_cols}}}{{r}}{{\footnotesize\textit{{Continued on next page\ldots}}}} \\" + "\n"
        r"\endfoot" + "\n"
        r"\endlastfoot"
    )