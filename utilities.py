import re
import json


prefix = "$"
usercommands = {}
aliases = {}
client = None
def command(f=None, alias=None, prefix=prefix):
    def decorator(f):
        global usercommands
        if alias: aliases[re.compile(alias)] = prefix + f.__name__
        usercommands[prefix + f.__name__] = f
        async def inner(*args, **kwargs):
            f(*args, **kwargs)
        return inner
    if f: return decorator(f)
    else: return decorator


def to_async(func):
    async def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner


async def reply(message, text):
    if len(str(text)) > 2000:
        return await message.channel.send("output exceeded 2000 characters")
    else:
        return await message.channel.send(text)


def load_text():
    text = {}
    text["pcnames"] = ["Isaac", "Garet", "Ivan", "Mia", "Felix", "Jenna", "Sheba", "Piers"]
    text["elements"] = ["Venus", "Mercury", "Mars", "Jupiter", "Neutral"]
    mtoken = re.compile(r"{\d*}")
    with open(r"text/GStext.txt") as f:
        lines = f.read().splitlines()
        text["item_descriptions"] = lines[146:607]
        lines = list(map(lambda x: mtoken.sub("", x), lines))
        text["items"] = lines[607:1068]
        text["enemynames"] = lines[1068:1447]
        text["abilities"] = lines[1447:2181]
        text["move_descriptions"] = lines[2181:2915]
        text["classes"] = lines[2915:3159]
        text["djinn"] = lines[1747:1827]
    with open(r"text/customtext.txt") as f:
        lines = f.read().splitlines()
        text["ability_effects"] = lines[0:92]
        text["equipped_effects"] = lines[92:120]
        text["summons"] = lines[120:149]
    return text


def namedict(jsonobj):
    out = {}
    for entry in jsonobj:
        if not entry.get("name"): continue
        name = entry["name"].lower()
        if out.get(name):
            out[name].append(entry)
        else:
            out[name] = [entry]
        out[name.replace("'","")] = out[name]
        out[name.replace("-"," ")] = out[name]
    return out


DataTables, Namemaps, UserData, Text = {}, {}, {}, {}
def load_data():
    global DataTables, Namemaps, UserData, Text
    from copy import deepcopy
    print("Loading database...", end="\r")
    DataTables.clear(); Namemaps.clear(); Text.clear()
    for name in [
            "djinndata", "summondata", "enemydata", "itemdata", "abilitydata", "pcdata",
            "classdata", "elementdata", "enemygroupdata", "encounterdata"]:
        with open(rf"data/{name}.json") as f:
            DataTables[name] = json.load(f)
            if name == "enemydata":
                DataTables["enemydata-h"] = deepcopy(DataTables["enemydata"])
                for entry in DataTables["enemydata-h"]:
                    entry["HP"] = min(0x3FFF, int(1.5*entry["HP"]))
                    entry["ATK"] = int(1.25*entry["ATK"])
                    entry["DEF"] = int(1.25*entry["DEF"])
    for k,v in DataTables.items():
        Namemaps[k] = namedict(v)
    Text.update(**load_text())
    print("Loaded database    ")


mquote = re.compile(r"\".*?\"|\'.*?\'")
mkwarg = re.compile(r"([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*([^ =]\S*)")
mtoken = re.compile(r"{(\d+)}")
def parse(s):
    groups = []
    args, kwargs = [], {}
    def addtoken(m):
        groups.append(m.group())
        return f"{{{len(groups)-1}}}"
    def addkwarg(m):
        kwargs[m.group(1)] = m.group(2)
    def gettoken(m):
        return groups[int(m.group(1))]
    s = mquote.sub(addtoken, s)
    s = mkwarg.sub(addkwarg, s)
    args = re.findall(r"\S+", s)
    for i, arg in enumerate(args):
        args[i] = mtoken.sub(gettoken, arg)
    for k,v in kwargs.items():
        kwargs[k] = mtoken.sub(gettoken, v)
    return args, kwargs


def wrap(iterable, maxwidth, pos=0):
    group = "{}" if isinstance(iterable, (dict, set)) else "[]"
    if not iterable: return group
    out = group[0]; pos += 1
    initpos = pos
    if isinstance(iterable, dict):
        iterable = (f"{k}: {v}" for k,v in iterable.items())
    else:
        iterable = iter(iterable)
    entry = str(next(iterable))
    out += entry; pos += len(entry)
    for entry in iterable:
        entry = str(entry)
        pos += len(entry) + 2
        if pos >= maxwidth-1:
            pos = initpos
            out += ",\n" + " "*pos + entry
            pos += len(entry)
        else:
            out += ", " + entry
    out += group[1]
    return out


def dictstr(dictionary, js=False, maxwidth=78):
    if js: return json.dumps(dictionary, indent=4)
    out = ""
    maxlen = len(max(dictionary.keys(), key=lambda x: len(x)))
    for k,v in dictionary.items():
        out += f"\n{k+'  ':<{maxlen+2}}"
        if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
            out += wrap(v, maxwidth, maxlen+2)
        else:
            out += str(v)
    return out[1:]


def tableH(dictlist, fields=None, border=None):
    fields = fields or dictlist[0].keys()
    for f in fields:
        for d in dictlist:
            d[f] = d.get(f, None)
    widths = {k: len(k) for k in fields}
    for d in dictlist:
        for k in fields:
            widths[k] = max(widths[k], len(str(d[k])))
    out = " ".join((f"{k:^{w}.{w}}" for k,w in widths.items()))  # Heading
    if border:
        out += "\n" + " ".join((border*w for w in widths.values()))
    template = " ".join((f"{{{k}:<{w}.{w}}}" for k,w in widths.items()))
    for d in dictlist:
        out += "\n" + template.format(**{k:str(v) for k,v in d.items()})
    return out


def tableV(dictlist):
    columns = [[]] + [[] for d in dictlist]
    for i,d in enumerate(dictlist):
        for k,v in d.items():
            if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
                count = max((len(x[k]) for x in dictlist))
                v = iter(v)
                start = True
                for j in range(count):
                    if start: columns[0].append(k); start = False
                    else: columns[0].append("")
                    try: columns[i+1].append(str(next(v)))
                    except StopIteration: columns[i+1].append("")
            else:
                columns[0].append(k)
                columns[i+1].append(str(v))
    widths = [len(max(c, key=len)) for c in columns]
    template = "  ".join((f"{{:{w}.{w}}}" for w in widths))
    return "\n".join(template.format(*row) for row in zip(*columns))


class Charmap:
    def __init__(self):
        self.charmap = []
    def addtext(self, text, coords):
        x, y = coords
        cm = self.charmap
        cm.extend(([] for i in range(y-len(cm)+1)))
        for char in text:
            if char == "\n":
                y += 1
                x = coords[0]
            else:
                if y >= len(cm):
                    cm.extend(([] for i in range(y-len(cm)+1)))
                if x >= len(cm[y]):
                    cm[y].extend((" " for i in range(x-len(cm[y])+1)))
                cm[y][x] = char
                x += 1
    def __str__(self):
        return "\n".join(("".join(row) for row in self.charmap))


class TerminalMessage:
    def __init__(self, content="", ID=0):
        from types import SimpleNamespace as SN
        self.author = SN(name="admin", id=ID)
        self.content, self.attachments = self.get_attachments(content)
        self.guild = SN(name=None)
        self.channel = SN(name=None, send=self.send)
        self.edit = self.send
    
    async def send(self, content=""):
        content = content.replace("```","\n").replace("`","")
        print(content)
        return TerminalMessage(content)
    
    def get_attachments(self, text):
        import io
        attachments = []
        def msub(m):
            filename = m.group(1).strip('"')
            with open(filename, "rb") as f:
                buffer = io.BytesIO(f.read())
                buffer.read = to_async(buffer.read)
                buffer.url = filename
            attachments.append(buffer)
        text = re.sub(r"\sattach\s*=\s*(\".*?\"|\S+)", msub, text)
        return text, attachments


def terminal(callback):
    import asyncio
    ID = 0
    async def loop():
        nonlocal ID
        while True:
            try: text = input("> ")
            except KeyboardInterrupt: return
            if text in ("quit", "exit"): return
            if text.startswith("setid"): ID=int(text[len("setid"):])
            message = TerminalMessage(content=text, ID=ID)
            await callback(message)
    asyncio.run(loop())