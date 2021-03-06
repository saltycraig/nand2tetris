"""main.py

Author: C.D. MacEachern <craigm@fastmail.com>
"""

import sys

SYMBOLS = {
        'R0':  0,
        'R1':  1,
        'R2':  2,
        'R3':  3,
        'R4':  4,
        'R5':  5,
        'R6':  6,
        'R7':  7,
        'R8':  8,
        'R9':  9,
        'R10': 10,
        'R11': 11,
        'R12': 12,
        'R13': 13,
        'R14': 14,
        'R15': 15,
        'SCREEN': 16384,
        'SP': 0,
        'LCL': 1,
        'THIS': 3,
        'THAT': 4,
        'KBD': 24576,
        'ARG': 2,
        }
JUMP_BITS = {
        'null': '000',
        'JGT': '001',
        'JEQ': '010',
        'JGE': '011',
        'JLT': '100',
        'JNE': '101',
        'JLE': '110',
        'JMP': '111',
        }
DEST_BITS = {
        'null': '000',
        'M': '001',
        'D': '010',
        'A': '100',
        'MD': '011',
        'AM': '101',
        'AD': '110',
        'AMD': '111',}
COMP_BITS = {
    '0': '0101010',
    '1': '0111111',
    '-1': '0111010',
    'D': '0001100',
    'A': '0110000',
    '!D': '0001101',
    '!A': '0110001',
    '-D': '0001111',
    '-A': '0110011',
    'D+1': '0011111',
    'A+1': '0110111',
    'D-1': '0001110',
    'A-1': '0110010',
    'D+A': '0000010',
    'D-A': '0010011',
    'A-D': '0000111',
    'D&A': '0000000',
    'D|A': '0010101',
    'M': '1110000',
    '!M': '1110001',
    '-M': '1110011',
    'M+1': '1110111',
    'M-1': '1110010',
    'D+M': '1000010',
    'D-M': '1010011',
    'M-D': '1000111',
    'D&M': '1000000',
    'D|M': '1010101',}
FREEMEM = 16

def first_pass(lines: list):
    """For each instruction of the form "(xxx)": do 1. Add the
    pair (xxx: address) to the symbol table, where address is the
    number of the instruction following (xxx), i.e., next line.
    """
    idx = 0
    for line in lines:
        if line[0] == '(':
            end = line.index(')')  # raises ValueError on not found
            key = line[1:end]
            SYMBOLS[key] = idx
        else:
            idx += 1

def second_pass(lines: list):
    """Converts each line in the `lines` input into the equivalent
    Hack binary machine opcode and write it to file. Skip processing
    lines that are symbolic labels e.g., (OUTPUT_FIRST) because we already
    did that in first pass.
    """
    fname = sys.argv[1]
    end = fname.index('.asm')
    fout = fname[:end] + '.hack'

    try:
        with open(fout, 'w') as fd:
            for line in lines:
                if line[0] == '(':
                    continue  # skip and goto next iteration
                # A-instructions: '@2' '@FOOBAR'
                elif line[0] == '@':
                    instruction = translate_a_instruction(line)
                # C-instructions: 'D=M' 'D=M+1' 'A=D-1;JGT', etc.
                else:
                    instruction = translate_c_instruction(line)
                fd.write(instruction + "\n")
    except OSError:
        print('Error: opening or writing to file failed.')
        sys.exit(1)

def translate_a_instruction(line: str) -> str:
    """Return a Hack machine language instruction in string format."""
    global FREEMEM
    instruction = ''
    # 1. case: first character of line is '@'
    if line[0] == '@':
        # @foo, @LOOP, @SP, @THIS, @SCREEN, @R0...@R15, etc.
        if line[1].isalpha():
            value = SYMBOLS.get(line[1:])
            # found in table, e.g., int 34 returned
            # GOTCHA: if value from key is 0, just using 'if value' fails!
            if value is not None:
                # zfill() left fills string with 0s to pad out to size N
                instruction = format(value, 'b').zfill(16)
            # not found in table, new variable
            else:
                print("Assigning freemem position {} to {}".format(str(FREEMEM), line))
                SYMBOLS[line[1:]] = FREEMEM
                value = FREEMEM
                FREEMEM += 1
                instruction = format(value, 'b').zfill(16)
        # @0 ... @N, e.g. @16384, just directly translate
        else:
            value = int(line[1:])  # @16384
            instruction = format(value, 'b').zfill(16)
    # 2. case: first character of line is '('
    elif line[0] == '(':
        endidx = line.index(')')  # raises ValueError if not found
        key = line[1:endidx]
        value = SYMBOLS.get(key)
        if value:
            instruction = format(value, 'b').zfill(16)
        else:
            raise RuntimeError('Error: Could not find "{}" in the symbol'
                    ' table.'.format(key))
            sys.exit(1)
    # 3. case: here be dragons (i.e., unknown)
    else:
        raise SyntaxError('Error: First character of line could not be parsed.')
        sys.exit(1)

    # print('A-instruction conversion: {} \t\t {}'.format(line, instruction))
    return instruction

def translate_c_instruction(line: str) -> str:
    """Return a Hack machine language instruction in string format.

    C-instruction bits decoded: 111A CCCC CCDD DJJJ
    111 : always used
    A   : 1 if in certain comp table, 0 if in the other one
    CCCCCC : comparison function to use on the Hack ALU.
    DDD : destination bits, i.e., which registers to save ALU results.
    JJJ : jump bits, if any on, perform that type of jump based on ALU result.

    C-instruction syntax: dest=comp;jump

    Syntax: bracketed are optional
    [DEST=]COMP[;JMP]

    All valid c-instructions:
    D=M
    D=D-M
    D;JGT
    D=M+1;JLT
    """
    # print("Current line: " + line)
    # print(SYMBOLS)

    # DDD
    try:
        end = line.index('=')
        dkey = line[:end]
    except ValueError:
        dkey = 'null'
    dbits = DEST_BITS[dkey]

    # ACCCCCC
    try:
        start = line.index('=') + 1
    except ValueError:
        start= None
    try:
        end = line.index(';')
    except ValueError:
        end = None
    cvalue = line[start:end]
    cbits = COMP_BITS[cvalue]

    # JJJ
    try:
        start = line.index(';') + 1
        jvalue = line[start:]
    except ValueError:
        jvalue = 'null'
    jbits = JUMP_BITS[jvalue]

    instruction = '111'
    instruction += cbits # 7 bits
    instruction += dbits # 3 bits
    instruction += jbits # 3 bits

    # print('C-instruction conversion: {} \t\t {}'.format(line, instruction))
    return instruction

def main():
    res = []
    with open(sys.argv[1]) as lines:
        for line in lines:
            if line.startswith(('/', '*', '\n')) or not line:
                continue
            squeezed = line.replace(' ','')
            trailing_comment_rm = squeezed.partition('/')[0]
            res.append(trailing_comment_rm)

    # Remove left and right whitespace
    stripped_lines = [i.strip() for i in res]

    first_pass(stripped_lines)
    second_pass(stripped_lines)


if __name__ == '__main__':
    if sys.argv[1]:
        main()
