"""Create a disposable, explicitly labeled demo; never read Robbie's photo library."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import we

ROOT = Path(__file__).resolve().parent
SAMPLES = [
    ('photo-1519501025264-65ba15a82390', 'After the last train', 'A city skyline at night, lit windows against the dark sky'),
    ('photo-1477959858617-67f85cf4f1df', 'A place to begin', 'Dense city buildings seen from above'),
    ('photo-1480714378408-67cf0d13bc1b', 'Another way through', 'An urban landscape with streets and tall buildings'),
    ('photo-1449824913935-59a10b8d2000', 'Street-level signals', 'A city street lined with buildings'),
    ('photo-1514565131-fce0801e5785', 'Room for the horizon', 'A city skyline beneath an open sky'),
    ('photo-1519608487953-e999c86e7455', 'Between connections', 'A colorful nighttime landscape'),
]


def main():
    root = ROOT / 'workspace'
    if (root / 'content').exists():
        raise SystemExit('Demo workspace already exists; no overwrite performed')
    source = ROOT / 'demo-inputs'
    source.mkdir(exist_ok=True)
    def fetch(record):
        key, title, alt = record
        path = source / (key + '.jpg')
        if not path.exists():
            url = f'https://images.unsplash.com/{key}?auto=format&fit=max&w=2600&q=92'
            request = urllib.request.Request(url, headers={'User-Agent': 'WE-Corp-local-design-prototype/0.1'})
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read(15_000_000)
            path.write_bytes(raw)
        return path
    paths = list(ThreadPoolExecutor(max_workers=4).map(fetch, SAMPLES))
    we.initialize(root)
    we.write_json(root / 'content/site.json', {'name': 'WE CORP', 'tagline': 'Tools for a life of your own.', 'demo': True})
    (root / 'content/home.md').write_text('## You can do this too.\n\nWE is an invitation to use technology on your own terms: to make things, share knowledge, and build connections you have a say in.\n\nNot a promise of perfect independence. A practice of taking back a little more agency, together.\n\n**Own your files. Understand your tools. Leave when you choose.**\n')
    we.add_member(root, 'murmuur', 'murmuur', 'Photography / visual media / independent networks')
    meta = we.read_json(we.member_dir(root, 'murmuur') / 'member.json')
    meta['contact'] = 'demo-contact@example.test'
    we.write_json(we.member_dir(root, 'murmuur') / 'member.json', meta)
    (we.member_dir(root, 'murmuur') / 'bio.md').write_text('I am interested in the places where images, people and networks meet. In small tools that make room for a bigger life.\n\nThis is a **demonstration portfolio**, using reference photographs rather than my own work. The structure is ready for real projects and images.\n')
    for path, (_, title, alt) in zip(paths, SAMPLES):
        item = we.import_photo(root, 'murmuur', path, title, alt)
        we.set_photo(root, 'murmuur', item['id'], published=True, caption='Reference image from Unsplash / local design demonstration, not a photograph by murmuur.')
    entries = [
        ('posts', 'a-network-of-our-own', 'A network of our own', 'An invitation, not another platform to disappear into.', '2026-09-28', '## Start with the feeling\n\nWhat would technology look like if its success was measured by the room it left in your life?\n\nNot how long you stayed. Not how much you disclosed. Whether you could make something, understand it, and take it with you.\n\n> The point is not to become indispensable. The point is to help someone become capable.\n\n## A small beginning\n\nA shared folder. A local library. A place to leave a useful note. A network becomes meaningful through what people do together.\n\n### Files, not feeds\n\n- Write in a text editor you like.\n- Keep a copy outside the service.\n- Share deliberately.\n- Make leaving possible.\n\n```text\nwe post import murmuur first-note ./note.md --title "First note"\nwe publish\n```\n\nThis essay is sample copy for the prototype, not a published statement.\n'),
        ('posts', 'a-kit-for-going-places', 'A kit for going places', 'Portable access. Persistent work. Enough space to move.', '2026-09-24', '## Carry the connection, not the whole server\n\nA traveling kit can help you reach tools without turning every trip into a maintenance job.\n\nThe files should survive the laptop closing. The person using them should understand where they live.\n\nThis is demonstration writing for the interface.\n'),
        ('projects', 'we-field-node', 'WE / Field Node', 'A physical invitation into a shared digital space.', '2026-09-26', '## A prototype, not a deployed product\n\nA proposed portable gateway that makes independent networking tangible. A small device, a field manual, and an invitation to participate.\n\n### Design question\n\nCan the first interaction make someone feel capable rather than dependent on the operator?\n\n### What this demonstration shows\n\nThe portfolio structure supports a project description written in Markdown. This entry is illustrative, not evidence of a finished field-node product.\n'),
        ('projects', 'relay-desktop', 'Relay / A shared front door', 'A browser desktop connecting people with useful tools.', '2026-09-20', '## A place to begin\n\nRelay provides a desktop-style interface for accessing registered tools. Accounts and grants determine access; presentation is not the permission boundary.\n\nThis public website is independent of Relay and does not expose the private desktop.\n\nThis project text is placeholder copy, to be replaced with a reviewed case study.\n'),
    ]
    for kind, slug, title, summary, date, body in entries:
        path = we.create_entry(root, 'murmuur', kind, slug, title)
        meta, _ = we.read_entry(path)
        we.write_entry(path, {**meta, 'summary': summary, 'date': date, 'published': True}, body)
    we.create_entry(root, 'murmuur', 'posts', 'private-working-note', 'Unpublished working note')
    we.publish(root)
    we.write_json(ROOT / 'demo-inputs/sources.json', [{'file': p.name, 'source': f'https://images.unsplash.com/{r[0]}', 'purpose': 'Local reference only, not user photography or a license determination'} for p, r in zip(paths, SAMPLES)])
    print('Demo workspace initialized; reference photos processed; static site locally published.')


if __name__ == '__main__':
    main()
