from docint.schemas import OCRToken


def detect_regions(tokens: list[OCRToken], page_height: float) -> dict[str, list[OCRToken]]:
    """
    Categorizes tokens into Header, Body, or Footer based on their Y-coordinates.
    """
    regions = {
        "header": [],
        "body": [],
        "footer": []
    }

    if not tokens:
        return regions

    header_threshold = page_height * 0.15
    footer_threshold = page_height * 0.85

    for token in tokens:
        x1, y1, x2, y2 = token.bbox

        if y2 <= header_threshold:
            regions["header"].append(token)
        elif y1 >= footer_threshold:
            regions["footer"].append(token)
        else:
            regions["body"].append(token)

    return regions


def group_into_lines(tokens: list[OCRToken], y_tolerance: float = 10.0) -> list[list[OCRToken]]:
    """
    Groups OCRTokens that share roughly the same vertical Y-center into horizontal lines,
    sorted top-to-bottom, and left-to-right within each line.
    """
    if not tokens:
        return []

    # Sort tokens top-to-bottom by their vertical midpoint
    sorted_tokens = sorted(tokens, key=lambda t: (t.bbox[1] + t.bbox[3]) / 2.0)
    lines: list[list[OCRToken]] = []

    for token in sorted_tokens:
        y_center = (token.bbox[1] + token.bbox[3]) / 2.0
        placed = False

        for line in lines:
            line_y_center = (line[0].bbox[1] + line[0].bbox[3]) / 2.0
            if abs(y_center - line_y_center) <= y_tolerance:
                line.append(token)
                placed = True
                break

        if not placed:
            lines.append([token])

    # Sort tokens inside each horizontal line from left to right (by x1)
    for line in lines:
        line.sort(key=lambda t: t.bbox[0])

    return lines


def detect_key_value_pairs(tokens: list[OCRToken], y_tolerance: float = 10.0) -> dict[str, str]:
    """
    Finds key-value pairs on the same horizontal line where a key ends with ':'
    (e.g., [OCRToken('Total:'), OCRToken('$50.00')] -> {'Total': '$50.00'}).
    """
    kv_pairs = {}
    lines = group_into_lines(tokens, y_tolerance=y_tolerance)

    for line in lines:
        for i, token in enumerate(line):
            if token.text.endswith(":") and i + 1 < len(line):
                key = token.text[:-1].strip()
                # Join all tokens to the right of the key on the same line
                value = " ".join(t.text for t in line[i + 1:]).strip()
                if key and value:
                    kv_pairs[key] = value
                break

    return kv_pairs


def detect_table_rows(tokens: list[OCRToken], min_columns: int = 3, y_tolerance: float = 10.0) -> list[list[str]]:
    """
    Detects potential table rows by finding horizontal lines that contain at least
    `min_columns` horizontally separated tokens.
    """
    table_rows = []
    lines = group_into_lines(tokens, y_tolerance=y_tolerance)

    for line in lines:
        # Ignore lines that are clearly Key-Value pairs (containing a colon)
        if any(t.text.endswith(":") for t in line):
            continue
        if len(line) >= min_columns:
            table_rows.append([t.text for t in line])

    return table_rows