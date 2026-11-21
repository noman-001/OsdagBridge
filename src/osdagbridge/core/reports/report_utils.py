import re

from osdagbridge.core.utils.common import (
    KEY_MP_GD_MEMBER_ID,
    KEY_MP_GD_SELECT_GIRDER,
    KEY_MP_GIRDER_DEPTH,
    KEY_TS_NO_OF_GIRDERS
)


def _tex(value):
    """Escape a Python value for safe LaTeX embedding."""
    s = str(value) if value is not None else ''
    if not s:
        return r''
    for uni, ascii_ in [('∠', 'L'), ('ⅹ', 'x'), ('×', 'x')]:
        s = s.replace(uni, ascii_)
    s = s.replace('\\', '@@OSDAG_BSLASH@@')
    for ch, esc in [('&', r'\&'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'),
                    ('{', r'\{'), ('}', r'\}'),
                    ('_', r'\_\allowbreak{}'),
                    ('~', r'\textasciitilde{}'), ('^', r'\^{}')]:
        s = s.replace(ch, esc)
    s = s.replace('@@OSDAG_BSLASH@@', r'\textbackslash{}')
    s = s.replace(':', r':\allowbreak{}')
    return s


def _render_value(source_dict, key, unit=""):
    val = source_dict.get(key)
    if val in ("", None):
        return ""
    return _tex(val) + unit


def get_girder_entries(input_dict):
    """Retrieve all girder labels and member IDs from backend keys."""
    n = int(input_dict.get(KEY_TS_NO_OF_GIRDERS, 0))

    entries = []
    for i in range(1, n + 1):
        entries.append(
            (
                input_dict.get(f"{KEY_MP_GD_SELECT_GIRDER}.G{i}", ""),
                input_dict.get(f"{KEY_MP_GD_MEMBER_ID}.G{i}.M1", ""),
            )
        )

    return entries


def _fig_or_placeholder(path, caption, width=r'0.9\textwidth'):
    if path:
        p = path.replace('\\', '/')
        return (r'\begin{figure}[H]' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[width=' + width + ']{' + p + '}\n'
                r'\caption*{' + caption + '}\n'
                r'\end{figure}')
    return (r'\begin{figure}[H]' + '\n'
            r'\centering' + '\n'
            r'\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}' + '\n'
            r'\caption*{' + caption + '}\n'
            r'\end{figure}')


def _fig_embed(path, caption, width=r'\textwidth', height=None):
    if path:
        p = path.replace('\\', '/')
        opts = 'width=' + width
        if height:
            opts += ',height=' + height + ',keepaspectratio'
        return (r'\begin{figure}[H]' + '\n'
                r'\vspace{-0.5em}' + '\n'
                r'\centering' + '\n'
                r'\includegraphics[' + opts + ']{' + p + '}\n'
                r'\vspace{0.5em}' + '\n'
                r'\caption*{\small ' + caption + '}\n'
                r'\vspace{-0.5em}' + '\n'
                r'\end{figure}')
    return (r'\noindent\fbox{\parbox{0.97\textwidth}{' + '\n'
            r'\textit{[ PLACEHOLDER: ' + caption + r' ]}' + '\n'
            r'}}')


def ensure_longtable_headers(tex_str):
    """Add repeating headers to longtable blocks that span multiple rows."""
    pattern = re.compile(
        r"(\\begin\{longtable\}\{[^\n]+\})(.*?)(\\end\{longtable\})",
        re.DOTALL,
    )

    def _patch(match):
        start_tag, body, end_tag = match.groups()
        if r"\endhead" in body:
            return match.group(0)

        hdr_re = re.compile(
            r"^(\s*(?:\\caption(?:\[[^\]]*\])?\{[^\n]*?\}(?:\s*\\\\)?\s*)?)"
            r"(\\hline\s*\n)"
            r"([^\n]+\\\\(?:\[[^\]]*\])?\s*\n)"
            r"(\\hline\s*\n)",
            re.DOTALL,
        )
        m = hdr_re.match(body)
        if not m:
            return match.group(0)

        cap_part, hline1, header_row, hline2 = m.groups()
        rest = body[m.end():]

        if r"\multirow" in header_row or r"\textnormal" in header_row:
            return match.group(0)

        data_rows = len(re.findall(r"\\\\", rest))
        if data_rows < 8:
            return match.group(0)

        # In re.sub replacement strings, \\\\ produces two literal backslashes
        header_row_nobreak = re.sub(
            r"\\\\(\[[^\]]*\])?(\s*\n)$",
            r"\\\\*\1\2",
            header_row,
        )
        rest_nobreak_first = re.sub(
            r"\\\\(\[[^\]]*\])?(\s*\n\\hline)",
            r"\\\\*\1\2",
            rest,
            count=1,
        )

        num_cols = header_row.count("&") + 1

        cap_first = cap_part.strip()
        cap_cont = ""
        if cap_first:
            if not cap_first.endswith(r"\\"):
                cap_first = cap_first + r" \\*"
            cap_first = "\n" + cap_first + "\n"
            cap_cont = re.sub(
                r"\\caption\{(.*)\}\s*\\\\\*?",
                r"\\caption[]{\1 \\textit{(Continued)}} \\\\*",
                cap_first,
            )

        patched_head = (
            f"{cap_first}"
            f"{hline1}"
            f"\\rowcolor{{tableHeaderBg}}\n"
            f"{header_row_nobreak}"
            f"{hline2}"
            f"\\endfirsthead\n"
            f"{cap_cont}"
            f"{hline1}"
            f"\\rowcolor{{tableHeaderBg}}\n"
            f"{header_row_nobreak}"
            f"{hline2}"
            f"\\endhead\n"
            f"\\multicolumn{{{num_cols}}}{{r}}{{\\footnotesize\\textit{{Continued on next page\\ldots}}}} \\\\\n"
            f"\\endfoot\n"
            f"\\endlastfoot\n"
        )
        return start_tag + patched_head + rest_nobreak_first + end_tag

    return pattern.sub(_patch, tex_str)