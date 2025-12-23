import os
import random
import re
import shutil
import sys

PUNCTUATION = ",.:;?!"
WORD = r"[A-Za-z0-9']+"

def read_tsc(fn: str) -> str:
	size = os.path.getsize(fn)
	mp = size // 2
	with open(fn, "rb") as f:
		f.seek(mp)
		cipher = f.read(1)[0]
		f.seek(0)
		b = f.read()
	a = bytearray(c - cipher & 255 for c in b)
	a[mp] = cipher
	s = a.decode("shift_jis", "replace").lstrip().replace("\x00\x00", "\r\n")
	return "\r\n" + s

def write_tsc(s: str, fn: str, compat: bool = True):
	b = s.encode("shift_jis", "replace")
	if b and compat:
		b = b"\r\n" + b
		mp = len(b) // 2
		while b[mp:mp + 3] != b"\r\n#" and b[mp:mp + 3] != b"\r\n-" and b[mp:mp + 4] != b"  \r\n":
			b = b"  " + b
			mp = len(b) // 2
		b = b" " + b[:mp] + b"\x00" + b[mp:]
		assert b[len(b) // 2] == 0
	elif b:
		mp = len(b) // 2
		cipher = b[mp]
		a = bytearray(c + cipher & 255 for c in b)
		a[mp] = cipher
		b = a.data
	with open(fn, "wb") as f:
		f.write(b)

tsc_argc = {
	"AE+": 0, "AM+": 9, "AM-": 4, "AMJ": 9, "ANP": 14,
	"BOA": 4, "BSL": 4,
	"CAT": 0, "CIL": 0, "CLO": 0, "CLR": 0, "CMP": 14, "CMU": 4, "CNP": 14, "CPS": 0, "CRE": 0, "CSS": 0,
	"DNA": 4, "DNP": 4,
	"ECJ": 9, "END": 0, "EQ+": 4, "EQ-": 4, "ESC": 0, "EVE": 0,
	"FAC": 4, "FAI": 4, "FAO": 4, "FL+": 4, "FL-": 4, "FLA": 0, "FLJ": 9, "FMU": 0, "FOB": 9, "FOM": 4, "FON": 9, "FRE": 0,
	"GIT": 4,
	"HMC": 0,
	"INI": 0, "INP": 14, "IT+": 4, "IT-": 4, "ITJ": 9,
	"KEY": 0,
	"LDP": 0, "LI+": 4,
	"ML+": 4, "MLP": 0, "MM0": 0, "MNA": 0, "MNP": 19, "MOV": 9, "MP+": 4, "MPJ": 9, "MS2": 0, "MS3": 0, "MS4": 0, "MSG": 0, "MYB": 4, "MYD": 4,
	"NCJ": 9, "NOD": 0, "NUM": 4,
	"PRI": 0, "PS+": 9,
	"QUA": 4,
	"RMU": 0,
	"SAT": 0, "SIL": 4, "SK+": 4, "SK-": 4, "SKJ": 9, "SLP": 0, "SMC": 0, "SMP": 9, "SNP": 19, "SOU": 4, "SPS": 0, "SSS": 4, "STC": 0, "SVP": 0,
	"TAM": 14, "TRA": 0, "TUR": 0,
	"UNI": 4, "UNJ": 9,
	"WAI": 4, "WAS": 0,
	"XX1": 4,
	"YNJ": 4,
	"ZAM": 0,
}

def parse_command(s: str, i: int):
	cmd = s[i + 1:i + 4]
	assert len(cmd) == 3, cmd
	extra = tsc_argc[cmd]
	i += 4
	args = list(filter(bool, re.split(r"[^0-9]+", s[i:i + extra])))
	i += extra
	return cmd, args, i

def parse_event(s: str, i: int):
	out = []
	bufstart = bufend = None
	affects_fac_open = True
	fac_open = False
	next_fac_open = False
	while True:
		i2 = s.find("<", i)
		if i2 < 0:
			break
		if bufstart is not None and i2 > i:
			bufend = i2
		i = i2
		cmd, args, i = parse_command(s, i)
		if bufstart is not None and bufend is None:
			while i < len(s) and not s[i].strip():
				i += 1
			bufstart = i
		match cmd:
			case "FAC":
				next_fac_open = bool(args and args[0] != "0000")
				fac_open = fac_open or next_fac_open
			case "MSG" | "MS2" | "MS3" | "MS4" | "TUR":
				if cmd == "MSG":
					affects_fac_open = True
				elif cmd in ("MS2", "MS3", "MS4"):
					affects_fac_open = False
				if bufstart is None:
					while i < len(s) and not s[i].strip():
						i += 1
					bufstart = i
					bufend = None
			case "END" | "EVE" | "INI" | "LDP" | "TRA":
				break
			case "CLO":
				if bufstart is not None and bufend is not None:
					out.append((bufstart, bufend, fac_open and affects_fac_open))
				bufstart = None
				bufend = None
				fac_open = False
			case "CLR":
				if bufstart is not None and bufend is not None:
					out.append((bufstart, bufend, fac_open and affects_fac_open))
					fac_open = next_fac_open
					while i < len(s) and not s[i].strip():
						i += 1
					bufstart = i
					bufend = None
			case _:
				continue
	if bufstart is not None and bufend is not None:
		out.append((bufstart, bufend, fac_open and affects_fac_open))
	return i, out

def split_tsc_text(s: str):
	out = []
	i = 0
	try:
		while i < len(s):
			i = s.find("#", i)
			if i < 0:
				break
			eventnum = s[i + 1:i + 5]
			i += 5
			try:
				assert len(eventnum) == 4 and eventnum.isnumeric(), eventnum
			except AssertionError:
				continue
			while i < len(s) and not s[i].strip():
				i += 1
			if i >= len(s) or s[i] == "#":
				continue
			try:
				i, subs = parse_event(s, i)
			except KeyError:
				continue
			subs = [t for t in subs if t[0] != t[1]]
			out.append(subs)
	except Exception:
		print(s[i:i + 256])
		raise
	return out

def find_all_words(s: str):
	eventsubs = split_tsc_text(s)
	for subs in eventsubs:
		for start, end, fac_open in subs:
			sub = s[start:end]
			while sub:
				try:
					curr, sub = sub.split(None, 1)
				except ValueError:
					curr, sub = sub, ""
				while True:
					i = curr.find("<")
					if i < 0:
						break
					try:
						cmd, args, i2 = parse_command(curr, i)
					except KeyError:
						break
					curr = curr[:i] + curr[i2:]
				match = re.match(WORD, curr)
				if match:
					yield match.group().lower()

def randomise_word(w: str, dictionary: tuple = ()) -> str:
	match = re.match(WORD, w)
	if match:
		w2 = random.choice(dictionary)
		if match.start() == 0:
			if match.end() - match.start() > 1 and match.group().isupper():
				w2 = w2.upper()
			elif w[match.start()].isupper() or match.group().isnumeric():
				w2 = w2.capitalize()
		return w[:match.start()] + w2 + w[match.end():]
	return w

def apply_random_translate(s: str, dictionary: tuple = (), chance: float = 0.5, force: bool = True) -> str:
	out = []
	eventsubs = split_tsc_text(s)
	idx = 0
	for subs in eventsubs:
		if force and subs:
			chosen = random.randint(0, len(subs) - 1)
		else:
			chosen = -1
		start_sentence = True
		for i, (start, end, fac_open) in enumerate(subs):
			if start > idx:
				out.append(s[idx:start])
				idx = end
			words = []
			sub = s[start:end]
			while sub:
				try:
					curr, sub = sub.split(None, 1)
				except ValueError:
					curr, sub = sub, ""
				while True:
					j = curr.find("<")
					if j < 0:
						break
					cmd, args, j2 = parse_command(curr, j)
					if j:
						words.append(curr[:j])
					words.append(curr[j:j2])
					curr = curr[j2:]
				if curr:
					words.append(curr)
			k = -1
			if words and i == chosen:
				choices = [i for i, w in enumerate(words) if w.strip() and not w.startswith("<")]
				k = random.choice(choices) if choices else 0
			charcount = 0
			was_pause = False
			limit = 27 if fac_open else 34
			for j, w in enumerate(words):
				if not w.strip() or w.startswith("<"):
					was_pause = "<NOD" in w or "<WAI" in w
					if "<NUM" in w:
						words[j] = " " + w
					continue
				if j == k or random.random() < chance:
					words[j] = w = randomise_word(w, dictionary)
				if j:
					if charcount + len(w) + 1 > limit or was_pause and start_sentence:
						words[j] = "\r\n" + w
						charcount = len(w)
					elif w and w[0] not in PUNCTUATION:
						words[j] = " " + w
						charcount += 1 + len(w)
					else:
						charcount += len(w)
				else:
					charcount += len(w)
				if w and w[-1] in PUNCTUATION:
					start_sentence = True
				else:
					start_sentence = False
				was_pause = False
			out.append("".join(words))
	if idx < len(s):
		out.append(s[idx:])
	return "".join(out)

def read_exe_segments(b: bytes) -> dict:
	segments = {0: 0}
	if b[:4] != b"\x4d\x5a\x90\x00":
		return segments
	start = int.from_bytes(b[0x3c:0x3e], "little")
	base = int.from_bytes(b[start + 0x34:start + 0x38], "little")
	for i in range(start + 0xf8, 0x1000, 0x28):
		seg = b[i:i + 0x28]
		if seg[0] == 0:
			break
		virtual = int.from_bytes(seg[12:16], "little") + base
		raw = int.from_bytes(seg[20:24], "little")
		segments[virtual] = raw
	return segments

def read_exe_segment(b: bytes, segs: dict, start=0, end=None) -> bytes:
	if end is None:
		end = start + 1
		read_one = True
	else:
		read_one = False
	if end <= start:
		if read_one:
			raise EOFError
		return b""
	out_virtual = out_raw = 0
	for k, v in segs.items():
		if start >= k:
			out_virtual, out_raw = k, v
		else:
			break
	off_start = start - out_virtual + out_raw
	out = b[off_start:off_start + end - start]
	if read_one:
		return out[0]
	return out

def write_exe_segment(b: bytearray, segs: dict, start=0, data=b"") -> bytearray:
	if not data:
		return b
	out_virtual = out_raw = 0
	for k, v in segs.items():
		if start >= k:
			out_virtual, out_raw = k, v
		else:
			break
	off_start = start - out_virtual + out_raw
	b[off_start:off_start + len(data)] = data
	return b

def conditional_exe_patch(b: bytearray, segs: dict, start=0, src=b"", dst=b"") -> bytearray:
	if not dst:
		return False
	out_virtual = out_raw = 0
	for k, v in segs.items():
		if start >= k:
			out_virtual, out_raw = k, v
		else:
			break
	off_start = start - out_virtual + out_raw
	if not src or b[off_start:off_start + len(src)] == src:
		b[off_start:off_start + len(dst)] = dst
	return True

def read_patch(s: str) -> bytes:
	return bytes(int(n, 16) for n in s.split())

def apply_patch(path: str, off: int, src: bytes, dst: bytes) -> int:
	with open(path, "rb+") as f:
		f.seek(off)
		if f.read(len(src)) == src:
			f.seek(off)
			f.write(dst)
			print("Patched external:", path)
			return 1
	return 0


try:
	from importlib.metadata import version
	__version__ = version("scramble")
except Exception:
	__version__ = "0.0.0-unknown"

def main():
	if len(sys.argv) == 1:
		if not os.path.exists("data/npc.tbl"):
			raise SystemExit(input("Please run this program within a Cave Story folder, or from the terminal as a standalone program. "))
		from dataclasses import dataclass
		@dataclass(slots=True)
		class MockArgs:
			version: str
			scramble_rate: float
			force: bool
			text_compatible: bool
			run: bool
			game_folder: str
		ctx = MockArgs(
			f'%(prog)s {__version__}',
			0.1,
			True,
			True,
			True,
			os.path.abspath("."),
		)
	else:
		import argparse
		parser = argparse.ArgumentParser(
			prog="scramble",
			description="Cave Story dialogue scrambler",
		)
		parser.add_argument("-V", '--version', action='version', version=f'%(prog)s {__version__}')
		parser.add_argument("-sr", '--scramble-rate', help="Chance for each word to be scrambled; defaults to 0.1", type=float, required=False, default=0.1)
		parser.add_argument("-f", "--force", action=argparse.BooleanOptionalAction, default=True, help="Forces at least one change per TSC event; defaults to TRUE")
		parser.add_argument("-tc", "--text-compatible", action=argparse.BooleanOptionalAction, default=True, help="Forces output to be both TSC and TXT compliant; defaults to TRUE")
		parser.add_argument("-st", "--speed-text", action=argparse.BooleanOptionalAction, default=True, help="Enables a slightly modified version of the SpeedText hack; CURRENTLY UNIMPLEMENTED")
		parser.add_argument("-r", "--run", action=argparse.BooleanOptionalAction, default=False, help="Immediately run the game after patching; defaults to FALSE")
		parser.add_argument("game_folder", help='Top level directory of folder to process. Output will be a copy of this folder with the "~" character appended.')
		ctx = parser.parse_args()

	dictionary = set()
	custom_dictionary = "dictionary.txt"
	if os.path.exists(custom_dictionary):
		with open(custom_dictionary, "r") as f:
			s = f.read()
		dictionary.update(w for i, w in enumerate(s.splitlines()) if len(w) >= 3 or len(w) == 3 and i < 6000 or len(w) == 2 and i < 100)
	else:
		for root, dirs, files in os.walk(ctx.game_folder):
			dirs[:] = [d for d in dirs if d not in ("_internal", "Manual")]
			for fn in files:
				path = os.path.join(root, fn)
				if not fn.endswith(".tsc"):
					if ctx.text_compatible and fn.endswith(".exe"):
						with open(path, "rb") as f:
							b = f.read()
						segs = read_exe_segments(b)
						offs = 0x420c55
						patch = read_patch("E8 76 B3 FE FF")
						if read_exe_segment(b, segs, offs, offs + len(patch)) == patch:
							offs = 0x420c2f
							mapdata = int.from_bytes(read_exe_segment(b, segs, offs, offs + 4), "little")
							maps = []
							curr = mapdata + 165
							while True:
								for i in range(35):
									if read_exe_segment(b, segs, curr + i) == 0:
										break
								if i:
									name = read_exe_segment(b, segs, curr, curr + i).decode("shift_jis", "replace")
									words = "".join(c for c in name.casefold() if c != "�").split()
									for word in words:
										if not word:
											continue
										maps.append(word)
								if not read_exe_segment(b, segs, curr + 35):
									break
								curr += 200
							dictionary.update(maps)
					continue
				s = read_tsc(path)
				dictionary.update(find_all_words(s))
	dictionary = [w for w in dictionary if len(w) > 1 and (len(w) > 2 or w.isalpha())]
	dictionary.extend("AI")
	dictionary.sort()
	dictionary = tuple(dictionary)

	ctx.game_folder = os.path.abspath(ctx.game_folder)
	output_dir = ctx.game_folder + "~"
	# if os.path.exists(output_dir):
	# 	shutil.rmtree(output_dir, ignore_errors=True)

	exe_path = None
	patched = 0
	for root, dirs, files in os.walk(ctx.game_folder):
		dirs[:] = [d for d in dirs if d not in ("_internal", "Manual")]
		for fn in files:
			if fn.endswith(".py"):
				continue
			path = os.path.join(root, fn)
			folder = root.replace(ctx.game_folder, output_dir)
			os.makedirs(folder, exist_ok=True)
			path2 = os.path.join(folder, fn)
			if not fn.endswith(".tsc"):
				if os.path.exists(path2):
					with open(path, "rb") as fi:
						with open(path2, "rb+") as fo:
							fo.truncate(os.path.getsize(path))
							fo.seek(0)
							shutil.copyfileobj(fi, fo)
				else:
					shutil.copyfile(path, path2)
				if ctx.text_compatible and fn.endswith(".exe"):
					with open(path, "rb") as f:
						b = f.read()
					b = bytearray(b)
					segs = read_exe_segments(b)
					offs = 0x420c55
					patch = read_patch("E8 76 B3 FE FF")
					if read_exe_segment(b, segs, offs, offs + len(patch)) == patch:
						exe_path = path2
						patched += 1
						offs = 0x420c2f
						mapdata = int.from_bytes(read_exe_segment(b, segs, offs, offs + 4), "little")
						maps = []
						curr = mapdata + 165
						while True:
							for i in range(35):
								if read_exe_segment(b, segs, curr + i) == 0:
									break
							if i:
								name = read_exe_segment(b, segs, curr, curr + i).decode("shift_jis", "replace")
								words = "".join(c for c in name if c != "�").split()
								if words:
									for i, word in enumerate(words):
										if not word:
											continue
										if random.random() < ctx.scramble_rate * 3:
											words[i] = randomise_word(word, dictionary)
								new_name = " ".join(words).encode("shift_jis", "replace") + b"\x00"
								write_exe_segment(b, segs, curr, new_name)
							if not read_exe_segment(b, segs, curr + 35):
								break
							curr += 200
						if conditional_exe_patch(
							b, segs,
							0x4215de,
							read_patch("C7 45 F0 F9 FF FF FF"),
							read_patch("C7 45 F0 00 00 00 00"),
						):
							conditional_exe_patch(
								b, segs,
								0x421639,
								b"",
								read_patch("74 05 8B 4D F4 EB 0E 03 45 08 80 38 00 75 0E B1 0D 90 90 90 90"),
							)
						# if conditional_exe_patch(
						# 	b, segs,
							
						# )
						print("Patched exe:", path)
					with open(path2, "wb") as f:
						f.write(b)
				if fn.casefold() == "config.dat":
					patched += apply_patch(
						path2,
						108,
						b"\x00",
						b"\x02",
					)
				continue
			s = read_tsc(path)
			s = apply_random_translate(s, dictionary, chance=ctx.scramble_rate, force=ctx.force)
			write_tsc(s, path2, compat=ctx.text_compatible)
			patched += 1
	if patched:
		print("Total patched files:", patched)
	if ctx.run:
		if not exe_path:
			print("No Cave Story EXE detected, skipping...")
		else:
			print("Running:", exe_path)
			import json
			os.system(json.dumps(exe_path))

if __name__ == "__main__":
	main()