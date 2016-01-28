from flask import Flask, g, render_template, request, redirect, jsonify
import time
from collections import namedtuple
import sqlite3
import os


app = Flask(__name__)


def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect('pastes.db')
    return g.sqlite_db


@app.teardown_appcontext
def close(e):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def format_paste_filename(id):
    return os.path.join(app.root_path, 'pastes', str(id))


def write_paste(title, author, body, edit_id):
    conn = get_db()
    c = conn.cursor()

    c.execute('''insert into pastes(title, author, inserted_at, edited_from)
    values (?, ?, ?, ?); ''',
              (title, author, int(time.time()), edit_id))
    id = c.execute('select last_insert_rowid() from pastes').fetchone()[0]
    conn.commit()
    with open(format_paste_filename(id), 'w') as f:
        f.write(body.encode('utf-8'))
    return id


Paste = namedtuple('Paste', 'id title author inserted_at body edited_from')


def sorted_pastes(pastes):
    return sorted(lambda a, b: -1 if a.id < b.id else 0 if a.id == b.id else 1,
                  pastes)


def read_paste(id):
    with open(format_paste_filename(id)) as f:
        body = unicode(f.read(), 'utf-8')

    title, author, inserted_at, edited_from = get_db().cursor().execute(
        '''
        select title, author, inserted_at, edited_from from pastes where id = ?
        ''', (id,)).fetchone()

    return Paste(id=id, title=title, author=author, inserted_at=inserted_at,
                 edited_from=edited_from, body=body)


def read_all_pastes():
    return (read_paste(int(id)) for id in os.listdir('pastes'))


def lookup_forms(*names):
    return tuple(map(lambda name: request.form[name].strip(), names))


def format_time(s):
    return time.strftime('%x %X', time.localtime(s))


def submit_page(edit_id=None):
    if request.method == 'POST':
        title, author, body = lookup_forms('title', 'author', 'body')
        return redirect('/pastes/' +
                        str(write_paste(title, author, body, edit_id)))
    else:
        paste = None
        if edit_id:
            try:
                paste = read_paste(edit_id)
            except IOError:
                pass
        return render_template('submit.html',
                               title=paste and paste.title,
                               author=paste and paste.author,
                               body=paste and paste.body)


@app.route('/', methods=['GET', 'POST'])
def home_page():
    return submit_page()


@app.route('/edit/<id>', methods=['GET', 'POST'])
def edit_paste(id):
    return submit_page(id)


@app.route('/search')
def search_page():
    return render_template('search.html')


@app.route('/_do_search')
def search():
    title = request.args.get('title', '')
    author = request.args.get('author', '')

    pastes = get_db().cursor().execute(
        'select id, title, author, inserted_at from pastes'
    ).fetchall()
    return jsonify(dict(matches=list(do_search(title, author, pastes))))


def do_search(title, author, pastes):
    everything = not author and not title
    for p in pastes:
        tmatch = title and p[1] == title
        amatch = author and p[2] == author
        if tmatch or amatch or everything:
            yield dict(
                id=p[0],
                title=p[1],
                author=p[2],
                inserted_at=format_time(p[3])
            )


@app.route('/pastes/<id>')
def paste_page(id):
    try:
        paste = read_paste(id)
        return render_template('paste.html',
                               title=paste.title,
                               author=paste.author,
                               time=format_time(paste.inserted_at),
                               edited_from=paste.edited_from,
                               body=paste.body,
                               id=id)
    except IOError:
        return render_template('paste_not_found.html')


Family = namedtuple('Family', 'paste children')


def familyToDict(f):
    return dict(
        paste=pasteToDict(f.paste),
        children=map(familyToDict, f.children)
    )


def pasteToDict(p):
    return dict(
        id=p.id,
        title=p.title,
        author=p.author,
        inserted_at=p.inserted_at,
        body=p.body,
        edited_from=p.edited_from
    )


@app.route('/family/<id>')
def family(id):
    try:
        id = int(id)
    except (ValueError, IOError):
        return render_template('paste_not_found.html')
    family = find_family(list(read_all_pastes()), id)
    return render_template('family.html', family=familyToDict(family))


def find_children(pastes_list, id):
    res = []
    for p in pastes_list:
        if (p.edited_from == id):
            res.append(p)
    return res


def find_family(pastes_list, id):
    # optimize me? this is weird
    pastes = {p.id: p for p in pastes_list}
    og = id  # OG stands for Original Glue
    while pastes[og].edited_from:
        og = int(pastes[id].edited_from)

    def recur(id):
        return Family(pastes[id],
                      map(lambda p: recur(p.id),
                          find_children(pastes_list, id)))
    return recur(id)


if __name__ == '__main__':
    app.run(debug=True)
