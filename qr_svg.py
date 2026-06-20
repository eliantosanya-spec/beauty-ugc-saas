VERSION = 3
SIZE = 29
DATA_CODEWORDS = 55
ECC_CODEWORDS = 15
MASK = 0


def qr_svg(data, scale=8, border=4):
    matrix = make_qr(data)
    total = (SIZE + border * 2) * scale
    rects = []
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                rects.append(
                    f'<rect x="{(x + border) * scale}" y="{(y + border) * scale}" width="{scale}" height="{scale}"/>'
                )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="{total}" '
        f'viewBox="0 0 {total} {total}" role="img" aria-label="Upload QR code">'
        f'<rect width="100%" height="100%" fill="#fff"/>'
        f'<g fill="#111">{"".join(rects)}</g></svg>'
    )


def make_qr(data):
    raw = data.encode("utf-8")
    if len(raw) > 53:
        raise ValueError("QR data is too long for this MVP generator")

    bits = []
    append_bits(bits, 0b0100, 4)
    append_bits(bits, len(raw), 8)
    for byte in raw:
        append_bits(bits, byte, 8)
    capacity_bits = DATA_CODEWORDS * 8
    append_bits(bits, 0, min(4, capacity_bits - len(bits)))
    while len(bits) % 8:
        bits.append(0)

    data_codewords = [bits_to_int(bits[i : i + 8]) for i in range(0, len(bits), 8)]
    pads = [0xEC, 0x11]
    i = 0
    while len(data_codewords) < DATA_CODEWORDS:
        data_codewords.append(pads[i % 2])
        i += 1

    codewords = data_codewords + reed_solomon_remainder(data_codewords, ECC_CODEWORDS)
    modules = [[None for _ in range(SIZE)] for _ in range(SIZE)]
    reserve = [[False for _ in range(SIZE)] for _ in range(SIZE)]

    add_function_patterns(modules, reserve)
    draw_codewords(modules, reserve, codewords)
    apply_mask(modules, reserve)
    draw_format_bits(modules, reserve)

    return [[bool(cell) for cell in row] for row in modules]


def append_bits(bits, value, length):
    for i in range(length - 1, -1, -1):
        bits.append((value >> i) & 1)


def bits_to_int(bits):
    value = 0
    for bit in bits:
        value = (value << 1) | bit
    return value


def set_module(modules, reserve, x, y, dark, is_function=True):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        modules[y][x] = bool(dark)
        if is_function:
            reserve[y][x] = True


def add_function_patterns(modules, reserve):
    draw_finder(modules, reserve, 0, 0)
    draw_finder(modules, reserve, SIZE - 7, 0)
    draw_finder(modules, reserve, 0, SIZE - 7)
    draw_alignment(modules, reserve, 22, 22)

    for i in range(8, SIZE - 8):
        set_module(modules, reserve, i, 6, i % 2 == 0)
        set_module(modules, reserve, 6, i, i % 2 == 0)

    set_module(modules, reserve, 8, SIZE - 8, True)

    for i in range(9):
        if i != 6:
            set_module(modules, reserve, 8, i, False)
            set_module(modules, reserve, i, 8, False)
            set_module(modules, reserve, SIZE - 1 - i, 8, False)
            set_module(modules, reserve, 8, SIZE - 1 - i, False)


def draw_finder(modules, reserve, x0, y0):
    for dy in range(-1, 8):
        for dx in range(-1, 8):
            x = x0 + dx
            y = y0 + dy
            if not (0 <= x < SIZE and 0 <= y < SIZE):
                continue
            dark = 0 <= dx <= 6 and 0 <= dy <= 6 and (
                dx in (0, 6) or dy in (0, 6) or (2 <= dx <= 4 and 2 <= dy <= 4)
            )
            set_module(modules, reserve, x, y, dark)


def draw_alignment(modules, reserve, cx, cy):
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            dark = max(abs(dx), abs(dy)) in (0, 2)
            set_module(modules, reserve, cx + dx, cy + dy, dark)


def draw_codewords(modules, reserve, codewords):
    bits = []
    for codeword in codewords:
        append_bits(bits, codeword, 8)
    bit_index = 0
    direction = -1
    x = SIZE - 1
    while x > 0:
        if x == 6:
            x -= 1
        y_range = range(SIZE - 1, -1, -1) if direction == -1 else range(SIZE)
        for y in y_range:
            for dx in (0, -1):
                xx = x + dx
                if reserve[y][xx]:
                    continue
                modules[y][xx] = bits[bit_index] if bit_index < len(bits) else 0
                bit_index += 1
        direction *= -1
        x -= 2


def apply_mask(modules, reserve):
    for y in range(SIZE):
        for x in range(SIZE):
            if not reserve[y][x] and (x + y) % 2 == 0:
                modules[y][x] = not modules[y][x]


def draw_format_bits(modules, reserve):
    # Error correction level L is format value 1. Mask 0 gives raw format 01000.
    value = format_bits((0b01 << 3) | MASK)
    coords_a = [
        (8, 0),
        (8, 1),
        (8, 2),
        (8, 3),
        (8, 4),
        (8, 5),
        (8, 7),
        (8, 8),
        (7, 8),
        (5, 8),
        (4, 8),
        (3, 8),
        (2, 8),
        (1, 8),
        (0, 8),
    ]
    coords_b = [
        (SIZE - 1, 8),
        (SIZE - 2, 8),
        (SIZE - 3, 8),
        (SIZE - 4, 8),
        (SIZE - 5, 8),
        (SIZE - 6, 8),
        (SIZE - 7, 8),
        (8, SIZE - 8),
        (8, SIZE - 7),
        (8, SIZE - 6),
        (8, SIZE - 5),
        (8, SIZE - 4),
        (8, SIZE - 3),
        (8, SIZE - 2),
        (8, SIZE - 1),
    ]
    for i in range(15):
        bit = (value >> i) & 1
        x, y = coords_a[i]
        set_module(modules, reserve, x, y, bit)
        x, y = coords_b[i]
        set_module(modules, reserve, x, y, bit)


def format_bits(value):
    data = value << 10
    generator = 0x537
    for i in range(14, 9, -1):
        if (data >> i) & 1:
            data ^= generator << (i - 10)
    return ((value << 10) | data) ^ 0x5412


def reed_solomon_remainder(data, degree):
    generator = rs_generator(degree)
    result = [0] * degree
    for byte in data:
        factor = byte ^ result.pop(0)
        result.append(0)
        if factor:
            for i, coef in enumerate(generator):
                result[i] ^= gf_mul(coef, factor)
    return result


def rs_generator(degree):
    result = [1]
    root = 1
    for _ in range(degree):
        result = poly_mul(result, [1, root])
        root = gf_mul(root, 2)
    return result[1:]


def poly_mul(a, b):
    result = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            result[i + j] ^= gf_mul(x, y)
    return result


def gf_mul(x, y):
    z = 0
    for i in range(8):
        if (y >> i) & 1:
            z ^= x << i
    for i in range(14, 7, -1):
        if (z >> i) & 1:
            z ^= 0x11D << (i - 8)
    return z & 0xFF
