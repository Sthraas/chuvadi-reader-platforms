# CropBox (D-160): what each page of crop.pdf shows. Usage: t_crop.py <crop.pdf>
import helpers as h, json
from lt_base import *
F = sys.argv[1]
PIX = """var w=document.querySelector('.rpage-wrap[data-page="I"]'); if(!w) return 'no page';
var b=w.getBoundingClientRect(); var svg=[...w.querySelectorAll('svg')].find(s=>+((s.getAttribute('viewBox')||'').split(' ')[2])>100); if(!svg) return 'not drawn';
var vb=svg.getAttribute('viewBox'); var txt=svg.textContent.replace(/\\s+/g,' ').trim().slice(0,60); var im=svg.querySelector('image');
var xml=new XMLSerializer().serializeToString(svg); if(!/xmlns=/.test(xml.slice(0,200))) xml=xml.replace('<svg','<svg xmlns="http://www.w3.org/2000/svg"');
return new Promise(res=>{var i=new Image(); i.onload=()=>{var W=400,H=Math.round(400*b.height/b.width); var c=document.createElement('canvas'); c.width=W; c.height=H; var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,W,H); x.drawImage(i,0,0,W,H);
 var d=x.getImageData(0,0,W,H).data, g=0; for(var k=0;k<d.length;k+=4){ if(d[k]<80&&d[k+1]>110&&d[k+2]<80) g++; }
 function at(fx,fy){var px=Math.round(fx*W), py=Math.round(fy*H), o=(py*W+px)*4; var r=d[o],gg=d[o+1],bl=d[o+2]; return r>200&&gg<80&&bl<80?'red':bl>200&&r<80&&gg<80?'blue':gg>110&&r<80?'green':r>230&&gg>230&&bl>230?'white':'other';}
 res({box:Math.round(b.width)+'x'+Math.round(b.height), ratio:+(b.width/b.height).toFixed(3), viewBox:vb, image:!!im, text:txt, green:g,
      corners:{bl:at(0.05,0.96), tr:at(0.95,0.04), tl:at(0.05,0.04), br:at(0.95,0.96)}});};
 i.onerror=()=>res({box:Math.round(b.width)+'x'+Math.round(b.height), ratio:+(b.width/b.height).toFixed(3), viewBox:vb, text:txt, err:'svg not decodable'}); i.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(xml);})"""
a = App(APP, EV + "/crop", display=":75"); h.bind(a); a.start_display()
try:
    a.launch(); time.sleep(4); a.send("open " + F, timeout=15); time.sleep(4)
    n = int(a.js("return document.querySelectorAll('.rpage-wrap').length"))
    for i in range(n):
        a.js(f"var b=document.querySelector('.tb-pg-box'); b.value='{i+1}'; b.dispatchEvent(new Event('change')); return 1"); time.sleep(2.5)
        print("CROP page", i + 1, json.dumps(a.js(PIX.replace('"I"', f'"{i}"'))), flush=True)
    a.shot("crop-last")
finally: a.stop()
