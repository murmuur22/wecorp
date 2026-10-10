"""Create a separate directory prototype fixture. Do not touch the first workspace."""
from pathlib import Path
import shutil
import json
import argparse
import urllib.request
from PIL import Image
import explorer as ex

REFERENCES = {'street.jpg':'photo-1519501025264-65ba15a82390.jpg', 'neon.jpg':'photo-1519608487953-e999c86e7455.jpg', 'skyline.jpg':'photo-1514565131-fce0801e5785.jpg', 'city.jpg':'photo-1477959858617-67f85cf4f1df.jpg', 'unlinked.jpg':'photo-1449824913935-59a10b8d2000.jpg'}


def prepare_photos(inputs, download=False):
    inputs = Path(inputs)
    missing = [name for name in REFERENCES.values() if not (inputs / name).is_file()]
    if missing and not download:
        raise ValueError('Reference photos are missing. Run with --download-photos to fetch Unsplash samples, or populate demo-inputs yourself.')
    if not missing:
        return
    inputs.mkdir(parents=True, exist_ok=True)
    for name in missing:
        photo_id = Path(name).stem
        url = f'https://images.unsplash.com/{photo_id}?auto=format&fit=max&w=2600&q=92'
        request = urllib.request.Request(url, headers={'User-Agent':'WE-Corp-demo/0.2'})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read(15_000_001)
        if len(raw) > 15_000_000:
            raise ValueError('Reference download exceeds 15 MB')
        import io
        with Image.open(io.BytesIO(raw)) as image:
            image.verify()
        destination = inputs / name
        with destination.open('xb') as output:
            output.write(raw)


def main():
    parser = argparse.ArgumentParser(description='Create the local directory demo without overwriting a workspace')
    parser.add_argument('--download-photos', action='store_true', help='Explicitly download reference photographs from Unsplash')
    args = parser.parse_args()
    source = ex.DEFAULT_SOURCE
    if source.exists():
        raise SystemExit('Directory demo already exists; no overwrite')
    prepare_photos(ex.CODE / 'demo-inputs', download=args.download_photos)
    source.mkdir(parents=True)
    pages = {
        'index.md': '# A network of our own.\n\nTechnology should give you room to live.\nNot another company to live inside.\n\nWE is an invitation to make useful things, understand them,\nand help someone else become capable too.\n\n- Own your files.\n- Share deliberately.\n- Leave when you choose.\n\n[Read the idea](about.md) · [Learn the controls](manual/keys.md)\n\nSomeone gave you a member address? Use the command line below.\nExample: `cd @murmuur`\n\n> LOCAL DEMONSTRATION / sample copy, not a final public statement.\n',
        'about.md': '# Less dependence. More possibility.\n\nA community network is not just a cable or a VPN.\nIt is people making decisions about the tools they share.\n\n## A practice, not a purity test\n\nHardware, software and internet access still have outside dependencies.\nThe direction is more agency, portable work, and the ability to leave.\n\n[Return home](index.md)\n',
        '@murmuur/index.md': '# murmuur\n\nPhotography / visual media / independent networks\n\nI am interested in the places where images, people and networks meet.\nIn small tools that make room for a bigger life.\n\n## Open a directory\n\n- [Photography](photography/index.md)\n- [Writing](writing/index.md)\n- [Selected work](work/index.md)\n- [Contact](contact.md)\n\nThis is a demonstration portfolio with reference photographs.\nThe photographs are not work by murmuur.\n',
        '@murmuur/contact.md': '# Start a conversation.\n\nThe idea on one side. A person on the other.\n\n```text\nwecorp.network\nwecorp.network/@murmuur\n```\n\nContact placeholder: [demo-contact@example.test](mailto:demo-contact@example.test)\n\n[Back to portfolio](index.md)\n',
        '@murmuur/photography/index.md': '# Photography\n\nA photograph can be a way of paying attention.\nThese are local reference images for evaluating the interface.\n\n## Collections\n\n- [City at night](city-at-night.md)\n- [Open horizons](horizons.md)\n\nImages do not appear in the file bar. They appear where a Markdown\ndocument references them, in the order the document gives them.\n\n[Related field note](../writing/independence.md)\n',
        '@murmuur/photography/city-at-night.md': '# City at night\n\nReference photographs / interface demonstration / not my own work.\nClick a frame to browse the images referenced by this document.\n\n![A rainy city street with reflected headlights and a blue sky](images/street.jpg)\n\n*After the last train / reference image.*\n\n![A neon-lit nighttime street with purple and blue storefront lights](images/neon.jpg)\n\n*Between connections / reference image.*\n\n[Related writing](../writing/independence.md#files-not-feeds)\n',
        '@murmuur/photography/horizons.md': '# Open horizons\n\nTwo reference frames. One Markdown document.\n\n![City buildings beneath an open sky](images/skyline.jpg)\n\n![Buildings seen from above in a dense city landscape](images/city.jpg)\n\n[City at night](city-at-night.md)\n',
        '@murmuur/writing/index.md': '# Field notes\n\nPlain text you can take with you.\n\n- [Independence](independence.md)\n- [A network is a relationship](network.md)\n- [Notes on moving](notes.md)\n',
        '@murmuur/writing/independence.md': '# Independence\n\nNot a perfect escape from every dependency.\nEnough agency to decide what stays in your life.\n\n## Files, not feeds\n\nA directory can be a place to think without being a platform\nsomeone else has to keep giving you permission to use.\n\nWrite in Neovim, another editor, or a notes application.\nKeep the Markdown, the photographs, and the relationships between them.\n\n[Look at the photographs](../photography/city-at-night.md)\n\n[Read about WireGuard elsewhere](https://www.wireguard.com/)\n\nThis is sample writing for the local prototype.\n',
        '@murmuur/writing/network.md': '# A network is a relationship\n\nThe person presenting WE should not be the only person\nwho knows how to keep it alive.\n\n[Another note](notes.md) · [Return to the collection](index.md)\n',
        '@murmuur/writing/notes.md': '# Notes on moving\n\nCarry your connection, not a constant maintenance obligation.\n\nThis is sample copy, not a deployed service promise.\n',
        '@murmuur/work/index.md': '# Selected work\n\n- [WE Field Node / proposed concept](field-node.md)\n\nThe directory is the organization. The documents explain the work.\n',
        '@murmuur/work/field-node.md': '# WE Field Node\n\nA proposed portable invitation into a shared digital space.\n\n## The question\n\nCan the first encounter make someone feel capable,\nrather than dependent on the person running it?\n\nThis entry is demonstration copy, not evidence of a finished product.\n',
        'manual/index.md': '# A directory you can publish\n\nStart with Markdown and the files it references.\n\n- [Keyboard controls](keys.md)\n- [Publishing and recovery](publishing.md)\n\n[Download the field note](attachments/field-guide.txt)\n',
        'manual/keys.md': '# Keyboard controls\n\nThe header is your pinned navigation.\nThe next bar is the current directory: your `ls`.\nThe document lives below both.\n\n- Press the key printed beside an entry to open it.\n- Use arrows and Enter when there are too many entries for single keys.\n- `u` goes up a directory. `Escape` goes back.\n- `/` focuses command entry. Typing does not trigger navigation.\n- `r` switches between rendered and raw Markdown in the browser.\n- `k` toggles single-letter shortcuts; ordinary Tab navigation remains.\n\n## Commands\n\n```text\nls\ncd photography\nopen city-at-night.md\ncd ..\nhome\n```\n\nThese same navigation commands work in the actual terminal.\n',
        'manual/publishing.md': '# Publishing and recovery\n\nThe public website stays static.\nNavigation is discovered during a build, not from the VPS filesystem.\n\n```text\npython explorer.py validate\npython explorer.py publish\npython explorer.py rollback RELEASE_ID\n```\n\nA failed build leaves the previous public release selected.\nRollback restores public output, not your working files.\n\nUnlisted pages are still public by address. Drafts are excluded.\n',
        '@murmuur/writing/private-draft.md': '---\n{"published": false}\n---\n# Private working draft\n\nThis must never enter the public output.\n',
    }
    for relative, content in pages.items():
        p = source/relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(content)
    config = source/'.head/navigation.json'; config.parent.mkdir()
    config.write_text(json.dumps({'brand':'WE CORP','pins':[{'label':'About','path':'about.md'},{'label':'Manual','path':'manual/'}],'submenu_depth':1}, indent=2))
    member_config = source/'@murmuur/.head/navigation.json'; member_config.parent.mkdir()
    member_config.write_text('{"listed":false}')
    attachment = source/'manual/attachments/field-guide.txt'; attachment.parent.mkdir()
    attachment.write_text('WE / demo field guide\nKeep a copy. Understand the boundary. Help someone become capable.\n')
    images = source/'@murmuur/photography/images'; images.mkdir()
    for name, original in REFERENCES.items():
        shutil.copyfile(ex.CODE/'demo-inputs'/original, images/name)
    release = ex.publish_directory(source, ex.DEFAULT_STATE)
    print(json.dumps({'source':str(source),'published_release':release,'fixture_pages':len(pages),'references':'Unsplash samples from explicit download or local demo cache'},indent=2))


if __name__ == '__main__': main()
