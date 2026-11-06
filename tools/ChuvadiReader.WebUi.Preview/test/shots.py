import sys, os, asyncio
from playwright.async_api import async_playwright
S=os.environ.get('WEBUI_TEST_DIR','/tmp/chuvadi-webui-test'); OUT=os.path.join(S,'shots'); os.makedirs(OUT,exist_ok=True); D=os.path.join(S,'docs')
HAND='file://'+os.path.abspath(os.path.join(os.path.dirname(__file__),'../../../docs/design-handoff'))+'/Portal%20%26%20Android.dc.html'
# size name -> (width, height, preview server, touch)
SIZES={'desktop':(1280,720,'http://127.0.0.1:5101',False),'tablet':(1280,800,'http://127.0.0.1:5103',True),'phone':(390,844,'http://127.0.0.1:5104',True)}
async def settle(p, ms=900):
    await p.wait_for_load_state('networkidle'); await p.wait_for_timeout(ms)
async def handout(pw):
    b=await pw.chromium.launch(); p=await b.new_page(viewport={'width':1500,'height':1000})
    await p.goto(HAND); await settle(p,2500)
    for fid in ['12a','12b','12c']:
        await p.locator(f'[id="{fid}"]').screenshot(path=f'{OUT}/handout-{fid}.png')
    await b.close()
async def mine(pw, bname):
    bt=getattr(pw,bname); b=await bt.launch()
    errors=[]
    for sname,(w,h,WEB,touch) in SIZES.items():
        ctx=await b.new_context(viewport={'width':w,'height':h}, has_touch=touch and bname!='firefox'); p=await ctx.new_page()
        p.on('console', lambda m: errors.append(f'{bname}/{sname} console {m.type}: {m.text}') if m.type in ('error','warning') else None)
        p.on('pageerror', lambda e: errors.append(f'{bname}/{sname} pageerror: {e}'))
        await p.goto(WEB+'/_preview/sign-in'); await settle(p)
        await p.screenshot(path=f'{OUT}/{bname}-{sname}-signin.png', full_page=True)
        await p.goto(WEB+'/_preview/gate'); await settle(p)
        await p.screenshot(path=f'{OUT}/{bname}-{sname}-gate.png', full_page=True)
        await p.goto(WEB+'/_preview/open?path='+D+'/discharge-summary.pdf'); await settle(p,2500)
        await p.screenshot(path=f'{OUT}/{bname}-{sname}-reader.png')
        if sname=='phone':
            menu=p.locator('button[aria-label="More"]').first
            if await menu.count():
                await menu.click(); await p.wait_for_timeout(500)
                await p.screenshot(path=f'{OUT}/{bname}-{sname}-reader-menu.png')
                if not await p.locator('.ppa').count(): errors.append(f'{bname}/{sname}: no portal account block in the menu')
            else: errors.append(f'{bname}/{sname}: no phone menu button')
        else:
            chip=p.locator('.acct-chip')
            if await chip.count():
                await chip.click(); await p.wait_for_timeout(400)
                await p.screenshot(path=f'{OUT}/{bname}-{sname}-reader-acct.png')
            else: errors.append(f'{bname}/{sname}: no account chip')
        await ctx.close()
    await b.close(); return errors
async def main():
    async with async_playwright() as pw:
        if 'handout' in sys.argv: await handout(pw)
        errs=[]
        for bn in [a for a in sys.argv[1:] if a in ('chromium','firefox','webkit')]:
            errs+=await mine(pw,bn)
        print('\n'.join(errs) or 'no console errors')
asyncio.run(main())
