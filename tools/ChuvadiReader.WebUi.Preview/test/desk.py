import sys, os, asyncio
from playwright.async_api import async_playwright
S=os.environ.get('WEBUI_TEST_DIR','/tmp/chuvadi-webui-test'); D=os.path.join(S,'docs'); tag=sys.argv[1]
OUT=os.path.join(S,'desk',tag); os.makedirs(OUT,exist_ok=True)
URL='http://127.0.0.1:5102'
PAGES=[('home','/'),('library','/library'),('settings','/settings'),('reader','/_preview/open?path='+D+'/discharge-summary.pdf')]
async def main():
    async with async_playwright() as pw:
        for bn in (sys.argv[2].split(',') if len(sys.argv)>2 else ['chromium','firefox','webkit']):
            b=await getattr(pw,bn).launch()
            for w,h in [(1280,720),(1024,768)]:
                ctx=await b.new_context(viewport={'width':w,'height':h}); p=await ctx.new_page()
                for name,path in PAGES:
                    await p.goto(URL+path); await p.wait_for_load_state('networkidle'); await p.wait_for_timeout(2500 if name=='reader' else 1000)
                    await p.add_style_tag(content='.sb-clock{visibility:hidden!important} *{caret-color:transparent!important}')
                    await p.mouse.move(w//2, h-5); await p.wait_for_timeout(300)
                    await p.screenshot(path=f'{OUT}/{bn}-{w}-{name}.png')
                    # hover the left bar to show expanded labels
                    await p.mouse.move(30, 300); await p.wait_for_timeout(500)
                    await p.screenshot(path=f'{OUT}/{bn}-{w}-{name}-hover.png')
                await ctx.close()
            await b.close()
asyncio.run(main())
