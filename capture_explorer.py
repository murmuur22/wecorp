"""Capture the directory prototype and execute real local operator workflows."""
from pathlib import Path
import subprocess
import tempfile
import json
import sys
import os
import shlex
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright
import explorer as ex
from cli import console, TERMINAL
from verify_capture import sheet

OUT=ex.CODE/'artifacts/explorer'
SHOTS=OUT/'screenshots'
BASE='http://127.0.0.1:8768'


def cli_capture(name,args,source=ex.DEFAULT_SOURCE,state=ex.DEFAULT_STATE,env=None,expected=0):
    target=OUT/'terminal'/(name+'.html');target.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([sys.executable,str(ex.CODE/'explorer.py'),'--source',str(source),'--state',str(state),'--export',str(target),*args],capture_output=True,text=True,env=env)
    target.with_suffix('.txt').write_text(result.stdout+result.stderr)
    assert result.returncode==expected,(args,result.stdout,result.stderr)
    return target


def board(name,title,items):
    width=1140; height=960
    canvas=Image.new('RGB',(width*2+48,height+90),'#0a0a0a')
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('/System/Library/Fonts/Menlo.ttc',18)
    draw.text((24,16),title,font=font,fill='#eeeeee')
    for i,(label,path) in enumerate(items):
        x=24+i*(width+12)
        draw.text((x,48),label,font=font,fill='#999999')
        image=Image.open(path).convert('RGB')
        # Crop only this overview; original full-page PNGs remain in the package.
        image=image.crop((0,0,min(width,image.width),min(height,image.height)))
        canvas.paste(image,(x,82))
    target=OUT/(name+'.jpg');canvas.save(target,quality=95);return target


def main():
    SHOTS.mkdir(parents=True,exist_ok=True)
    captures={}
    routes=[('home','/'),('portfolio','/@murmuur/'),('photography','/@murmuur/photography/'),('frames','/@murmuur/photography/city-at-night/'),('horizons','/@murmuur/photography/horizons/'),('writing','/@murmuur/writing/'),('note','/@murmuur/writing/independence/'),('work','/@murmuur/work/'),('project','/@murmuur/work/field-node/'),('contact','/@murmuur/contact/'),('manual','/manual/'),('keys','/manual/keys/')]
    for name,path in routes:
        captures['cli-'+name]=cli_capture('cli-'+name,['show',path])
    c=console();ex.render_terminal(ex.Catalog(ex.DEFAULT_SOURCE),'/@murmuur/',c,selected=2)
    selected=OUT/'terminal/cli-selected.html';selected.write_text(c.export_html(theme=TERMINAL,inline_styles=True));captures['cli-selected']=selected
    proof=Path(tempfile.mkdtemp(prefix='workflow-',dir=OUT))
    source=proof/'public';state=proof/'state'
    captures['cli-import-plan']=cli_capture('cli-import-plan',['import-tree',str(ex.DEFAULT_SOURCE),str(source)])
    assert not source.exists()
    captures['cli-import-apply']=cli_capture('cli-import-apply',['import-tree',str(ex.DEFAULT_SOURCE),str(source),'--apply'])
    assert not (source/'@murmuur/photography/images/unlinked.jpg').exists()
    captures['cli-new']=cli_capture('cli-new',['new','@murmuur/photography/new-study.md','--title','A new photographic study'],source,state)
    captures['cli-photo-import']=cli_capture('cli-photo-import',['photo-import',str(ex.CODE/'demo-inputs/photo-1449824913935-59a10b8d2000.jpg'),'@murmuur/photography/images/new.jpg'],source,state)
    editor=proof/'test_editor.py'
    editor.write_text('from pathlib import Path\nimport sys,os\np=Path(sys.argv[1]);p.write_text(os.environ["WE_EDITOR_TEXT"]);print("Editor save verified:",p.name)\n')
    env={**os.environ,'EDITOR':shlex.join([sys.executable,str(editor)]),'WE_EDITOR_TEXT':'# A new photographic study\n\n![A reference city street](images/new.jpg)\n\n[Another collection](city-at-night.md)\n'}
    captures['cli-edit']=cli_capture('cli-edit',['edit','@murmuur/photography/new-study.md'],source,state,env)
    assert 'images/new.jpg' in (source/'@murmuur/photography/new-study.md').read_text()
    captures['cli-head']=cli_capture('cli-head',['head','@murmuur','--depth','2'],source,state)
    captures['cli-validate']=cli_capture('cli-validate',['validate'],source,state)
    captures['cli-publish']=cli_capture('cli-publish',['publish'],source,state)
    first=(state/'current').resolve().name
    captures['cli-publish-second']=cli_capture('cli-publish-second',['publish'],source,state)
    captures['cli-rollback']=cli_capture('cli-rollback',['rollback',first],source,state)
    assert (state/'current').resolve().name==first
    (source/'broken.md').write_text('[Missing](not-a-page.md)')
    captures['cli-failed-build']=cli_capture('cli-failed-build',['publish'],source,state,expected=1)
    assert (state/'current').resolve().name==first
    captures['cli-status']=cli_capture('cli-status',['status'],source,state)
    errors=[]
    positions={}
    with sync_playwright() as p:
        browser=p.chromium.launch()
        page=browser.new_page(viewport={'width':1140,'height':960},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        for name,path in routes:
            assert page.goto(BASE+path).status==200
            for img in page.locator('.markdown img').all():img.scroll_into_view_if_needed();img.evaluate('(e)=>e.decode()')
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(SHOTS/('web-'+name+'.png')),full_page=True)
        page.goto(BASE+'/@murmuur/')
        positions={key:page.locator(key).bounding_box() for key in ('#header-bar','#directory-bar','.document-label')}
        page.keyboard.press('r')
        assert page.locator('.raw').is_visible()
        page.screenshot(path=str(SHOTS/'web-raw.png'),full_page=True)
        page.keyboard.press('r')
        page.keyboard.press('ArrowDown');page.keyboard.press('ArrowDown');page.keyboard.press('ArrowDown')
        page.screenshot(path=str(SHOTS/'web-selected.png'),full_page=True)
        page.locator('summary.entry-token').filter(has_text='photography/').click()
        assert page.locator('details.directory-menu[open]').count()>=1
        page.screenshot(path=str(SHOTS/'web-submenu.png'),full_page=True)
        page.goto(BASE+'/@murmuur/photography/city-at-night/')
        page.locator('[data-image="0"]').click()
        page.locator('#viewer-image').evaluate('(e)=>e.decode()')
        page.screenshot(path=str(SHOTS/'web-image-viewer.png'),full_page=True)
        page.keyboard.press('ArrowRight')
        assert page.locator('#image-position').inner_text()=='IMAGE 2 / 2'
        page.locator('#viewer-image').evaluate('(e)=>e.decode()')
        page.screenshot(path=str(SHOTS/'web-image-next.png'),full_page=True)
        page.keyboard.press('Escape')
        page.keyboard.press('?')
        page.screenshot(path=str(SHOTS/'web-help.png'),full_page=True)
        page.goto(BASE+'/@murmuur/')
        page.keyboard.press('/');page.keyboard.type('cd photography')
        page.screenshot(path=str(SHOTS/'web-command.png'),full_page=True)
        page.keyboard.press('Enter');page.wait_for_url('**/@murmuur/photography/')
        mobile=browser.new_page(viewport={'width':390,'height':844})
        mobile.goto(BASE+'/@murmuur/')
        mobile.screenshot(path=str(SHOTS/'web-mobile.png'),full_page=True)
        terminal=browser.new_page(viewport={'width':1140,'height':960})
        for name,target in captures.items():
            terminal.goto(target.as_uri())
            terminal.add_style_tag(content='body{margin:0;background:#0a0a0a;color:#eeeeee}pre{font:14px/1.65 Menlo,Consolas,monospace;max-width:calc(104ch + 1px);margin:24px auto;white-space:pre-wrap}code{font:inherit}')
            if name == 'cli-portfolio':
                # Fractional ch rounding must not wrap a full 104-column header.
                assert terminal.locator('code > span').first.bounding_box()['height'] < 23.1
            terminal.screenshot(path=str(SHOTS/(name+'.png')),full_page=True)
        browser.close()
    assert not errors,errors
    boards=[
        board('01-mirrored-interface','WE / THE SAME SHELL, TWO READERS',[('Browser / rendered Markdown',SHOTS/'web-portfolio.png'),('Actual CLI output / source Markdown',SHOTS/'cli-portfolio.png')]),
        board('02-raw-parity','WE / THE SAME DOCUMENT AND DIRECTORY',[('Browser / Raw mode',SHOTS/'web-raw.png'),('Actual CLI output / source Markdown',SHOTS/'cli-portfolio.png')]),
        board('03-photography','WE / LINKED PHOTOGRAPHS',[('A Markdown page containing photographs',SHOTS/'web-frames.png'),('Built-in viewer / arrows browse this page',SHOTS/'web-image-viewer.png')]),
        board('04-keyboard-navigation','WE / KEYBOARD FIRST',[('Current-directory menu / clickable files',SHOTS/'web-submenu.png'),('Navigation help / dynamic shortcuts',SHOTS/'web-help.png')]),
        board('05-publishing','WE / FILES TO A STATIC WEBSITE',[('Actual CLI / directory import plan',SHOTS/'cli-import-plan.png'),('Actual CLI / publication',SHOTS/'cli-publish.png')]),
    ]
    report={'cli_invocations':len(captures)-1,'web_routes_captured':len(routes),'pageerrors':errors,'relative_photo_viewer_verified':True,'import_excluded_unlinked_assets':True,'editor_save_verified':True,'rollback_read_back':True,'failed_build_preserved_output':True,'browser_chrome_positions':positions,'proof_workspace':str(proof),'boards':[str(p.relative_to(ex.CODE)) for p in boards]}
    (OUT/'capture-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
