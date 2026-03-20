# ⬡ Embedded Calculator

> **⚠️ Vibe coded & early stage** — This tool was built through iterative AI-assisted development ("vibe coding") and is still in early stages. Expect rough edges, missing features, and occasional quirks. Contributions and bug reports are very welcome.

A desktop calculator built specifically for embedded systems and firmware development. It speaks your language: hex, binary, registers, bit fields, and bitwise operations — all in one place, with no browser required.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-informational?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square)
![License](https://img.shields.io/badge/License-GPL-green?style=flat-square)

---

## Why?

When you're reading a datasheet at 11pm trying to figure out what `0xA04F3C00` means, you don't want to be switching between a hex calculator, a binary converter, and a spreadsheet. This calculator keeps everything in one view and lets you work the way firmware engineers actually think — in registers and bit fields.

---

## Features

### Multi-base Entry
Four always-visible input fields show the current value simultaneously in **Hexadecimal**, **Decimal**, **Octal**, and **Binary**. Editing any one of them instantly updates the other three. Invalid characters for each base are blocked at the keyboard level.

Optional **Float** (IEEE 754 single) and **Double** (IEEE 754 double) rows can be toggled on to show how the current bit pattern is interpreted as a floating-point number.

### Configurable Word Width
Switch between **8, 16, 32, 64, and 128-bit** mode from the top bar. Overflow is handled correctly with per-size masking for all operations. Changing the width clips the current value to the new range.

### Signed / Unsigned Mode
Toggle **Signed** interpretation to display negative values correctly in the decimal field using two's complement.

### Calculator Tab
A full button panel with:

**Arithmetic:** `+` `-` `×` `÷` `%`

**Bitwise logic:** `AND` `OR` `XOR` `NOT`

**Shifts:** `LSL ←` (logical shift left), `LSR →` (logical shift right), `ASR →` (arithmetic shift right), `ROL` (rotate left), `ROR` (rotate right), `<<1` / `>>1` (single-step shifts)

**Shortcuts:** `FF` (fill all bits with 1), `00` (double zero), `NEG` (two's complement negate), `ABS` (absolute value), `DEL` (backspace), `CLR` (clear all)

An expression strip above the buttons shows the pending operation, e.g. `0xDEAD  AND`.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `0–9`, `A–F` | Digit input (valid chars for current base) |
| `Enter` | Equals (`=`) |
| `Escape` | Clear |
| `+` `-` `*` `/` `%` | Arithmetic operators |
| `<` | Logical shift left |
| `>` | Logical shift right (tap twice quickly for arithmetic shift right) |
| `Backspace` | Delete last digit |

Input always goes to the currently active base field, regardless of where the mouse is. The active field is always visually highlighted so you know exactly where your keystrokes will land.

### Bit View Tab
A canvas that renders every bit as a clickable square, arranged in rows of 8, 16, or 32 bits depending on the word width. Bit indices are shown above each cell.

**Toggling bits:** Click any bit to flip its value. Fields are preserved.

**Marking bit fields:** Hold **Ctrl** and drag across a range of bits to define a named field. Additional fields can be added with further Ctrl+drags. Each field is shown in a distinct color.

Fields persist until explicitly cleared — changing the number value updates the field values, but the field boundaries stay in place.

**Resizable split:** The divider between the bit canvas and the field panel below it is draggable. Pull it up or down to give more space to whichever section you need.

### Bit Field Panel
Every marked field gets its own row in the panel below the bit canvas showing:

- The color dot and bit range (`bits[7:4]  (4b)`)
- Its current value in **HEX** and **DEC**
- An editable entry for each — type a new value and press `Enter` or `↵` to write it back into the register, updating all other displays automatically

Input in field entries is validated against the field's bit width — you can't accidentally enter a value that won't fit.

Press **Escape** while a field entry is focused to deselect it without applying changes.

---

## Installation

No dependencies beyond Python's standard library.

```bash
# Clone the repo
git clone https://github.com/yourname/embedded-calc.git
cd embedded-calc

# Run directly
python3 embedded_calc.py
```

Requires **Python 3.8+** with Tkinter. Tkinter ships with most Python distributions. On Debian/Ubuntu you may need:

```bash
sudo apt install python3-tk
```

---

## Usage Tips

- **Switch active base** by clicking any of the four input fields, or by clicking the HEX/DEC/OCT/BIN radio buttons in the Calculator tab.
- **Define register fields** in Bit View: hold Ctrl and drag across the bits you care about. Mark all your fields first, then tweak values in the panel below.
- **Chain operations** with the expression strip: press `AND`, type your mask, then press `=`. The strip shows the full expression while you're building it.
- **Float debugging**: enable the Float or Double row to instantly see how your hex value is interpreted as IEEE 754 — useful for checking NaN bit patterns, infinity, etc.

---

## Known Limitations / Rough Edges

This is early-stage vibe-coded software. Known issues include:

- No expression history or undo
- No copy-to-clipboard button (use the entry fields directly)
- Float/Double entry editing is display-only; typing in those fields will parse back into the bit pattern but precision may vary
- The `>` / `>>` key disambiguation uses a 350ms timer — it works, but feels slightly laggy
- UI layout is not yet responsive to very small window sizes
- No dark/light theme toggle (dark-only for now)

---

## Contributing

Bug reports, feature requests, and pull requests are welcome. This started as a personal tool scratched together quickly — if you find it useful and want to help make it more robust, go for it.

---

## License

GPL — see [LICENSE](LICENSE) for details.
