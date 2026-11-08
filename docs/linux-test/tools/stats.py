import sys,re,statistics as st,glob,os
for f in sorted(glob.glob('/home/claude/evidence/timing/*.txt')):
    rows=[dict(re.findall(r'(\w+)=([\d.-]+)',l)) for l in open(f)]
    out=[os.path.basename(f)[:-4]+f" n={len(rows)}"]
    for k in ['shown','map','pageloaded','firstrender','content','settled']:
        v=[float(r[k]) for r in rows if k in r and float(r[k])>=0]
        if v: out.append(f"{k} med {st.median(v):.0f} worst {max(v):.0f} best {min(v):.0f}")
    print(" | ".join(out))
