import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen
src, out = sys.argv[1], sys.argv[2]
f=TTFont(src); gs=f.getGlyphSet(); gname=f.getBestCmap()[ord('ச')]
bp=BoundsPen(gs); gs[gname].draw(bp); x0,y0,x1,y1=bp.bounds
# measured ink box of the browser render at S=1024 (left,top,right,bottom)
L,T,R,B=307,271,717,611
sx=(R-L)/(x1-x0); sy=(B-T)/(y1-y0); s=(sx+sy)/2
print('glyph',gname,'units',bp.bounds,'scale x/y',round(sx,5),round(sy,5))
def path(S, ox=0, oy=0):
    k=S/1024*s
    pen=SVGPathPen(gs, ntos=lambda v: ('%.2f'%v).rstrip('0').rstrip('.'))
    # font y up -> svg y down; map font x0 -> L, y1 -> T
    tp=TransformPen(pen,(k,0,0,-k, ox+L*S/1024 - x0*k, oy+T*S/1024 + y1*k))
    gs[gname].draw(tp); return pen.getCommands()
S=1024
P=dict(bg='#8a3a1c', fg='#fbf7ec', leaf='#f2ead6')
def parts(S, ox=0, oy=0, bg=P['bg'], fg=P['fg'], leaf=P['leaf']):
    lh=round(S*0.11); hole=round(S*0.05); ht=round(S*0.03)
    lx=ox+0.12*S; lw=0.76*S; ly=oy+0.60*S
    hy=ly+ht+hole/2
    return (f'<rect x="{lx:g}" y="{ly:g}" width="{lw:g}" height="{lh}" rx="{lh/2:g}" fill="{leaf}" fill-opacity=".95"/>'
            f'<circle cx="{ox+0.24*S+hole/2:g}" cy="{hy:g}" r="{hole/2:g}" fill="{bg}"/>'
            f'<circle cx="{ox+S-0.24*S-hole/2:g}" cy="{hy:g}" r="{hole/2:g}" fill="{bg}"/>'
            f'<path d="{path(S,ox,oy)}" fill="{fg}"/>')
hdr='<?xml version="1.0" encoding="UTF-8"?>\n<!-- DRAFT for Arun\'s final check (A-09). Chuvadi app icon, from Brand Assets.dc.html: the letter ச (Tiro Tamil, OFL, converted to a path) on a binding-red tile with a palm-leaf strip and two binding holes. -->\n'
r=round(S*0.225)
open(out+'/icon-master.svg','w').write(hdr+f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><rect width="1024" height="1024" rx="{r}" fill="{P["bg"]}"/>{parts(S)}</svg>\n')
# Play Store icon: full-bleed square (Google applies its own mask)
open(out+'/icon-store-square.svg','w').write(hdr+f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024"><rect width="1024" height="1024" fill="{P["bg"]}"/>{parts(S)}</svg>\n')
# Adaptive icon: 108-unit canvas, the design tile mapped to the central 72 units (the visible area).
C=1536; pad=256
open(out+'/appicon_background.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{C}" height="{C}" viewBox="0 0 {C} {C}"><rect width="{C}" height="{C}" fill="{P["bg"]}"/></svg>\n')
open(out+'/appicon_foreground.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{C}" height="{C}" viewBox="0 0 {C} {C}">{parts(S,pad,pad)}</svg>\n')
# Monochrome (themed icons, Android 13+): one colour; the binding holes are cut out (even-odd).
def mono(S, ox, oy):
    lh=round(S*0.11); hole=round(S*0.05); ht=round(S*0.03)
    lx=ox+0.12*S; lw=0.76*S; ly=oy+0.60*S; rr=lh/2; hy=ly+ht+hole/2; hr=hole/2
    leaf=(f'M{lx+rr:g},{ly:g}H{lx+lw-rr:g}A{rr:g},{rr:g} 0 0 1 {lx+lw-rr:g},{ly+lh:g}H{lx+rr:g}A{rr:g},{rr:g} 0 0 1 {lx+rr:g},{ly:g}Z')
    def circ(cx): return f'M{cx-hr:g},{hy:g}a{hr:g},{hr:g} 0 1 0 {2*hr:g},0a{hr:g},{hr:g} 0 1 0 {-2*hr:g},0Z'
    holes=circ(ox+0.24*S+hr)+circ(ox+S-0.24*S-hr)
    return f'<path d="{leaf}{holes}" fill="#000000" fill-rule="evenodd"/><path d="{path(S,ox,oy)}" fill="#000000"/>'
open(out+'/appicon_monochrome.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{C}" height="{C}" viewBox="0 0 {C} {C}">{mono(S,pad,pad)}</svg>\n')
