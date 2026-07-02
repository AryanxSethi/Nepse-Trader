LOOKUP_TABLE = [
    5, 8, 4, 7, 9, 3, 1, 0, 6, 2,
    5, 8, 4, 7, 9, 3, 1, 0, 6, 2,
    5, 8, 4, 7, 9, 3, 1, 0, 6, 2,
    5, 8, 4, 7, 9, 3, 1, 0, 6, 2,
]


def rdx(salt2: int) -> int:
    v = salt2
    r = 0
    while v > 0:
        r = (r << 3) | (v & 7)
        v >>= 3
    return r


def cdx(salt2: int) -> str:
    a = rdx(salt2) + 96480
    v = a
    r = ''
    while v > 0:
        r = str(LOOKUP_TABLE[v % 10]) + r
        v //= 10
    return r


def ndx(salt2: int) -> int:
    return (salt2 * 3 + 7) % 13


def mdx(salt1: int, salt2: int) -> str:
    return chr(salt1 ^ salt2)


def bdx(generated_css: str) -> str:
    parts = generated_css.split('{')
    if len(parts) < 2:
        return generated_css
    body = parts[1].rstrip('}')
    rules = body.split(';')
    sorted_rules = sorted(rules, key=lambda x: len(x.strip()))
    return parts[0] + '{' + ';'.join(sorted_rules) + '}'


def extract_salts(css_text: str) -> tuple[int, int]:
    salt1 = 0
    salt2 = 0
    for line in css_text.splitlines():
        line = line.strip()
        if 'salt1' in line.lower() or '--salt1' in line:
            import re
            m = re.search(r'[-]?\d+', line)
            if m:
                salt1 = int(m.group())
        if 'salt2' in line.lower() or '--salt2' in line:
            import re
            m = re.search(r'[-]?\d+', line)
            if m:
                salt2 = int(m.group())
    return salt1, salt2


def build_column_map(salt1: int, salt2: int, columns: list[str]) -> dict[str, str]:
    indices = [ndx(salt2 + i) for i in range(len(columns))]
    standard = ['ltp', 'change', 'percentChange', 'open', 'high', 'low',
                'volume', 'turnover', 'close', 'previousClose', '52WeekHigh',
                '52WeekLow', 'lastUpdatedTime']
    mapping = {}
    for i, col in enumerate(columns):
        if i < len(indices) and indices[i] < len(standard):
            mapping[col] = standard[indices[i]]
        else:
            mapping[col] = col
    return mapping
